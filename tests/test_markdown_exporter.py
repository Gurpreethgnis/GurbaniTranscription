"""
Test script for Markdown Exporter.

Milestone 6: Verify Markdown export works correctly.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    FormattedDocument,
    DocumentSection,
    QuoteContent
)
from exports.markdown_exporter import MarkdownExporter


def create_test_document():
    """Create a test formatted document."""
    quote_content = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji",
        ang=1,
        raag="Japji",
        author="Guru Nanak Dev Ji",
        context_lines=["Context line 1", "Context line 2"]
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
            content="Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh",
            start_time=5.0,
            end_time=7.0
        ),
        DocumentSection(
            section_type="katha",
            content="This is the main katha content with multiple lines.\nIt continues here.",
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


def test_markdown_export():
    """Test Markdown export."""
    exporter = MarkdownExporter()
    document = create_test_document()
    
    output_path = Path("test_output.md")
    
    # Export
    result_path = exporter.export(document, output_path)
    
    # Verify file exists
    assert result_path.exists(), "Markdown file should exist"
    assert result_path.suffix == ".md", "Should have .md extension"
    
    # Read and verify content
    content = result_path.read_text(encoding='utf-8')
    
    # Verify title
    assert "# Test Katha" in content, "Should have title"
    
    # Verify metadata
    assert "**Source:**" in content, "Should have source header"
    assert "test.mp3" in content, "Should have source filename"
    
    # Verify sections
    assert "## Opening Gurbani" in content, "Should have opening Gurbani header"
    assert "## Fateh" in content, "Should have Fateh header"
    assert "ਵਾਹਿਗੁਰੂ" in content, "Should have Gurmukhi text"
    assert "*Waheguru*" in content, "Should have Roman transliteration"
    
    # Verify quote metadata
    assert "Ang: 1" in content, "Should have Ang"
    assert "Raag: Japji" in content, "Should have Raag"
    assert "Author: Guru Nanak Dev Ji" in content, "Should have Author"
    
    # Verify context lines
    assert "Context:" in content, "Should have context section"
    assert "Context line 1" in content, "Should have context lines"
    
    # Verify timestamps
    assert "[Time:" in content, "Should have timestamps"
    
    print("[PASS] Markdown export test passed")
    print(f"  - File size: {len(content)} characters")
    print(f"  - Lines: {len(content.splitlines())}")
    
    # Show first few lines (skip Unicode for Windows console)
    print("\n  First 10 lines:")
    for i, line in enumerate(content.splitlines()[:10], 1):
        try:
            print(f"    {i}: {line[:60]}...")
        except UnicodeEncodeError:
            # Skip lines with problematic Unicode for console display
            print(f"    {i}: [Line with Unicode content]")
    
    # Clean up
    result_path.unlink()


def test_quote_formatting():
    """Test quote formatting specifically."""
    exporter = MarkdownExporter()
    
    quote = QuoteContent(
        gurmukhi="ਸਤਿਗੁਰੁ ਪ੍ਰਸਾਦਿ",
        roman="Satgur Prasaad",
        source="Sri Guru Granth Sahib Ji",
        ang=2
    )
    
    section = DocumentSection(
        section_type="quote",
        content=quote,
        start_time=10.0,
        end_time=15.0
    )
    
    formatted = exporter._format_section(section)
    
    assert "ਸਤਿਗੁਰੁ ਪ੍ਰਸਾਦਿ" in formatted, "Should have Gurmukhi"
    assert "*Satgur Prasaad*" in formatted, "Should have Roman"
    assert "Ang: 2" in formatted, "Should have metadata"
    assert "[Time:" in formatted, "Should have timestamp"
    
    print("[PASS] Quote formatting test passed")


def main():
    """Run all tests."""
    print("Testing Markdown Exporter...\n")
    
    test_markdown_export()
    test_quote_formatting()
    
    print("\n[SUCCESS] All Markdown Exporter tests passed!")


if __name__ == "__main__":
    main()
