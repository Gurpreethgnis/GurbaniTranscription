"""
ASR-C: English-Optimized Whisper Automatic Speech Recognition.

This ASR engine uses a Whisper model optimized for English transcription,
serving as a fallback for English segments and noisy audio.
"""
from typing import Optional
import config
from asr.base_asr import BaseASR


class ASREnglish(BaseASR):
    """
    ASR-C: English-optimized Whisper ASR engine.
    
    Optimized for English transcription with forced English language.
    Used primarily for english_speech routes and as a fallback.
    """
    
    engine_name = "asr_c_english"
    default_beam_size = 5  # Standard beam size for English
    default_language = 'en'  # Always force English
    route_to_language = {
        'punjabi_speech': 'en',  # Override - always use English
        'english_speech': 'en',
        'scripture_quote_likely': 'en',
        'mixed': 'en'
    }
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-C English service.
        
        Args:
            model_size: Whisper model size (defaults to config.ASR_C_MODEL)
        """
        self.force_language = getattr(config, 'ASR_C_FORCE_LANGUAGE', 'en')
        super().__init__(model_size)
    
    def _get_default_model_size(self) -> str:
        """Get the default model size from config."""
        return getattr(config, 'ASR_C_MODEL', 'medium')
    
    def _get_language_for_route(self, language: Optional[str], route: Optional[str]) -> Optional[str]:
        """Always force English language regardless of route."""
        return self.force_language
