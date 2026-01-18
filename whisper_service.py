"""
Whisper service for audio transcription using faster-whisper.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import config


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


class WhisperService:
    """Service for handling Whisper model transcription using faster-whisper."""
    
    def __init__(self, model_size: Optional[str] = None):
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
                print(f"Loading faster-whisper model: {self.model_size} on GPU ({self.device_name})")
            else:
                compute_type = "int8"  # Use INT8 for CPU (faster on CPU)
                print(f"Loading faster-whisper model: {self.model_size} on CPU")
            
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=compute_type,
                # Use more CPU threads for better performance
                cpu_threads=4 if self.device == "cpu" else 0
            )
            
            print(f"Model {self.model_size} loaded successfully on {self.device.upper()}")
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {str(e)}")
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe",
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Transcribe audio file using faster-whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'pa' for Punjabi, 'ur' for Urdu)
                     If None, auto-detect
            task: 'transcribe' or 'translate'
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with transcription results and metadata
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                task=task,
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection - helps with long silences
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # Minimum silence duration
                    speech_pad_ms=200,  # Padding around speech
                ),
                word_timestamps=False,  # Disable for speed, enable if needed
            )
            
            # Collect segments with progress updates
            text_segments = []
            full_text = ""
            total_duration = getattr(info, 'duration', None)
            
            for segment in segments:
                text_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })
                full_text += segment.text + " "
                
                # Update progress if callback provided
                if progress_callback and total_duration and total_duration > 0:
                    progress = min(100, (segment.end / total_duration) * 100)
                    try:
                        progress_callback({
                            "progress": progress,
                            "current_time": segment.end,
                            "total_time": total_duration,
                            "segment_text": segment.text[:50] if segment.text else ""
                        })
                    except Exception as cb_error:
                        print(f"Progress callback error (non-fatal): {cb_error}")
            
            result = {
                "text": full_text.strip(),
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": text_segments,
                "duration": total_duration
            }
            
            # Final progress callback
            if progress_callback:
                try:
                    progress_callback({
                        "progress": 100,
                        "message": "Processing complete"
                    })
                except Exception as cb_error:
                    print(f"Progress callback error (non-fatal): {cb_error}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"Transcription error: {error_msg}")
            raise RuntimeError(f"Transcription failed: {error_msg}")
    
    def transcribe_with_language_detection(
        self,
        audio_path: Path,
        language_hints: Optional[list] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Transcribe with automatic language detection, using hints if provided.
        
        Args:
            audio_path: Path to audio file
            language_hints: List of language codes to prioritize (e.g., ['pa', 'ur', 'en'])
            progress_callback: Optional callback function for progress updates
        
        Returns:
            Dictionary with transcription results and metadata
        """
        return self.transcribe(audio_path, language=None, progress_callback=progress_callback)
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None


# Global service instance (lazy loading)
_whisper_service: Optional[WhisperService] = None


def get_whisper_service() -> WhisperService:
    """Get or create the global Whisper service instance."""
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService()
    return _whisper_service
