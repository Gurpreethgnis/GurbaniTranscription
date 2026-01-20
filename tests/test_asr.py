"""
Consolidated ASR engine tests.

Tests for:
- ASR-A (Whisper)
- ASR-B (Indic)
- ASR-C (English)
- ASR Fusion
- BaseASR class

Replaces: test_phase1.py (ASR tests), test_phase2.py (Multi-ASR tests)
"""
import sys
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures import (
    create_sample_audio_chunk,
    create_sample_segment,
    create_sample_asr_result,
    create_sample_fusion_result
)


class TestASRImports(unittest.TestCase):
    """Test that all ASR modules can be imported."""
    
    def test_import_base_asr(self):
        """Test BaseASR import."""
        from asr.base_asr import BaseASR
        self.assertTrue(hasattr(BaseASR, 'transcribe_chunk'))
        self.assertTrue(hasattr(BaseASR, 'transcribe_file'))
    
    def test_import_asr_whisper(self):
        """Test ASRWhisper import."""
        from asr.asr_whisper import ASRWhisper
        self.assertEqual(ASRWhisper.engine_name, "asr_a_whisper")
    
    def test_import_asr_indic(self):
        """Test ASRIndic import."""
        from asr.asr_indic import ASRIndic
        self.assertEqual(ASRIndic.engine_name, "asr_b_indic")
        self.assertEqual(ASRIndic.default_language, 'hi')
    
    def test_import_asr_english(self):
        """Test ASREnglish import."""
        from asr.asr_english_fallback import ASREnglish
        self.assertEqual(ASREnglish.engine_name, "asr_c_english")
        self.assertEqual(ASREnglish.default_language, 'en')
    
    def test_import_asr_fusion(self):
        """Test ASRFusion import."""
        from asr.asr_fusion import ASRFusion
        self.assertTrue(hasattr(ASRFusion, 'fuse'))


class TestASRModels(unittest.TestCase):
    """Test ASR data models."""
    
    def test_audio_chunk(self):
        """Test AudioChunk creation and attributes."""
        chunk = create_sample_audio_chunk(0.0, 10.0)
        self.assertEqual(chunk.start_time, 0.0)
        self.assertEqual(chunk.end_time, 10.0)
        self.assertEqual(chunk.duration, 10.0)
    
    def test_segment(self):
        """Test Segment creation and serialization."""
        segment = create_sample_segment()
        segment_dict = segment.to_dict()
        
        self.assertEqual(segment.text, "Test transcription")
        self.assertEqual(segment.confidence, 0.85)
        self.assertIn('start', segment_dict)
        self.assertIn('end', segment_dict)
    
    def test_asr_result(self):
        """Test ASRResult creation and serialization."""
        result = create_sample_asr_result()
        
        self.assertEqual(result.text, "Test transcription")
        self.assertEqual(result.engine, "asr_a_whisper")
        self.assertEqual(len(result.segments), 1)
    
    def test_fusion_result(self):
        """Test FusionResult creation and serialization."""
        from core.models import FusionResult
        
        result = create_sample_fusion_result()
        result_dict = result.to_dict()
        
        self.assertEqual(result.fused_text, "Test transcription")
        self.assertEqual(result.agreement_score, 0.90)
        self.assertIn('hypotheses', result_dict)


class TestASRConfiguration(unittest.TestCase):
    """Test ASR configuration."""
    
    def test_asr_whisper_config(self):
        """Test ASR-A uses correct config."""
        import config
        from asr.asr_whisper import ASRWhisper
        
        # Verify class uses config model size
        asr = object.__new__(ASRWhisper)
        asr.model_size = None
        asr.model = None
        self.assertEqual(asr._get_default_model_size(), config.WHISPER_MODEL_SIZE)
    
    def test_asr_indic_config(self):
        """Test ASR-B uses correct config."""
        import config
        from asr.asr_indic import ASRIndic
        
        asr = object.__new__(ASRIndic)
        asr.fallback_model = getattr(config, 'ASR_B_FALLBACK_MODEL', 'large-v3')
        asr.model = None
        expected = getattr(config, 'ASR_B_MODEL', None) or asr.fallback_model
        self.assertEqual(asr._get_default_model_size(), expected)
    
    def test_asr_english_config(self):
        """Test ASR-C uses correct config."""
        import config
        from asr.asr_english_fallback import ASREnglish
        
        asr = object.__new__(ASREnglish)
        asr.model = None
        expected = getattr(config, 'ASR_C_MODEL', 'medium')
        self.assertEqual(asr._get_default_model_size(), expected)


class TestASRRouteMapping(unittest.TestCase):
    """Test route to language mapping."""
    
    def test_whisper_route_mapping(self):
        """Test ASR-A route to language mapping."""
        from asr.asr_whisper import ASRWhisper
        
        self.assertEqual(ASRWhisper.route_to_language.get('punjabi_speech'), 'pa')
        self.assertEqual(ASRWhisper.route_to_language.get('english_speech'), 'en')
        self.assertIsNone(ASRWhisper.route_to_language.get('mixed'))
    
    def test_indic_route_mapping(self):
        """Test ASR-B route to language mapping (uses Hindi for Indic content)."""
        from asr.asr_indic import ASRIndic
        
        self.assertEqual(ASRIndic.route_to_language.get('punjabi_speech'), 'hi')
        self.assertEqual(ASRIndic.route_to_language.get('scripture_quote_likely'), 'hi')
    
    def test_english_route_mapping(self):
        """Test ASR-C always forces English."""
        from asr.asr_english_fallback import ASREnglish
        
        asr = object.__new__(ASREnglish)
        asr.force_language = 'en'
        
        # Should always return English regardless of route
        self.assertEqual(asr._get_language_for_route(None, 'punjabi_speech'), 'en')
        self.assertEqual(asr._get_language_for_route(None, 'mixed'), 'en')


def run_tests():
    """Run all ASR tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestASRImports))
    suite.addTests(loader.loadTestsFromTestCase(TestASRModels))
    suite.addTests(loader.loadTestsFromTestCase(TestASRConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestASRRouteMapping))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

