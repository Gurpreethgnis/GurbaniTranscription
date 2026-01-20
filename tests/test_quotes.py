"""
Consolidated quote detection tests.

Tests for:
- Quote candidate detection
- Scripture database lookups
- Quote matching/alignment
- Canonical text replacement

Replaces: test_phase4_quotes.py, test_phase4_simple.py, test_phase4_milestone1.py,
          test_phase4_milestone2.py, test_matching_debug.py
"""
import sys
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestQuoteImports(unittest.TestCase):
    """Test quote detection module imports."""
    
    def test_import_quote_candidates(self):
        """Test QuoteCandidateDetector import."""
        from quotes.quote_candidates import QuoteCandidateDetector
        self.assertTrue(hasattr(QuoteCandidateDetector, 'detect_candidates'))
    
    def test_import_assisted_matcher(self):
        """Test AssistedMatcher import."""
        from quotes.assisted_matcher import AssistedMatcher
        self.assertTrue(hasattr(AssistedMatcher, 'match'))
    
    def test_import_canonical_replacer(self):
        """Test CanonicalReplacer import."""
        from quotes.canonical_replacer import CanonicalReplacer
        self.assertTrue(hasattr(CanonicalReplacer, 'replace'))
    
    def test_import_models(self):
        """Test quote-related model imports."""
        from core.models import QuoteMatch, QuoteCandidate, ScriptureSource
        self.assertTrue(ScriptureSource.SGGS)
        self.assertTrue(ScriptureSource.DASAM)


class TestQuoteModels(unittest.TestCase):
    """Test quote-related data models."""
    
    def test_quote_candidate(self):
        """Test QuoteCandidate model."""
        from core.models import QuoteCandidate
        
        candidate = QuoteCandidate(
            text="ਵਾਹਿਗੁਰੂ",
            start_time=0.0,
            end_time=5.0,
            confidence=0.85
        )
        
        self.assertEqual(candidate.text, "ਵਾਹਿਗੁਰੂ")
        self.assertEqual(candidate.confidence, 0.85)
    
    def test_quote_match(self):
        """Test QuoteMatch model."""
        from core.models import QuoteMatch, ScriptureSource
        
        match = QuoteMatch(
            source=ScriptureSource.SGGS,
            page=1,
            line=1,
            canonical_text="ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            romanized="Ik Oankaar Sat Naam Kartaa Purakh",
            confidence=0.95
        )
        
        self.assertEqual(match.source, ScriptureSource.SGGS)
        self.assertEqual(match.page, 1)
        self.assertGreater(match.confidence, 0.9)
    
    def test_quote_match_serialization(self):
        """Test QuoteMatch serialization."""
        from core.models import QuoteMatch, ScriptureSource
        
        match = QuoteMatch(
            source=ScriptureSource.SGGS,
            page=100,
            line=5,
            canonical_text="Test",
            romanized="Test",
            confidence=0.90
        )
        
        match_dict = match.to_dict()
        self.assertIn('source', match_dict)
        self.assertIn('page', match_dict)
        self.assertIn('confidence', match_dict)


class TestScriptureConfig(unittest.TestCase):
    """Test scripture configuration."""
    
    def test_config_paths(self):
        """Test scripture database paths are configured."""
        import config
        
        self.assertTrue(hasattr(config, 'SCRIPTURE_DB_PATH'))
        self.assertTrue(hasattr(config, 'DASAM_DB_PATH'))
        self.assertTrue(hasattr(config, 'QUOTE_MATCH_CONFIDENCE_THRESHOLD'))
    
    def test_quote_detection_settings(self):
        """Test quote detection settings."""
        import config
        
        self.assertGreater(config.QUOTE_MATCH_CONFIDENCE_THRESHOLD, 0.0)
        self.assertLessEqual(config.QUOTE_MATCH_CONFIDENCE_THRESHOLD, 1.0)
        self.assertGreater(config.QUOTE_CANDIDATE_MIN_WORDS, 0)


class TestQuoteCandidateDetector(unittest.TestCase):
    """Test quote candidate detection."""
    
    def test_detector_initialization(self):
        """Test QuoteCandidateDetector initializes."""
        from quotes.quote_candidates import QuoteCandidateDetector
        
        detector = QuoteCandidateDetector()
        self.assertIsNotNone(detector)
    
    def test_detect_empty_input(self):
        """Test detection on empty input."""
        from quotes.quote_candidates import QuoteCandidateDetector
        
        detector = QuoteCandidateDetector()
        candidates = detector.detect_candidates("", 0.0, 0.0)
        
        self.assertEqual(len(candidates), 0)


class TestCanonicalReplacer(unittest.TestCase):
    """Test canonical text replacement."""
    
    def test_replacer_initialization(self):
        """Test CanonicalReplacer initializes."""
        from quotes.canonical_replacer import CanonicalReplacer
        
        replacer = CanonicalReplacer()
        self.assertIsNotNone(replacer)


def run_tests():
    """Run all quote detection tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestQuoteImports))
    suite.addTests(loader.loadTestsFromTestCase(TestQuoteModels))
    suite.addTests(loader.loadTestsFromTestCase(TestScriptureConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestQuoteCandidateDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestCanonicalReplacer))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

