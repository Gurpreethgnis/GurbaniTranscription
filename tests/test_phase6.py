"""
Phase 6: Live Mode + WebSocket UI - Test Suite

Tests for live transcription WebSocket functionality.
Note: Full end-to-end testing requires a microphone and browser.
"""
import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from ui.websocket_server import WebSocketServer
import config


class TestWebSocketServer(unittest.TestCase):
    """Test WebSocket server initialization and basic functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    def test_websocket_server_initialization(self):
        """Test WebSocket server can be initialized."""
        server = WebSocketServer(self.app, orchestrator_callback=None)
        self.assertIsNotNone(server)
        self.assertIsNotNone(server.socketio)
        self.assertEqual(server.app, self.app)
    
    def test_websocket_server_with_callback(self):
        """Test WebSocket server with orchestrator callback."""
        def test_callback(audio_bytes, session_id, chunk_data):
            pass
        
        server = WebSocketServer(self.app, orchestrator_callback=test_callback)
        self.assertEqual(server.orchestrator_callback, test_callback)
    
    def test_emit_draft_caption(self):
        """Test draft caption emission (mock)."""
        server = WebSocketServer(self.app, orchestrator_callback=None)
        
        # Test that method exists and can be called without errors
        # (actual emission requires active WebSocket connection)
        try:
            server.emit_draft_caption(
                session_id="test_session",
                segment_id="seg_001",
                start=0.0,
                end=1.0,
                text="Test text",
                confidence=0.8,
                gurmukhi="ਟੈਸਟ",
                roman="Test"
            )
            # If no exception, method works
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"emit_draft_caption failed: {e}")
    
    def test_emit_verified_update(self):
        """Test verified update emission (mock)."""
        server = WebSocketServer(self.app, orchestrator_callback=None)
        
        try:
            server.emit_verified_update(
                session_id="test_session",
                segment_id="seg_001",
                start=0.0,
                end=1.0,
                gurmukhi="ਟੈਸਟ",
                roman="Test",
                confidence=0.9,
                quote_match=None,
                needs_review=False
            )
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"emit_verified_update failed: {e}")
    
    def test_emit_error(self):
        """Test error emission (mock)."""
        server = WebSocketServer(self.app, orchestrator_callback=None)
        
        try:
            server.emit_error(
                session_id="test_session",
                message="Test error",
                error_type="test"
            )
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"emit_error failed: {e}")


class TestLiveOrchestratorIntegration(unittest.TestCase):
    """Test live orchestrator integration."""
    
    def test_live_callback_parameter(self):
        """Test orchestrator accepts live_callback parameter."""
        from orchestrator import Orchestrator
        
        def test_callback(event_type, data):
            pass
        
        # Should not raise exception
        try:
            orch = Orchestrator(live_callback=test_callback)
            self.assertIsNotNone(orch.live_callback)
        except Exception as e:
            self.fail(f"Orchestrator with live_callback failed: {e}")
    
    def test_process_live_audio_chunk_method_exists(self):
        """Test process_live_audio_chunk method exists."""
        from orchestrator import Orchestrator
        
        orch = Orchestrator()
        self.assertTrue(hasattr(orch, 'process_live_audio_chunk'))
        self.assertTrue(callable(getattr(orch, 'process_live_audio_chunk')))


class TestConfig(unittest.TestCase):
    """Test Phase 6 configuration parameters."""
    
    def test_live_config_parameters_exist(self):
        """Test Phase 6 config parameters are defined."""
        self.assertTrue(hasattr(config, 'LIVE_CHUNK_DURATION_MS'))
        self.assertTrue(hasattr(config, 'LIVE_DRAFT_DELAY_MS'))
        self.assertTrue(hasattr(config, 'LIVE_VERIFIED_DELAY_S'))
        self.assertTrue(hasattr(config, 'WEBSOCKET_PING_INTERVAL'))
        self.assertTrue(hasattr(config, 'WEBSOCKET_PING_TIMEOUT'))
    
    def test_live_config_parameter_types(self):
        """Test config parameters have correct types."""
        self.assertIsInstance(config.LIVE_CHUNK_DURATION_MS, int)
        self.assertIsInstance(config.LIVE_DRAFT_DELAY_MS, int)
        self.assertIsInstance(config.LIVE_VERIFIED_DELAY_S, float)
        self.assertIsInstance(config.WEBSOCKET_PING_INTERVAL, int)
        self.assertIsInstance(config.WEBSOCKET_PING_TIMEOUT, int)


class TestRoutes(unittest.TestCase):
    """Test Flask routes for live mode."""
    
    def setUp(self):
        """Set up test client."""
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_live_route_exists(self):
        """Test /live route exists and returns 200."""
        response = self.client.get('/live')
        self.assertEqual(response.status_code, 200)
    
    def test_live_route_returns_html(self):
        """Test /live route returns HTML content."""
        response = self.client.get('/live')
        self.assertIn(b'<!DOCTYPE html>', response.data)
        self.assertIn(b'Live Katha Transcription', response.data)
    
    def test_live_route_includes_socketio_script(self):
        """Test /live route includes Socket.IO client script."""
        response = self.client.get('/live')
        self.assertIn(b'socket.io', response.data.lower())


class TestDependencies(unittest.TestCase):
    """Test Phase 6 dependencies are available."""
    
    def test_flask_socketio_import(self):
        """Test flask-socketio can be imported."""
        try:
            import flask_socketio
            self.assertTrue(True)
        except ImportError:
            self.fail("flask-socketio not installed")
    
    def test_eventlet_import(self):
        """Test eventlet can be imported."""
        try:
            import eventlet
            self.assertTrue(True)
        except ImportError:
            self.fail("eventlet not installed")


if __name__ == '__main__':
    unittest.main()
