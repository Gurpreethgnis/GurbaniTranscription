"""
Test script for Base Exporter.

Milestone 4: Verify base exporter interface works correctly.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    FormattedDocument,
    DocumentSection,
    QuoteContent,
    QuoteMatch,
    ScriptureSource
)
from exports import ExportManager
from exports.base_exporter import BaseExporter
from core.errors import ExportError


class TestExporter(BaseExporter):
    """Test exporter implementation."""
    
    def __init__(self):
        super().__init__("test", ".test")
        self.exported_docs = []
    
    def _export_impl(self, document: FormattedDocument, output_path: Path) -> Path:
        """Test implementation that just records the export."""
        self.exported_docs.append((document, output_path))
        # Create a dummy file
        output_path.write_text(f"Test export: {document.title}", encoding="utf-8")
        return output_path


def test_base_exporter():
    """Test base exporter functionality."""
    exporter = TestExporter()
    
    # Create test document
    quote_content = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji"
    )
    
    sections = [
        DocumentSection(
            section_type="opening_gurbani",
            content=quote_content,
            start_time=0.0,
            end_time=5.0
        ),
        DocumentSection(
            section_type="fateh",
            content="Waheguru Ji Ka Khalsa",
            start_time=5.0,
            end_time=7.0
        )
    ]
    
    doc = FormattedDocument(
        title="Test Document",
        source_file="test.mp3",
        created_at=datetime.now().isoformat(),
        sections=sections,
        metadata={}
    )
    
    # Test export
    output_path = Path("test_output.test")
    result_path = exporter.export(doc, output_path)
    
    assert result_path.exists(), "Exported file should exist"
    assert result_path.suffix == ".test", "Should have correct extension"
    assert len(exporter.exported_docs) == 1, "Should have recorded export"
    
    # Clean up
    result_path.unlink()
    
    print("[PASS] Base exporter test passed")


def test_export_manager():
    """Test export manager."""
    manager = ExportManager()
    
    # Register test exporter
    exporter = TestExporter()
    manager.register_exporter("test", exporter)
    
    # Test get_exporter
    retrieved = manager.get_exporter("test")
    assert retrieved is exporter, "Should return registered exporter"
    
    # Test unsupported format
    try:
        manager.get_exporter("unknown")
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "not supported" in str(e).lower()
        print("[PASS] Unsupported format handled correctly")
    
    # Test get_supported_formats
    formats = manager.get_supported_formats()
    assert "test" in formats, "Should include registered format"
    
    print("[PASS] Export manager test passed")


def test_helper_methods():
    """Test base exporter helper methods."""
    exporter = TestExporter()
    
    # Test with QuoteContent
    quote_content = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji"
    )
    
    quote_section = DocumentSection(
        section_type="quote",
        content=quote_content,
        start_time=0.0,
        end_time=5.0
    )
    
    text = exporter._get_section_text(quote_section)
    assert text == "ਵਾਹਿਗੁਰੂ", "Should extract Gurmukhi text"
    
    roman = exporter._get_section_roman(quote_section)
    assert roman == "Waheguru", "Should extract Roman text"
    
    # Test with string content
    text_section = DocumentSection(
        section_type="katha",
        content="Regular text",
        start_time=10.0,
        end_time=15.0
    )
    
    text = exporter._get_section_text(text_section)
    assert text == "Regular text", "Should extract string text"
    
    roman = exporter._get_section_roman(text_section)
    assert roman is None, "String sections don't have Roman"
    
    print("[PASS] Helper methods test passed")


def main():
    """Run all tests."""
    print("Testing Base Exporter...\n")
    
    test_base_exporter()
    test_export_manager()
    test_helper_methods()
    
    print("\n[SUCCESS] All Base Exporter tests passed!")


if __name__ == "__main__":
    main()
