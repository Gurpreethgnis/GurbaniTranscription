"""
Gurmukhi Script Lock and Enforcement Module.

Ensures ASR output is constrained to Gurmukhi script only, with repair
mechanisms for non-Gurmukhi characters that slip through.
"""
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from data.language_domains import DomainMode, GurmukhiScript

logger = logging.getLogger(__name__)


@dataclass
class ScriptAnalysis:
    """
    Analysis results for script content in text.
    
    Provides metrics about script composition for validation and repair decisions.
    """
    total_chars: int
    gurmukhi_chars: int
    latin_chars: int
    devanagari_chars: int
    arabic_chars: int
    space_punct_chars: int
    other_chars: int
    
    @property
    def gurmukhi_ratio(self) -> float:
        """Ratio of Gurmukhi characters to total non-whitespace."""
        non_ws = self.total_chars - self.space_punct_chars
        if non_ws <= 0:
            return 1.0
        return self.gurmukhi_chars / non_ws
    
    @property
    def latin_ratio(self) -> float:
        """Ratio of Latin characters to total."""
        if self.total_chars <= 0:
            return 0.0
        return self.latin_chars / self.total_chars
    
    @property
    def script_purity(self) -> float:
        """
        Script purity score (Gurmukhi chars / all script chars).
        
        Returns 1.0 if text is pure Gurmukhi, lower if mixed.
        """
        script_chars = (
            self.gurmukhi_chars +
            self.latin_chars +
            self.devanagari_chars +
            self.arabic_chars +
            self.other_chars
        )
        if script_chars <= 0:
            return 1.0
        return self.gurmukhi_chars / script_chars
    
    @property
    def is_pure_gurmukhi(self) -> bool:
        """Check if text is pure Gurmukhi (no other scripts)."""
        return self.script_purity >= 0.99
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_chars': self.total_chars,
            'gurmukhi_chars': self.gurmukhi_chars,
            'latin_chars': self.latin_chars,
            'devanagari_chars': self.devanagari_chars,
            'arabic_chars': self.arabic_chars,
            'space_punct_chars': self.space_punct_chars,
            'other_chars': self.other_chars,
            'gurmukhi_ratio': self.gurmukhi_ratio,
            'latin_ratio': self.latin_ratio,
            'script_purity': self.script_purity,
            'is_pure_gurmukhi': self.is_pure_gurmukhi,
        }


