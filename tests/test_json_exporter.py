"""
Test script for JSON Exporter.

Milestone 5: Verify JSON export works correctly.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    FormattedDocument,
    DocumentSection,
    QuoteContent
)
from exports.json_exporter import JSONExporter


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
            content="Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh",
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
        metadata={"total_segments": 3, "avg_confidence": 0.9}
    )


def test_json_export():
    """Test JSON export."""
    exporter = JSONExporter()
    document = create_test_document()
    
    output_path = Path("test_output.json")
    
    # Export
    result_path = exporter.export(document, output_path)
    
    # Verify file exists
    assert result_path.exists(), "JSON file should exist"
    assert result_path.suffix == ".json", "Should have .json extension"
    
    # Verify JSON is valid
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verify structure
    assert data["title"] == "Test Katha", "Title should match"
    assert data["source_file"] == "test.mp3", "Source file should match"
    assert len(data["sections"]) == 3, "Should have 3 sections"
    assert data["metadata"]["total_segments"] == 3, "Metadata should match"
    
    # Verify sections
    opening_section = data["sections"][0]
    assert opening_section["section_type"] == "opening_gurbani"
    assert isinstance(opening_section["content"], dict), "Quote content should be dict"
    assert opening_section["content"]["gurmukhi"] == "ਵਾਹਿਗੁਰੂ"
    
    fateh_section = data["sections"][1]
    assert fateh_section["section_type"] == "fateh"
    assert fateh_section["content"] == "Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh"
    
    # Verify Unicode is preserved
    assert "ਵਾਹਿਗੁਰੂ" in json.dumps(data, ensure_ascii=False), "Unicode should be preserved"
    
    print("[PASS] JSON export test passed")
    print(f"  - File size: {result_path.stat().st_size} bytes")
    print(f"  - Sections: {len(data['sections'])}")
    
    # Clean up
    result_path.unlink()


def test_json_roundtrip():
    """Test that exported JSON can be read back."""
    exporter = JSONExporter()
    document = create_test_document()
    
    output_path = Path("test_roundtrip.json")
    exporter.export(document, output_path)
    
    # Read back
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verify we can reconstruct key information
    assert data["title"] == document.title
    assert len(data["sections"]) == len(document.sections)
    
    # Clean up
    output_path.unlink()
    
    print("[PASS] JSON roundtrip test passed")


def main():
    """Run all tests."""
    print("Testing JSON Exporter...\n")
    
    test_json_export()
    test_json_roundtrip()
    
    print("\n[SUCCESS] All JSON Exporter tests passed!")


if __name__ == "__main__":
    main()
