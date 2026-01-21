"""
Flask backend server for audio transcription application.

Uses the Orchestrator pipeline for all transcription operations.
"""
import time
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import config
from utils.file_manager import FileManager
from audio.audio_utils import get_audio_duration
from core.orchestrator import Orchestrator
from ui.websocket_server import WebSocketServer

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

# Initialize services
file_manager = FileManager()
orchestrator = None
live_orchestrator = None  # Phase 6: Separate orchestrator for live mode
websocket_server = None  # Phase 6: WebSocket server

# Progress tracking for active transcriptions
progress_store = {}

# Phase 6: Live session tracking
live_sessions = {}  # session_id -> {start_time, chunks_processed}


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


def init_live_orchestrator(websocket_server_instance):
    """
    Initialize Orchestrator for live mode with WebSocket callback.
    
    Phase 6: Live mode orchestrator with event callbacks.
    """
    global live_orchestrator
    if live_orchestrator is None:
        try:
            print("Initializing Live Orchestrator (this may take a moment)...")
            
            def live_callback(event_type: str, data: dict):
                """Callback for live mode events."""
                if not websocket_server_instance:
                    return
                
                session_id = data.get('session_id', 'unknown')
                
                if event_type == 'draft':
                    websocket_server_instance.emit_draft_caption(
                        session_id=session_id,
                        segment_id=data.get('segment_id', 'unknown'),
                        start=data.get('start', 0.0),
                        end=data.get('end', 0.0),
                        text=data.get('text', ''),
                        confidence=data.get('confidence', 0.0),
                        gurmukhi=data.get('gurmukhi'),
                        roman=data.get('roman')
                    )
                elif event_type == 'verified':
                    websocket_server_instance.emit_verified_update(
                        session_id=session_id,
                        segment_id=data.get('segment_id', 'unknown'),
                        start=data.get('start', 0.0),
                        end=data.get('end', 0.0),
                        gurmukhi=data.get('gurmukhi', ''),
                        roman=data.get('roman', ''),
                        confidence=data.get('confidence', 0.0),
                        quote_match=data.get('quote_match'),
                        needs_review=data.get('needs_review', False)
                    )
                elif event_type == 'error':
                    websocket_server_instance.emit_error(
                        session_id=session_id,
                        message=data.get('message', 'Unknown error'),
                        error_type=data.get('error_type', 'processing')
                    )
            
            live_orchestrator = Orchestrator(live_callback=live_callback)
            print("Live Orchestrator initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize Live Orchestrator: {e}")
            import traceback
            traceback.print_exc()
            live_orchestrator = None
    return live_orchestrator


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/live')
def live():
    """Serve the live transcription page."""
    return render_template('live.html')


