"""
Consolidated API endpoint tests.

Tests for:
- Flask routes
- Upload endpoint
- Transcribe endpoints
- Export endpoints
- Status/health endpoints

Replaces: test_server_health.py, test_transcribe_v2.py, test_live_route.py
"""
import sys
from pathlib import Path
import unittest
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAPIImports(unittest.TestCase):
    """Test API imports."""
    
    def test_import_flask_app(self):
        """Test Flask app import."""
        from app import app
        self.assertIsNotNone(app)
    
    def test_import_config(self):
        """Test config import."""
        import config
        self.assertTrue(hasattr(config, 'HOST'))
        self.assertTrue(hasattr(config, 'PORT'))


class TestAPIRoutes(unittest.TestCase):
    """Test API route definitions."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_index_route_exists(self):
        """Test index route exists."""
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])
    
    def test_status_route_exists(self):
        """Test status route exists."""
        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')
    
    def test_live_route_exists(self):
        """Test live route exists."""
        response = self.client.get('/live')
        self.assertEqual(response.status_code, 200)
    
    def test_history_route_exists(self):
        """Test history route exists."""
        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)


class TestUploadEndpoint(unittest.TestCase):
    """Test upload endpoint."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_upload_requires_file(self):
        """Test upload requires a file."""
        response = self.client.post('/upload')
        self.assertEqual(response.status_code, 400)


class TestTranscribeEndpoint(unittest.TestCase):
    """Test transcribe endpoints."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_transcribe_requires_filename(self):
        """Test transcribe requires filename."""
        response = self.client.post(
            '/transcribe',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_transcribe_v2_requires_filename(self):
        """Test transcribe-v2 requires filename."""
        response = self.client.post(
            '/transcribe-v2',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_transcribe_nonexistent_file(self):
        """Test transcribe returns 404 for nonexistent file."""
        response = self.client.post(
            '/transcribe-v2',
            data=json.dumps({'filename': 'nonexistent.mp3'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)


class TestExportEndpoint(unittest.TestCase):
    """Test export endpoints."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_export_nonexistent_file(self):
        """Test export returns error for nonexistent file."""
        response = self.client.get('/export/nonexistent.mp3/txt')
        self.assertIn(response.status_code, [404, 500])


class TestLogEndpoint(unittest.TestCase):
    """Test log endpoint."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_log_returns_list(self):
        """Test log endpoint returns a list."""
        response = self.client.get('/log')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)


class TestProgressEndpoint(unittest.TestCase):
    """Test progress endpoint."""
    
    def setUp(self):
        from app import app
        self.app = app
        self.client = app.test_client()
    
    def test_progress_nonexistent_file(self):
        """Test progress returns 404 for nonexistent file."""
        response = self.client.get('/progress/nonexistent.mp3')
        self.assertEqual(response.status_code, 404)


def run_tests():
    """Run all API tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAPIImports))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIRoutes))
    suite.addTests(loader.loadTestsFromTestCase(TestUploadEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestTranscribeEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestExportEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestLogEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestProgressEndpoint))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

