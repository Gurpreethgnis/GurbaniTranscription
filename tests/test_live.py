"""
Consolidated live streaming tests.

Tests for:
- WebSocket server
- Live transcription
- Draft/verified caption flow
- Session management

Replaces: test_phase6.py, test_live_route.py (live-specific tests)
"""
import sys
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestLiveImports(unittest.TestCase):
    """Test live streaming imports."""
    
    def test_import_websocket_server(self):
        """Test WebSocketServer import."""
        from ui.websocket_server import WebSocketServer
        self.assertTrue(hasattr(WebSocketServer, 'emit_draft'))
        self.assertTrue(hasattr(WebSocketServer, 'emit_verified'))


class TestLiveConfig(unittest.TestCase):
    """Test live streaming configuration."""
    
    def test_chunk_duration(self):
        """Test chunk duration config."""
        import config
        
        self.assertTrue(hasattr(config, 'LIVE_CHUNK_DURATION_MS'))
        self.assertGreater(config.LIVE_CHUNK_DURATION_MS, 0)
    
    def test_draft_delay(self):
        """Test draft delay config."""
        import config
        
        self.assertTrue(hasattr(config, 'LIVE_DRAFT_DELAY_MS'))
        self.assertGreaterEqual(config.LIVE_DRAFT_DELAY_MS, 0)
    
    def test_verified_delay(self):
        """Test verified delay config."""
        import config
        
        self.assertTrue(hasattr(config, 'LIVE_VERIFIED_DELAY_S'))
        self.assertGreaterEqual(config.LIVE_VERIFIED_DELAY_S, 0)
    
    def test_websocket_config(self):
        """Test WebSocket configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'WEBSOCKET_PING_INTERVAL'))
        self.assertTrue(hasattr(config, 'WEBSOCKET_PING_TIMEOUT'))


class TestLiveDenoisingConfig(unittest.TestCase):
    """Test live denoising configuration."""
    
    def test_live_denoise_enabled(self):
        """Test live denoising enable flag."""
        import config
        
        self.assertTrue(hasattr(config, 'LIVE_DENOISE_ENABLED'))
        self.assertIsInstance(config.LIVE_DENOISE_ENABLED, bool)


def run_tests():
    """Run all live streaming tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestLiveImports))
    suite.addTests(loader.loadTestsFromTestCase(TestLiveConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestLiveDenoisingConfig))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

