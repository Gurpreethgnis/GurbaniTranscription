"""
Base ASR class providing shared functionality for all ASR engines.

This module provides the abstract base class that all ASR engines should extend,
reducing code duplication across ASRWhisper, ASRIndic, and ASREnglish.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any
import config
from core.models import AudioChunk, ASRResult, Segment
from utils.device_utils import detect_device

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("ERROR: faster-whisper is not installed. Install with: pip install faster-whisper")


class BaseASR(ABC):
    """
    Abstract base class for ASR engines.
    
    Provides shared functionality for model loading, transcription,
    and segment processing.
    """
    
    # Subclasses should override these
    engine_name: str = "base_asr"
    default_beam_size: int = 5
    default_language: Optional[str] = None
    route_to_language: Dict[str, Optional[str]] = {
        'punjabi_speech': 'pa',
        'english_speech': 'en',
        'scripture_quote_likely': 'pa',
        'mixed': None
    }
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize the ASR engine.
        
        Args:
            model_size: Whisper model size (defaults to subclass-specific default)
        """
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. Install with: pip install faster-whisper"
            )
        
        self.model_size = model_size or self._get_default_model_size()
        self.model = None
        self.device, self.device_name = detect_device()
        self._load_model()
    
    @abstractmethod
    def _get_default_model_size(self) -> str:
        """Get the default model size for this ASR engine."""
        pass
    
    def _get_compute_type(self) -> str:
        """Determine compute type based on device."""
        if self.device == "cuda":
            return "float16"
        return "int8"
    
    def _load_model(self):
        """Load the Whisper model."""
        compute_type = self._get_compute_type()
        device_info = f"GPU ({self.device_name})" if self.device == "cuda" else "CPU"
        
        print(f"Loading {self.engine_name} model: {self.model_size} on {device_info}")
        
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4 if self.device == "cpu" else 0
            )
            print(f"{self.engine_name} model {self.model_size} loaded successfully on {self.device.upper()}")
        except Exception as e:
            raise RuntimeError(f"Failed to load {self.engine_name} model: {str(e)}")
    
    def _get_language_for_route(self, language: Optional[str], route: Optional[str]) -> Optional[str]:
        """
        Determine language from route if not provided.
        
        Args:
            language: Explicitly provided language code
            route: Route string from language identification
        
        Returns:
            Language code or None for auto-detect
        """
        if language is not None:
            return language
        if route:
            return self.route_to_language.get(route, self.default_language)
        return self.default_language
    
    def _extract_confidence(self, segment) -> float:
        """Extract confidence from a whisper segment."""
        no_speech_prob = getattr(segment, 'no_speech_prob', 0.0)
        return 1.0 - no_speech_prob if no_speech_prob is not None else 0.8
    
    def _get_transcription_params(
        self,
        language: Optional[str],
        vad_filter: bool = False,
        initial_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get transcription parameters.
        
        Args:
            language: Language code to use
            vad_filter: Whether to enable VAD filtering
            initial_prompt: Optional prompt to bias transcription toward specific vocabulary
        
        Returns:
            Dictionary of transcription parameters
        """
        params = {
            "language": language,
            "task": "transcribe",
            "beam_size": self.default_beam_size,
            "vad_filter": vad_filter,
            "word_timestamps": False,
        }
        
        # Add initial prompt if provided (biases Whisper toward specific vocabulary)
        if initial_prompt:
            params["initial_prompt"] = initial_prompt
        
        if vad_filter:
            params["vad_parameters"] = {
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            }
        return params
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code to force (e.g., 'pa', 'en')
            route: Route string (e.g., 'punjabi_speech', 'english_speech')
            initial_prompt: Optional prompt to bias transcription toward specific vocabulary
        
        Returns:
            ASRResult with transcription and segments
        """
        language = self._get_language_for_route(language, route)
        params = self._get_transcription_params(language, vad_filter=False, initial_prompt=initial_prompt)
        
        segments, info = self.model.transcribe(str(chunk.audio_path), **params)
        
        # Filter segments to only include those within chunk time range
        chunk_segments = []
        full_text = ""
        
        for segment in segments:
            if segment.start < chunk.end_time and segment.end > chunk.start_time:
                adjusted_start = max(0, segment.start - chunk.start_time)
                adjusted_end = min(chunk.duration, segment.end - chunk.start_time)
                
                chunk_segments.append(Segment(
                    start=adjusted_start,
                    end=adjusted_end,
                    text=segment.text.strip(),
                    confidence=self._extract_confidence(segment),
                    language=info.language
                ))
                full_text += segment.text + " "
        
        overall_confidence = (
            sum(seg.confidence for seg in chunk_segments) / len(chunk_segments)
            if chunk_segments else 0.0
        )
        
        return ASRResult(
            text=full_text.strip(),
            language=info.language,
            confidence=overall_confidence,
            segments=chunk_segments,
            engine=self.engine_name,
            language_probability=getattr(info, 'language_probability', None)
        )
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code to force, or None for auto-detect
            initial_prompt: Optional prompt to bias transcription toward specific vocabulary
        
        Returns:
            ASRResult with transcription and segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        language = language or self.default_language
        params = self._get_transcription_params(language, vad_filter=True, initial_prompt=initial_prompt)
        
        try:
            segments, info = self.model.transcribe(str(audio_path), **params)
            
            segment_list = []
            full_text = ""
            
            for segment in segments:
                segment_list.append(Segment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=self._extract_confidence(segment),
                    language=info.language
                ))
                full_text += segment.text + " "
            
            overall_confidence = (
                sum(seg.confidence for seg in segment_list) / len(segment_list)
                if segment_list else 0.0
            )
            
            return ASRResult(
                text=full_text.strip(),
                language=info.language,
                confidence=overall_confidence,
                segments=segment_list,
                engine=self.engine_name,
                language_probability=getattr(info, 'language_probability', None)
            )
            
        except Exception as e:
            print(f"{self.engine_name} transcription error: {e}")
            raise RuntimeError(f"{self.engine_name} transcription failed: {e}")
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None

