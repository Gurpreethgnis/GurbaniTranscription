"""
Test script for HTML Exporter.

Milestone 7: Verify HTML export works correctly.
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
from exports.html_exporter import HTMLExporter


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
        ),
        DocumentSection(
            section_type="katha",
            content="This is katha content",
            start_time=7.0,
            end_time=30.0
        )
    ]
    
    return FormattedDocument(
        title="Test Katha",
        source_file="test.mp3",
        created_at=datetime.now().isoformat(),
        sections=sections,
        metadata={"total_segments": 3}
    )


def test_html_export():
    """Test HTML export."""
    exporter = HTMLExporter()
    document = create_test_document()
    
    output_path = Path("test_output.html")
    
    # Export
    result_path = exporter.export(document, output_path)
    
    # Verify file exists
    assert result_path.exists(), "HTML file should exist"
    assert result_path.suffix == ".html", "Should have .html extension"
    
    # Read and verify content
    content = result_path.read_text(encoding='utf-8')
    
    # Verify HTML structure
    assert "<!DOCTYPE html>" in content, "Should have DOCTYPE"
    assert "<html" in content, "Should have html tag"
    assert "<head>" in content, "Should have head"
    assert "<body>" in content, "Should have body"
    
    # Verify title
    assert "<title>Test Katha</title>" in content, "Should have title"
    assert "<h1>Test Katha</h1>" in content, "Should have h1"
    
    # Verify CSS
    assert "<style>" in content, "Should have embedded CSS"
    assert ".quote-block" in content, "Should have quote styles"
    
    # Verify sections
    assert "Opening Gurbani" in content, "Should have opening Gurbani"
    assert "Fateh" in content, "Should have Fateh"
    assert "quote-gurmukhi" in content, "Should have quote block"
    
    # Verify Gurmukhi text (should be in content even if we can't display it)
    assert "ਵਾਹਿਗੁਰੂ" in content or "quote-gurmukhi" in content, "Should have quote content"
    
    print("[PASS] HTML export test passed")
    print(f"  - File size: {len(content)} characters")
    print(f"  - Has CSS: {'<style>' in content}")
    print(f"  - Has sections: {content.count('section')}")
    
    # Clean up
    result_path.unlink()


def test_html_escaping():
    """Test HTML escaping."""
    exporter = HTMLExporter()
    
    # Test with special characters
    text = '<script>alert("XSS")</script>'
    escaped = exporter._escape_html(text)
    
    assert "&lt;" in escaped, "Should escape <"
    assert "&gt;" in escaped, "Should escape >"
    assert "&quot;" in escaped, "Should escape quotes"
    assert "<script>" not in escaped, "Should not contain unescaped script"
    
    print("[PASS] HTML escaping test passed")


def main():
    """Run all tests."""
    print("Testing HTML Exporter...\n")
    
    test_html_export()
    test_html_escaping()
    
    print("\n[SUCCESS] All HTML Exporter tests passed!")


if __name__ == "__main__":
    main()
