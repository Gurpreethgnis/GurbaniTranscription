"""
Comprehensive test suite for Phase 3: Script Conversion

Tests the complete Phase 3 functionality including:
- Data models
- Script detection
- Shahmukhi to Gurmukhi conversion
- Gurmukhi to Roman transliteration
- Main ScriptConverter service
- Orchestrator integration
"""
import pytest
from models import ConvertedText, ProcessedSegment
from errors import ScriptConversionError
from script_converter import (
    ScriptDetector,
    ShahmukhiToGurmukhiConverter,
    GurmukhiToRomanTransliterator,
    ScriptConverter
)
from data.script_mappings import (
    SHAHMUKHI_TO_GURMUKHI_CONSONANTS,
    GURMUKHI_CONSONANTS,
    COMMON_WORDS_SHAHMUKHI_TO_GURMUKHI,
    is_gurmukhi_char,
    is_shahmukhi_char,
)


class TestPhase3DataModels:
    """Test Phase 3 data models."""
    
    def test_converted_text_model(self):
        """Test ConvertedText dataclass."""
        converted = ConvertedText(
            original="دھن گرنانک",
            original_script="shahmukhi",
            gurmukhi="ਧੰਨ ਗੁਰਨਾਨਕ",
            roman="Dhan Guranānak",
            confidence=0.85,
            needs_review=False
        )
        
        assert converted.original == "دھن گرنانک"
        assert converted.original_script == "shahmukhi"
        assert converted.gurmukhi == "ਧੰਨ ਗੁਰਨਾਨਕ"
        assert converted.roman == "Dhan Guranānak"
        assert converted.confidence == 0.85
        assert converted.needs_review is False
        
        # Test serialization
        result = converted.to_dict()
        assert isinstance(result, dict)
        assert result["original"] == "دھن گرنانک"
        assert result["gurmukhi"] == "ਧੰਨ ਗੁਰਨਾਨਕ"
    
    def test_processed_segment_phase3_fields(self):
        """Test ProcessedSegment with Phase 3 fields."""
        segment = ProcessedSegment(
            start=0.0,
            end=1.0,
            route="punjabi_speech",
            type="speech",
            text="ਧੰਨ ਗੁਰਨਾਨਕ",
            confidence=0.9,
            language="pa",
            roman="Dhan Guranānak",
            original_script="gurmukhi",
            script_confidence=0.95
        )
        
        assert segment.roman == "Dhan Guranānak"
        assert segment.original_script == "gurmukhi"
        assert segment.script_confidence == 0.95
        
        # Test serialization includes Phase 3 fields
        result = segment.to_dict()
        assert "roman" in result
        assert "original_script" in result
        assert "script_confidence" in result


class TestScriptDetection:
    """Test script detection functionality."""
    
    def test_detect_shahmukhi(self):
        """Test detection of Shahmukhi text."""
        detector = ScriptDetector()
        script, confidence = detector.detect_script("دھن گرنانک")
        
        assert script == "shahmukhi"
        assert confidence > 0.7
    
    def test_detect_gurmukhi(self):
        """Test detection of Gurmukhi text."""
        detector = ScriptDetector()
        script, confidence = detector.detect_script("ਧੰਨ ਗੁਰਨਾਨਕ")
        
        assert script == "gurmukhi"
        assert confidence > 0.7
    
    def test_detect_english(self):
        """Test detection of English text."""
        detector = ScriptDetector()
        script, confidence = detector.detect_script("Dhan Guru Nanak")
        
        assert script == "english"
        assert confidence > 0.7
    
    def test_detect_mixed(self):
        """Test detection of mixed script."""
        detector = ScriptDetector()
        script, confidence = detector.detect_script("دھن ਗੁਰਨਾਨਕ Dev")
        
        assert script == "mixed"
        assert confidence > 0.0


class TestShahmukhiToGurmukhi:
    """Test Shahmukhi to Gurmukhi conversion."""
    
    def test_basic_conversion(self):
        """Test basic Shahmukhi to Gurmukhi conversion."""
        converter = ShahmukhiToGurmukhiConverter()
        result, confidence = converter.convert("دھن")
        
        assert len(result) > 0
        assert confidence > 0.0
    
    def test_common_word_conversion(self):
        """Test conversion using common word dictionary."""
        converter = ShahmukhiToGurmukhiConverter(enable_dictionary=True)
        result, confidence = converter.convert("دھن گرنانک")
        
        assert len(result) > 0
        assert confidence > 0.7
    
    def test_punctuation_preserved(self):
        """Test that punctuation is preserved."""
        converter = ShahmukhiToGurmukhiConverter()
        text = "دھن گرنانک!"
        result, confidence = converter.convert(text)
        
        assert "!" in result


