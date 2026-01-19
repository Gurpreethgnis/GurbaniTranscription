"""
Script conversion service for dual-output generation.

This module provides:
1. Automatic script detection
2. Shahmukhi to Gurmukhi conversion
3. Gurmukhi to Roman transliteration
4. Dual-output (Gurmukhi + Roman) generation

Phase 3: Script Conversion Module
Phase 5: Added Gurmukhi normalization
"""
import logging
import unicodedata
from typing import Tuple, Dict, Optional, List
from data.gurmukhi_normalizer import GurmukhiNormalizer
from data.script_mappings import (
    is_gurmukhi_char,
    is_shahmukhi_char,
    is_devanagari_char,
    is_latin_char,
    get_gurmukhi_unicode_range,
    get_shahmukhi_unicode_range,
    get_devanagari_unicode_range,
    SHAHMUKHI_TO_GURMUKHI_CONSONANTS,
    SHAHMUKHI_VOWELS,
    SHAHMUKHI_DIACRITICS,
    SHAHMUKHI_NUKTA_VARIANTS,
    COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI,
    GURMUKHI_INDEPENDENT_VOWELS,
    GURMUKHI_DEPENDENT_VOWELS,
    GURMUKHI_CONSONANTS,
    GURMUKHI_SPECIAL_MARKS,
)
from core.errors import ScriptConversionError

logger = logging.getLogger(__name__)


