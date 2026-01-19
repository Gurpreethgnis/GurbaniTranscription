"""
Test suite for Phase 3, Milestone 3.5: Gurmukhi to Roman Transliterator

Tests the GurmukhiToRomanTransliterator class.
"""
import pytest
from script_converter import GurmukhiToRomanTransliterator


class TestGurmukhiToRomanTransliterator:
    """Test the GurmukhiToRomanTransliterator class."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.transliterator = GurmukhiToRomanTransliterator(scheme="practical")
    
    def test_empty_text(self):
        """Test transliteration of empty text."""
        result = self.transliterator.transliterate("")
        assert result == ""
        
        result = self.transliterator.transliterate("   ")
        assert result == ""
    
    def test_independent_vowels(self):
        """Test transliteration of independent vowels."""
        result = self.transliterator.transliterate("ਅ")
        assert "a" in result.lower()
        
        result = self.transliterator.transliterate("ਆ")
        assert "ā" in result.lower() or "aa" in result.lower()
    
    def test_basic_consonants(self):
        """Test transliteration of basic consonants."""
        result = self.transliterator.transliterate("ਕ")
        assert "ka" in result.lower()
        
        result = self.transliterator.transliterate("ਸ")
        assert "sa" in result.lower()
        
        result = self.transliterator.transliterate("ਹ")
        assert "ha" in result.lower()
    
    def test_consonant_with_vowel(self):
        """Test consonant with dependent vowel."""
        result = self.transliterator.transliterate("ਕਾ")
        assert "kā" in result.lower() or "kaa" in result.lower()
        
        result = self.transliterator.transliterate("ਕੀ")
        assert "kī" in result.lower() or "kee" in result.lower()
    
    def test_common_words(self):
        """Test transliteration of common words."""
        # "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ" - Sat Sri Akal
        result = self.transliterator.transliterate("ਸਤਿ")
        assert len(result) > 0
        assert "s" in result.lower() or "t" in result.lower()
        
        result = self.transliterator.transliterate("ਅਕਾਲ")
        assert len(result) > 0
        assert "a" in result.lower()
    
    def test_nasalization(self):
        """Test transliteration with nasalization marks."""
        result = self.transliterator.transliterate("ਧੰਨ")
        assert len(result) > 0
        # Should handle bindi/tippi
    
    def test_punctuation_preserved(self):
        """Test that punctuation is preserved."""
        result = self.transliterator.transliterate("ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ!")
        assert "!" in result
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        result = self.transliterator.transliterate("ਸਤਿ 123")
        assert "123" in result
    
    def test_whitespace_preserved(self):
        """Test that whitespace is preserved."""
        text = "ਸਤਿ ਸ੍ਰੀ"
        result = self.transliterator.transliterate(text)
        
        # Should have space between words
        words = result.split()
        assert len(words) >= 2
    
    def test_multi_word(self):
        """Test transliteration of multiple words."""
        text = "ਧੰਨ ਗੁਰਨਾਨਕ"
        result = self.transliterator.transliterate(text)
        
        assert len(result) > 0
        words = result.split()
        assert len(words) >= 2
    
    def test_practical_scheme_capitalization(self):
        """Test that practical scheme capitalizes words."""
        transliterator = GurmukhiToRomanTransliterator(scheme="practical")
        result = transliterator.transliterate("ਸਤਿ ਸ੍ਰੀ")
        
        # First letter of each word should be capitalized
        words = result.split()
        for word in words:
            if word and word[0].isalpha():
                assert word[0].isupper()
    
    def test_real_world_example(self):
        """Test with real-world Gurmukhi example."""
        text = "ਧੰਨ ਗੁਰਨਾਨਕ ਦੇਵ ਜੀ ਮਹਾਰਾਜ"
        result = self.transliterator.transliterate(text)
        
        assert len(result) > 0
        # Should transliterate all words
        words = result.split()
        assert len(words) >= 4  # At least 4 words


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
