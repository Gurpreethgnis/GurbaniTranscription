"""
ASR-A: Whisper-based Automatic Speech Recognition.

This is the primary ASR engine using faster-whisper with support for
chunked processing and forced language per segment.
"""
import os
from pathlib import Path
from typing import Optional, List
import config
from core.models import AudioChunk, ASRResult, Segment

def detect_device():
    """Detect available device (CUDA GPU or CPU)."""
    require_gpu = getattr(config, "REQUIRE_GPU", False)
    # Check for environment variable to force CPU mode
    force_cpu = os.getenv("FORCE_CPU", "false").lower() == "true"
    if force_cpu:
        if require_gpu:
            raise RuntimeError("FORCE_CPU is set but REQUIRE_GPU=true. Refusing CPU fallback.")
        print("FORCE_CPU environment variable set, using CPU mode")
        return "cpu", "CPU (forced)"
    
    try:
        import torch
        
        if not torch.cuda.is_available():
            if require_gpu:
                raise RuntimeError("CUDA is not available but REQUIRE_GPU=true.")
            print("CUDA is not available, using CPU")
            return "cpu", "CPU"
        
        device_name = torch.cuda.get_device_name(0)
        device_props = torch.cuda.get_device_properties(0)
        compute_cap = f"sm_{device_props.major}{device_props.minor}"
        
        # Get supported architectures
        arch_list = torch.cuda.get_arch_list()
        print(f"GPU detected: {device_name} (Compute: {compute_cap})")
        print(f"PyTorch CUDA version: {torch.version.cuda}")
        print(f"Supported architectures: {arch_list}")
        
        # Check if compute capability is supported
        if compute_cap not in arch_list:
            print(f"WARNING: {compute_cap} not in supported architectures!")
            print("This may cause 'no kernel image available' errors.")
            print("Attempting GPU operations anyway...")
        
        # Test GPU compatibility with actual operations
        try:
            # Test tensor creation and computation
            test_tensor = torch.randn(10, 10, device="cuda")
            result = torch.matmul(test_tensor, test_tensor)
            result_mean = result.mean().item()
            del test_tensor, result
            torch.cuda.empty_cache()
            
            print(f"✓ GPU compatibility test passed (test result: {result_mean:.4f})")
            return "cuda", device_name
            
        except RuntimeError as e:
            error_msg = str(e).lower()
            if "no kernel image" in error_msg or "cuda error" in error_msg:
                if require_gpu:
                    raise RuntimeError(
                        "GPU compatibility test failed and REQUIRE_GPU=true. "
                        "Install a compatible PyTorch/CUDA build for this GPU."
                    )
                print(f"[ERROR] GPU compatibility test failed: {e}")
                print("Falling back to CPU mode.")
                print("To fix: Use PyTorch nightly with CUDA 12.8+ for RTX 50 series support")
                return "cpu", "CPU (CUDA incompatible)"
            else:
                # Re-raise if it's a different error
                raise
        
    except ImportError:
        if require_gpu:
            raise RuntimeError("PyTorch is not installed but REQUIRE_GPU=true.")
        print("PyTorch not available, using CPU")
        return "cpu", "CPU"
    except Exception as e:
        print(f"Warning: Error detecting device, using CPU: {e}")
        return "cpu", "CPU"

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("ERROR: faster-whisper is not installed. Install with: pip install faster-whisper")


