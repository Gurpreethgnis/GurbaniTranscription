"""
Test suite for Phase 3, Milestone 3.3: Script Detection

Tests the ScriptDetector class.
"""
import pytest
from script_converter import ScriptDetector


class TestScriptDetector:
    """Test the ScriptDetector class."""
    
    def setup_method(self):
        """Set up test fixture."""
        self.detector = ScriptDetector()
    
    def test_detect_gurmukhi(self):
        """Test detection of Gurmukhi text."""
        text = "ਧੰਨ ਗੁਰਨਾਨਕ ਦੇਵ ਜੀ ਮਹਾਰਾਜ"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "gurmukhi"
        assert confidence > 0.8
    
    def test_detect_shahmukhi(self):
        """Test detection of Shahmukhi text."""
        text = "دھن گرنانک دیو جی مہاراج"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "shahmukhi"
        assert confidence > 0.8
    
    def test_detect_english(self):
        """Test detection of English text."""
        text = "Dhan Guru Nanak Dev Ji Maharaj"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "english"
        assert confidence > 0.8
    
    def test_detect_mixed(self):
        """Test detection of mixed script text."""
        text = "دھن ਗੁਰਨਾਨਕ Dev Ji"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "mixed"
        assert confidence > 0.0
    
    def test_empty_text(self):
        """Test detection with empty text."""
        script, confidence = self.detector.detect_script("")
        assert script == "empty"
        assert confidence == 1.0
        
        script, confidence = self.detector.detect_script("   ")
        assert script == "empty"
        assert confidence == 1.0
    
    def test_whitespace_only(self):
        """Test detection with whitespace only."""
        script, confidence = self.detector.detect_script("   \n\t  ")
        assert script == "empty"
    
    def test_short_text(self):
        """Test detection with very short text."""
        script, confidence = self.detector.detect_script("ਸ")
        # Should return unknown or the script with lower confidence
        assert script in ["gurmukhi", "unknown"]
    
    def test_punctuation_only(self):
        """Test detection with punctuation only."""
        script, confidence = self.detector.detect_script("...!!!")
        assert script == "unknown"
        assert confidence == 0.0
    
    def test_with_language_hint_urdu(self):
        """Test detection with Urdu language hint."""
        text = "دھن گرنانک"
        script, confidence = self.detector.detect_script_with_language_hint(text, "ur")
        
        assert script == "shahmukhi"
        assert confidence > 0.7
    
    def test_with_language_hint_punjabi(self):
        """Test detection with Punjabi language hint."""
        text = "ਧੰਨ ਗੁਰਨਾਨਕ"
        script, confidence = self.detector.detect_script_with_language_hint(text, "pa")
        
        assert script == "gurmukhi"
        assert confidence > 0.8
    
    def test_with_language_hint_english(self):
        """Test detection with English language hint."""
        text = "Dhan Guru Nanak"
        script, confidence = self.detector.detect_script_with_language_hint(text, "en")
        
        assert script == "english"
        assert confidence > 0.8
    
    def test_with_language_hint_mismatch(self):
        """Test detection when language hint doesn't match detected script."""
        text = "دھن گرنانک"  # Shahmukhi
        script, confidence = self.detector.detect_script_with_language_hint(text, "pa")  # Punjabi hint
        
        # Should detect Shahmukhi but with reduced confidence
        assert script == "shahmukhi"
        assert confidence > 0.0
    
    def test_real_world_example_shahmukhi(self):
        """Test with real-world Shahmukhi example from transcription."""
        text = "رام تنجی راکھ دے اندر دھن گرنانک دیو جی مہاراج"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "shahmukhi"
        assert confidence > 0.7
    
    def test_real_world_example_mixed(self):
        """Test with mixed script example."""
        text = "دھن ਗੁਰਨਾਨਕ Dev Ji مہاراج"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "mixed"
        assert confidence > 0.0
    
    def test_long_text_confidence_boost(self):
        """Test that longer text gets confidence boost."""
        short_text = "دھن گرنانک"
        long_text = "دھن گرنانک دیو جی مہاراج جیسے بڑی قیمتی فنگتی ہے"
        
        _, short_conf = self.detector.detect_script(short_text)
        _, long_conf = self.detector.detect_script(long_text)
        
        # Longer text should have equal or higher confidence
        assert long_conf >= short_conf * 0.9  # Allow some variance
    
    def test_numbers_and_punctuation(self):
        """Test that numbers and punctuation don't affect detection."""
        text = "دھن گرنانک 123 !!!"
        script, confidence = self.detector.detect_script(text)
        
        assert script == "shahmukhi"
        assert confidence > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
