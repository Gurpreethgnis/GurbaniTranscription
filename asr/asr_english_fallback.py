"""
ASR-C: English-Optimized Whisper Automatic Speech Recognition.

This ASR engine uses a Whisper model optimized for English transcription,
serving as a fallback for English segments and noisy audio.
"""
import os
from pathlib import Path
from typing import Optional, List
import config
from models import AudioChunk, ASRResult, Segment

# Reuse device detection from asr_whisper
from asr.asr_whisper import detect_device

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("ERROR: faster-whisper is not installed. Install with: pip install faster-whisper")


class ASREnglish:
    """
    ASR-C: English-optimized Whisper ASR engine.
    
    Optimized for English transcription with forced English language.
    Used primarily for english_speech routes and as a fallback.
    """
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-C English service.
        
        Args:
            model_size: Whisper model size (defaults to config.ASR_C_MODEL)
        """
        self.model_size = model_size or getattr(config, 'ASR_C_MODEL', 'medium')
        self.force_language = getattr(config, 'ASR_C_FORCE_LANGUAGE', 'en')
        self.model = None
        self.device, self.device_name = detect_device()
        self._load_model()
    
    def _load_model(self):
        """Load the English Whisper model."""
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. Install with: pip install faster-whisper"
            )
        
        # Determine compute type based on device
        if self.device == "cuda":
            compute_type = "float16"
        else:
            compute_type = "int8"
        
        try:
            print(f"Loading ASR-C (English Whisper {self.model_size}) on {self.device.upper()}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4 if self.device == "cpu" else 0
            )
            print(f"ASR-C model {self.model_size} loaded successfully on {self.device.upper()}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ASR-C Whisper model: {str(e)}")
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk with forced English language.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code (forced to 'en' for ASR-C)
            route: Route string (ignored, always uses English)
        
        Returns:
            ASRResult with transcription and segments
        """
        # Always force English for ASR-C
        language = self.force_language
        
        audio_path = chunk.audio_path
        
        # Transcribe with faster-whisper
        # Optimized VAD parameters for English speech patterns
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            beam_size=5,  # Standard beam size for English
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
            engine="asr_c_english",
            language_probability=getattr(info, 'language_probability', None)
        )
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file with forced English language.
        
        Args:
            audio_path: Path to audio file
            language: Language code (forced to 'en' for ASR-C)
        
        Returns:
            ASRResult with transcription and segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Always force English
        language = self.force_language
        
        try:
            # Transcribe with faster-whisper
            # Optimized VAD parameters for English
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=300,  # Shorter for English
                    speech_pad_ms=150,
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
                engine="asr_c_english",
                language_probability=getattr(info, 'language_probability', None)
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"ASR-C transcription error: {error_msg}")
            raise RuntimeError(f"ASR-C transcription failed: {error_msg}")
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
