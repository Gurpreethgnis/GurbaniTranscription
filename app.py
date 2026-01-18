"""
Flask backend server for audio transcription application.
"""
import os
import time
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import config
from whisper_service import get_whisper_service
from file_manager import FileManager
from audio_utils import get_audio_duration
from orchestrator import Orchestrator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

# Initialize services
file_manager = FileManager()
whisper_service = None
orchestrator = None

# Progress tracking for active transcriptions
progress_store = {}


def init_whisper():
    """Initialize Whisper service (lazy loading)."""
    global whisper_service
    if whisper_service is None:
        try:
            whisper_service = get_whisper_service()
        except Exception as e:
            print(f"Warning: Failed to initialize Whisper: {e}")
            whisper_service = None
    return whisper_service


def init_orchestrator():
    """Initialize Orchestrator service (lazy loading)."""
    global orchestrator
    if orchestrator is None:
        try:
            print("Initializing Orchestrator (this may take a moment)...")
            orchestrator = Orchestrator()
            print("Orchestrator initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize Orchestrator: {e}")
            import traceback
            traceback.print_exc()
            orchestrator = None
    return orchestrator


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('templates', 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.route('/status', methods=['GET'])
def status():
    """Health check and status endpoint."""
    service = init_whisper()
    return jsonify({
        "status": "ok",
        "whisper_loaded": service is not None and service.is_model_loaded(),
        "model_size": config.WHISPER_MODEL_SIZE if service else None
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload audio file to server."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check file extension
    filename = secure_filename(file.filename)
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in config.SUPPORTED_FORMATS:
        return jsonify({
            "error": f"Unsupported file format. Supported: {', '.join(config.SUPPORTED_FORMATS)}"
        }), 400
    
    # Save file
    file_path = config.UPLOAD_DIR / filename
    
    # Handle duplicate filenames
    counter = 1
    original_path = file_path
    while file_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        file_path = config.UPLOAD_DIR / f"{stem}_{counter}{suffix}"
        counter += 1
    
    file.save(file_path)
    
    # Check if already processed
    file_hash = file_manager.get_file_hash(file_path)
    is_processed, log_entry = file_manager.is_file_processed(filename, file_hash)
    
    return jsonify({
        "filename": file_path.name,
        "original_filename": filename,
        "file_path": str(file_path),
        "already_processed": is_processed,
        "log_entry": log_entry
    })


@app.route('/transcribe', methods=['POST'])
def transcribe_file():
    """Transcribe a single audio file with progress tracking."""
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({"error": "Filename required"}), 400
    
    filename = data['filename']
    file_path = config.UPLOAD_DIR / filename
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    # Initialize Whisper if needed
    service = init_whisper()
    if not service:
        return jsonify({"error": "Whisper service not available"}), 500
    
    try:
        # Check if already processed
        file_hash = file_manager.get_file_hash(file_path)
        is_processed, log_entry = file_manager.is_file_processed(filename, file_hash)
        
        if is_processed and log_entry and log_entry.get("status") == "success":
            # Return existing transcription - but verify files actually exist
            text_path, json_path = file_manager.get_output_paths(filename)
            
            # If files don't exist, reprocess the file
            if not text_path or not json_path:
                # Files missing, remove from log and reprocess
                log_data = file_manager.load_log()
                log_data = [e for e in log_data if e.get("filename") != filename]
                file_manager.save_log(log_data)
                # Continue to process below
            else:
                # Files exist, return them
                # Read transcription text from file
                transcription_text = ""
                if text_path.exists():
                    with open(text_path, "r", encoding="utf-8") as f:
                        transcription_text = f.read()
                
                return jsonify({
                    "status": "success",
                    "message": "File already processed",
                    "transcription": transcription_text,
                    "language": log_entry.get("language_detected"),
                    "text_file": str(text_path),
                    "json_file": str(json_path),
                    "log_entry": log_entry
                })
        
        # Get audio duration for progress estimation
        audio_duration = get_audio_duration(file_path)
        start_time = time.time()
        
        # Progress callback
        progress_data = {
            "filename": filename,
            "progress": 0,
            "status": "processing",
            "message": "Starting transcription...",
            "elapsed_time": 0,
            "estimated_remaining": None,
            "audio_duration": audio_duration
        }
        progress_store[filename] = progress_data
        
        def progress_callback(update):
            """Update progress store with latest information."""
            elapsed = time.time() - start_time
            progress_data["elapsed_time"] = elapsed
            progress_data["progress"] = update.get("progress", 0)
            progress_data["message"] = update.get("message", "Transcribing...")
            
            # Estimate remaining time
            if progress_data["progress"] > 0 and progress_data["progress"] < 100:
                estimated_total = elapsed / (progress_data["progress"] / 100)
                progress_data["estimated_remaining"] = max(0, estimated_total - elapsed)
            elif audio_duration:
                # Rough estimate: Whisper typically processes at 0.5-2x realtime
                # Use conservative 1x realtime estimate
                progress_data["estimated_remaining"] = max(0, audio_duration - elapsed)
        
        # Transcribe with progress callback
        result = whisper_service.transcribe_with_language_detection(
            file_path,
            language_hints=config.LANGUAGE_HINTS,
            progress_callback=progress_callback
        )
        
        transcription_text = result.get("text", "")
        language = result.get("language", "unknown")
        total_time = time.time() - start_time
        
        # Save transcription
        metadata = {
            "language": language,
            "language_probability": result.get("language_probability"),
            "segments": result.get("segments", []),
            "processing_time": total_time
        }
        text_path, json_path = file_manager.save_transcription(
            filename,
            transcription_text,
            metadata
        )
        
        # Update log
        log_entry = file_manager.add_log_entry(
            filename=filename,
            status="success",
            transcription=transcription_text,
            language=language,
            file_hash=file_hash,
            model_used=config.WHISPER_MODEL_SIZE
        )
        
        # Update progress to complete
        progress_data["progress"] = 100
        progress_data["status"] = "completed"
        progress_data["message"] = "Transcription complete"
        progress_data["estimated_remaining"] = 0
        
        return jsonify({
            "status": "success",
            "transcription": transcription_text,
            "language": language,
            "text_file": str(text_path),
            "json_file": str(json_path),
            "log_entry": log_entry,
            "processing_time": total_time
        })
        
    except Exception as e:
        # Log error
        file_hash = file_manager.get_file_hash(file_path)
        file_manager.add_log_entry(
            filename=filename,
            status="error",
            error=str(e),
            file_hash=file_hash
        )
        
        # Update progress with error
        if filename in progress_store:
            progress_store[filename]["status"] = "error"
            progress_store[filename]["message"] = f"Error: {str(e)}"
        
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
    finally:
        # Clean up progress after a delay (keep for 30 seconds)
        def cleanup():
            time.sleep(30)
            if filename in progress_store:
                del progress_store[filename]
        threading.Thread(target=cleanup, daemon=True).start()


@app.route('/transcribe-v2', methods=['POST'])
def transcribe_file_v2():
    """Transcribe a single audio file using the orchestrator pipeline (Phase 1)."""
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({"error": "Filename required"}), 400
    
    filename = data['filename']
    file_path = config.UPLOAD_DIR / filename
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    # Initialize orchestrator if needed
    try:
        orch = init_orchestrator()
        if not orch:
            error_msg = "Orchestrator service not available. Check server logs for initialization errors."
            print(f"ERROR: {error_msg}")
            return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Failed to initialize orchestrator: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500
    
    try:
        # Check if already processed
        file_hash = file_manager.get_file_hash(file_path)
        is_processed, log_entry = file_manager.is_file_processed(filename, file_hash)
        
        if is_processed and log_entry and log_entry.get("status") == "success":
            # Try to load existing orchestrator output
            text_path, json_path = file_manager.get_output_paths(filename)
            if text_path and json_path:
                import json as json_lib
                with open(json_path, "r", encoding="utf-8") as f:
                    existing_data = json_lib.load(f)
                    # Check if it's orchestrator format
                    if "segments" in existing_data.get("metadata", {}):
                        return jsonify({
                            "status": "success",
                            "message": "File already processed",
                            "result": existing_data.get("metadata", {}),
                            "text_file": str(text_path),
                            "json_file": str(json_path)
                        })
        
        # Get audio duration for progress estimation
        audio_duration = get_audio_duration(file_path)
        start_time = time.time()
        
        # Progress callback
        progress_data = {
            "filename": filename,
            "progress": 0,
            "status": "processing",
            "message": "Starting orchestrated transcription...",
            "elapsed_time": 0,
            "estimated_remaining": None,
            "audio_duration": audio_duration
        }
        progress_store[filename] = progress_data
        
        # Transcribe using orchestrator
        print(f"Starting transcription of {filename} using orchestrator...")
        try:
            result = orch.transcribe_file(file_path, mode="batch")
            print(f"Transcription completed for {filename}")
        except Exception as transcribe_error:
            error_msg = f"Transcription failed: {str(transcribe_error)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            raise transcribe_error
        
        total_time = time.time() - start_time
        
        # Convert result to dict for JSON serialization
        result_dict = result.to_dict()
        
        # Save transcription
        # Extract full text for text file
        full_text = result.transcription.get("gurmukhi", "")
        if not full_text:
            # Fallback: concatenate segment texts
            full_text = " ".join(seg.text for seg in result.segments)
        
        metadata = {
            "language": result.segments[0].language if result.segments else "unknown",
            "segments": [seg.to_dict() for seg in result.segments],
            "transcription": result.transcription,
            "metrics": result.metrics,
            "processing_time": total_time,
            "mode": "orchestrated_v2"
        }
        
        text_path, json_path = file_manager.save_transcription(
            filename,
            full_text,
            metadata
        )
        
        # Update log
        log_entry = file_manager.add_log_entry(
            filename=filename,
            status="success",
            transcription=full_text,
            language=result.segments[0].language if result.segments else "unknown",
            file_hash=file_hash,
            model_used=f"{config.WHISPER_MODEL_SIZE} (orchestrated)"
        )
        
        # Update progress to complete
        progress_data["progress"] = 100
        progress_data["status"] = "completed"
        progress_data["message"] = "Transcription complete"
        progress_data["estimated_remaining"] = 0
        
        return jsonify({
            "status": "success",
            "result": result_dict,
            "text_file": str(text_path),
            "json_file": str(json_path),
            "log_entry": log_entry,
            "processing_time": total_time
        })
        
    except Exception as e:
        # Log error
        file_hash = file_manager.get_file_hash(file_path)
        file_manager.add_log_entry(
            filename=filename,
            status="error",
            error=str(e),
            file_hash=file_hash
        )
        
        # Update progress with error
        if filename in progress_store:
            progress_store[filename]["status"] = "error"
            progress_store[filename]["message"] = f"Error: {str(e)}"
        
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
    finally:
        # Clean up progress after a delay (keep for 30 seconds)
        def cleanup():
            time.sleep(30)
            if filename in progress_store:
                del progress_store[filename]
        threading.Thread(target=cleanup, daemon=True).start()


@app.route('/transcribe-batch', methods=['POST'])
def transcribe_batch():
    """Transcribe multiple files in batch."""
    data = request.get_json()
    
    if not data or 'filenames' not in data:
        return jsonify({"error": "Filenames list required"}), 400
    
    filenames = data['filenames']
    if not isinstance(filenames, list):
        return jsonify({"error": "Filenames must be a list"}), 400
    
    # Initialize Whisper if needed
    service = init_whisper()
    if not service:
        return jsonify({"error": "Whisper service not available"}), 500
    
    results = []
    
    for filename in filenames:
        file_path = config.UPLOAD_DIR / filename
        
        if not file_path.exists():
            results.append({
                "filename": filename,
                "status": "error",
                "error": "File not found"
            })
            continue
        
        try:
            # Check if already processed
            file_hash = file_manager.get_file_hash(file_path)
            is_processed, log_entry = file_manager.is_file_processed(filename, file_hash)
            
            if is_processed and log_entry and log_entry.get("status") == "success":
                results.append({
                    "filename": filename,
                    "status": "skipped",
                    "message": "Already processed",
                    "log_entry": log_entry
                })
                continue
            
            # Transcribe
            result = whisper_service.transcribe_with_language_detection(
                file_path,
                language_hints=config.LANGUAGE_HINTS
            )
            
            transcription_text = result.get("text", "")
            language = result.get("language", "unknown")
            
            # Save transcription
            metadata = {
                "language": language,
                "language_probability": result.get("language_probability"),
                "segments": result.get("segments", [])
            }
            text_path, json_path = file_manager.save_transcription(
                filename,
                transcription_text,
                metadata
            )
            
            # Update log
            log_entry = file_manager.add_log_entry(
                filename=filename,
                status="success",
                transcription=transcription_text,
                language=language,
                file_hash=file_hash,
                model_used=config.WHISPER_MODEL_SIZE
            )
            
            results.append({
                "filename": filename,
                "status": "success",
                "transcription": transcription_text,
                "language": language,
                "text_file": str(text_path),
                "json_file": str(json_path)
            })
            
        except Exception as e:
            # Log error
            file_hash = file_manager.get_file_hash(file_path)
            file_manager.add_log_entry(
                filename=filename,
                status="error",
                error=str(e),
                file_hash=file_hash
            )
            
            results.append({
                "filename": filename,
                "status": "error",
                "error": str(e)
            })
    
    return jsonify({
        "status": "completed",
        "results": results,
        "total": len(filenames),
        "successful": sum(1 for r in results if r.get("status") == "success"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped")
    })


@app.route('/progress/<filename>', methods=['GET'])
def get_progress(filename):
    """Get progress for a specific file transcription."""
    if filename in progress_store:
        return jsonify(progress_store[filename])
    return jsonify({"error": "No progress data found"}), 404


@app.route('/log', methods=['GET'])
def get_log():
    """Get the processing log."""
    log_data = file_manager.load_log()
    return jsonify({
        "log": log_data,
        "total_entries": len(log_data)
    })


@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a transcription file."""
    from urllib.parse import unquote
    
    # Decode URL encoding (e.g., %20 -> space)
    decoded_filename = unquote(filename)
    # Security: ensure filename doesn't contain path traversal
    safe_filename = Path(decoded_filename).name
    
    # Check if it's a text or json file
    file_path = None
    base_dir = None
    
    if safe_filename.endswith('.txt'):
        base_dir = config.TRANSCRIPTIONS_DIR
        file_path = base_dir / safe_filename
    elif safe_filename.endswith('.json'):
        base_dir = config.JSON_DIR
        file_path = base_dir / safe_filename
    
    # If exact match not found, try with underscores (spaces -> underscores)
    if file_path and not file_path.exists():
        alt_filename = safe_filename.replace(' ', '_')
        if base_dir:
            file_path = base_dir / alt_filename
    
    # If still not found, search for files with similar base name
    if file_path and not file_path.exists() and base_dir:
        base_name = Path(safe_filename).stem
        # Try to find any file with similar name
        for existing_file in base_dir.glob(f"{base_name}*"):
            if existing_file.is_file():
                file_path = existing_file
                break
    
    if file_path and file_path.exists() and file_path.is_file():
        return send_file(str(file_path), as_attachment=True, download_name=safe_filename)
    
    return jsonify({"error": f"File not found: {safe_filename}"}), 404


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size limit exceeded."""
    return jsonify({
        "error": f"File too large. Maximum size: {config.MAX_FILE_SIZE_MB}MB"
    }), 413


@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def handle_server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Test GPU first if test script exists
    try:
        import test_gpu
        print("Running GPU compatibility test...")
        gpu_ok = test_gpu.test_gpu()
        if not gpu_ok:
            print("WARNING: GPU test failed, but continuing with initialization...")
    except ImportError:
        print("GPU test script not found, skipping test...")
    except Exception as e:
        print(f"GPU test error (continuing anyway): {e}")
    
    print("\nInitializing Whisper service...")
    init_whisper()
    print(f"Starting server on http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
