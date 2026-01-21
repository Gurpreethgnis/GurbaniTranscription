"""
Translation Service for Gurbani Transcription.

Provides translation capabilities with:
- Multiple provider support (Google, Azure, OpenAI, LibreTranslate)
- Caching layer for scripture translations from SGGS database
- Batch processing support
- Language detection and routing
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import json

from core.models import (
    TranslationProvider,
    SupportedLanguage,
    TranslatedSegment,
    TranslationResult,
    TranslationLanguageStatus,
    ProcessedSegment
)
from services.translation_providers import (
    BaseTranslationProvider,
    get_translation_provider,
    get_available_translation_providers
)

logger = logging.getLogger(__name__)


# Supported languages with metadata
SUPPORTED_LANGUAGES: Dict[str, SupportedLanguage] = {
    "en": SupportedLanguage(
        code="en",
        name="English",
        native_name="English",
        flag_emoji="🇬🇧",
        is_cached=True  # SGGS English translations available
    ),
    "hi": SupportedLanguage(
        code="hi",
        name="Hindi",
        native_name="हिन्दी",
        flag_emoji="🇮🇳",
        is_cached=False
    ),
    "pa": SupportedLanguage(
        code="pa",
        name="Punjabi",
        native_name="ਪੰਜਾਬੀ",
        flag_emoji="🇮🇳",
        is_cached=True  # Source language - always cached
    ),
    "ur": SupportedLanguage(
        code="ur",
        name="Urdu",
        native_name="اردو",
        flag_emoji="🇵🇰",
        is_cached=False
    ),
    "es": SupportedLanguage(
        code="es",
        name="Spanish",
        native_name="Español",
        flag_emoji="🇪🇸",
        is_cached=False
    ),
    "fr": SupportedLanguage(
        code="fr",
        name="French",
        native_name="Français",
        flag_emoji="🇫🇷",
        is_cached=False
    ),
    "de": SupportedLanguage(
        code="de",
        name="German",
        native_name="Deutsch",
        flag_emoji="🇩🇪",
        is_cached=False
    ),
    "it": SupportedLanguage(
        code="it",
        name="Italian",
        native_name="Italiano",
        flag_emoji="🇮🇹",
        is_cached=False
    ),
    "pt": SupportedLanguage(
        code="pt",
        name="Portuguese",
        native_name="Português",
        flag_emoji="🇧🇷",
        is_cached=False
    ),
    "ru": SupportedLanguage(
        code="ru",
        name="Russian",
        native_name="Русский",
        flag_emoji="🇷🇺",
        is_cached=False
    ),
    "zh": SupportedLanguage(
        code="zh",
        name="Mandarin",
        native_name="中文",
        flag_emoji="🇨🇳",
        is_cached=False
    ),
    "ja": SupportedLanguage(
        code="ja",
        name="Japanese",
        native_name="日本語",
        flag_emoji="🇯🇵",
        is_cached=False
    ),
    "ko": SupportedLanguage(
        code="ko",
        name="Korean",
        native_name="한국어",
        flag_emoji="🇰🇷",
        is_cached=False
    ),
    "ar": SupportedLanguage(
        code="ar",
        name="Arabic",
        native_name="العربية",
        flag_emoji="🇸🇦",
        is_cached=False
    ),
}


class TranslationService:
    """
    Main translation service with provider management and caching.
    """
    
    def __init__(
        self,
        primary_provider: str = "google",
        fallback_provider: Optional[str] = "libre",
        sggs_db_path: Optional[Path] = None,
        use_scripture_cache: bool = True
    ):
        """
        Initialize translation service.
        
        Args:
            primary_provider: Primary translation provider name
            fallback_provider: Fallback provider if primary fails
            sggs_db_path: Path to SGGS database for cached translations
            use_scripture_cache: Whether to use cached scripture translations
        """
        self.primary_provider_name = primary_provider
        self.fallback_provider_name = fallback_provider
        self.use_scripture_cache = use_scripture_cache
        
        # SGGS database for cached English translations
        self._sggs_db = None
        self._sggs_db_path = sggs_db_path
        
        # Translation cache (in-memory)
        self._translation_cache: Dict[str, str] = {}
        
        logger.info(f"TranslationService initialized with primary={primary_provider}, fallback={fallback_provider}")
    
    def _get_sggs_db(self):
        """Lazy-load SGGS database for cached translations."""
        if self._sggs_db is None and self.use_scripture_cache:
            try:
                from scripture.sggs_db import SGGSDatabase
                self._sggs_db = SGGSDatabase(self._sggs_db_path)
                logger.info("SGGS database loaded for translation caching")
            except Exception as e:
                logger.warning(f"Failed to load SGGS database: {e}")
                self._sggs_db = None
        return self._sggs_db
    
    def _get_provider(self, name: str) -> Optional[BaseTranslationProvider]:
        """Get a translation provider by name."""
        provider = get_translation_provider(name)
        if provider and provider.is_available():
            return provider
        return None
    
    def get_supported_languages(self) -> List[SupportedLanguage]:
        """Get list of all supported languages."""
        return list(SUPPORTED_LANGUAGES.values())
    
    def get_language(self, code: str) -> Optional[SupportedLanguage]:
        """Get language by code."""
        return SUPPORTED_LANGUAGES.get(code.lower())
    
    def get_language_status_for_transcription(
        self,
        segments: List[ProcessedSegment],
        source_language: str = "pa"
    ) -> List[TranslationLanguageStatus]:
        """
        Get translation language status for a transcription.
        
        Determines which languages have cached translations and which need API calls.
        
        Args:
            segments: Transcription segments
            source_language: Source language of transcription
        
        Returns:
            List of language status objects
        """
        statuses = []
        total_segments = len(segments)
        
        # Count scripture quote segments (which may have cached English translations)
        scripture_segments = sum(1 for seg in segments if seg.type == "scripture_quote")
        
        for code, language in SUPPORTED_LANGUAGES.items():
            # Skip source language
            if code == source_language:
                continue
            
            # Determine caching status
            if code == "en" and scripture_segments > 0:
                # English has cached translations for scripture quotes from SGGS
                cached_count = self._count_cached_english_translations(segments)
                if cached_count == total_segments:
                    status = "cached"
                elif cached_count > 0:
                    status = "will_translate"  # Partial cache
                else:
                    status = "will_translate"
            else:
                cached_count = 0
                status = "will_translate"
            
            # Check if provider supports this language
            provider = self._get_provider(self.primary_provider_name)
            if not provider or not provider.supports_language(code):
                fallback = self._get_provider(self.fallback_provider_name) if self.fallback_provider_name else None
                if not fallback or not fallback.supports_language(code):
                    status = "unavailable"
            
            statuses.append(TranslationLanguageStatus(
                language=language,
                status=status,
                cached_segments=cached_count,
                total_segments=total_segments
            ))
        
        return statuses
    
    def _count_cached_english_translations(self, segments: List[ProcessedSegment]) -> int:
        """Count segments that have cached English translations from SGGS database."""
        count = 0
        sggs_db = self._get_sggs_db()
        
        if not sggs_db:
            return 0
        
        for seg in segments:
            # Check if segment has a quote match with line_id
            if seg.quote_match and seg.quote_match.line_id:
                # Check if SGGS database has English translation for this line
                try:
                    translation = sggs_db.get_english_translation(seg.quote_match.line_id)
                    if translation:
                        count += 1
                except Exception:
                    pass
        
        return count
    
    def _get_cached_english_translation(
        self,
        segment: ProcessedSegment
    ) -> Optional[str]:
        """Get cached English translation from SGGS database for a segment."""
        if not segment.quote_match or not segment.quote_match.line_id:
            return None
        
        return self._get_cached_english_translation_by_line_id(segment.quote_match.line_id)
    
    def _get_cached_english_translation_by_line_id(
        self,
        line_id: str
    ) -> Optional[str]:
        """Get cached English translation from SGGS database by line ID."""
        if not line_id:
            return None
        
        sggs_db = self._get_sggs_db()
        if not sggs_db:
            return None
        
        try:
            return sggs_db.get_english_translation(line_id)
        except Exception as e:
            logger.debug(f"Failed to get cached translation for line {line_id}: {e}")
            return None
    
    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Tuple[str, TranslationProvider]:
        """
        Translate a single text.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            context: Optional context (e.g., "scripture", "katha")
            provider_name: Optional specific provider to use
        
        Returns:
            Tuple of (translated_text, provider_used)
        """
        if not text.strip():
            return text, TranslationProvider.CACHED
        
        # Check in-memory cache
        cache_key = f"{source_language}:{target_language}:{hash(text)}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key], TranslationProvider.CACHED
        
        # Get provider
        provider_to_use = provider_name or self.primary_provider_name
        provider = self._get_provider(provider_to_use)
        
        if not provider:
            # Try fallback
            if self.fallback_provider_name:
                provider = self._get_provider(self.fallback_provider_name)
                provider_to_use = self.fallback_provider_name
        
        if not provider:
            raise RuntimeError(f"No translation provider available")
        
        # Translate
        try:
            translated = provider.translate(text, source_language, target_language, context)
            
            # Cache result
            self._translation_cache[cache_key] = translated
            
            return translated, TranslationProvider(provider_to_use)
            
        except Exception as e:
            logger.error(f"Translation failed with {provider_to_use}: {e}")
            
            # Try fallback
            if provider_to_use != self.fallback_provider_name and self.fallback_provider_name:
                fallback = self._get_provider(self.fallback_provider_name)
                if fallback:
                    try:
                        translated = fallback.translate(text, source_language, target_language, context)
                        self._translation_cache[cache_key] = translated
                        return translated, TranslationProvider(self.fallback_provider_name)
                    except Exception as fallback_error:
                        logger.error(f"Fallback translation also failed: {fallback_error}")
            
            raise
    
    def translate_segments(
        self,
        segments: List[ProcessedSegment],
        source_language: str,
        target_language: str,
        provider_name: Optional[str] = None
    ) -> List[TranslatedSegment]:
        """
        Translate multiple segments.
        
        CRITICAL: For scripture quotes (Shabads/Gurbani), the original sacred text
        is NEVER modified or translated. We only provide the meaning/interpretation
        in the target language while preserving the original Gurmukhi intact.
        
        Args:
            segments: List of transcription segments
            source_language: Source language code
            target_language: Target language code
            provider_name: Optional specific provider to use
        
        Returns:
            List of translated segments with preserved scripture text
        """
        translated_segments = []
        
        for seg in segments:
            is_scripture = seg.type == "scripture_quote"
            
            # For scripture quotes: PRESERVE the original Gurmukhi, only get meaning
            # For katha: translate normally
            if is_scripture:
                # The original Gurmukhi is sacred and must NEVER be changed
                preserved_original = seg.text  # Always keep original Gurmukhi
                transliteration = seg.roman if seg.roman else None
                
                # Get the English meaning (from SGGS cache or translate the meaning)
                meaning_text = None
                provider_used = TranslationProvider.CACHED
                is_cached = False
                
                # Try to get cached English translation from SGGS database
                if target_language == "en":
                    cached = self._get_cached_english_translation(seg)
                    if cached:
                        meaning_text = cached
                        is_cached = True
                        logger.debug(f"Using cached English meaning for scripture segment {seg.start}-{seg.end}")
                
                # If no English cache, or target is not English, translate the meaning
                # (translate from Roman transliteration or existing meaning, NOT from Gurmukhi)
                if meaning_text is None:
                    # For scripture, translate the transliteration/Roman if available
                    # This gives the "meaning" without changing the sacred text
                    text_to_translate = seg.roman if seg.roman else seg.text
                    try:
                        meaning_text, provider_used = self.translate_text(
                            text_to_translate,
                            source_language,
                            target_language,
                            context="scripture_meaning",  # Context hint for translator
                            provider_name=provider_name
                        )
                    except Exception as e:
                        logger.error(f"Failed to get meaning for scripture segment {seg.start}-{seg.end}: {e}")
                        meaning_text = f"[Meaning unavailable]"
                
                translated_segments.append(TranslatedSegment(
                    start=seg.start,
                    end=seg.end,
                    source_text=seg.text,  # Original Gurmukhi
                    source_language=source_language,
                    translated_text=meaning_text,  # This is the MEANING, not a replacement
                    target_language=target_language,
                    provider=provider_used,
                    confidence=seg.confidence,
                    is_cached=is_cached,
                    is_scripture=True,
                    preserved_original=preserved_original,  # CRITICAL: Original Gurmukhi preserved
                    transliteration=transliteration
                ))
            else:
                # Katha (explanation) segments
                # IMPORTANT: Check if there are embedded scripture quotes - these must be preserved!
                has_embedded_quote = seg.quote_match is not None
                embedded_quotes = []
                
                if source_language == "pa":
                    source_text = seg.text  # Gurmukhi text
                elif source_language == "en" and seg.route == "english_speech":
                    source_text = seg.text  # English speech
                else:
                    source_text = seg.roman if seg.roman else seg.text
                
                translated_text = None
                provider_used = TranslationProvider.CACHED
                
                if has_embedded_quote:
                    # Katha segment contains an embedded Gurbani quote
                    # We need to preserve the quoted scripture and only translate the explanation
                    quote_match = seg.quote_match
                    canonical_text = quote_match.canonical_text  # The actual Gurbani
                    spoken_text = quote_match.spoken_text  # How it was spoken
                    
                    # Get the meaning of the embedded quote (for reference)
                    quote_meaning = None
                    if target_language == "en":
                        quote_meaning = self._get_cached_english_translation_by_line_id(quote_match.line_id)
                    
                    if quote_meaning is None:
                        # Try to translate the meaning
                        try:
                            roman_quote = quote_match.canonical_roman or seg.roman
                            if roman_quote:
                                quote_meaning, _ = self.translate_text(
                                    roman_quote,
                                    source_language,
                                    target_language,
                                    context="scripture_meaning",
                                    provider_name=provider_name
                                )
                        except Exception:
                            quote_meaning = "[Meaning unavailable]"
                    
                    # Store the embedded quote info
                    embedded_quotes.append({
                        "canonical_text": canonical_text,  # Original Gurmukhi - PRESERVED
                        "spoken_text": spoken_text,  # How it was transcribed
                        "meaning": quote_meaning,  # Translation of meaning only
                        "transliteration": quote_match.canonical_roman,
                        "ang": quote_match.ang,
                        "source": quote_match.source.value if quote_match.source else None
                    })
                    
                    # For the translated text, we translate the explanation parts
                    # but mark where the scripture quote should appear
                    # Create a placeholder pattern for the quote
                    try:
                        # Translate the full text, but we'll display it with the preserved quote
                        translated_text, provider_used = self.translate_text(
                            source_text,
                            source_language,
                            target_language,
                            context="katha_with_quote",  # Context hint
                            provider_name=provider_name
                        )
                        # The embedded quote info tells the frontend which parts to preserve
                    except Exception as e:
                        logger.error(f"Failed to translate katha segment {seg.start}-{seg.end}: {e}")
                        translated_text = f"[Translation failed]"
                    
                    logger.debug(f"Katha segment {seg.start}-{seg.end} has embedded quote: {canonical_text[:50]}...")
                else:
                    # Pure katha without embedded quotes - translate normally
                    try:
                        translated_text, provider_used = self.translate_text(
                            source_text,
                            source_language,
                            target_language,
                            context="katha",  # Explanation/commentary context
                            provider_name=provider_name
                        )
                    except Exception as e:
                        logger.error(f"Failed to translate katha segment {seg.start}-{seg.end}: {e}")
                        translated_text = f"[Translation failed: {source_text}]"
                
                translated_segments.append(TranslatedSegment(
                    start=seg.start,
                    end=seg.end,
                    source_text=source_text,
                    source_language=source_language,
                    translated_text=translated_text,
                    target_language=target_language,
                    provider=provider_used,
                    confidence=seg.confidence,
                    is_cached=False,
                    is_scripture=False,
                    preserved_original=None,
                    transliteration=None,
                    embedded_quotes=embedded_quotes if embedded_quotes else None,
                    has_embedded_quote=has_embedded_quote
                ))
        
        return translated_segments
    
    def translate_transcription(
        self,
        filename: str,
        segments: List[ProcessedSegment],
        source_language: str,
        target_language: str,
        provider_name: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate an entire transcription.
        
        IMPORTANT: Scripture/Shabad text is NEVER changed. The output preserves
        original Gurmukhi for all scripture quotes while providing meanings/translations
        for understanding. Katha (explanation) portions are fully translated.
        
        Args:
            filename: Source audio filename
            segments: Transcription segments
            source_language: Source language code
            target_language: Target language code
            provider_name: Optional specific provider to use
        
        Returns:
            Complete translation result with preserved scripture
        """
        logger.info(f"Translating {filename} from {source_language} to {target_language}")
        
        # Translate all segments (preserving scripture text)
        translated_segments = self.translate_segments(
            segments,
            source_language,
            target_language,
            provider_name
        )
        
        # Build full translation text with scripture preservation
        # Format: For scripture, show "Original | Meaning", for katha show translated text
        full_translation_parts = []
        for seg in translated_segments:
            if seg.is_scripture and seg.preserved_original:
                # Scripture: Show original Gurmukhi followed by meaning in brackets
                # The Gurmukhi is NEVER replaced, only annotated with meaning
                scripture_line = f"ੴ {seg.preserved_original}"
                if seg.transliteration:
                    scripture_line += f"\n   ({seg.transliteration})"
                scripture_line += f"\n   → {seg.translated_text}"
                full_translation_parts.append(scripture_line)
            else:
                # Katha: Just the translated text
                full_translation_parts.append(seg.translated_text)
        
        full_translation = "\n\n".join(full_translation_parts)
        
        # Count cached vs translated
        cached_count = sum(1 for seg in translated_segments if seg.is_cached)
        translated_count = len(translated_segments) - cached_count
        scripture_count = sum(1 for seg in translated_segments if seg.is_scripture)
        
        # Determine primary provider used
        providers_used = set(seg.provider for seg in translated_segments if not seg.is_cached)
        primary_provider = (
            list(providers_used)[0] if providers_used 
            else TranslationProvider.CACHED
        )
        
        result = TranslationResult(
            source_filename=filename,
            source_language=source_language,
            target_language=target_language,
            segments=translated_segments,
            full_translation=full_translation,
            provider=primary_provider,
            cached_count=cached_count,
            translated_count=translated_count,
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(
            f"Translation complete: {len(translated_segments)} segments, "
            f"{scripture_count} scripture (preserved), {cached_count} cached meanings, "
            f"{translated_count} katha translated"
        )
        
        return result
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available translation providers."""
        return get_available_translation_providers()


# Singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service(
    primary_provider: Optional[str] = None,
    fallback_provider: Optional[str] = None
) -> TranslationService:
    """
    Get or create the translation service singleton.
    
    Args:
        primary_provider: Override primary provider
        fallback_provider: Override fallback provider
    
    Returns:
        TranslationService instance
    """
    global _translation_service
    
    if _translation_service is None:
        import config
        
        _translation_service = TranslationService(
            primary_provider=primary_provider or getattr(config, 'TRANSLATION_PRIMARY_PROVIDER', 'google'),
            fallback_provider=fallback_provider or getattr(config, 'TRANSLATION_FALLBACK_PROVIDER', 'libre'),
            sggs_db_path=getattr(config, 'SCRIPTURE_DB_PATH', None),
            use_scripture_cache=getattr(config, 'TRANSLATION_USE_SGGS_ENGLISH', True)
        )
    
    return _translation_service

