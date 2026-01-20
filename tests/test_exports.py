"""
Consolidated export tests.

Tests for:
- BaseExporter
- ExportManager
- JSON Exporter
- Markdown Exporter
- HTML Exporter
- DOCX Exporter
- PDF Exporter

Replaces: test_base_exporter.py, test_json_exporter.py, test_markdown_exporter.py,
          test_html_exporter.py, test_docx_exporter.py, test_pdf_exporter.py
"""
import sys
from pathlib import Path
import tempfile
import unittest
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures import create_sample_document
from exports import ExportManager
from exports.base_exporter import BaseExporter
from core.models import FormattedDocument


class MockExporter(BaseExporter):
    """Mock exporter for testing base functionality."""
    
    def __init__(self):
        super().__init__("mock", ".mock")
        self.export_calls = []
    
    def _export_impl(self, document: FormattedDocument, output_path: Path) -> Path:
        self.export_calls.append((document, output_path))
        output_path.write_text(f"Mock: {document.title}", encoding="utf-8")
        return output_path


class TestBaseExporter(unittest.TestCase):
    """Test base exporter functionality."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.exporter = MockExporter()
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_creates_file(self):
        """Test that export creates a file."""
        doc = create_sample_document()
        output_path = self.test_dir / "output.mock"
        
        result = self.exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        self.assertEqual(result.suffix, ".mock")
    
    def test_export_records_call(self):
        """Test that export records the call."""
        doc = create_sample_document()
        output_path = self.test_dir / "output.mock"
        
        self.exporter.export(doc, output_path)
        
        self.assertEqual(len(self.exporter.export_calls), 1)
        self.assertEqual(self.exporter.export_calls[0][0].title, doc.title)
    
    def test_get_section_text(self):
        """Test _get_section_text helper."""
        doc = create_sample_document()
        
        # Test string content
        fateh_section = doc.sections[1]
        text = self.exporter._get_section_text(fateh_section)
        self.assertIn("Waheguru Ji Ka Khalsa", text)
        
        # Test QuoteContent
        gurbani_section = doc.sections[0]
        text = self.exporter._get_section_text(gurbani_section)
        self.assertIn("ਵਾਹਿਗੁਰੂ", text)


class TestExportManager(unittest.TestCase):
    """Test export manager."""
    
    def test_register_exporter(self):
        """Test registering an exporter."""
        manager = ExportManager()
        exporter = MockExporter()
        
        manager.register_exporter("mock", exporter)
        
        self.assertEqual(manager.get_exporter("mock"), exporter)
    
    def test_get_unregistered_exporter(self):
        """Test getting an unregistered exporter returns None."""
        manager = ExportManager()
        
        result = manager.get_exporter("nonexistent")
        
        self.assertIsNone(result)
    
    def test_list_exporters(self):
        """Test listing registered exporters."""
        manager = ExportManager()
        exporter = MockExporter()
        manager.register_exporter("mock", exporter)
        
        exporters = manager.list_exporters()
        
        self.assertIn("mock", exporters)


class TestJSONExporter(unittest.TestCase):
    """Test JSON exporter."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_json(self):
        """Test JSON export creates valid JSON."""
        from exports.json_exporter import JSONExporter
        import json
        
        exporter = JSONExporter()
        doc = create_sample_document()
        output_path = self.test_dir / "output.json"
        
        result = exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        with open(result, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data['title'], doc.title)
        self.assertIn('sections', data)


class TestMarkdownExporter(unittest.TestCase):
    """Test Markdown exporter."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_markdown(self):
        """Test Markdown export."""
        from exports.markdown_exporter import MarkdownExporter
        
        exporter = MarkdownExporter()
        doc = create_sample_document()
        output_path = self.test_dir / "output.md"
        
        result = exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        content = result.read_text(encoding='utf-8')
        self.assertIn(doc.title, content)
        self.assertIn('#', content)  # Markdown heading


class TestHTMLExporter(unittest.TestCase):
    """Test HTML exporter."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_html(self):
        """Test HTML export."""
        from exports.html_exporter import HTMLExporter
        
        exporter = HTMLExporter()
        doc = create_sample_document()
        output_path = self.test_dir / "output.html"
        
        result = exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        content = result.read_text(encoding='utf-8')
        self.assertIn('<html', content)
        self.assertIn(doc.title, content)


class TestDOCXExporter(unittest.TestCase):
    """Test DOCX exporter."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_docx(self):
        """Test DOCX export."""
        try:
            from exports.docx_exporter import DOCXExporter
        except ImportError:
            self.skipTest("python-docx not installed")
        
        exporter = DOCXExporter()
        doc = create_sample_document()
        output_path = self.test_dir / "output.docx"
        
        result = exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        self.assertEqual(result.suffix, '.docx')


class TestPDFExporter(unittest.TestCase):
    """Test PDF exporter."""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_export_pdf(self):
        """Test PDF export."""
        try:
            from exports.pdf_exporter import PDFExporter
        except ImportError:
            self.skipTest("reportlab not installed")
        
        exporter = PDFExporter()
        doc = create_sample_document()
        output_path = self.test_dir / "output.pdf"
        
        result = exporter.export(doc, output_path)
        
        self.assertTrue(result.exists())
        self.assertEqual(result.suffix, '.pdf')


def run_tests():
    """Run all export tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestBaseExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestExportManager))
    suite.addTests(loader.loadTestsFromTestCase(TestJSONExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestMarkdownExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestHTMLExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestDOCXExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestPDFExporter))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

