"""
Consolidated utility tests.

Tests for:
- Device detection
- File management
- Audio utilities
- Denoising
- Evaluation utilities

Replaces: test_gpu.py, test_denoiser.py, test_eval.py
"""
import sys
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestDeviceDetection(unittest.TestCase):
    """Test device detection utilities."""
    
    def test_import_detect_device(self):
        """Test detect_device import from utils."""
        from utils.device_utils import detect_device
        self.assertTrue(callable(detect_device))
    
    def test_detect_device_returns_tuple(self):
        """Test detect_device returns device tuple."""
        from utils.device_utils import detect_device
        
        result = detect_device()
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIn(result[0], ['cuda', 'cpu'])


class TestFileManager(unittest.TestCase):
    """Test file manager utilities."""
    
    def test_import_file_manager(self):
        """Test FileManager import."""
        from utils.file_manager import FileManager
        self.assertTrue(hasattr(FileManager, 'save_transcription'))
        self.assertTrue(hasattr(FileManager, 'get_file_hash'))
    
    def test_file_manager_initialization(self):
        """Test FileManager initializes."""
        from utils.file_manager import FileManager
        
        manager = FileManager()
        self.assertIsNotNone(manager)


class TestAudioUtils(unittest.TestCase):
    """Test audio utilities."""
    
    def test_import_get_audio_duration(self):
        """Test get_audio_duration import."""
        from audio.audio_utils import get_audio_duration
        self.assertTrue(callable(get_audio_duration))


class TestDenoiser(unittest.TestCase):
    """Test audio denoising."""
    
    def test_import_denoiser(self):
        """Test AudioDenoiser import."""
        from audio.denoiser import AudioDenoiser
        self.assertTrue(hasattr(AudioDenoiser, 'denoise'))
    
    def test_denoiser_config(self):
        """Test denoiser configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'ENABLE_DENOISING'))
        self.assertTrue(hasattr(config, 'DENOISE_STRENGTH'))
        self.assertTrue(hasattr(config, 'DENOISE_BACKEND'))


class TestEvaluation(unittest.TestCase):
    """Test evaluation utilities."""
    
    def test_eval_config(self):
        """Test evaluation configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'EVAL_GROUND_TRUTH_DIR'))
        self.assertTrue(hasattr(config, 'EVAL_REPORTS_DIR'))
        self.assertTrue(hasattr(config, 'EVAL_WER_THRESHOLD'))
        self.assertTrue(hasattr(config, 'EVAL_CER_THRESHOLD'))
    
    def test_eval_thresholds_valid(self):
        """Test evaluation thresholds are valid."""
        import config
        
        self.assertGreater(config.EVAL_WER_THRESHOLD, 0)
        self.assertLess(config.EVAL_WER_THRESHOLD, 1)
        self.assertGreater(config.EVAL_CER_THRESHOLD, 0)
        self.assertLess(config.EVAL_CER_THRESHOLD, 1)


class TestConfigOrganization(unittest.TestCase):
    """Test config organization."""
    
    def test_core_settings(self):
        """Test core settings exist."""
        import config
        
        self.assertTrue(hasattr(config, 'BASE_DIR'))
        self.assertTrue(hasattr(config, 'UPLOAD_DIR'))
        self.assertTrue(hasattr(config, 'OUTPUT_DIR'))
    
    def test_asr_settings(self):
        """Test ASR settings exist."""
        import config
        
        self.assertTrue(hasattr(config, 'WHISPER_MODEL_SIZE'))
        self.assertTrue(hasattr(config, 'ASR_B_MODEL'))
        self.assertTrue(hasattr(config, 'ASR_C_MODEL'))
    
    def test_pipeline_settings(self):
        """Test pipeline settings exist."""
        import config
        
        self.assertTrue(hasattr(config, 'VAD_AGGRESSIVENESS'))
        self.assertTrue(hasattr(config, 'FUSION_AGREEMENT_THRESHOLD'))
    
    def test_scripture_settings(self):
        """Test scripture settings exist."""
        import config
        
        self.assertTrue(hasattr(config, 'SCRIPTURE_DB_PATH'))
        self.assertTrue(hasattr(config, 'QUOTE_MATCH_CONFIDENCE_THRESHOLD'))
    
    def test_server_settings(self):
        """Test server settings exist."""
        import config
        
        self.assertTrue(hasattr(config, 'HOST'))
        self.assertTrue(hasattr(config, 'PORT'))
        self.assertTrue(hasattr(config, 'DEBUG'))


def run_tests():
    """Run all utility tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDeviceDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestFileManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestDenoiser))
    suite.addTests(loader.loadTestsFromTestCase(TestEvaluation))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigOrganization))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

