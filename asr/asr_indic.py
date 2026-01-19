"""
ASR-B: Indic-Tuned Whisper Automatic Speech Recognition.

This ASR engine uses a Whisper model fine-tuned for Indic languages
(Punjabi, Hindi, Braj) to provide better accuracy for Gurbani and
mixed-language Katha content.
"""
import os
from pathlib import Path
from typing import Optional, List
import config
from core.models import AudioChunk, ASRResult, Segment

# Reuse device detection from asr_whisper
from asr.asr_whisper import detect_device

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("ERROR: faster-whisper is not installed. Install with: pip install faster-whisper")


class ASRIndic:
    """
    ASR-B: Indic-tuned Whisper ASR engine.
    
    Optimized for Punjabi, Hindi, and Braj languages commonly found in Gurbani.
    """
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-B Indic service.
        
        Args:
            model_size: Indic-tuned model identifier or Whisper model size
                       Defaults to config.ASR_B_MODEL or falls back to standard Whisper
        """
        # Try Indic-specific model first, fallback to standard Whisper
        self.model_size = model_size or getattr(config, 'ASR_B_MODEL', None)
        self.fallback_model = getattr(config, 'ASR_B_FALLBACK_MODEL', 'large-v3')
        self.model = None
        self.device, self.device_name = detect_device()
        self._load_model()
    
    def _load_model(self):
        """Load the Indic-tuned Whisper model with fallback."""
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. Install with: pip install faster-whisper"
            )
        
        # Determine compute type based on device
        if self.device == "cuda":
            compute_type = "float16"
        else:
            compute_type = "int8"
        
        # Try to load Indic-specific model first
        if self.model_size and self.model_size not in ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']:
            # This looks like a HuggingFace model identifier
            try:
                print(f"Loading ASR-B (Indic-tuned) model: {self.model_size} on {self.device.upper()}")
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type,
                    cpu_threads=4 if self.device == "cpu" else 0
                )
                print(f"ASR-B Indic-tuned model {self.model_size} loaded successfully")
                return
            except Exception as e:
                print(f"Warning: Failed to load Indic model {self.model_size}: {e}")
                print(f"Falling back to standard Whisper {self.fallback_model}")
                self.model_size = self.fallback_model
        
        # Fallback to standard Whisper with forced Indic language
        try:
            print(f"Loading ASR-B (Whisper {self.model_size}) on {self.device.upper()}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4 if self.device == "cpu" else 0
            )
            print(f"ASR-B model {self.model_size} loaded successfully on {self.device.upper()}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ASR-B Whisper model: {str(e)}")
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk with Indic language optimization.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code to force (e.g., 'hi', 'pa')
                     If None, will use route to determine language
            route: Route string (e.g., 'punjabi_speech', 'scripture_quote_likely')
                  Used to determine language if language is None
        
        Returns:
            ASRResult with transcription and segments
        """
        # Determine language from route if not provided
        # For Indic ASR, prefer Hindi (hi) as it captures Braj/Sant Bhasha better
        if language is None and route:
            route_to_lang = {
                'punjabi_speech': 'hi',  # Use Hindi for better Indic coverage
                'english_speech': 'en',
                'scripture_quote_likely': 'hi',  # Gurbani in Hindi/Braj/Sant Bhasha
                'mixed': 'hi'  # Default to Hindi for mixed Indic content
            }
            language = route_to_lang.get(route, 'hi')
        elif language is None:
            language = 'hi'  # Default to Hindi for Indic ASR
        
        audio_path = chunk.audio_path
        
        # Transcribe with faster-whisper
        # Use higher beam size for complex Indic vocabulary
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            beam_size=7,  # Higher beam for Indic languages
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
                
                # Get confidence from segment
                confidence = getattr(segment, 'no_speech_prob', 0.0)
                confidence = 1.0 - confidence if confidence is not None else 0.8
                
                chunk_segments.append(Segment(
                    start=adjusted_start,
                    end=adjusted_end,
                    text=segment.text.strip(),
                    confidence=confidence,
                    language=info.language
                ))
                full_text += segment.text + " "
        
        # Calculate overall confidence
        overall_confidence = (
            sum(seg.confidence for seg in chunk_segments) / len(chunk_segments)
            if chunk_segments else 0.0
        )
        
        return ASRResult(
            text=full_text.strip(),
            language=info.language,
            confidence=overall_confidence,
            segments=chunk_segments,
            engine="asr_b_indic",
            language_probability=getattr(info, 'language_probability', None)
        )
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file with Indic language optimization.
        
        Args:
            audio_path: Path to audio file
            language: Language code to force (e.g., 'hi', 'pa'), or None for auto-detect
        
        Returns:
            ASRResult with transcription and segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Default to Hindi if not specified
        if language is None:
            language = 'hi'
        
        try:
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
                beam_size=7,  # Higher beam for Indic languages
                vad_filter=True,
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
                engine="asr_b_indic",
                language_probability=getattr(info, 'language_probability', None)
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"ASR-B transcription error: {error_msg}")
            raise RuntimeError(f"ASR-B transcription failed: {error_msg}")
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
