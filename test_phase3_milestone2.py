"""
Test suite for Phase 3, Milestone 3.2: Unicode Mapping Tables

Tests the script_mappings module.
"""
import pytest
from data.script_mappings import (
    SHAHMUKHI_TO_GURMUKHI_CONSONANTS,
    GURMUKHI_CONSONANTS,
    GURMUKHI_INDEPENDENT_VOWELS,
    GURMUKHI_DEPENDENT_VOWELS,
    COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI,
    is_gurmukhi_char,
    is_shahmukhi_char,
    is_devanagari_char,
    is_latin_char,
    get_gurmukhi_unicode_range,
    get_shahmukhi_unicode_range,
)


class TestUnicodeRanges:
    """Test Unicode range detection functions."""
    
    def test_gurmukhi_range(self):
        """Test Gurmukhi Unicode range."""
        range_obj = get_gurmukhi_unicode_range()
        assert isinstance(range_obj, range)
        assert 0x0A00 in range_obj
        assert 0x0A7F in range_obj
        assert 0x0A80 not in range_obj
    
    def test_shahmukhi_range(self):
        """Test Shahmukhi Unicode range."""
        range_obj = get_shahmukhi_unicode_range()
        assert isinstance(range_obj, range)
        assert 0x0600 in range_obj
        assert 0x06FF in range_obj
        assert 0x0700 not in range_obj
    
    def test_is_gurmukhi_char(self):
        """Test Gurmukhi character detection."""
        assert is_gurmukhi_char('ਸ') is True
        assert is_gurmukhi_char('ਹ') is True
        assert is_gurmukhi_char('ਕ') is True
        assert is_gurmukhi_char('ر') is False  # Shahmukhi
        assert is_gurmukhi_char('A') is False  # Latin
        assert is_gurmukhi_char('') is False
        assert is_gurmukhi_char(' ') is False
    
    def test_is_shahmukhi_char(self):
        """Test Shahmukhi character detection."""
        assert is_shahmukhi_char('ر') is True
        assert is_shahmukhi_char('د') is True
        assert is_shahmukhi_char('ਸ') is False  # Gurmukhi
        assert is_shahmukhi_char('A') is False  # Latin
        assert is_shahmukhi_char('') is False
    
    def test_is_devanagari_char(self):
        """Test Devanagari character detection."""
        assert is_devanagari_char('स') is True
        assert is_devanagari_char('ਹ') is False  # Gurmukhi
        assert is_devanagari_char('ر') is False  # Shahmukhi
        assert is_devanagari_char('') is False
    
    def test_is_latin_char(self):
        """Test Latin character detection."""
        assert is_latin_char('A') is True
        assert is_latin_char('z') is True
        assert is_latin_char('ਸ') is False  # Gurmukhi
        assert is_latin_char('ر') is False  # Shahmukhi
        assert is_latin_char('') is False
        assert is_latin_char('1') is False  # Number


class TestShahmukhiMappings:
    """Test Shahmukhi to Gurmukhi mappings."""
    
    def test_consonant_mappings_exist(self):
        """Test that key consonants are mapped."""
        assert 'ب' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        assert 'پ' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        assert 'ت' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        assert 'ج' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        assert 'ک' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
        assert 'گ' in SHAHMUKHI_TO_GURMUKHI_CONSONANTS
    
    def test_consonant_mappings_correct(self):
        """Test that mappings are correct."""
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['ب'] == 'ਬ'
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['پ'] == 'ਪ'
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['ت'] == 'ਤ'
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['ج'] == 'ਜ'
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['ک'] == 'ਕ'
        assert SHAHMUKHI_TO_GURMUKHI_CONSONANTS['گ'] == 'ਗ'
    
    def test_common_words_mapping(self):
        """Test common word mappings."""
        assert 'دھن' in COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI
        assert COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI['دھن'] == 'ਧੰਨ'
        assert 'گرنانک' in COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI
        assert COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI['گرنانک'] == 'ਗੁਰਨਾਨਕ'
        assert 'جی' in COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI
        assert COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI['جی'] == 'ਜੀ'


class TestGurmukhiMappings:
    """Test Gurmukhi to Roman mappings."""
    
    def test_independent_vowels(self):
        """Test independent vowel mappings."""
        assert 'ਅ' in GURMUKHI_INDEPENDENT_VOWELS
        assert GURMUKHI_INDEPENDENT_VOWELS['ਅ'] == 'a'
        assert GURMUKHI_INDEPENDENT_VOWELS['ਆ'] == 'ā'
        assert GURMUKHI_INDEPENDENT_VOWELS['ਇ'] == 'i'
        assert GURMUKHI_INDEPENDENT_VOWELS['ਈ'] == 'ī'
    
    def test_dependent_vowels(self):
        """Test dependent vowel (matra) mappings."""
        assert 'ਾ' in GURMUKHI_DEPENDENT_VOWELS
        assert GURMUKHI_DEPENDENT_VOWELS['ਾ'] == 'ā'
        assert GURMUKHI_DEPENDENT_VOWELS['ਿ'] == 'i'
        assert GURMUKHI_DEPENDENT_VOWELS['ੀ'] == 'ī'
        assert GURMUKHI_DEPENDENT_VOWELS['ੁ'] == 'u'
        assert GURMUKHI_DEPENDENT_VOWELS['ੂ'] == 'ū'
    
    def test_consonants(self):
        """Test consonant mappings."""
        assert 'ਕ' in GURMUKHI_CONSONANTS
        assert GURMUKHI_CONSONANTS['ਕ'] == 'k'
        assert GURMUKHI_CONSONANTS['ਖ'] == 'kh'
        assert GURMUKHI_CONSONANTS['ਗ'] == 'g'
        assert GURMUKHI_CONSONANTS['ਸ'] == 's'
        assert GURMUKHI_CONSONANTS['ਹ'] == 'h'
    
    def test_nukta_variants(self):
        """Test nukta variant mappings."""
        assert 'ਖ਼' in GURMUKHI_CONSONANTS
        assert 'ਗ਼' in GURMUKHI_CONSONANTS
        assert 'ਜ਼' in GURMUKHI_CONSONANTS
        assert 'ਫ਼' in GURMUKHI_CONSONANTS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
