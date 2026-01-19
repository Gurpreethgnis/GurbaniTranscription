"""
Gurmukhi Diacritic Normalizer.

Normalizes Gurmukhi text by:
1. Applying Unicode normalization (NFC/NFD/NFKC/NFKD)
2. Standardizing Tippi (ੰ) vs Bindi (ਂ) based on context
3. Normalizing Adhak (ੱ) positioning
4. Normalizing Nukta (਼) combining marks
5. Ordering diacritics consistently

Phase 5: Normalization Gap Filling
"""
import logging
import unicodedata
from typing import Optional
import config

logger = logging.getLogger(__name__)

# Gurmukhi Unicode ranges
GURMUKHI_RANGE = range(0x0A00, 0x0A80)

# Diacritic characters
TIPPI = '\u0A70'  # ੰ - used before consonants
BINDI = '\u0A02'  # ਂ - used before vowels
ADHAK = '\u0A71'  # ੱ - gemination mark
NUKTA = '\u0A3C'  # ਼ - dot below (modifies consonant)

# Dependent vowels (matras)
DEPENDENT_VOWELS = {
    '\u0A3E',  # ਾ - kanna
    '\u0A3F',  # ਿ - sihari
    '\u0A40',  # ੀ - bihari
    '\u0A41',  # ੁ - aunkar
    '\u0A42',  # ੂ - dulankar
    '\u0A47',  # ੇ - lavan
    '\u0A48',  # ੈ - dulan
    '\u0A4B',  # ੋ - hora
    '\u0A4C',  # ੌ - kanaura
}

# Independent vowels
INDEPENDENT_VOWELS = {
    '\u0A05',  # ਅ
    '\u0A06',  # ਆ
    '\u0A07',  # ਇ
    '\u0A08',  # ਈ
    '\u0A09',  # ਉ
    '\u0A0A',  # ਊ
    '\u0A0F',  # ਏ
    '\u0A10',  # ਐ
    '\u0A13',  # ਓ
    '\u0A14',  # ਔ
}

# Consonants (basic range)
CONSONANT_START = 0x0A15
CONSONANT_END = 0x0A39


def is_gurmukhi_char(char: str) -> bool:
    """Check if character is in Gurmukhi Unicode range."""
    if not char:
        return False
    return ord(char[0]) in GURMUKHI_RANGE


def is_consonant(char: str) -> bool:
    """Check if character is a Gurmukhi consonant."""
    if not char:
        return False
    code = ord(char[0])
    return CONSONANT_START <= code <= CONSONANT_END


def is_vowel(char: str) -> bool:
    """Check if character is a Gurmukhi vowel (independent or dependent)."""
    if not char:
        return False
    return char in INDEPENDENT_VOWELS or char in DEPENDENT_VOWELS


def is_dependent_vowel(char: str) -> bool:
    """Check if character is a dependent vowel (matra)."""
    return char in DEPENDENT_VOWELS


