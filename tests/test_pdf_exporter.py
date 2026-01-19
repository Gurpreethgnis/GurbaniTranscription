"""
Test script for PDF Exporter.

Milestone 9: Verify PDF export works correctly.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    FormattedDocument,
    DocumentSection,
    QuoteContent
)
from exports.pdf_exporter import PDFExporter, WEASYPRINT_AVAILABLE


def create_test_document():
    """Create a test formatted document."""
    quote_content = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji",
        ang=1,
        raag="Japji",
        author="Guru Nanak Dev Ji"
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
    
    return FormattedDocument(
        title="Test Katha",
        source_file="test.mp3",
        created_at=datetime.now().isoformat(),
        sections=sections,
        metadata={"total_segments": 2}
    )


def test_pdf_export():
    """Test PDF export."""
    if not WEASYPRINT_AVAILABLE:
        print("[SKIP] WeasyPrint not installed, skipping PDF export test")
        print("       Install with: pip install weasyprint")
        return
    
    exporter = PDFExporter()
    document = create_test_document()
    
    output_path = Path("test_output.pdf")
    
    # Export
    result_path = exporter.export(document, output_path)
    
    # Verify file exists
    assert result_path.exists(), "PDF file should exist"
    assert result_path.suffix == ".pdf", "Should have .pdf extension"
    
    # Verify file is not empty
    file_size = result_path.stat().st_size
    assert file_size > 0, "PDF file should not be empty"
    
    print("[PASS] PDF export test passed")
    print(f"  - File size: {file_size} bytes")
    
    # Clean up
    result_path.unlink()


def main():
    """Run all tests."""
    print("Testing PDF Exporter...\n")
    
    test_pdf_export()
    
    if WEASYPRINT_AVAILABLE:
        print("\n[SUCCESS] All PDF Exporter tests passed!")
    else:
        print("\n[INFO] PDF exporter requires WeasyPrint (not installed)")


if __name__ == "__main__":
    main()