class ASRWhisper:
    """
    ASR-A: Whisper-based ASR engine.
    
    Supports chunked processing with forced language per segment.
    """
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-A Whisper service.
        
        Args:
            model_size: Whisper model size (defaults to config.WHISPER_MODEL_SIZE)
        """
        self.model_size = model_size or config.WHISPER_MODEL_SIZE
        self.model = None
        self.device, self.device_name = detect_device()
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model."""
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. Install with: pip install faster-whisper"
            )
        
        try:
            # Determine compute type based on device
            if self.device == "cuda":
                compute_type = "float16"  # Use FP16 for GPU (faster, less memory)
                print(f"Loading ASR-A (Whisper) model: {self.model_size} on GPU ({self.device_name})")
            else:
                compute_type = "int8"  # Use INT8 for CPU (faster on CPU)
                print(f"Loading ASR-A (Whisper) model: {self.model_size} on CPU")
            
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4 if self.device == "cpu" else 0
            )
            
            print(f"ASR-A model {self.model_size} loaded successfully on {self.device.upper()}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ASR-A Whisper model: {str(e)}")
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code to force (e.g., 'pa', 'en')
                     If None, will use route to determine language
            route: Route string (e.g., 'punjabi_speech', 'english_speech')
                  Used to determine language if language is None
        
        Returns:
            ASRResult with transcription and segments
        """
        # Determine language from route if not provided
        if language is None and route:
            route_to_lang = {
                'punjabi_speech': 'pa',
                'english_speech': 'en',
                'scripture_quote_likely': 'pa',  # Gurbani is in Punjabi/Sant Bhasha
                'mixed': None  # Auto-detect
            }
            language = route_to_lang.get(route)
        
        # For chunked audio, we need to extract the chunk first
        # For now, we'll transcribe the full file but use timestamps
        # In a production system, you might want to extract chunks to temp files
        audio_path = chunk.audio_path
        
        # Transcribe with faster-whisper
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            beam_size=5,
            vad_filter=False,  # Disable VAD since we're already chunking
            word_timestamps=False,
        )
        
        # Filter segments to only include those within chunk time range
        chunk_segments = []
        full_text = ""
        
        for segment in segments:
            # Check if segment overlaps with chunk
            if (segment.start < chunk.end_time and segment.end > chunk.start_time):
                # Adjust timestamps relative to chunk start
                adjusted_start = max(0, segment.start - chunk.start_time)
                adjusted_end = min(chunk.duration, segment.end - chunk.start_time)
                
                # Get confidence from segment (if available)
                confidence = getattr(segment, 'no_speech_prob', 0.0)
                # Convert no_speech_prob to confidence (inverse)
                confidence = 1.0 - confidence if confidence is not None else 0.8
                
                chunk_segments.append(Segment(
                    start=adjusted_start,
                    end=adjusted_end,
                    text=segment.text.strip(),
                    confidence=confidence,
                    language=info.language
                ))
                full_text += segment.text + " "
        
        # Calculate overall confidence (average of segment confidences)
        overall_confidence = (
            sum(seg.confidence for seg in chunk_segments) / len(chunk_segments)
            if chunk_segments else 0.0
        )
        
        return ASRResult(
            text=full_text.strip(),
            language=info.language,
            confidence=overall_confidence,
            segments=chunk_segments,
            engine="asr_a_whisper",
            language_probability=getattr(info, 'language_probability', None)
        )
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code to force (e.g., 'pa', 'en'), or None for auto-detect
        
        Returns:
            ASRResult with transcription and segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
                beam_size=5,
                vad_filter=True,  # Use VAD for full-file transcription
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
                word_timestamps=False,
            )
            
            # Collect segments
            segment_list = []
            full_text = ""
            
            for segment in segments:
                # Get confidence from segment
                confidence = getattr(segment, 'no_speech_prob', 0.0)
                confidence = 1.0 - confidence if confidence is not None else 0.8
                
                segment_list.append(Segment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=confidence,
                    language=info.language
                ))
                full_text += segment.text + " "
            
            # Calculate overall confidence
            overall_confidence = (
                sum(seg.confidence for seg in segment_list) / len(segment_list)
                if segment_list else 0.0
            )
            
            return ASRResult(
                text=full_text.strip(),
                language=info.language,
                confidence=overall_confidence,
                segments=segment_list,
                engine="asr_a_whisper",
                language_probability=getattr(info, 'language_probability', None)
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"ASR-A transcription error: {error_msg}")
            raise RuntimeError(f"ASR-A transcription failed: {error_msg}")
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
