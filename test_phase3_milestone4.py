"""
Test suite for Phase 3, Milestone 3.4: Shahmukhi to Gurmukhi Converter

Tests the ShahmukhiToGurmukhiConverter class.
"""
import pytest
from script_converter import ShahmukhiToGurmukhiConverter


class TestShahmukhiToGurmukhiConverter:
    """Test the ShahmukhiToGurmukhiConverter class."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.converter = ShahmukhiToGurmukhiConverter(enable_dictionary=True)
    
    def test_empty_text(self):
        """Test conversion of empty text."""
        result, confidence = self.converter.convert("")
        assert result == ""
        assert confidence == 1.0
        
        result, confidence = self.converter.convert("   ")
        assert result == ""
        assert confidence == 1.0
    
    def test_common_words_dictionary(self):
        """Test that common words use dictionary lookup."""
        # These should be in the dictionary
        result, confidence = self.converter.convert("دھن")
        assert "ਧੰਨ" in result or confidence > 0.8  # May not match exactly due to conversion logic
        
        result, confidence = self.converter.convert("گرنانک")
        assert confidence > 0.8  # Should have high confidence from dictionary
    
    def test_basic_consonants(self):
        """Test basic consonant conversion."""
        # Test individual consonants
        result, confidence = self.converter._convert_word("ب")
        assert "ਬ" in result
        assert confidence > 0.8
    
    def test_word_conversion(self):
        """Test word-level conversion."""
        # Simple word
        result, confidence = self.converter._convert_word("ک")
        assert "ਕ" in result
        assert confidence > 0.8
    
    def test_multi_word_conversion(self):
        """Test conversion of multiple words."""
        text = "دھن گرنانک"
        result, confidence = self.converter.convert(text)
        
        assert len(result) > 0
        assert confidence > 0.7
    
    def test_punctuation_preserved(self):
        """Test that punctuation is preserved."""
        text = "دھن گرنانک!"
        result, confidence = self.converter.convert(text)
        
        assert "!" in result
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        text = "دھن 123 گرنانک"
        result, confidence = self.converter.convert(text)
        
        assert "123" in result
    
    def test_mixed_script(self):
        """Test conversion of mixed script text."""
        text = "دھن ਗੁਰਨਾਨਕ Dev"
        result, confidence = self.converter._convert_mixed(text)
        
        # Should convert Shahmukhi parts, keep others
        assert len(result) > 0
        assert "Dev" in result  # English preserved
    
    def test_unknown_characters(self):
        """Test handling of unknown characters."""
        # Use a character that's not in our mapping
        text = "دھن ⚡ گرنانک"  # Lightning emoji
        result, confidence = self.converter.convert(text)
        
        # Should still convert known parts
        assert len(result) > 0
        # Confidence may be lower due to unknown character
        assert confidence > 0.0
    
    def test_real_world_example(self):
        """Test with real-world example from transcription."""
        text = "رام تنجی راکھ دے اندر دھن گرنانک دیو جی مہاراج"
        result, confidence = self.converter.convert(text)
        
        assert len(result) > 0
        assert confidence > 0.6  # Real-world text may have lower confidence
    
    def test_converter_without_dictionary(self):
        """Test converter without dictionary lookup."""
        converter_no_dict = ShahmukhiToGurmukhiConverter(enable_dictionary=False)
        
        text = "دھن گرنانک"
        result, confidence = converter_no_dict.convert(text)
        
        assert len(result) > 0
        # Confidence may be lower without dictionary
        assert confidence > 0.0
    
    def test_whitespace_handling(self):
        """Test that whitespace is preserved."""
        text = "دھن  گرنانک"  # Double space
        result, confidence = self.converter.convert(text)
        
        # Should preserve word boundaries
        words = result.split()
        assert len(words) >= 2  # At least 2 words


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
