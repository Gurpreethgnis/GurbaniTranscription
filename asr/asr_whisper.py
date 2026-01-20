"""
ASR-A: Whisper-based Automatic Speech Recognition.

This is the primary ASR engine using faster-whisper with support for
chunked processing and forced language per segment.
"""
from typing import Optional
import config
from asr.base_asr import BaseASR


class ASRWhisper(BaseASR):
    """
    ASR-A: Primary Whisper-based ASR engine.
    
    Supports chunked processing with forced language per segment.
    Uses standard Whisper model for general transcription.
    """
    
    engine_name = "asr_a_whisper"
    default_beam_size = 5
    default_language = None  # Auto-detect
    route_to_language = {
        'punjabi_speech': 'pa',
        'english_speech': 'en',
        'scripture_quote_likely': 'pa',  # Gurbani is in Punjabi/Sant Bhasha
        'mixed': None  # Auto-detect
    }
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-A Whisper service.
        
        Args:
            model_size: Whisper model size (defaults to config.WHISPER_MODEL_SIZE)
        """
        super().__init__(model_size)
    
    def _get_default_model_size(self) -> str:
        """Get the default model size from config."""
        return config.WHISPER_MODEL_SIZE
