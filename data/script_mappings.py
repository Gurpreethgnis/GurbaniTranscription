"""
Unicode character mapping tables for script conversion.

This module contains:
1. Shahmukhi (Arabic-based Punjabi) to Gurmukhi mapping
2. Gurmukhi to Roman (ISO 15919 based) transliteration mapping
3. Special handling for nasalization, aspiration, nukta, etc.

Unicode Ranges:
- Gurmukhi: U+0A00 - U+0A7F
- Shahmukhi (Arabic): U+0600 - U+06FF
- Devanagari: U+0900 - U+097F
"""
from typing import Dict, List, Tuple

# ============================================================================
# SHAHMUKHI TO GURMUKHI CONSONANT MAPPINGS
# ============================================================================

SHAHMUKHI_TO_GURMUKHI_CONSONANTS: Dict[str, str] = {
    # Basic consonants
    'ب': 'ਬ',  # ba
    'پ': 'ਪ',  # pa
    'ت': 'ਤ',  # ta
    'ٹ': 'ਟ',  # tta (retroflex)
    'ث': 'ਸ',  # sa (Arabic origin, often mapped to ਸ)
    'ج': 'ਜ',  # ja
    'چ': 'ਚ',  # cha
    'ح': 'ਹ',  # ha (Arabic ha, often mapped to ਹ)
    'خ': 'ਖ਼',  # kha (with nukta)
    'د': 'ਦ',  # da
    'ڈ': 'ਡ',  # dda (retroflex)
    'ذ': 'ਜ਼',  # za (with nukta)
    'ر': 'ਰ',  # ra
    'ڑ': 'ੜ',  # rra (retroflex)
    'ز': 'ਜ਼',  # za (with nukta)
    'ژ': 'ਜ਼',  # zha (with nukta)
    'س': 'ਸ',  # sa
    'ش': 'ਸ਼',  # sha (with nukta)
    'ص': 'ਸ',  # sa (Arabic origin)
    'ض': 'ਜ਼',  # za (Arabic origin)
    'ط': 'ਤ',  # ta (Arabic origin)
    'ظ': 'ਜ਼',  # za (Arabic origin)
    'ع': '',    # ayn (often silent in Punjabi, or becomes ਅ)
    'غ': 'ਗ਼',  # gha (with nukta)
    'ف': 'ਫ਼',  # fa (with nukta)
    'ق': 'ਕ',  # qa
    'ک': 'ਕ',  # ka
    'گ': 'ਗ',  # ga
    'ل': 'ਲ',  # la
    'م': 'ਮ',  # ma
    'ن': 'ਨ',  # na
    'ں': 'ਂ',   # nasal mark (bindi)
    'ہ': 'ਹ',  # ha
    'ھ': '',   # aspiration mark (modifies previous consonant)
    'و': 'ਵ',  # va (when consonant), 'ਓ' or 'ੋ' when vowel
    'ی': 'ਯ',  # ya (when consonant), 'ਈ' or 'ੀ' when vowel
    'ے': 'ਏ',  # ye (vowel marker)
    'ۓ': 'ਏ',  # ye (variant)
}

# Nukta variants (special characters with dot below)
SHAHMUKHI_NUKTA_VARIANTS: Dict[str, str] = {
    'کھ': 'ਖ਼',  # kha with nukta
    'گھ': 'ਗ਼',  # gha with nukta
    'پھ': 'ਫ਼',  # pha with nukta
    'جھ': 'ਝ',  # jha
    'چھ': 'ਛ',  # cha
    'ٹھ': 'ਠ',  # ttha
    'ڈھ': 'ਢ',  # ddha
    'بھ': 'ਭ',  # bha
    'دھ': 'ਧ',  # dha
    'تھ': 'ਥ',  # tha
}

# ============================================================================
# SHAHMUKHI VOWEL MAPPINGS (Context-dependent)
# ============================================================================

# Vowel mappings - context matters for Arabic script
SHAHMUKHI_VOWELS: Dict[str, List[str]] = {
    # Alif (ا) - can be initial ਅ or medial ਾ
    'ا': ['ਅ', 'ਾ'],
    # Alif with hamza (أ) - initial vowel
    'أ': ['ਅ'],
    # Alif with madda (آ) - long aa
    'آ': ['ਆ'],
    # Waw (و) - can be ਵ (consonant), ਓ (vowel), or ੋ (vowel mark)
    'و': ['ਵ', 'ਓ', 'ੋ'],
    # Ye (ی) - can be ਯ (consonant), ਈ (vowel), or ੀ (vowel mark)
    'ی': ['ਯ', 'ਈ', 'ੀ'],
    # Ye (ے) - vowel marker
    'ے': ['ਏ', 'ੇ'],
    # Hamza (ء) - glottal stop, often silent
    'ء': [''],
}

# Vowel diacritics (zer, zabar, pesh, etc.)
SHAHMUKHI_DIACRITICS: Dict[str, str] = {
    'َ': 'ਾ',   # zabar (a)
    'ِ': 'ੀ',   # zer (i)
    'ُ': 'ੂ',   # pesh (u)
    'ً': 'ਂ',   # tanwin (nasal)
    'ٍ': 'ਂ',   # tanwin (nasal)
    'ٌ': 'ਂ',   # tanwin (nasal)
}

# ============================================================================
# GURMUKHI TO ROMAN TRANSLITERATION
# ============================================================================