class ScriptLock:
    """
    Gurmukhi script enforcement and validation.
    
    Provides:
    - Script analysis and validation
    - Character filtering to remove non-Gurmukhi
    - Transliteration fallback for common Latin/Devanagari
    """
    
    # Unicode ranges for script detection
    GURMUKHI_RANGE = (0x0A00, 0x0A7F)
    DEVANAGARI_RANGE = (0x0900, 0x097F)
    ARABIC_RANGE = (0x0600, 0x06FF)
    LATIN_BASIC_RANGE = (0x0041, 0x007A)  # A-Z, a-z
    LATIN_EXTENDED_RANGE = (0x00C0, 0x024F)  # Extended Latin
    
    # Common Latin to Gurmukhi transliteration (basic phonetic mapping)
    LATIN_TO_GURMUKHI = {
        'a': 'ਅ', 'aa': 'ਆ', 'i': 'ਇ', 'ee': 'ਈ', 'u': 'ਉ', 'oo': 'ਊ',
        'e': 'ਏ', 'ai': 'ਐ', 'o': 'ਓ', 'au': 'ਔ',
        'k': 'ਕ', 'kh': 'ਖ', 'g': 'ਗ', 'gh': 'ਘ', 'ng': 'ਙ',
        'ch': 'ਚ', 'chh': 'ਛ', 'j': 'ਜ', 'jh': 'ਝ',
        't': 'ਤ', 'th': 'ਥ', 'd': 'ਦ', 'dh': 'ਧ', 'n': 'ਨ',
        'p': 'ਪ', 'ph': 'ਫ', 'b': 'ਬ', 'bh': 'ਭ', 'm': 'ਮ',
        'y': 'ਯ', 'r': 'ਰ', 'l': 'ਲ', 'v': 'ਵ', 'w': 'ਵ',
        's': 'ਸ', 'sh': 'ਸ਼', 'h': 'ਹ',
        # Special
        'x': 'ਖ਼', 'z': 'ਜ਼', 'f': 'ਫ਼', 'q': 'ਕ',
    }
    
    # Common Devanagari to Gurmukhi mapping
    DEVANAGARI_TO_GURMUKHI = {
        # Vowels
        'अ': 'ਅ', 'आ': 'ਆ', 'इ': 'ਇ', 'ई': 'ਈ', 'उ': 'ਉ', 'ऊ': 'ਊ',
        'ए': 'ਏ', 'ऐ': 'ਐ', 'ओ': 'ਓ', 'औ': 'ਔ',
        # Consonants
        'क': 'ਕ', 'ख': 'ਖ', 'ग': 'ਗ', 'घ': 'ਘ', 'ङ': 'ਙ',
        'च': 'ਚ', 'छ': 'ਛ', 'ज': 'ਜ', 'झ': 'ਝ', 'ञ': 'ਞ',
        'ट': 'ਟ', 'ठ': 'ਠ', 'ड': 'ਡ', 'ढ': 'ਢ', 'ण': 'ਣ',
        'त': 'ਤ', 'थ': 'ਥ', 'द': 'ਦ', 'ध': 'ਧ', 'न': 'ਨ',
        'प': 'ਪ', 'फ': 'ਫ', 'ब': 'ਬ', 'भ': 'ਭ', 'म': 'ਮ',
        'य': 'ਯ', 'र': 'ਰ', 'ल': 'ਲ', 'व': 'ਵ',
        'श': 'ਸ਼', 'ष': 'ਸ਼', 'स': 'ਸ', 'ह': 'ਹ',
        # Vowel signs
        'ा': 'ਾ', 'ि': 'ਿ', 'ी': 'ੀ', 'ु': 'ੁ', 'ू': 'ੂ',
        'े': 'ੇ', 'ै': 'ੈ', 'ो': 'ੋ', 'ौ': 'ੌ',
        # Marks
        'ं': 'ੰ', 'ः': 'ਃ', '्': '੍', 'ँ': 'ੰ',
        # Nukta forms
        'क़': 'ਕ਼', 'ख़': 'ਖ਼', 'ग़': 'ਗ਼', 'ज़': 'ਜ਼', 'फ़': 'ਫ਼',
        # Numbers
        '०': '੦', '१': '੧', '२': '੨', '३': '੩', '४': '੪',
        '५': '੫', '६': '੬', '७': '੭', '८': '੮', '९': '੯',
    }
    
    def __init__(self, mode: DomainMode = DomainMode.SGGS):
        """
        Initialize script lock.
        
        Args:
            mode: Domain mode for context-specific handling
        """
        self.mode = mode
        
        # Build reverse lookup for detection
        self._gurmukhi_chars = GurmukhiScript.get_all_allowed_chars()
    
    def _is_in_range(self, char: str, range_start: int, range_end: int) -> bool:
        """Check if character is in Unicode range."""
        if len(char) != 1:
            return False
        code_point = ord(char)
        return range_start <= code_point <= range_end
    
    def _classify_char(self, char: str) -> str:
        """
        Classify a character by script.
        
        Returns:
            'gurmukhi', 'latin', 'devanagari', 'arabic', 'space', 'punct', or 'other'
        """
        if len(char) != 1:
            return 'other'
        
        code_point = ord(char)
        
        # Whitespace and punctuation
        if char in ' \t\n\r':
            return 'space'
        if char in GurmukhiScript.ALLOWED_PUNCTUATION:
            return 'punct'
        
        # Gurmukhi
        if self._is_in_range(char, *self.GURMUKHI_RANGE):
            return 'gurmukhi'
        
        # Devanagari
        if self._is_in_range(char, *self.DEVANAGARI_RANGE):
            return 'devanagari'
        
        # Arabic
        if self._is_in_range(char, *self.ARABIC_RANGE):
            return 'arabic'
        
        # Latin
        if (self._is_in_range(char, *self.LATIN_BASIC_RANGE) or
            self._is_in_range(char, *self.LATIN_EXTENDED_RANGE)):
            return 'latin'
        
        # ASCII digits
        if char in GurmukhiScript.ASCII_DIGITS:
            return 'digit'
        
        return 'other'
    
    def analyze(self, text: str) -> ScriptAnalysis:
        """
        Analyze script composition of text.
        
        Args:
            text: Text to analyze
        
        Returns:
            ScriptAnalysis with detailed metrics
        """
        gurmukhi = 0
        latin = 0
        devanagari = 0
        arabic = 0
        space_punct = 0
        other = 0
        
        for char in text:
            classification = self._classify_char(char)
            
            if classification == 'gurmukhi':
                gurmukhi += 1
            elif classification == 'latin':
                latin += 1
            elif classification == 'devanagari':
                devanagari += 1
            elif classification == 'arabic':
                arabic += 1
            elif classification in ('space', 'punct', 'digit'):
                space_punct += 1
            else:
                other += 1
        
        return ScriptAnalysis(
            total_chars=len(text),
            gurmukhi_chars=gurmukhi,
            latin_chars=latin,
            devanagari_chars=devanagari,
            arabic_chars=arabic,
            space_punct_chars=space_punct,
            other_chars=other,
        )
    
    def validate(self, text: str, strict: bool = True) -> Tuple[bool, ScriptAnalysis]:
        """
        Validate text for Gurmukhi purity.
        
        Args:
            text: Text to validate
            strict: If True, require near-pure Gurmukhi (>95%)
        
        Returns:
            Tuple of (is_valid, analysis)
        """
        analysis = self.analyze(text)
        
        if strict:
            # Strict mode: >95% Gurmukhi, <2% Latin
            is_valid = (
                analysis.script_purity >= 0.95 and
                analysis.latin_ratio < 0.02
            )
        else:
            # Lenient mode: >80% Gurmukhi
            is_valid = analysis.script_purity >= 0.80
        
        return is_valid, analysis
    
    def _transliterate_latin_word(self, word: str) -> str:
        """
        Attempt basic transliteration of Latin word to Gurmukhi.
        
        This is a simple phonetic approximation, not a proper transliteration.
        """
        word_lower = word.lower()
        result = []
        i = 0
        
        while i < len(word_lower):
            # Try two-character combinations first
            if i + 1 < len(word_lower):
                two_char = word_lower[i:i+2]
                if two_char in self.LATIN_TO_GURMUKHI:
                    result.append(self.LATIN_TO_GURMUKHI[two_char])
                    i += 2
                    continue
            
            # Try single character
            char = word_lower[i]
            if char in self.LATIN_TO_GURMUKHI:
                result.append(self.LATIN_TO_GURMUKHI[char])
            elif char.isalpha():
                # Unknown letter, skip
                pass
            else:
                # Keep non-letter characters
                result.append(char)
            i += 1
        
        return ''.join(result)
    
    def _convert_devanagari(self, text: str) -> str:
        """Convert Devanagari characters to Gurmukhi equivalents."""
        result = []
        for char in text:
            if char in self.DEVANAGARI_TO_GURMUKHI:
                result.append(self.DEVANAGARI_TO_GURMUKHI[char])
            else:
                result.append(char)
        return ''.join(result)
    
    def repair(
        self,
        text: str,
        attempt_transliteration: bool = True,
        preserve_punctuation: bool = True
    ) -> Tuple[str, bool]:
        """
        Repair text by removing or converting non-Gurmukhi characters.
        
        Args:
            text: Text to repair
            attempt_transliteration: Try to transliterate Latin/Devanagari
            preserve_punctuation: Keep punctuation marks
        
        Returns:
            Tuple of (repaired_text, was_modified)
        """
        original = text
        
        # Step 1: Convert Devanagari to Gurmukhi
        if attempt_transliteration:
            text = self._convert_devanagari(text)
        
        # Step 2: Handle Latin sequences
        if attempt_transliteration:
            # Find Latin word sequences and transliterate
            latin_word_pattern = re.compile(r'[A-Za-z]+')
            
            def replace_latin(match):
                latin_word = match.group(0)
                # Only transliterate short words (likely phonetic)
                if len(latin_word) <= 10:
                    return self._transliterate_latin_word(latin_word)
                # Long sequences (likely English) - remove
                return ''
            
            text = latin_word_pattern.sub(replace_latin, text)
        
        # Step 3: Filter remaining non-allowed characters
        result = []
        for char in text:
            classification = self._classify_char(char)
            
            if classification == 'gurmukhi':
                result.append(char)
            elif classification in ('space', 'digit'):
                result.append(char)
            elif classification == 'punct' and preserve_punctuation:
                result.append(char)
            # Skip other characters
        
        repaired = ''.join(result)
        
        # Clean up multiple spaces
        repaired = re.sub(r' +', ' ', repaired).strip()
        
        was_modified = repaired != original
        
        if was_modified:
            logger.debug(f"Script repair: '{original[:50]}...' -> '{repaired[:50]}...'")
        
        return repaired, was_modified
    
    def enforce(
        self,
        text: str,
        strict: bool = True,
        repair_on_fail: bool = True
    ) -> Tuple[str, ScriptAnalysis, bool]:
        """
        Enforce Gurmukhi script on text.
        
        Args:
            text: Text to enforce
            strict: Strict validation threshold
            repair_on_fail: Attempt repair if validation fails
        
        Returns:
            Tuple of (output_text, analysis, was_repaired)
        """
        is_valid, analysis = self.validate(text, strict)
        
        if is_valid:
            return text, analysis, False
        
        if repair_on_fail:
            repaired, _ = self.repair(text)
            _, new_analysis = self.validate(repaired, strict)
            return repaired, new_analysis, True
        
        return text, analysis, False


def enforce_gurmukhi(
    text: str,
    mode: DomainMode = DomainMode.SGGS,
    strict: bool = True
) -> str:
    """
    Convenience function to enforce Gurmukhi script.
    
    Args:
        text: Text to enforce
        mode: Domain mode
        strict: Strict enforcement
    
    Returns:
        Gurmukhi-only text
    """
    lock = ScriptLock(mode)
    result, _, _ = lock.enforce(text, strict=strict)
    return result


def analyze_script(text: str) -> ScriptAnalysis:
    """
    Convenience function to analyze script composition.
    
    Args:
        text: Text to analyze
    
    Returns:
        ScriptAnalysis with metrics
    """
    lock = ScriptLock()
    return lock.analyze(text)


def is_gurmukhi_pure(text: str, threshold: float = 0.95) -> bool:
    """
    Check if text meets Gurmukhi purity threshold.
    
    Args:
        text: Text to check
        threshold: Minimum purity ratio (default 95%)
    
    Returns:
        True if text is sufficiently Gurmukhi
    """
    analysis = analyze_script(text)
    return analysis.script_purity >= threshold

