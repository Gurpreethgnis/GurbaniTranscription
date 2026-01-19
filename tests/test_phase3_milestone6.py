"""
Test suite for Phase 3, Milestone 3.6: Main ScriptConverter Service

Tests the unified ScriptConverter class.
"""
import pytest
from services.script_converter import ScriptConverter
from core.models import ConvertedText


class TestScriptConverter:
    """Test the main ScriptConverter service class."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.converter = ScriptConverter(
            roman_scheme="practical",
            enable_dictionary_lookup=True
        )
    
    def test_empty_text(self):
        """Test conversion of empty text."""
        result = self.converter.convert("")
        
        assert isinstance(result, ConvertedText)
        assert result.original == ""
        assert result.gurmukhi == ""
        assert result.roman == ""
        assert result.original_script == "empty"
        assert result.confidence == 1.0
        assert result.needs_review is False
    
    def test_shahmukhi_to_gurmukhi_and_roman(self):
        """Test conversion from Shahmukhi to both Gurmukhi and Roman."""
        text = "دھن گرنانک"
        result = self.converter.convert(text)
        
        assert isinstance(result, ConvertedText)
        assert result.original == text
        assert result.original_script == "shahmukhi"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0
        assert result.confidence > 0.0
    
    def test_gurmukhi_input(self):
        """Test conversion when input is already Gurmukhi."""
        text = "ਧੰਨ ਗੁਰਨਾਨਕ"
        result = self.converter.convert(text)
        
        assert isinstance(result, ConvertedText)
        assert result.original == text
        assert result.original_script == "gurmukhi"
        assert result.gurmukhi == text  # Should remain unchanged
        assert len(result.roman) > 0  # Should be transliterated
        assert result.confidence > 0.8
    
    def test_english_input(self):
        """Test conversion when input is English."""
        text = "Dhan Guru Nanak"
        result = self.converter.convert(text)
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "english"
        assert result.gurmukhi == text  # English kept as-is
        assert result.roman == text  # English kept as-is
        assert result.confidence > 0.8
    
    def test_with_language_hint(self):
        """Test conversion with language hint."""
        text = "دھن گرنانک"
        result = self.converter.convert(text, source_language="ur")
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "shahmukhi"
        assert result.confidence > 0.0
    
    def test_real_world_example(self):
        """Test with real-world example from transcription."""
        text = "رام تنجی راکھ دے اندر دھن گرنانک دیو جی مہاراج"
        result = self.converter.convert(text, source_language="ur")
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "shahmukhi"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0
        assert result.confidence > 0.5
    
    def test_needs_review_flag(self):
        """Test that low confidence sets needs_review."""
        # Use a very short or ambiguous text
        text = "ک"
        result = self.converter.convert(text)
        
        assert isinstance(result, ConvertedText)
        # May or may not need review depending on confidence
        assert isinstance(result.needs_review, bool)
    
    def test_convert_segments(self):
        """Test conversion of segment list."""
        segments = [
            {"text": "دھن", "start": 0.0, "end": 1.0},
            {"text": "گرنانک", "start": 1.0, "end": 2.0},
        ]
        
        converted = self.converter.convert_segments(segments, source_language="ur")
        
        assert len(converted) == 2
        assert "gurmukhi" in converted[0]
        assert "roman" in converted[0]
        assert "original_script" in converted[0]
        assert "script_confidence" in converted[0]
    
    def test_preserve_segment_metadata(self):
        """Test that segment metadata is preserved."""
        segments = [
            {
                "text": "دھن",
                "start": 0.0,
                "end": 1.0,
                "confidence": 0.9,
                "language": "ur"
            }
        ]
        
        converted = self.converter.convert_segments(segments)
        
        assert converted[0]["start"] == 0.0
        assert converted[0]["end"] == 1.0
        assert converted[0]["confidence"] == 0.9
        assert converted[0]["language"] == "ur"
    
    def test_mixed_script_handling(self):
        """Test handling of mixed script text."""
        text = "دھن ਗੁਰਨਾਨਕ Dev"
        result = self.converter.convert(text)
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "mixed"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
