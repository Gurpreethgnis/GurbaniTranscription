"""
Language and Domain Identification Service.

This service identifies the language and domain type for audio segments
to route them to appropriate ASR engines.

Phase 1: Rule-based detection (can be enhanced with ML later).
"""
from pathlib import Path
from typing import Optional
from core.models import AudioChunk

# Route types
ROUTE_PUNJABI_SPEECH = "punjabi_speech"
ROUTE_ENGLISH_SPEECH = "english_speech"
ROUTE_SCRIPTURE_QUOTE_LIKELY = "scripture_quote_likely"
ROUTE_MIXED = "mixed"


class LangIDService:
    """
    Language and domain identification service.
    
    Phase 1 implementation uses rule-based heuristics.
    Future: Can be enhanced with ML-based classification.
    """
    
    def __init__(
        self,
        quick_asr_service: Optional[object] = None,
        punjabi_threshold: float = 0.6,
        english_threshold: float = 0.6
    ):
        """
        Initialize LangID service.
        
        Args:
            quick_asr_service: Optional ASR service for quick language detection
            punjabi_threshold: Threshold for Punjabi detection (0.0-1.0)
            english_threshold: Threshold for English detection (0.0-1.0)
        """
        self.quick_asr_service = quick_asr_service
        self.punjabi_threshold = punjabi_threshold
        self.english_threshold = english_threshold
    
    def identify_segment(self, audio_chunk: AudioChunk) -> str:
        """
        Identify language/domain for an audio segment.
        
        Args:
            audio_chunk: AudioChunk to identify
        
        Returns:
            Route string: "punjabi_speech", "english_speech", 
                          "scripture_quote_likely", or "mixed"
        """
        # Strategy 1: Use quick ASR pass if available
        if self.quick_asr_service is not None:
            try:
                # Run a quick transcription pass for language detection
                # Use transcribe_chunk to avoid excessive VAD filtering on short segments
                result = self.quick_asr_service.transcribe_chunk(
                    audio_chunk,
                    language=None  # Auto-detect
                )
                
                detected_lang = result.language.lower()
                confidence = result.language_probability if result.language_probability is not None else 0.5
                
                # Map language codes to routes
                if detected_lang == 'pa' and confidence >= self.punjabi_threshold:
                    # Check if it might be scripture (heuristic: check for Gurmukhi script)
                    text = result.text
                    if self._looks_like_scripture(text):
                        return ROUTE_SCRIPTURE_QUOTE_LIKELY
                    return ROUTE_PUNJABI_SPEECH
                elif detected_lang == 'en' and confidence >= self.english_threshold:
                    return ROUTE_ENGLISH_SPEECH
                elif detected_lang in ['pa', 'hi', 'ur']:
                    # Punjabi/Hindi/Urdu - likely Punjabi speech
                    if self._looks_like_scripture(result.text):
                        return ROUTE_SCRIPTURE_QUOTE_LIKELY
                    return ROUTE_PUNJABI_SPEECH
                else:
                    # Mixed or unknown
                    return ROUTE_MIXED
                    
            except Exception as e:
                print(f"Warning: Quick ASR pass failed for language detection: {e}")
                # Fall through to heuristic-based detection
        
        # Strategy 2: Heuristic-based detection (fallback)
        # For Phase 1, default to Punjabi speech (most common case)
        # This can be enhanced with audio feature analysis later
        return ROUTE_PUNJABI_SPEECH
    
    def _looks_like_scripture(self, text: str) -> bool:
        """
        Heuristic check if text looks like Gurbani/scripture.
        
        This is a simple rule-based check. Can be enhanced with:
        - Gurmukhi vocabulary matching
        - Poetic meter detection
        - Known Gurbani phrase patterns
        
        Args:
            text: Transcribed text to check
        
        Returns:
            True if text appears to be scripture-like
        """
        if not text:
            return False
        
        # Check for Gurmukhi script (Unicode range: 0A00-0A7F)
        gurmukhi_chars = sum(1 for char in text if '\u0A00' <= char <= '\u0A7F')
        total_chars = len([c for c in text if c.isalnum()])
        
        if total_chars > 0:
            gurmukhi_ratio = gurmukhi_chars / total_chars
            # If more than 50% Gurmukhi characters, likely scripture
            if gurmukhi_ratio > 0.5:
                return True
        
        # Check for common Gurbani phrase patterns (can be expanded)
        scripture_indicators = [
            'ਵਾਹਿਗੁਰੂ',
            'ਸਤਿਗੁਰੂ',
            'ਗੁਰੂ',
            'ਬਾਣੀ',
            'ਸ਼ਬਦ',
            'ਅੰਗ',
            'ਰਾਗ'
        ]
        
        text_lower = text.lower()
        for indicator in scripture_indicators:
            if indicator in text:
                return True
        
        return False
    
    def get_language_code(self, route: str) -> Optional[str]:
        """
        Get language code for a route.
        
        Args:
            route: Route string
        
        Returns:
            Language code (e.g., 'pa', 'en') or None
        """
        route_to_lang = {
            ROUTE_PUNJABI_SPEECH: 'pa',
            ROUTE_ENGLISH_SPEECH: 'en',
            ROUTE_SCRIPTURE_QUOTE_LIKELY: 'pa',  # Gurbani is in Punjabi/Sant Bhasha
            ROUTE_MIXED: None  # Auto-detect
        }
        return route_to_lang.get(route)