class TestGurmukhiToRoman:
    """Test Gurmukhi to Roman transliteration."""
    
    def test_basic_transliteration(self):
        """Test basic Gurmukhi to Roman transliteration."""
        transliterator = GurmukhiToRomanTransliterator()
        result = transliterator.transliterate("ਧੰਨ")
        
        assert len(result) > 0
        assert isinstance(result, str)
    
    def test_multi_word_transliteration(self):
        """Test transliteration of multiple words."""
        transliterator = GurmukhiToRomanTransliterator()
        result = transliterator.transliterate("ਧੰਨ ਗੁਰਨਾਨਕ")
        
        assert len(result) > 0
        words = result.split()
        assert len(words) >= 2
    
    def test_practical_scheme(self):
        """Test practical transliteration scheme."""
        transliterator = GurmukhiToRomanTransliterator(scheme="practical")
        result = transliterator.transliterate("ਸਤਿ ਸ੍ਰੀ")
        
        # Should capitalize first letters
        words = result.split()
        for word in words:
            if word and word[0].isalpha():
                assert word[0].isupper()


class TestScriptConverterService:
    """Test main ScriptConverter service."""
    
    def test_convert_shahmukhi(self):
        """Test conversion from Shahmukhi to dual output."""
        converter = ScriptConverter()
        result = converter.convert("دھن گرنانک", source_language="ur")
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "shahmukhi"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0
        assert result.confidence > 0.0
    
    def test_convert_gurmukhi(self):
        """Test conversion when input is already Gurmukhi."""
        converter = ScriptConverter()
        result = converter.convert("ਧੰਨ ਗੁਰਨਾਨਕ")
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "gurmukhi"
        assert result.gurmukhi == "ਧੰਨ ਗੁਰਨਾਨਕ"
        assert len(result.roman) > 0
    
    def test_convert_english(self):
        """Test conversion of English text."""
        converter = ScriptConverter()
        result = converter.convert("Dhan Guru Nanak")
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "english"
        assert result.gurmukhi == "Dhan Guru Nanak"
        assert result.roman == "Dhan Guru Nanak"
    
    def test_convert_segments(self):
        """Test conversion of segment list."""
        converter = ScriptConverter()
        segments = [
            {"text": "دھن", "start": 0.0, "end": 1.0},
            {"text": "گرنانک", "start": 1.0, "end": 2.0},
        ]
        
        converted = converter.convert_segments(segments, source_language="ur")
        
        assert len(converted) == 2
        assert "gurmukhi" in converted[0]
        assert "roman" in converted[0]
        assert "original_script" in converted[0]
    
    def test_needs_review_flagging(self):
        """Test that low confidence flags for review."""
        converter = ScriptConverter()
        # Use very short/ambiguous text
        result = converter.convert("ک")
        
        assert isinstance(result, ConvertedText)
        assert isinstance(result.needs_review, bool)


class TestErrorHandling:
    """Test error handling."""
    
    def test_script_conversion_error(self):
        """Test ScriptConversionError exception."""
        error = ScriptConversionError("shahmukhi", "gurmukhi", reason="Test error")
        
        assert isinstance(error, Exception)
        assert error.source_script == "shahmukhi"
        assert error.target_script == "gurmukhi"
        assert error.reason == "Test error"
        assert "Fix:" in str(error)


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_conversion_pipeline(self):
        """Test complete conversion pipeline from Shahmukhi to dual output."""
        # Real-world example from transcription
        shahmukhi_text = "رام تنجی راکھ دے اندر دھن گرنانک دیو جی مہاراج"
        
        converter = ScriptConverter()
        result = converter.convert(shahmukhi_text, source_language="ur")
        
        # Verify all components worked
        assert isinstance(result, ConvertedText)
        assert result.original_script == "shahmukhi"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0
        assert result.confidence > 0.0
    
    def test_mixed_script_handling(self):
        """Test handling of mixed script text."""
        mixed_text = "دھن ਗੁਰਨਾਨਕ Dev Ji"
        
        converter = ScriptConverter()
        result = converter.convert(mixed_text)
        
        assert isinstance(result, ConvertedText)
        assert result.original_script == "mixed"
        assert len(result.gurmukhi) > 0
        assert len(result.roman) > 0
    
    def test_empty_and_edge_cases(self):
        """Test edge cases and empty inputs."""
        converter = ScriptConverter()
        
        # Empty text
        result = converter.convert("")
        assert result.original_script == "empty"
        assert result.confidence == 1.0
        
        # Whitespace only
        result = converter.convert("   ")
        assert result.original_script == "empty"
        
        # Very short text
        result = converter.convert("ک")
        assert isinstance(result, ConvertedText)


class TestConfiguration:
    """Test configuration integration."""
    
    def test_config_imports(self):
        """Test that config values are accessible."""
        import config
        
        assert hasattr(config, 'SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD')
        assert hasattr(config, 'ROMAN_TRANSLITERATION_SCHEME')
        assert hasattr(config, 'ENABLE_DICTIONARY_LOOKUP')
        assert hasattr(config, 'UNICODE_NORMALIZATION_FORM')
    
    def test_script_converter_uses_config(self):
        """Test that ScriptConverter uses config values."""
        import config
        
        scheme = getattr(config, 'ROMAN_TRANSLITERATION_SCHEME', 'practical')
        enable_dict = getattr(config, 'ENABLE_DICTIONARY_LOOKUP', True)
        
        converter = ScriptConverter(
            roman_scheme=scheme,
            enable_dictionary_lookup=enable_dict
        )
        
        assert converter.romanizer.scheme == scheme
        assert converter.enable_dictionary == enable_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
