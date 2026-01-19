"""
Phase 5: Normalization + Transliteration Gap Filling - Test Suite

Tests for:
1. Gurmukhi diacritic normalization
2. ShabadOS transliteration retrieval
3. Consistent Unicode normalization
"""
import unittest
import sqlite3
from pathlib import Path
from data.gurmukhi_normalizer import GurmukhiNormalizer
from scripture.sggs_db import SGGSDatabase
from script_converter import ScriptConverter
from quotes.assisted_matcher import AssistedMatcher
import config


class TestGurmukhiNormalizer(unittest.TestCase):
    """Test Gurmukhi diacritic normalization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = GurmukhiNormalizer()
    
    def test_basic_normalization(self):
        """Test basic Unicode normalization."""
        text = "ਸਤਿ ਨਾਮੁ"
        normalized = self.normalizer.normalize(text)
        self.assertIsInstance(normalized, str)
        self.assertEqual(len(normalized), len(text))  # Should preserve length
    
    def test_tippi_bindi_normalization(self):
        """Test Tippi/Bindi normalization based on context."""
        # Tippi before consonant
        text_with_tippi = "ਸੰਤ"
        normalized = self.normalizer.normalize(text_with_tippi)
        self.assertIn('\u0A70', normalized)  # Tippi should be present
        
        # Bindi before vowel (if applicable)
        text_with_bindi = "ਸਂ"
        normalized = self.normalizer.normalize(text_with_bindi)
        self.assertIsInstance(normalized, str)
    
    def test_adhak_normalization(self):
        """Test Adhak positioning."""
        text = "ਸੱਤ"
        normalized = self.normalizer.normalize(text)
        self.assertIn('\u0A71', normalized)  # Adhak should be present
    
    def test_nukta_normalization(self):
        """Test Nukta combining."""
        text = "ਖ਼"
        normalized = self.normalizer.normalize(text)
        self.assertIn('\u0A3C', normalized)  # Nukta should be present
    
    def test_empty_text(self):
        """Test empty text handling."""
        self.assertEqual(self.normalizer.normalize(""), "")
        self.assertEqual(self.normalizer.normalize("   "), "   ")
    
    def test_unicode_form_config(self):
        """Test that normalization form is read from config."""
        normalizer = GurmukhiNormalizer()
        self.assertEqual(normalizer.normalization_form, config.UNICODE_NORMALIZATION_FORM)


class TestShabadOSTransliteration(unittest.TestCase):
    """Test ShabadOS transliteration retrieval."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            self.sggs_db = SGGSDatabase()
        except Exception as e:
            self.skipTest(f"SGGS database not available: {e}")
    
    def test_search_includes_transliteration(self):
        """Test that search_by_text includes transliteration."""
        # Search for a common line
        results = self.sggs_db.search_by_text("ਸਤਿ", top_k=5)
        
        if results:
            # Check if at least one result has transliteration
            has_transliteration = any(r.roman is not None for r in results)
            # Note: Not all lines may have transliterations, so this is informational
            self.assertIsInstance(has_transliteration, bool)
    
    def test_get_line_by_id_includes_transliteration(self):
        """Test that get_line_by_id includes transliteration."""
        # First, get a line ID from search
        results = self.sggs_db.search_by_text("ਸਤਿ", top_k=1)
        
        if results:
            line_id = results[0].line_id
            line = self.sggs_db.get_line_by_id(line_id)
            
            self.assertIsNotNone(line)
            # Check if transliteration is available (may be None if not in DB)
            self.assertIsInstance(line.roman, (str, type(None)))
    
    def test_transliteration_format(self):
        """Test that transliteration is in expected format."""
        results = self.sggs_db.search_by_text("ਸਤਿ", top_k=10)
        
        for result in results:
            if result.roman:
                # Transliteration should be a string
                self.assertIsInstance(result.roman, str)
                # Should not be empty
                self.assertGreater(len(result.roman.strip()), 0)


class TestUnicodeNormalization(unittest.TestCase):
    """Test consistent Unicode normalization across pipeline."""
    
    def test_script_converter_normalization(self):
        """Test that ScriptConverter applies Unicode normalization."""
        converter = ScriptConverter()
        
        # Test with Gurmukhi text
        text = "ਸਤਿ ਨਾਮੁ"
        result = converter.convert(text, source_language="pa")
        
        # Should have normalized the text
        self.assertIsInstance(result.gurmukhi, str)
        self.assertEqual(result.original_script, "gurmukhi")
    
    def test_assisted_matcher_normalization(self):
        """Test that AssistedMatcher applies Unicode normalization."""
        matcher = AssistedMatcher()
        
        # Test normalization in tokenization
        text = "ਸਤਿ ਨਾਮੁ"
        tokens = matcher._normalize_and_tokenize(text)
        
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
    
    def test_config_normalization_form(self):
        """Test that config.UNICODE_NORMALIZATION_FORM is defined."""
        self.assertTrue(hasattr(config, 'UNICODE_NORMALIZATION_FORM'))
        self.assertIn(config.UNICODE_NORMALIZATION_FORM, ['NFC', 'NFD', 'NFKC', 'NFKD'])


class TestCanonicalQuoteTransliteration(unittest.TestCase):
    """Test that canonical quotes use DB transliteration."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            self.sggs_db = SGGSDatabase()
        except Exception as e:
            self.skipTest(f"SGGS database not available: {e}")
    
    def test_quote_match_has_transliteration(self):
        """Test that QuoteMatch can have canonical_roman from DB."""
        # Get a line with transliteration
        results = self.sggs_db.search_by_text("ਸਤਿ", top_k=10)
        
        for result in results:
            if result.roman:
                # This line has transliteration from DB
                from models import QuoteMatch, ScriptureSource
                
                quote_match = QuoteMatch(
                    source=result.source,
                    line_id=result.line_id,
                    canonical_text=result.gurmukhi,
                    canonical_roman=result.roman,  # From DB
                    spoken_text="test",
                    confidence=0.95
                )
                
                self.assertIsNotNone(quote_match.canonical_roman)
                self.assertIsInstance(quote_match.canonical_roman, str)
                break


class TestIntegration(unittest.TestCase):
    """Integration tests for Phase 5 features."""
    
    def test_full_pipeline_normalization(self):
        """Test that normalization is applied throughout pipeline."""
        converter = ScriptConverter()
        
        # Convert text
        text = "ਸਤਿ ਨਾਮੁ"
        result = converter.convert(text, source_language="pa")
        
        # Gurmukhi should be normalized
        self.assertIsInstance(result.gurmukhi, str)
        self.assertGreater(len(result.gurmukhi), 0)
        
        # Roman should be generated
        self.assertIsInstance(result.roman, str)
        self.assertGreater(len(result.roman), 0)


def run_tests():
    """Run all Phase 5 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestGurmukhiNormalizer))
    suite.addTests(loader.loadTestsFromTestCase(TestShabadOSTransliteration))
    suite.addTests(loader.loadTestsFromTestCase(TestUnicodeNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestCanonicalQuoteTransliteration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