class ScriptDetector:
    """
    Detects the script of input text.
    
    Supports detection of:
    - Gurmukhi (ਪੰਜਾਬੀ)
    - Shahmukhi (Arabic-based Punjabi: پنجابی)
    - Devanagari (देवनागरी)
    - English/Latin (A-Z, a-z)
    - Mixed (combination of scripts)
    """
    
    # Unicode ranges for script detection
    GURMUKHI_RANGE = get_gurmukhi_unicode_range()
    SHAHMUKHI_RANGE = get_shahmukhi_unicode_range()
    DEVANAGARI_RANGE = get_devanagari_unicode_range()
    LATIN_RANGE = range(0x0041, 0x007B)  # A-Z, a-z
    
    # Minimum character threshold for script detection
    MIN_CHARS_FOR_DETECTION = 2
    
    def detect_script(self, text: str) -> Tuple[str, float]:
        """
        Detect predominant script in text.
        
        Args:
            text: Input text to analyze
        
        Returns:
            Tuple of (script_name, confidence) where:
            - script_name: "gurmukhi", "shahmukhi", "devanagari", "english", "mixed", or "unknown"
            - confidence: Float between 0.0 and 1.0
        """
        if not text or not text.strip():
            return "empty", 1.0
        
        # Remove whitespace and punctuation for analysis
        text_clean = ''.join(c for c in text if c.isalnum() or c.isspace())
        text_clean = text_clean.strip()
        
        if not text_clean:
            return "unknown", 0.0
        
        # Count characters by script
        script_counts: Dict[str, int] = {
            "gurmukhi": 0,
            "shahmukhi": 0,
            "devanagari": 0,
            "english": 0,
            "other": 0
        }
        
        total_chars = 0
        
        for char in text_clean:
            if char.isspace():
                continue
            
            total_chars += 1
            
            if is_gurmukhi_char(char):
                script_counts["gurmukhi"] += 1
            elif is_shahmukhi_char(char):
                script_counts["shahmukhi"] += 1
            elif is_devanagari_char(char):
                script_counts["devanagari"] += 1
            elif is_latin_char(char):
                script_counts["english"] += 1
            else:
                script_counts["other"] += 1
        
        # If too few characters, return unknown
        if total_chars < self.MIN_CHARS_FOR_DETECTION:
            logger.debug(f"Insufficient characters for detection: {total_chars}")
            return "unknown", 0.5
        
        # Calculate percentages
        script_percentages: Dict[str, float] = {}
        for script, count in script_counts.items():
            if script != "other":
                script_percentages[script] = count / total_chars if total_chars > 0 else 0.0
        
        # Find dominant script
        dominant_script = max(script_percentages.items(), key=lambda x: x[1])
        script_name, percentage = dominant_script
        
        # Check if mixed (multiple scripts with significant presence)
        significant_scripts = [
            s for s, p in script_percentages.items()
            if p >= 0.2  # At least 20% presence
        ]
        
        if len(significant_scripts) > 1:
            # Mixed script
            logger.debug(f"Mixed script detected: {significant_scripts}")
            # Calculate confidence based on how dominant the primary script is
            confidence = percentage
            return "mixed", confidence
        
        # Single script detected
        confidence = percentage
        
        # Adjust confidence based on total character count
        # More characters = higher confidence
        if total_chars >= 10:
            confidence = min(1.0, confidence * 1.1)  # Boost for longer text
        elif total_chars < 5:
            confidence = confidence * 0.8  # Reduce for very short text
        
        logger.debug(
            f"Detected script: {script_name} "
            f"(confidence: {confidence:.2f}, chars: {total_chars})"
        )
        
        return script_name, min(1.0, confidence)
    
    def detect_script_with_language_hint(
        self,
        text: str,
        language_code: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Detect script with optional language code hint from ASR.
        
        Args:
            text: Input text to analyze
            language_code: Optional language code from ASR (e.g., "ur", "pa", "hi", "en")
        
        Returns:
            Tuple of (script_name, confidence)
        """
        script, confidence = self.detect_script(text)
        
        # Adjust based on language hint
        if language_code:
            language_to_script = {
                "ur": "shahmukhi",  # Urdu typically uses Shahmukhi
                "pa": "gurmukhi",   # Punjabi typically uses Gurmukhi
                "hi": "devanagari", # Hindi uses Devanagari
                "en": "english",    # English
            }
            
            expected_script = language_to_script.get(language_code.lower())
            
            if expected_script:
                if script == expected_script:
                    # Boost confidence if matches
                    confidence = min(1.0, confidence * 1.1)
                elif script == "mixed" or script == "unknown":
                    # If uncertain, prefer the language hint
                    script = expected_script
                    confidence = 0.7  # Moderate confidence when relying on hint
                else:
                    # Mismatch - reduce confidence slightly
                    confidence = confidence * 0.9
                    logger.warning(
                        f"Script mismatch: detected '{script}' but language hint suggests '{expected_script}'"
                    )
        
        return script, confidence


class ShahmukhiToGurmukhiConverter:
    """
    Converts Shahmukhi (Arabic-based Punjabi) to Gurmukhi script.
    
    Handles:
    - Character-by-character conversion
    - Vowel inference (Arabic is abjad, vowels often implicit)
    - Common word dictionary lookup
    - RTL to LTR conversion
    - Special characters (nukta, nasalization)
    """
    
    def __init__(self, enable_dictionary: bool = True):
        """
        Initialize converter.
        
        Args:
            enable_dictionary: Use common word dictionary for disambiguation
        """
        self.consonant_map = SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        self.vowel_map = SHAHMUKHI_VOWELS
        self.diacritic_map = SHAHMUKHI_DIACRITICS
        self.nukta_variants = SHAHMUKHI_NUKTA_VARIANTS
        self.common_words = COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI if enable_dictionary else {}
        self.enable_dictionary = enable_dictionary
        
        logger.debug(f"ShahmukhiToGurmukhiConverter initialized (dictionary: {enable_dictionary})")
    
    def convert(self, text: str) -> Tuple[str, float]:
        """
        Convert Shahmukhi text to Gurmukhi.
        
        Args:
            text: Shahmukhi text to convert
        
        Returns:
            Tuple of (gurmukhi_text, confidence)
        """
        if not text or not text.strip():
            return "", 1.0
        
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Split into words (preserve spaces)
        words = text.split()
        converted_words = []
        total_confidence = 0.0
        word_count = 0
        
        for word in words:
            if not word:
                converted_words.append("")
                continue
            
            # Try dictionary lookup first
            if self.enable_dictionary and word in self.common_words:
                converted_word = self.common_words[word]
                confidence = 0.95  # High confidence for dictionary matches
                logger.debug(f"Dictionary match: '{word}' → '{converted_word}'")
            else:
                # Character-by-character conversion
                converted_word, confidence = self._convert_word(word)
            
            converted_words.append(converted_word)
            total_confidence += confidence
            word_count += 1
        
        # Calculate average confidence
        avg_confidence = total_confidence / word_count if word_count > 0 else 1.0
        
        # Join words back
        result = " ".join(converted_words)
        
        logger.debug(
            f"Converted {word_count} words, avg confidence: {avg_confidence:.2f}"
        )
        
        return result, avg_confidence
    
    def _convert_word(self, word: str) -> Tuple[str, float]:
        """
        Convert a single word from Shahmukhi to Gurmukhi.
        
        Args:
            word: Single word in Shahmukhi
        
        Returns:
            Tuple of (gurmukhi_word, confidence)
        """
        if not word:
            return "", 1.0
        
        # Reverse word (Shahmukhi is RTL, Gurmukhi is LTR)
        # But we'll process LTR and build result
        chars = list(word)
        result_chars: List[str] = []
        confidence_sum = 0.0
        char_count = 0
        
        i = 0
        while i < len(chars):
            char = chars[i]
            
            # Check for nukta variants (two-character sequences)
            if i + 1 < len(chars):
                two_char = char + chars[i + 1]
                if two_char in self.nukta_variants:
                    result_chars.append(self.nukta_variants[two_char])
                    confidence_sum += 0.9
                    char_count += 1
                    i += 2
                    continue
            
            # Check for diacritics
            if char in self.diacritic_map:
                # Diacritic modifies previous character
                if result_chars:
                    # Add vowel mark to previous character
                    result_chars[-1] += self.diacritic_map[char]
                confidence_sum += 0.8
                char_count += 1
                i += 1
                continue
            
            # Check for vowels (context-dependent)
            if char in self.vowel_map:
                vowel_options = self.vowel_map[char]
                # Simple heuristic: if at start, use independent vowel
                # Otherwise, use dependent vowel
                if not result_chars:
                    # Start of word - use independent vowel
                    result_chars.append(vowel_options[0])
                else:
                    # After consonant - use dependent vowel if available
                    if len(vowel_options) > 1:
                        result_chars.append(vowel_options[1])
                    else:
                        result_chars.append(vowel_options[0])
                confidence_sum += 0.85
                char_count += 1
                i += 1
                continue
            
            # Check for consonants
            if char in self.consonant_map:
                gurmukhi_char = self.consonant_map[char]
                if gurmukhi_char:  # Skip empty mappings (like ع)
                    result_chars.append(gurmukhi_char)
                    confidence_sum += 0.9
                    char_count += 1
                i += 1
                continue
            
            # Unknown character - pass through or skip
            if char.isspace() or char.isdigit() or char in ".,!?;:()[]{}\"'":
                result_chars.append(char)
                confidence_sum += 1.0  # Punctuation is always correct
            else:
                # Unknown character - log and skip
                logger.warning(f"Unknown Shahmukhi character: '{char}' (U+{ord(char):04X})")
                confidence_sum += 0.5  # Low confidence for unknown
            char_count += 1
            i += 1
        
        # Calculate confidence
        confidence = confidence_sum / char_count if char_count > 0 else 1.0
        
        # Join characters
        result = "".join(result_chars)
        
        return result, confidence
    
    def _convert_mixed(self, text: str) -> Tuple[str, float]:
        """
        Convert mixed-script text (best-effort).
        
        Args:
            text: Mixed script text
        
        Returns:
            Tuple of (converted_text, confidence)
        """
        # Split by words and convert only Shahmukhi words
        words = text.split()
        converted_words = []
        total_confidence = 0.0
        word_count = 0
        
        for word in words:
            # Check if word contains Shahmukhi
            has_shahmukhi = any(is_shahmukhi_char(c) for c in word)
            
            if has_shahmukhi:
                converted, conf = self._convert_word(word)
                converted_words.append(converted)
                total_confidence += conf
            else:
                # Keep as-is (Gurmukhi, English, etc.)
                converted_words.append(word)
                total_confidence += 1.0
            
            word_count += 1
        
        avg_confidence = total_confidence / word_count if word_count > 0 else 1.0
        result = " ".join(converted_words)
        
        return result, avg_confidence


class GurmukhiToRomanTransliterator:
    """
    Transliterates Gurmukhi text to Roman script.
    
    Supports multiple transliteration schemes:
    - ISO 15919 (academic/scholarly)
    - IAST (Sanskrit-based)
    - Practical (simplified, user-friendly)
    
    Handles:
    - Independent and dependent vowels
    - Consonants and conjuncts
    - Nasalization (bindi, tippi)
    - Gemination (adhak)
    - Nukta consonants
    """
    
    def __init__(self, scheme: str = "practical"):
        """
        Initialize transliterator.
        
        Args:
            scheme: Transliteration scheme ("iso15919", "iast", "practical")
        """
        self.scheme = scheme
        self.independent_vowels = GURMUKHI_INDEPENDENT_VOWELS
        self.dependent_vowels = GURMUKHI_DEPENDENT_VOWELS
        self.consonants = GURMUKHI_CONSONANTS
        self.special_marks = GURMUKHI_SPECIAL_MARKS
        
        logger.debug(f"GurmukhiToRomanTransliterator initialized with scheme='{scheme}'")
    
    def transliterate(self, gurmukhi_text: str) -> str:
        """
        Transliterate Gurmukhi text to Roman script.
        
        Args:
            gurmukhi_text: Gurmukhi text to transliterate
        
        Returns:
            Roman transliteration
        """
        if not gurmukhi_text or not gurmukhi_text.strip():
            return ""
        
        # Process character by character
        result_chars = []
        chars = list(gurmukhi_text)
        
        i = 0
        while i < len(chars):
            char = chars[i]
            
            # Check for independent vowels
            if char in self.independent_vowels:
                result_chars.append(self.independent_vowels[char])
                i += 1
                continue
            
            # Check for consonants
            if char in self.consonants:
                consonant = self.consonants[char]
                
                # Look ahead for dependent vowel or special marks
                has_vowel = False
                has_nasal = False
                
                if i + 1 < len(chars):
                    next_char = chars[i + 1]
                    
                    # Check for adhak (gemination) first
                    if next_char == 'ੱ':
                        # Double the following consonant
                        if i + 2 < len(chars):
                            next_consonant = chars[i + 2]
                            if next_consonant in self.consonants:
                                result_chars.append(consonant)
                                result_chars.append(self.consonants[next_consonant])
                                i += 3
                                continue
                    
                    # Check for nasalization (bindi/tippi)
                    if next_char in ['ਂ', 'ੰ']:
                        has_nasal = True
                        # Check if there's a vowel after nasal
                        if i + 2 < len(chars) and chars[i + 2] in self.dependent_vowels:
                            vowel = self.dependent_vowels[chars[i + 2]]
                            result_chars.append(consonant + vowel + 'ṃ')
                            i += 3
                            continue
                        else:
                            result_chars.append(consonant + 'aṃ')
                            i += 2
                            continue
                    
                    # Check for dependent vowel
                    if next_char in self.dependent_vowels:
                        vowel = self.dependent_vowels[next_char]
                        result_chars.append(consonant + vowel)
                        i += 2
                        continue
                
                # Standalone consonant (implicit 'a' vowel)
                result_chars.append(consonant + 'a')
                i += 1
                continue
            
            # Check for dependent vowels (standalone - shouldn't happen, but handle gracefully)
            if char in self.dependent_vowels:
                # This is unusual - might be a formatting issue
                result_chars.append(self.dependent_vowels[char])
                i += 1
                continue
            
            # Check for special marks
            if char in self.special_marks:
                mark = self.special_marks[char]
                if mark:  # Only add if mark has a representation
                    result_chars.append(mark)
                i += 1
                continue
            
            # Preserve whitespace, punctuation, numbers
            if char.isspace() or char.isdigit() or char in ".,!?;:()[]{}\"'":
                result_chars.append(char)
                i += 1
                continue
            
            # Unknown character - pass through
            result_chars.append(char)
            i += 1
        
        result = "".join(result_chars)
        
        # Post-process: clean up common issues
        result = self._post_process(result)
        
        return result
    
    def _post_process(self, text: str) -> str:
        """
        Post-process transliteration to fix common issues.
        
        Args:
            text: Raw transliteration
        
        Returns:
            Cleaned transliteration
        """
        # Remove double 'a' vowels (consonant + 'a' + vowel 'a')
        import re
        
        # Fix: consonant + 'a' + 'ā' -> consonant + 'ā'
        text = re.sub(r'([a-z]+)aā', r'\1ā', text)
        text = re.sub(r'([a-z]+)ai', r'\1ai', text)
        text = re.sub(r'([a-z]+)ae', r'\1e', text)
        text = re.sub(r'([a-z]+)ao', r'\1o', text)
        
        # Capitalize first letter of each word (for practical scheme)
        if self.scheme == "practical":
            words = text.split()
            capitalized_words = []
            for word in words:
                if word and word[0].isalpha():
                    capitalized_words.append(word[0].upper() + word[1:])
                else:
                    capitalized_words.append(word)
            text = " ".join(capitalized_words)
        
        return text


class ScriptConverter:
    """
    Main service for script conversion and transliteration.
    
    Converts ASR output (which may be in Shahmukhi/Urdu) to:
    1. Gurmukhi script (ਪੰਜਾਬੀ)
    2. Roman transliteration (Panjābī)
    
    This is the unified interface that coordinates:
    - Script detection
    - Shahmukhi to Gurmukhi conversion
    - Gurmukhi to Roman transliteration
    """
    
    def __init__(
        self,
        roman_scheme: str = "practical",
        enable_dictionary_lookup: bool = True
    ):
        """
        Initialize script converter.
        
        Args:
            roman_scheme: Romanization scheme ("iso15919", "iast", "practical")
            enable_dictionary_lookup: Use common word dictionary for disambiguation
        """
        self.detector = ScriptDetector()
        self.shahmukhi_converter = ShahmukhiToGurmukhiConverter(
            enable_dictionary=enable_dictionary_lookup
        )
        self.romanizer = GurmukhiToRomanTransliterator(scheme=roman_scheme)
        self.gurmukhi_normalizer = GurmukhiNormalizer()  # Phase 5: Gurmukhi diacritic normalization
        self.enable_dictionary = enable_dictionary_lookup
        
        logger.info(f"ScriptConverter initialized with scheme='{roman_scheme}', dictionary={enable_dictionary_lookup}")
    
    def convert(
        self,
        text: str,
        source_language: Optional[str] = None
    ) -> 'ConvertedText':
        """
        Convert text to dual-output (Gurmukhi + Roman).
        
        Args:
            text: Input text from ASR
            source_language: Language code from ASR (e.g., "ur", "pa", "hi")
        
        Returns:
            ConvertedText with Gurmukhi and Roman representations
        
        Raises:
            ScriptConversionError: If conversion fails critically
        """
        from core.models import ConvertedText
        
        if not text or not text.strip():
            return ConvertedText(
                original=text,
                original_script="empty",
                gurmukhi="",
                roman="",
                confidence=1.0,
                needs_review=False
            )
        
        try:
            # Step 0: Apply Unicode normalization (Phase 5)
            try:
                import config
                unicode_form = getattr(config, 'UNICODE_NORMALIZATION_FORM', 'NFC')
            except ImportError:
                unicode_form = 'NFC'
            
            text = unicodedata.normalize(unicode_form, text)
            
            # Step 1: Detect script
            script, detect_confidence = self.detector.detect_script_with_language_hint(
                text, source_language
            )
            logger.debug(f"Detected script: {script} (confidence: {detect_confidence:.2f})")
            
            # Step 2: Convert to Gurmukhi if needed
            if script == "gurmukhi":
                gurmukhi_text = text
                convert_confidence = 1.0
                logger.debug("Input already in Gurmukhi, no conversion needed")
            elif script == "shahmukhi":
                gurmukhi_text, convert_confidence = self.shahmukhi_converter.convert(text)
                logger.debug(
                    f"Converted Shahmukhi → Gurmukhi "
                    f"(confidence: {convert_confidence:.2f})"
                )
            elif script == "english":
                # Keep English as-is for Gurmukhi field, romanize as-is
                gurmukhi_text = text
                convert_confidence = 1.0
                logger.debug("Input is English, keeping as-is")
            elif script == "mixed":
                # Attempt best-effort conversion
                gurmukhi_text, convert_confidence = self.shahmukhi_converter._convert_mixed(text)
                logger.debug(
                    f"Converted mixed script (confidence: {convert_confidence:.2f})"
                )
            else:
                # Unknown script - keep as-is with low confidence
                gurmukhi_text = text
                convert_confidence = 0.5
                logger.warning(f"Unknown script '{script}', keeping text as-is")
            
            # Step 2.5: Normalize Gurmukhi text (Phase 5)
            if script == "gurmukhi" or (script in ["shahmukhi", "mixed"] and gurmukhi_text):
                # Apply Gurmukhi-specific normalization
                gurmukhi_text = self.gurmukhi_normalizer.normalize(gurmukhi_text)
                logger.debug("Applied Gurmukhi normalization")
            
            # Step 3: Romanize
            if script == "english":
                roman_text = text
            else:
                roman_text = self.romanizer.transliterate(gurmukhi_text)
                logger.debug(f"Transliterated to Roman: {roman_text[:50]}...")
            
            # Step 4: Calculate overall confidence
            overall_confidence = detect_confidence * convert_confidence
            
            # Determine if review is needed
            # Import config threshold (will be added in milestone 3.7)
            try:
                import config
                threshold = getattr(config, 'SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD', 0.7)
            except ImportError:
                threshold = 0.7
            
            needs_review = overall_confidence < threshold
            
            if needs_review:
                logger.warning(
                    f"Low conversion confidence ({overall_confidence:.2f}), "
                    f"flagging for review"
                )
            
            return ConvertedText(
                original=text,
                original_script=script,
                gurmukhi=gurmukhi_text,
                roman=roman_text,
                confidence=overall_confidence,
                needs_review=needs_review
            )
        
        except Exception as e:
            logger.error(f"Script conversion failed: {e}", exc_info=True)
            raise ScriptConversionError(
                source_script=script if 'script' in locals() else "unknown",
                target_script="gurmukhi",
                reason=str(e)
            )
    
    def convert_segments(
        self,
        segments: list,
        source_language: Optional[str] = None
    ) -> list:
        """
        Convert a list of segments, updating text fields.
        
        Args:
            segments: List of segment dicts with 'text' field
            source_language: Language code from ASR
        
        Returns:
            Updated segments with converted text
        """
        converted_segments = []
        
        for segment in segments:
            text = segment.get('text', '')
            converted = self.convert(text, source_language)
            
            # Update segment with converted text
            updated_segment = segment.copy()
            updated_segment['gurmukhi'] = converted.gurmukhi
            updated_segment['roman'] = converted.roman
            updated_segment['original_script'] = converted.original_script
            updated_segment['script_confidence'] = converted.confidence
            
            if converted.needs_review:
                updated_segment['needs_review'] = True
            
            converted_segments.append(updated_segment)
        
        return converted_segments
