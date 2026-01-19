"""
Gurmukhi Unicode to ASCII Transliteration Converter.

Converts Unicode Gurmukhi (ਸਤਿ ਨਾਮੁ) to ASCII transliteration format (siq nwmu)
as used in ShabadOS database.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Basic mapping from Unicode Gurmukhi to ASCII transliteration
# This is a simplified mapping - can be enhanced with a full conversion table
GURMUKHI_TO_ASCII: Dict[str, str] = {
    # Vowels
    'ਅ': 'A', 'ਆ': 'Aw', 'ਇ': 'i', 'ਈ': 'I', 'ਉ': 'u', 'ਊ': 'U', 'ਏ': 'ey', 'ਐ': 'AY', 'ਓ': 'o', 'ਔ': 'aU',
    'ਾ': 'w', 'ਿ': 'i', 'ੀ': 'I', 'ੁ': 'u', 'ੂ': 'U', 'ੇ': 'ey', 'ੈ': 'AY', 'ੋ': 'o', 'ੌ': 'aU',
    
    # Consonants (basic mapping)
    'ਕ': 'k', 'ਖ': 'K', 'ਗ': 'g', 'ਘ': 'G', 'ਙ': '^',
    'ਚ': 'c', 'ਛ': 'C', 'ਜ': 'j', 'ਝ': 'J', 'ਞ': '&',
    'ਟ': 'q', 'ਠ': 'Q', 'ਡ': 'f', 'ਢ': 'F', 'ਣ': 'x',
    'ਤ': 't', 'ਥ': 'T', 'ਦ': 'd', 'ਧ': 'D', 'ਨ': 'n',
    'ਪ': 'p', 'ਫ': 'P', 'ਬ': 'b', 'ਭ': 'B', 'ਮ': 'm',
    'ਯ': 'y', 'ਰ': 'r', 'ਲ': 'l', 'ਵ': 'v',
    'ਸ': 's', 'ਸ਼': 'S', 'ਹ': 'h',
    'ੜ': 'R',
    
    # Special characters
    '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4',
    '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',
    
    # Common words (direct mapping for accuracy)
    'ਸਤਿ': 'siq', 'ਨਾਮੁ': 'nwmu', 'ਕਰਤਾ': 'krqw', 'ਪੁਰਖੁ': 'purKu',
    'ਵਾਹਿਗੁਰੂ': 'vwhgurU', 'ਸਤਿਗੁਰੂ': 'siqgurU', 'ਗੁਰੂ': 'gurU',
    'ਬਾਣੀ': 'bwxI', 'ਸ਼ਬਦ': 'sbd',
}


def gurmukhi_to_ascii(text: str) -> str:
    """
    Convert Unicode Gurmukhi to ASCII transliteration.
    
    This is a simplified converter. For production use, consider using
    a more comprehensive library or mapping table.
    
    Args:
        text: Unicode Gurmukhi text
    
    Returns:
        ASCII transliteration
    """
    if not text:
        return ""
    
    # Split into words to handle word-level mappings
    words = text.split()
    converted_words = []
    
    for word in words:
        # Check if entire word is in mapping (most accurate)
        if word in GURMUKHI_TO_ASCII:
            converted_words.append(GURMUKHI_TO_ASCII[word])
        else:
            # Character-by-character conversion
            converted_chars = []
            for char in word:
                if char in GURMUKHI_TO_ASCII:
                    converted_chars.append(GURMUKHI_TO_ASCII[char])
                else:
                    converted_chars.append(char)  # Keep as-is if no mapping
            converted_words.append(''.join(converted_chars))
    
    return ' '.join(converted_words)


def try_ascii_search(text: str) -> str:
    """
    Try to convert text to ASCII format for database search.
    
    If text is already ASCII, returns as-is.
    If text is Unicode Gurmukhi, converts to ASCII.
    
    Args:
        text: Input text (Unicode Gurmukhi or ASCII)
    
    Returns:
        ASCII transliteration for searching
    """
    # Check if text is already ASCII (no Unicode Gurmukhi characters)
    has_gurmukhi_unicode = any('\u0A00' <= char <= '\u0A7F' for char in text)
    
    if has_gurmukhi_unicode:
        # Convert Unicode to ASCII
        ascii_text = gurmukhi_to_ascii(text)
        logger.debug(f"Converted Unicode Gurmukhi to ASCII: '{text[:30]}' → '{ascii_text[:30]}'")
        return ascii_text
    else:
        # Already ASCII or other format
        return text
