"""
Real-time Quote Context Detector.

Detects when a speaker is about to quote or is quoting from scripture
based on linguistic signals, patterns, and context from previous segments.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QuoteContextResult:
    """Result of quote context detection."""
    is_quote_likely: bool            # Whether a quote is likely in this segment
    is_quote_intro: bool             # Whether this is an intro to a quote
    quote_confidence: float          # Confidence score (0-1)
    expected_quote_length: Optional[int]  # Expected words if known
    detected_signals: List[str]      # List of detected signals
    context_type: str                # 'intro', 'quote_start', 'quote_middle', 'quote_end', 'none'


class QuoteContextDetector:
    """
    Detects quote context in real-time during transcription.
    
    Uses multiple signals:
    - Introductory phrases ("ਜਿਵੇਂ ਬਾਣੀ ਚ ਕਿਹਾ")
    - Ang/page references
    - Raag references
    - Quote-like vocabulary density
    - Previous segment context
    """
    
    # Introductory phrases that signal an upcoming quote
    INTRO_PATTERNS = [
        # "As stated in Bani"
        (r'ਜਿਵੇਂ\s+ਬਾਣੀ\s+(?:ਵਿੱਚ|ਚ)\s+(?:ਕਿਹਾ|ਆਇਆ|ਲਿਖਿਆ)', 'intro_jive_bani'),
        (r'ਜਿਵੇਂ\s+ਕਿਹਾ\s+ਹੈ', 'intro_jive_kiha'),
        
        # "Guru Sahib says"
        (r'ਗੁਰੂ\s+ਸਾਹਿਬ\s+(?:ਫੁਰਮਾਉਂਦੇ|ਫਰਮਾਉਂਦੇ|ਕਹਿੰਦੇ)\s+(?:ਹਨ|ਨੇ)', 'intro_guru_says'),
        (r'ਸਤਿਗੁਰੂ\s+(?:ਜੀ\s+)?(?:ਫੁਰਮਾਉਂਦੇ|ਕਹਿੰਦੇ)', 'intro_satguru_says'),
        
        # "Gurbani states"
        (r'ਗੁਰਬਾਣੀ\s+(?:ਦਾ\s+)?(?:ਫੁਰਮਾਨ|ਬਚਨ)\s+ਹੈ', 'intro_gurbani_farman'),
        (r'ਗੁਰਬਾਣੀ\s+(?:ਫੁਰਮਾਉਂਦੀ|ਕਹਿੰਦੀ)\s+ਹੈ', 'intro_gurbani_says'),
        
        # "On Ang X"
        (r'ਅੰਗ\s+\d+\s+(?:ਤੇ|ਉੱਤੇ|ਵਿੱਚ)', 'intro_ang_ref'),
        (r'ਪੰਨਾ\s+\d+\s+(?:ਤੇ|ਉੱਤੇ)', 'intro_page_ref'),
        
        # "In Raag X"
        (r'ਰਾਗ\s+\w+\s+(?:ਵਿੱਚ|ਚ)', 'intro_raag_ref'),
        
        # "This Shabad says"
        (r'(?:ਇਸ|ਇਹ)\s+ਸ਼ਬਦ\s+(?:ਵਿੱਚ|ਚ)', 'intro_shabad_ref'),
        (r'(?:ਇਸ|ਇਹ)\s+ਸਲੋਕ\s+(?:ਵਿੱਚ|ਚ)', 'intro_salok_ref'),
        
        # "Listen to this"
        (r'ਸੁਣੋ\s+(?:ਜੀ)?', 'intro_suno'),
        
        # "The meaning is"
        (r'(?:ਇਸ\s+ਦਾ\s+)?ਅਰਥ\s+ਹੈ', 'intro_arth'),
        
        # Mahala reference
        (r'ਮਹਲਾ\s+[੧੨੩੪੫੬੭੮੯1-9]', 'intro_mahala'),
    ]
    
    # Patterns that indicate we're IN a quote (not just intro)
    QUOTE_INTERNAL_PATTERNS = [
        # Rahao marker
        (r'॥\s*ਰਹਾਉ\s*॥', 'quote_rahao'),
        (r'॥\s*\d+\s*॥', 'quote_verse_number'),
        
        # Salok/Pauri markers
        (r'ਸਲੋਕ\s+ਮ(?:ਹਲਾ)?\s*[੧੨੩੪੫1-5]', 'quote_salok'),
        (r'ਪਉੜੀ\s*॥', 'quote_pauri'),
        
        # Traditional Gurbani punctuation
        (r'॥\s*॥', 'quote_double_danda'),
    ]
    
    # High-frequency archaic/Gurbani vocabulary
    GURBANI_VOCABULARY = {
        # Divine names (archaic forms)
        'ਹਰਿ', 'ਪ੍ਰਭ', 'ਪ੍ਰਭੁ', 'ਗੋਬਿੰਦ', 'ਗੋਪਾਲ', 'ਮਾਧੋ',
        # Core concepts
        'ਨਾਮੁ', 'ਨਾਮਿ', 'ਸਬਦੁ', 'ਸਬਦਿ', 'ਹੁਕਮੁ', 'ਹੁਕਮਿ',
        # Archaic verb forms
        'ਹੋਇ', 'ਹੋਵੈ', 'ਕਰੈ', 'ਜਪੈ', 'ਮਿਲੈ', 'ਪਾਵੈ',
        # Archaic suffixes
        'ਕਉ', 'ਤਉ', 'ਜਉ', 'ਸਉ',
        # Spiritual terms
        'ਮੁਕਤਿ', 'ਜੁਗਤਿ', 'ਭਗਤਿ', 'ਬਿਰਤਿ',
        # Sant Bhasha markers
        'ਮੋਹਿ', 'ਤੋਹਿ', 'ਕਾਹੂ', 'ਜਾਹੂ',
    }
    
    # Minimum vocabulary density to suggest a quote
    MIN_VOCAB_DENSITY = 0.25
    
    def __init__(self):
        """Initialize quote context detector."""
        # Compile patterns
        self.intro_patterns = [
            (re.compile(pattern, re.UNICODE | re.IGNORECASE), name)
            for pattern, name in self.INTRO_PATTERNS
        ]
        self.internal_patterns = [
            (re.compile(pattern, re.UNICODE), name)
            for pattern, name in self.QUOTE_INTERNAL_PATTERNS
        ]
        
        # Context tracking
        self._previous_was_intro = False
        self._quote_in_progress = False
    
    def detect(
        self,
        text: str,
        previous_text: Optional[str] = None,
        previous_result: Optional[QuoteContextResult] = None
    ) -> QuoteContextResult:
        """
        Detect quote context in text.
        
        Args:
            text: Current segment text
            previous_text: Text from previous segment
            previous_result: Result from previous segment
        
        Returns:
            QuoteContextResult with detection details
        """
        signals = []
        confidence = 0.0
        context_type = 'none'
        expected_length = None
        
        # Signal 1: Check for intro patterns
        intro_matches = self._check_intro_patterns(text)
        if intro_matches:
            signals.extend([f"intro:{m}" for m in intro_matches])
            confidence += 0.3 * len(intro_matches)
            context_type = 'intro'
        
        # Signal 2: Check for quote internal patterns
        internal_matches = self._check_internal_patterns(text)
        if internal_matches:
            signals.extend([f"internal:{m}" for m in internal_matches])
            confidence += 0.4 * len(internal_matches)
            context_type = 'quote_middle' if self._quote_in_progress else 'quote_start'
        
        # Signal 3: Check Gurbani vocabulary density
        vocab_density = self._calculate_vocab_density(text)
        if vocab_density >= self.MIN_VOCAB_DENSITY:
            signals.append(f"vocab_density:{vocab_density:.2f}")
            confidence += vocab_density * 0.3
        
        # Signal 4: Context from previous segment
        if previous_result and previous_result.is_quote_intro:
            signals.append("follows_intro")
            confidence += 0.3
            context_type = 'quote_start'
        
        # Signal 5: Previous was mid-quote
        if previous_result and previous_result.context_type in ('quote_start', 'quote_middle'):
            if vocab_density >= 0.15:  # Lower threshold for continuation
                signals.append("quote_continuation")
                confidence += 0.2
                context_type = 'quote_middle'
        
        # Normalize confidence
        confidence = min(1.0, confidence)
        
        # Determine if this is a quote intro or actual quote
        is_quote_intro = context_type == 'intro'
        is_quote_likely = confidence >= 0.3 or context_type in ('quote_start', 'quote_middle')
        
        # Update state for next call
        self._previous_was_intro = is_quote_intro
        self._quote_in_progress = context_type in ('quote_start', 'quote_middle')
        
        return QuoteContextResult(
            is_quote_likely=is_quote_likely,
            is_quote_intro=is_quote_intro,
            quote_confidence=confidence,
            expected_quote_length=expected_length,
            detected_signals=signals,
            context_type=context_type
        )
    
    def _check_intro_patterns(self, text: str) -> List[str]:
        """Check for intro patterns in text."""
        matches = []
        for pattern, name in self.intro_patterns:
            if pattern.search(text):
                matches.append(name)
        return matches
    
    def _check_internal_patterns(self, text: str) -> List[str]:
        """Check for quote-internal patterns."""
        matches = []
        for pattern, name in self.internal_patterns:
            if pattern.search(text):
                matches.append(name)
        return matches
    
    def _calculate_vocab_density(self, text: str) -> float:
        """Calculate Gurbani vocabulary density in text."""
        words = set(re.findall(r'[\u0A00-\u0A7F]+', text))
        
        if not words:
            return 0.0
        
        gurbani_words = words.intersection(self.GURBANI_VOCABULARY)
        return len(gurbani_words) / len(words)
    
    def reset_context(self) -> None:
        """Reset context tracking state."""
        self._previous_was_intro = False
        self._quote_in_progress = False
    
    def extract_ang_reference(self, text: str) -> Optional[int]:
        """
        Extract Ang (page) number if referenced.
        
        Args:
            text: Text to search
        
        Returns:
            Ang number if found, None otherwise
        """
        # Match "ਅੰਗ 123" or "Ang 123"
        match = re.search(r'ਅੰਗ\s*(\d+)', text)
        if match:
            return int(match.group(1))
        
        match = re.search(r'[Aa]ng\s*(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def extract_raag_reference(self, text: str) -> Optional[str]:
        """
        Extract Raag name if referenced.
        
        Args:
            text: Text to search
        
        Returns:
            Raag name if found, None otherwise
        """
        match = re.search(r'ਰਾਗ\s+([\u0A00-\u0A7F]+)', text)
        if match:
            return match.group(1)
        return None


def detect_quote_context(
    text: str,
    previous_text: Optional[str] = None
) -> QuoteContextResult:
    """
    Convenience function to detect quote context.
    
    Args:
        text: Current segment text
        previous_text: Previous segment text
    
    Returns:
        QuoteContextResult
    """
    detector = QuoteContextDetector()
    return detector.detect(text, previous_text)


def is_likely_quote(text: str, threshold: float = 0.4) -> bool:
    """
    Quick check if text is likely a quote.
    
    Args:
        text: Text to check
        threshold: Confidence threshold
    
    Returns:
        True if likely a quote
    """
    result = detect_quote_context(text)
    return result.is_quote_likely and result.quote_confidence >= threshold