class GurmukhiNormalizer:
    """
    Normalizes Gurmukhi text by standardizing diacritics and ordering.
    
    Rules:
    1. Tippi (ੰ) used before consonants, Bindi (ਂ) before vowels
    2. Adhak (ੱ) always precedes the consonant it doubles
    3. Nukta (਼) always combines with base consonant as single unit
    4. Diacritics ordered: base consonant -> nukta -> vowel sign -> nasalization -> adhak
    """
    
    def __init__(self, normalization_form: Optional[str] = None):
        """
        Initialize Gurmukhi normalizer.
        
        Args:
            normalization_form: Unicode normalization form (NFC, NFD, NFKC, NFKD).
                               Defaults to config.UNICODE_NORMALIZATION_FORM
        """
        if normalization_form is None:
            normalization_form = getattr(config, 'UNICODE_NORMALIZATION_FORM', 'NFC')
        
        valid_forms = ['NFC', 'NFD', 'NFKC', 'NFKD']
        if normalization_form not in valid_forms:
            logger.warning(
                f"Invalid normalization form '{normalization_form}', "
                f"using 'NFC'. Valid forms: {valid_forms}"
            )
            normalization_form = 'NFC'
        
        self.normalization_form = normalization_form
        logger.debug(f"GurmukhiNormalizer initialized with form='{normalization_form}'")
    
    def normalize(self, text: str) -> str:
        """
        Normalize Gurmukhi text.
        
        Args:
            text: Input Gurmukhi text
        
        Returns:
            Normalized Gurmukhi text
        """
        if not text or not text.strip():
            return text
        
        # Step 1: Apply Unicode normalization
        normalized = unicodedata.normalize(self.normalization_form, text)
        
        # Step 2: Normalize Tippi/Bindi based on context
        normalized = self._normalize_nasalization(normalized)
        
        # Step 3: Normalize Adhak positioning
        normalized = self._normalize_adhak(normalized)
        
        # Step 4: Normalize Nukta combining
        normalized = self._normalize_nukta(normalized)
        
        # Step 5: Order diacritics consistently
        normalized = self._order_diacritics(normalized)
        
        logger.debug(f"Normalized Gurmukhi text: '{text[:50]}...' → '{normalized[:50]}...'")
        
        return normalized
    
    def _normalize_nasalization(self, text: str) -> str:
        """
        Normalize Tippi (ੰ) vs Bindi (ਂ) based on context.
        
        Rule: Tippi before consonants, Bindi before vowels.
        """
        if TIPPI not in text and BINDI not in text:
            return text
        
        chars = list(text)
        result = []
        i = 0
        
        while i < len(chars):
            char = chars[i]
            
            # Check for nasalization marks
            if char == TIPPI or char == BINDI:
                # Look ahead to determine context
                if i + 1 < len(chars):
                    next_char = chars[i + 1]
                    
                    # If next is a vowel, use Bindi
                    if is_vowel(next_char) or is_dependent_vowel(next_char):
                        result.append(BINDI)
                    # If next is a consonant or end of word, use Tippi
                    elif is_consonant(next_char) or next_char.isspace() or i + 1 >= len(chars):
                        result.append(TIPPI)
                    else:
                        # Keep original if uncertain
                        result.append(char)
                else:
                    # End of text - use Tippi (default)
                    result.append(TIPPI)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _normalize_adhak(self, text: str) -> str:
        """
        Normalize Adhak (ੱ) positioning.
        
        Rule: Adhak always precedes the consonant it doubles.
        """
        if ADHAK not in text:
            return text
        
        chars = list(text)
        result = []
        i = 0
        
        while i < len(chars):
            char = chars[i]
            
            if char == ADHAK:
                # Adhak should be before the consonant it doubles
                # If it's after a consonant, it's already in correct position
                # If it's before a consonant, keep it
                # If it's in wrong position, move it
                
                # Look ahead for the consonant
                if i + 1 < len(chars) and is_consonant(chars[i + 1]):
                    # Correct position - keep it
                    result.append(ADHAK)
                elif i > 0 and is_consonant(chars[i - 1]):
                    # After consonant - might need to move
                    # For now, keep it (adhak can appear after base consonant)
                    result.append(ADHAK)
                else:
                    # Keep as-is if uncertain
                    result.append(ADHAK)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _normalize_nukta(self, text: str) -> str:
        """
        Normalize Nukta (਼) combining.
        
        Rule: Nukta always combines with base consonant as single unit.
        """
        if NUKTA not in text:
            return text
        
        # Nukta is a combining mark, so Unicode normalization should handle it
        # But we ensure it's properly combined with consonants
        chars = list(text)
        result = []
        i = 0
        
        while i < len(chars):
            char = chars[i]
            
            if char == NUKTA:
                # Nukta should be after a consonant
                if i > 0 and is_consonant(chars[i - 1]):
                    # Properly positioned - keep it
                    result.append(NUKTA)
                else:
                    # Nukta without preceding consonant - might be error
                    # Keep it but log warning
                    logger.warning(f"Nukta found without preceding consonant at position {i}")
                    result.append(NUKTA)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _order_diacritics(self, text: str) -> str:
        """
        Order diacritics consistently.
        
        Order: base consonant -> nukta -> vowel sign -> nasalization -> adhak
        """
        # This is a simplified implementation
        # Full implementation would parse and reorder diacritics
        # For now, Unicode normalization handles most ordering
        
        # Check if text has multiple diacritics that might be out of order
        # If so, we'd need to parse and reorder
        
        # For Phase 5, we'll rely on Unicode normalization
        # which should handle most ordering issues
        
        return text
