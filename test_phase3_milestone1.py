"""
Test suite for Phase 3, Milestone 3.1: Data Models & Exceptions

Tests the ConvertedText dataclass and ScriptConversionError exception.
"""
import pytest
from models import ConvertedText
from errors import ScriptConversionError, TranscriptionError


class TestConvertedText:
    """Test the ConvertedText dataclass."""
    
    def test_create_basic(self):
        """Test creating a basic ConvertedText instance."""
        converted = ConvertedText(
            original="رام تنجی",
            original_script="shahmukhi",
            gurmukhi="ਰਾਮ ਤੰਜੀ",
            roman="Rām tanjī",
            confidence=0.85,
            needs_review=False
        )
        
        assert converted.original == "رام تنجی"
        assert converted.original_script == "shahmukhi"
        assert converted.gurmukhi == "ਰਾਮ ਤੰਜੀ"
        assert converted.roman == "Rām tanjī"
        assert converted.confidence == 0.85
        assert converted.needs_review is False
    
    def test_to_dict(self):
        """Test ConvertedText.to_dict() serialization."""
        converted = ConvertedText(
            original="دھن گرنانک",
            original_script="shahmukhi",
            gurmukhi="ਧੰਨ ਗੁਰਨਾਨਕ",
            roman="Dhan Guranānak",
            confidence=0.90,
            needs_review=False
        )
        
        result = converted.to_dict()
        
        assert isinstance(result, dict)
        assert result["original"] == "دھن گرنانک"
        assert result["original_script"] == "shahmukhi"
        assert result["gurmukhi"] == "ਧੰਨ ਗੁਰਨਾਨਕ"
        assert result["roman"] == "Dhan Guranānak"
        assert result["confidence"] == 0.90
        assert result["needs_review"] is False
    
    def test_needs_review_flag(self):
        """Test that low confidence sets needs_review."""
        converted = ConvertedText(
            original="test",
            original_script="mixed",
            gurmukhi="test",
            roman="test",
            confidence=0.5,  # Low confidence
            needs_review=True
        )
        
        assert converted.needs_review is True
        assert converted.confidence == 0.5
    
    def test_empty_text(self):
        """Test ConvertedText with empty strings."""
        converted = ConvertedText(
            original="",
            original_script="empty",
            gurmukhi="",
            roman="",
            confidence=1.0,
            needs_review=False
        )
        
        assert converted.original == ""
        assert converted.gurmukhi == ""
        assert converted.roman == ""
    
    def test_gurmukhi_input(self):
        """Test ConvertedText when input is already Gurmukhi."""
        converted = ConvertedText(
            original="ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ",
            original_script="gurmukhi",
            gurmukhi="ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ",
            roman="Sati Srī Akāl",
            confidence=1.0,
            needs_review=False
        )
        
        assert converted.original_script == "gurmukhi"
        assert converted.original == converted.gurmukhi


class TestScriptConversionError:
    """Test the ScriptConversionError exception."""
    
    def test_basic_error(self):
        """Test creating a basic ScriptConversionError."""
        error = ScriptConversionError("shahmukhi", "gurmukhi")
        
        assert isinstance(error, TranscriptionError)
        assert error.source_script == "shahmukhi"
        assert error.target_script == "gurmukhi"
        assert "shahmukhi" in str(error)
        assert "gurmukhi" in str(error)
        assert "Fix:" in str(error)
    
    def test_error_with_reason(self):
        """Test ScriptConversionError with a reason."""
        error = ScriptConversionError(
            "shahmukhi",
            "gurmukhi",
            reason="Unsupported character: ۃ"
        )
        
        assert error.reason == "Unsupported character: ۃ"
        assert "Unsupported character" in str(error)
    
    def test_error_inheritance(self):
        """Test that ScriptConversionError inherits from TranscriptionError."""
        error = ScriptConversionError("a", "b")
        
        assert isinstance(error, TranscriptionError)
        assert isinstance(error, Exception)
    
    def test_error_attributes(self):
        """Test that error attributes are accessible."""
        error = ScriptConversionError("devanagari", "gurmukhi", reason="test")
        
        assert error.source_script == "devanagari"
        assert error.target_script == "gurmukhi"
        assert error.reason == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