@app.route('/shabad')
def shabad():
    """Serve the shabad mode page (Phase 15)."""
    return render_template('shabad.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.route('/status', methods=['GET'])
def status():
    """Health check and status endpoint."""
    orch = init_orchestrator()
    return jsonify({
        "status": "ok",
        "orchestrator_loaded": orch is not None,
        "model_size": config.WHISPER_MODEL_SIZE
    })


# ============================================
# SHABAD MODE API ENDPOINTS (Phase 15)
# ============================================

@app.route('/api/praman/similar', methods=['POST'])
def get_similar_pramans():
    """
    Get semantically similar pramans for a given Gurmukhi text.
    
    Request JSON:
    {
        "text": "ਹਰਿ ਕਾ ਨਾਮੁ ਧਿਆਇ ਕੈ ਹੋਹੁ ਹਰਿਆ ਭਾਈ",
        "count": 5,
        "exclude_line_ids": ["123", "456"]  // Optional
    }
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field"}), 400
        
        text = data.get('text', '')
        count = data.get('count', config.PRAMAN_DEFAULT_SIMILAR_COUNT)
        exclude_ids = set(data.get('exclude_line_ids', []))
        
        # Get semantic praman service
        from services.semantic_praman import get_semantic_praman_service
        service = get_semantic_praman_service()
        
        # Ensure index is built
        if service.index is None:
            from scripture.sggs_db import SGGSDatabase
            sggs_db = SGGSDatabase()
            service.build_index(sggs_db=sggs_db)
        
        # Find similar pramans
        results = service.find_similar_pramans(text, top_k=count, exclude_line_ids=exclude_ids)
        
        return jsonify({
            "query_text": text,
            "pramans": [
                {
                    "line_id": p.line_id,
                    "gurmukhi": p.gurmukhi,
                    "roman": p.roman,
                    "source": p.source,
                    "ang": p.ang,
                    "raag": p.raag,
                    "author": p.author,
                    "similarity_score": p.similarity_score,
                    "shared_keywords": p.shared_keywords
                }
                for p in results
            ]
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error getting similar pramans: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/praman/dissimilar', methods=['POST'])
def get_dissimilar_pramans():
    """
    Get thematically contrasting pramans for a given Gurmukhi text.
    
    Request JSON:
    {
        "text": "ਹਰਿ ਕਾ ਨਾਮੁ ਧਿਆਇ ਕੈ ਹੋਹੁ ਹਰਿਆ ਭਾਈ",
        "count": 3,
        "exclude_line_ids": ["123", "456"]  // Optional
    }
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field"}), 400
        
        text = data.get('text', '')
        count = data.get('count', config.PRAMAN_DEFAULT_DISSIMILAR_COUNT)
        exclude_ids = set(data.get('exclude_line_ids', []))
        
        # Get semantic praman service
        from services.semantic_praman import get_semantic_praman_service
        service = get_semantic_praman_service()
        
        # Ensure index is built
        if service.index is None:
            from scripture.sggs_db import SGGSDatabase
            sggs_db = SGGSDatabase()
            service.build_index(sggs_db=sggs_db)
        
        # Find dissimilar pramans
        results = service.find_dissimilar_pramans(text, top_k=count, exclude_line_ids=exclude_ids)
        
        return jsonify({
            "query_text": text,
            "pramans": [
                {
                    "line_id": p.line_id,
                    "gurmukhi": p.gurmukhi,
                    "roman": p.roman,
                    "source": p.source,
                    "ang": p.ang,
                    "raag": p.raag,
                    "author": p.author,
                    "similarity_score": p.similarity_score,
                    "shared_keywords": p.shared_keywords
                }
                for p in results
            ]
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error getting dissimilar pramans: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/praman/search', methods=['POST'])
def search_pramans():
    """
    Search for both similar and dissimilar pramans.
    
    Request JSON:
    {
        "text": "ਹਰਿ ਕਾ ਨਾਮੁ ਧਿਆਇ ਕੈ ਹੋਹੁ ਹਰਿਆ ਭਾਈ",
        "similar_count": 5,
        "dissimilar_count": 3,
        "current_shabad_id": "optional_shabad_id"
    }
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field"}), 400
        
        text = data.get('text', '')
        similar_count = data.get('similar_count', config.PRAMAN_DEFAULT_SIMILAR_COUNT)
        dissimilar_count = data.get('dissimilar_count', config.PRAMAN_DEFAULT_DISSIMILAR_COUNT)
        current_shabad_id = data.get('current_shabad_id')
        
        # Get semantic praman service
        from services.semantic_praman import get_semantic_praman_service
        service = get_semantic_praman_service()
        
        # Ensure index is built
        if service.index is None:
            from scripture.sggs_db import SGGSDatabase
            sggs_db = SGGSDatabase()
            service.build_index(sggs_db=sggs_db)
        
        # Search pramans
        result = service.search_pramans(
            text,
            similar_count=similar_count,
            dissimilar_count=dissimilar_count,
            exclude_same_shabad=bool(current_shabad_id),
            current_shabad_id=current_shabad_id
        )
        
        return jsonify({
            "query_text": result.query_text,
            "query_keywords": result.query_keywords,
            "similar_pramans": [
                {
                    "line_id": p.line_id,
                    "gurmukhi": p.gurmukhi,
                    "roman": p.roman,
                    "source": p.source,
                    "ang": p.ang,
                    "raag": p.raag,
                    "author": p.author,
                    "similarity_score": p.similarity_score,
                    "shared_keywords": p.shared_keywords
                }
                for p in result.similar_pramans
            ],
            "dissimilar_pramans": [
                {
                    "line_id": p.line_id,
                    "gurmukhi": p.gurmukhi,
                    "roman": p.roman,
                    "source": p.source,
                    "ang": p.ang,
                    "raag": p.raag,
                    "author": p.author,
                    "similarity_score": p.similarity_score,
                    "shared_keywords": p.shared_keywords
                }
                for p in result.dissimilar_pramans
            ]
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error searching pramans: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


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
    """
    Transcribe a single audio file.
    
    DEPRECATED: This route now redirects to /transcribe-v2 which uses the
    full orchestrator pipeline. Kept for backwards compatibility.
    """
    # Simply delegate to the v2 endpoint
    return transcribe_file_v2()


@app.route('/transcribe-v2', methods=['POST'])
def transcribe_file_v2():
    """Transcribe a single audio file using the orchestrator pipeline."""
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
            "current_step": "initializing",
            "step_progress": 0,
            "step_details": None,
            "status": "processing",
            "message": "Starting orchestrated transcription...",
            "elapsed_time": 0,
            "estimated_remaining": None,
            "audio_duration": audio_duration
        }
        progress_store[filename] = progress_data
        
        # Parse processing options from request
        processing_options = data.get('processing_options', {})
        
        # Parse domain mode options
        domain_mode = data.get('domain_mode', 'sggs')
        strict_gurmukhi = data.get('strict_gurmukhi', True)
        
        # Create progress callback
        def progress_callback(step: str, step_progress: int, overall_progress: int, message: str, details: Optional[dict]):
            """Update progress store with step information."""
            elapsed = time.time() - start_time
            progress_data["current_step"] = step
            progress_data["step_progress"] = step_progress
            progress_data["progress"] = overall_progress
            progress_data["message"] = message
            progress_data["elapsed_time"] = elapsed
            progress_data["step_details"] = details
            
            # Estimate remaining time
            if overall_progress > 0 and overall_progress < 100:
                estimated_total = elapsed / (overall_progress / 100)
                progress_data["estimated_remaining"] = max(0, estimated_total - elapsed)
            elif audio_duration:
                progress_data["estimated_remaining"] = max(0, audio_duration - elapsed)
        
        # Transcribe using orchestrator
        print(f"Starting transcription of {filename} using orchestrator...")
        print(f"Domain mode: {domain_mode}, strict Gurmukhi: {strict_gurmukhi}")
        if processing_options:
            print(f"Processing options: {processing_options}")
        try:
            result = orch.transcribe_file(
                file_path, 
                mode="batch", 
                processing_options=processing_options, 
                progress_callback=progress_callback,
                domain_mode=domain_mode,
                strict_gurmukhi=strict_gurmukhi
            )
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
    """Transcribe multiple files in batch using the orchestrator pipeline."""
    data = request.get_json()
    
    if not data or 'filenames' not in data:
        return jsonify({"error": "Filenames list required"}), 400
    
    filenames = data['filenames']
    if not isinstance(filenames, list):
        return jsonify({"error": "Filenames must be a list"}), 400
    
    # Initialize orchestrator if needed
    orch = init_orchestrator()
    if not orch:
        return jsonify({"error": "Orchestrator service not available"}), 500
    
    results = []
    processing_options = data.get('processing_options', {})
    
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
            
            # Transcribe using orchestrator
            result = orch.transcribe_file(file_path, mode="batch", processing_options=processing_options)
            
            # Extract transcription
            full_text = result.transcription.get("gurmukhi", "")
            if not full_text:
                full_text = " ".join(seg.text for seg in result.segments)
            
            language = result.segments[0].language if result.segments else "unknown"
            
            # Save transcription
            metadata = {
                "language": language,
                "segments": [seg.to_dict() for seg in result.segments],
                "transcription": result.transcription,
                "metrics": result.metrics,
                "mode": "orchestrated_batch"
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
                language=language,
                file_hash=file_hash,
                model_used=f"{config.WHISPER_MODEL_SIZE} (orchestrated)"
            )
            
            results.append({
                "filename": filename,
                "status": "success",
                "transcription": full_text,
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


@app.route('/history')
def history():
    """History page showing all processed transcriptions."""
    return render_template('history.html')


@app.route('/settings')
def settings():
    """Settings page for ASR provider configuration."""
    return render_template('settings.html')


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get available ASR providers and their capabilities."""
    from asr.provider_registry import get_registry
    
    registry = get_registry()
    capabilities = registry.get_capabilities()
    
    return jsonify(capabilities)


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings."""
    import json as json_lib
    
    settings_file = config.SETTINGS_FILE
    
    # Default settings
    default_settings = {
        "primaryProvider": getattr(config, 'ASR_PRIMARY_PROVIDER', 'whisper'),
        "fallbackProvider": getattr(config, 'ASR_FALLBACK_PROVIDER', ''),
        "whisper": {
            "model": getattr(config, 'WHISPER_MODEL_SIZE', 'large')
        },
        "indicconformer": {
            "model": getattr(config, 'INDICCONFORMER_MODEL', 'ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large'),
            "language": getattr(config, 'INDICCONFORMER_LANGUAGE', 'pa')
        },
        "wav2vec2": {
            "model": getattr(config, 'WAV2VEC2_MODEL', 'Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10')
        },
        "commercial": {
            "enabled": getattr(config, 'USE_COMMERCIAL', False),
            "apiKey": "",  # Don't expose API key
            "provider": getattr(config, 'COMMERCIAL_PROVIDER', 'elevenlabs')
        },
        "processing": {
            "denoising": getattr(config, 'ENABLE_DENOISING', False),
            "denoiseBackend": getattr(config, 'DENOISE_BACKEND', 'noisereduce'),
            "enableFusion": True,
            "fusionThreshold": getattr(config, 'FUSION_AGREEMENT_THRESHOLD', 0.85)
        },
        "domain": {
            "mode": getattr(config, 'DOMAIN_MODE', 'sggs'),
            "strictGurmukhi": getattr(config, 'STRICT_GURMUKHI', True),
            "enableCorrection": getattr(config, 'ENABLE_DOMAIN_CORRECTION', True),
            "scriptPurityThreshold": getattr(config, 'SCRIPT_PURITY_THRESHOLD', 0.95),
            "latinRatioThreshold": getattr(config, 'LATIN_RATIO_THRESHOLD', 0.02),
            "oovRatioThreshold": getattr(config, 'OOV_RATIO_THRESHOLD', 0.35)
        }
    }
    
    # Try to load saved settings
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json_lib.load(f)
                # Merge saved with defaults (saved takes precedence)
                for key, value in saved_settings.items():
                    if key in default_settings:
                        if isinstance(value, dict) and isinstance(default_settings[key], dict):
                            default_settings[key].update(value)
                        else:
                            default_settings[key] = value
        except Exception as e:
            print(f"Failed to load settings file: {e}")
    
    return jsonify(default_settings)


@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save settings to file."""
    import json as json_lib
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    settings_file = config.SETTINGS_FILE
    
    # Ensure data directory exists
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Don't save sensitive data like API keys in plain text
        safe_data = data.copy()
        if 'commercial' in safe_data and 'apiKey' in safe_data['commercial']:
            # Store API key securely (in env var or encrypted file)
            api_key = safe_data['commercial'].get('apiKey', '')
            if api_key:
                # For now, just mask it in saved file
                safe_data['commercial']['apiKey'] = '***masked***'
                # Could also update environment or secure storage here
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json_lib.dump(safe_data, f, indent=2)
        
        # Update orchestrator if running
        orch = init_orchestrator()
        if orch and 'primaryProvider' in data:
            try:
                orch.set_primary_provider(data['primaryProvider'])
            except Exception as e:
                print(f"Failed to update orchestrator provider: {e}")
        
        # Update domain settings if provided
        if orch and 'domain' in data:
            try:
                domain_settings = data['domain']
                orch.set_domain_mode(
                    domain_settings.get('mode', 'sggs'),
                    domain_settings.get('strictGurmukhi', True)
                )
            except Exception as e:
                print(f"Failed to update domain settings: {e}")
        
        return jsonify({"status": "success", "message": "Settings saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/domain-settings', methods=['GET'])
def get_domain_settings():
    """Get current domain language prioritization settings."""
    orch = init_orchestrator()
    if orch:
        return jsonify(orch.get_domain_mode())
    
    # Return defaults if orchestrator not initialized
    return jsonify({
        'domain_mode': getattr(config, 'DOMAIN_MODE', 'sggs'),
        'strict_gurmukhi': getattr(config, 'STRICT_GURMUKHI', True),
        'enable_domain_correction': getattr(config, 'ENABLE_DOMAIN_CORRECTION', True),
    })


@app.route('/api/domain-settings', methods=['POST'])
def set_domain_settings():
    """Update domain language prioritization settings."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    orch = init_orchestrator()
    if not orch:
        return jsonify({"error": "Orchestrator not available"}), 500
    
    try:
        mode = data.get('domain_mode', 'sggs')
        strict = data.get('strict_gurmukhi', True)
        
        orch.set_domain_mode(mode, strict)
        
        return jsonify({
            "status": "success",
            "message": f"Domain mode set to {mode}, strict_gurmukhi: {strict}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/test-commercial', methods=['POST'])
def test_commercial_api():
    """Test commercial API connection."""
    data = request.get_json()
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({"success": False, "error": "No API key provided"})
    
    try:
        from asr.asr_commercial import ASRCommercial
        
        # Create temporary provider with test key
        provider = ASRCommercial(api_key=api_key)
        
        # Test connection
        if provider.check_api_health():
            quota = provider.get_remaining_quota()
            return jsonify({
                "success": True,
                "message": "Connection successful",
                "quota": quota
            })
        else:
            return jsonify({
                "success": False,
                "error": "API connection failed"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
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


@app.route('/format-document', methods=['POST'])
def format_document():
    """Format a transcription result into a structured document."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        filename = data.get("filename")
        if not filename:
            return jsonify({"error": "filename is required"}), 400
        
        # Get transcription result from saved JSON
        text_path, json_path = file_manager.get_output_paths(filename)
        if not json_path or not json_path.exists():
            return jsonify({"error": f"Transcription not found for {filename}"}), 404
        
        # Load transcription result
        import json as json_lib
        with open(json_path, 'r', encoding='utf-8') as f:
            saved_data = json_lib.load(f)
        
        # Reconstruct TranscriptionResult from saved data
        from models import TranscriptionResult, ProcessedSegment
        segments = [
            ProcessedSegment(**seg_data)
            for seg_data in saved_data.get("metadata", {}).get("segments", [])
        ]
        
        result = TranscriptionResult(
            filename=filename,
            segments=segments,
            transcription=saved_data.get("transcription", {}),
            metrics=saved_data.get("metadata", {})
        )
        
        # Format document
        orch = init_orchestrator()
        if not orch:
            return jsonify({"error": "Orchestrator not available"}), 500
        
        formatted_doc = orch.format_document(result)
        
        return jsonify({
            "status": "success",
            "document": formatted_doc.to_dict()
        })
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error formatting document: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/export/<filename>/<format>', methods=['GET'])
def export_document(filename: str, format: str):
    """
    Export formatted document in specified format.
    
    Args:
        filename: Original audio filename
        format: Export format (txt, json, markdown, html, docx, pdf)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from urllib.parse import unquote
        # Decode URL-encoded filename
        filename = unquote(filename)
        format_lower = format.lower()
        
        # Handle 'txt' as raw text download
        if format_lower == 'txt':
            text_path, _ = file_manager.get_output_paths(filename)
            if not text_path or not text_path.exists():
                logger.warning(f"Text file not found for: {filename}")
                return jsonify({"error": f"Text transcription not found for {filename}"}), 404
            
            return send_file(
                str(text_path),
                as_attachment=True,
                download_name=text_path.name,
                mimetype="text/plain; charset=utf-8"
            )
        
        # Handle 'json-raw' as raw JSON download (simple segments)
        if format_lower == 'json-raw':
            _, json_path = file_manager.get_output_paths(filename)
            if not json_path or not json_path.exists():
                logger.warning(f"JSON file not found for: {filename}")
                return jsonify({"error": f"JSON transcription not found for {filename}"}), 404
            
            return send_file(
                str(json_path),
                as_attachment=True,
                download_name=json_path.name,
                mimetype="application/json"
            )
        
        # Validate format for formatted exports
        supported_formats = ["json", "markdown", "html", "docx", "pdf"]
        if format_lower not in supported_formats:
            return jsonify({
                "error": f"Unsupported format: {format}",
                "supported_formats": ["txt", "json-raw"] + supported_formats
            }), 400
        
        # Get transcription result
        text_path, json_path = file_manager.get_output_paths(filename)
        if not json_path:
            logger.warning(f"No JSON file found for: {filename}")
            # Try to list available files for debugging
            available_files = list(config.JSON_DIR.glob("*.json"))
            logger.debug(f"Available JSON files: {[f.name for f in available_files[:10]]}")
            return jsonify({
                "error": f"Transcription not found for {filename}",
                "hint": "The file may not have been processed yet or the filename may have changed."
            }), 404
        
        # Load and reconstruct TranscriptionResult
        import json as json_lib
        with open(json_path, 'r', encoding='utf-8') as f:
            saved_data = json_lib.load(f)
        
        from models import TranscriptionResult, ProcessedSegment
        
        # Handle both old and new JSON formats
        metadata = saved_data.get("metadata", {})
        segments_data = metadata.get("segments", [])
        
        # If no segments in metadata, try to create minimal segment from transcription
        if not segments_data:
            logger.warning(f"No segments found in metadata for {filename}, creating minimal segment")
            transcription_text = saved_data.get("transcription", "")
            if isinstance(transcription_text, dict):
                transcription_text = transcription_text.get("gurmukhi", "") or transcription_text.get("roman", "")
            segments_data = [{
                "segment_id": "seg_0",
                "text": transcription_text,
                "start": 0.0,
                "end": 0.0,
                "language": metadata.get("language", "pa"),
                "confidence": 0.8
            }]
        
        segments = []
        for seg_data in segments_data:
            try:
                segments.append(ProcessedSegment(**seg_data))
            except Exception as seg_error:
                logger.warning(f"Failed to parse segment: {seg_error}")
                continue
        
        # Get transcription dict
        transcription = saved_data.get("transcription", {})
        if isinstance(transcription, str):
            transcription = {"gurmukhi": transcription, "roman": ""}
        
        result = TranscriptionResult(
            filename=filename,
            segments=segments,
            transcription=transcription,
            metrics=metadata
        )
        
        # Format document
        orch = init_orchestrator()
        if not orch:
            return jsonify({"error": "Orchestrator not available. Please try again later."}), 500
        
        formatted_doc = orch.format_document(result)
        
        # Export to requested format
        from exports import ExportManager
        from exports.json_exporter import JSONExporter
        from exports.markdown_exporter import MarkdownExporter
        from exports.html_exporter import HTMLExporter
        
        export_manager = ExportManager()
        export_manager.register_exporter("json", JSONExporter())
        export_manager.register_exporter("markdown", MarkdownExporter())
        export_manager.register_exporter("html", HTMLExporter())
        
        # Register optional exporters if available
        try:
            from exports.docx_exporter import DOCXExporter
            export_manager.register_exporter("docx", DOCXExporter())
        except ImportError as e:
            logger.debug(f"DOCX exporter not available: {e}")
            if format_lower == "docx":
                return jsonify({"error": "DOCX export not available. Install python-docx package."}), 501
        except Exception as e:
            logger.warning(f"Failed to register DOCX exporter: {e}")
            if format_lower == "docx":
                return jsonify({"error": f"DOCX export failed to initialize: {e}"}), 500
        
        try:
            from exports.pdf_exporter import PDFExporter
            export_manager.register_exporter("pdf", PDFExporter())
        except ImportError as e:
            logger.debug(f"PDF exporter not available: {e}")
            if format_lower == "pdf":
                return jsonify({"error": "PDF export not available. Install required PDF packages."}), 501
        except Exception as e:
            logger.warning(f"Failed to register PDF exporter: {e}")
            if format_lower == "pdf":
                return jsonify({"error": f"PDF export failed to initialize: {e}"}), 500
        
        # Get output path - use the stem of the actual found file
        base_name = json_path.stem  # Use the actual file stem, not the requested filename
        output_path = config.FORMATTED_DOCS_DIR / f"{base_name}"
        
        # Export
        exported_path = export_manager.export(formatted_doc, format_lower, output_path)
        
        logger.info(f"Successfully exported {filename} to {format_lower}: {exported_path}")
        
        # Return file
        return send_file(
            str(exported_path),
            as_attachment=True,
            download_name=exported_path.name,
            mimetype={
                "json": "application/json",
                "markdown": "text/markdown",
                "html": "text/html",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "pdf": "application/pdf"
            }.get(format_lower, "application/octet-stream")
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Error exporting document '{filename}' to {format}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


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
    
    # Lazy-load orchestrator on first request to speed up startup
    print(f"\nOrchestrator will be initialized on first request (using {config.WHISPER_MODEL_SIZE} model)...")
    
    # Phase 6: Initialize WebSocket server and live orchestrator
    print("\nInitializing WebSocket server for live mode...")
    websocket_server = WebSocketServer(app, orchestrator_callback=None, shabad_callback=None)
    
    # Initialize live orchestrator with WebSocket callback
    def handle_audio_chunk(audio_bytes: bytes, session_id: str, chunk_data: dict):
        """Handle audio chunk from WebSocket client."""
        live_orch = init_live_orchestrator(websocket_server)
        if not live_orch:
            websocket_server.emit_error(session_id, "Live orchestrator not available")
            return
        
        # Track session
        if session_id not in live_sessions:
            live_sessions[session_id] = {
                'start_time': time.time(),
                'chunks_processed': 0
            }
        
        # Process audio chunk
        start_time = chunk_data.get('start_time', 0.0)
        end_time = chunk_data.get('end_time', start_time + 1.0)
        
        # Store session_id in data for callback
        chunk_data['session_id'] = session_id
        
        # Process in background thread to avoid blocking
        def process_chunk():
            try:
                result = live_orch.process_live_audio_chunk(
                    audio_bytes=audio_bytes,
                    start_time=start_time,
                    end_time=end_time,
                    session_id=session_id
                )
                live_sessions[session_id]['chunks_processed'] += 1
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error processing live chunk: {e}", exc_info=True)
                websocket_server.emit_error(session_id, f"Processing error: {str(e)}")
        
        thread = threading.Thread(target=process_chunk)
        thread.daemon = True
        thread.start()
    
    # Phase 15: Shabad mode audio chunk handler
    def handle_shabad_audio_chunk(audio_bytes: bytes, session_id: str, chunk_data: dict):
        """Handle audio chunk for shabad mode with praman suggestions."""
        live_orch = init_live_orchestrator(websocket_server)
        if not live_orch:
            websocket_server.emit_error(session_id, "Shabad orchestrator not available")
            return None
        
        # Track session
        if session_id not in live_sessions:
            live_sessions[session_id] = {
                'start_time': time.time(),
                'chunks_processed': 0,
                'mode': 'shabad'
            }
        
        # Process audio chunk
        start_time = chunk_data.get('start_time', 0.0)
        end_time = chunk_data.get('end_time', start_time + 2.0)  # 2 second chunks for shabad
        similar_count = chunk_data.get('similar_count', config.PRAMAN_DEFAULT_SIMILAR_COUNT)
        dissimilar_count = chunk_data.get('dissimilar_count', config.PRAMAN_DEFAULT_DISSIMILAR_COUNT)
        
        # Process in background thread to avoid blocking
        def process_shabad_chunk():
            try:
                result = live_orch.process_shabad_audio_chunk(
                    audio_bytes=audio_bytes,
                    start_time=start_time,
                    end_time=end_time,
                    session_id=session_id,
                    similar_count=similar_count,
                    dissimilar_count=dissimilar_count
                )
                live_sessions[session_id]['chunks_processed'] += 1
                
                # Emit shabad update via WebSocket
                if result:
                    websocket_server.emit_shabad_full_update(session_id, result)
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error processing shabad chunk: {e}", exc_info=True)
                websocket_server.emit_error(session_id, f"Shabad processing error: {str(e)}")
        
        thread = threading.Thread(target=process_shabad_chunk)
        thread.daemon = True
        thread.start()
        
        return None  # Results sent via WebSocket
    
    # Update WebSocket server callbacks
    websocket_server.orchestrator_callback = handle_audio_chunk
    websocket_server.shabad_callback = handle_shabad_audio_chunk
    
    print(f"Starting server with WebSocket support on http://{config.HOST}:{config.PORT}")
    websocket_server.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