# Independent vowels
GURMUKHI_INDEPENDENT_VOWELS: Dict[str, str] = {
    'ਅ': 'a',
    'ਆ': 'ā',
    'ਇ': 'i',
    'ਈ': 'ī',
    'ਉ': 'u',
    'ਊ': 'ū',
    'ਏ': 'e',
    'ਐ': 'ai',
    'ਓ': 'o',
    'ਔ': 'au',
}

# Dependent vowels (matras)
GURMUKHI_DEPENDENT_VOWELS: Dict[str, str] = {
    'ਾ': 'ā',   # kanna
    'ਿ': 'i',   # sihari
    'ੀ': 'ī',   # bihari
    'ੁ': 'u',   # aunkar
    'ੂ': 'ū',   # dulankar
    'ੇ': 'e',   # lavan
    'ੈ': 'ai',  # dulan
    'ੋ': 'o',   # hora
    'ੌ': 'au',  # kanaura
}

# Consonants
GURMUKHI_CONSONANTS: Dict[str, str] = {
    'ਕ': 'k',
    'ਖ': 'kh',
    'ਗ': 'g',
    'ਘ': 'gh',
    'ਙ': 'ṅ',
    'ਚ': 'c',
    'ਛ': 'ch',
    'ਜ': 'j',
    'ਝ': 'jh',
    'ਞ': 'ñ',
    'ਟ': 'ṭ',
    'ਠ': 'ṭh',
    'ਡ': 'ḍ',
    'ਢ': 'ḍh',
    'ਣ': 'ṇ',
    'ਤ': 't',
    'ਥ': 'th',
    'ਦ': 'd',
    'ਧ': 'dh',
    'ਨ': 'n',
    'ਪ': 'p',
    'ਫ': 'ph',
    'ਬ': 'b',
    'ਭ': 'bh',
    'ਮ': 'm',
    'ਯ': 'y',
    'ਰ': 'r',
    'ਲ': 'l',
    'ਵ': 'v',
    'ਸ': 's',
    'ਸ਼': 'ś',  # sha with nukta
    'ਹ': 'h',
    'ੜ': 'ṛ',
    'ਖ਼': 'kh',  # kha with nukta (simplified)
    'ਗ਼': 'ġ',   # gha with nukta
    'ਜ਼': 'z',   # za with nukta
    'ਫ਼': 'f',   # fa with nukta
    'ਲ਼': 'ḷ',   # la with nukta
}

# Special marks
GURMUKHI_SPECIAL_MARKS: Dict[str, str] = {
    'ਂ': 'ṃ',    # bindi (nasalization)
    'ੰ': 'ṃ',    # tippi (nasalization)
    'ੱ': '',     # adhak (gemination - doubles following consonant)
    '਼': '',     # nukta (modifies previous consonant)
    'ੑ': '',     # udat (stress mark)
    'ੵ': '',     # yakaash (rare)
    '੶': '',     # abhaykari (rare)
}

# Half forms (conjuncts) - these combine with following consonants
# For now, we'll handle them in the converter logic
GURMUKHI_HALF_FORMS: Dict[str, str] = {
    '੍': '',  # virama (half form marker)
}

# ============================================================================
# COMMON WORD DICTIONARY (for disambiguation)
# ============================================================================

# Common Punjabi words in Shahmukhi with their Gurmukhi equivalents
# This helps with ambiguous conversions
COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI: Dict[str, str] = {
    # Common greetings and religious terms
    'دھن': 'ਧੰਨ',
    'گرنانک': 'ਗੁਰਨਾਨਕ',
    'دیو': 'ਦੇਵ',
    'جی': 'ਜੀ',
    'مہاراج': 'ਮਹਾਰਾਜ',
    'رام': 'ਰਾਮ',
    'تنجی': 'ਤੰਜੀ',
    'راکھ': 'ਰਾਖ',
    'دے': 'ਦੇ',
    'اندر': 'ਅੰਦਰ',
    'سری': 'ਸ੍ਰੀ',
    'اکال': 'ਅਕਾਲ',
    'ست': 'ਸਤਿ',
    
    # Common words
    'ہے': 'ਹੈ',
    'ہیں': 'ਹਨ',
    'نے': 'ਨੇ',
    'کو': 'ਕੋ',
    'سے': 'ਸੇ',
    'میں': 'ਮੇਂ',
    'کا': 'ਕਾ',
    'کی': 'ਕੀ',
    'کے': 'ਕੇ',
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_gurmukhi_unicode_range() -> range:
    """Get Unicode range for Gurmukhi script."""
    return range(0x0A00, 0x0A80)


def get_shahmukhi_unicode_range() -> range:
    """Get Unicode range for Shahmukhi (Arabic) script."""
    return range(0x0600, 0x0700)


def get_devanagari_unicode_range() -> range:
    """Get Unicode range for Devanagari script."""
    return range(0x0900, 0x0980)


def is_gurmukhi_char(char: str) -> bool:
    """Check if character is in Gurmukhi Unicode range."""
    if not char:
        return False
    code_point = ord(char[0])
    return code_point in get_gurmukhi_unicode_range()


def is_shahmukhi_char(char: str) -> bool:
    """Check if character is in Shahmukhi (Arabic) Unicode range."""
    if not char:
        return False
    code_point = ord(char[0])
    return code_point in get_shahmukhi_unicode_range()


def is_devanagari_char(char: str) -> bool:
    """Check if character is in Devanagari Unicode range."""
    if not char:
        return False
    code_point = ord(char[0])
    return code_point in get_devanagari_unicode_range()


def is_latin_char(char: str) -> bool:
    """Check if character is Latin (A-Z, a-z)."""
    if not char:
        return False
    return char.isalpha() and ord(char[0]) < 0x0100
