"""
Test script for document formatting models.

Milestone 1: Verify data models work correctly.
"""
import json
from datetime import datetime
from core.models import (
    QuoteContent,
    DocumentSection,
    FormattedDocument,
    ScriptureSource
)


def test_quote_content():
    """Test QuoteContent model."""
    quote = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        english_translation="Wonderful Lord",
        source="Sri Guru Granth Sahib Ji",
        ang=1,
        raag="Japji",
        author="Guru Nanak Dev Ji",
        context_lines=["Line 1", "Line 2"],
        line_id="123",
        shabad_id="456"
    )
    
    # Test serialization
    quote_dict = quote.to_dict()
    assert quote_dict["gurmukhi"] == "ਵਾਹਿਗੁਰੂ"
    assert quote_dict["roman"] == "Waheguru"
    assert quote_dict["ang"] == 1
    assert len(quote_dict["context_lines"]) == 2
    
    print("[PASS] QuoteContent model test passed")
    return quote


def test_document_section():
    """Test DocumentSection model."""
    # Test with quote content
    quote = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji"
    )
    
    section = DocumentSection(
        section_type="quote",
        content=quote,
        start_time=10.5,
        end_time=15.2,
        confidence=0.95
    )
    
    section_dict = section.to_dict()
    assert section_dict["section_type"] == "quote"
    assert section_dict["start_time"] == 10.5
    assert isinstance(section_dict["content"], dict)
    assert section_dict["content"]["gurmukhi"] == "ਵਾਹਿਗੁਰੂ"
    
    # Test with text content
    text_section = DocumentSection(
        section_type="katha",
        content="This is katha content",
        start_time=20.0,
        end_time=25.0
    )
    
    text_dict = text_section.to_dict()
    assert text_dict["section_type"] == "katha"
    assert text_dict["content"] == "This is katha content"
    
    print("[PASS] DocumentSection model test passed")
    return section, text_section


def test_formatted_document():
    """Test FormattedDocument model."""
    quote = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji"
    )
    
    sections = [
        DocumentSection(
            section_type="opening_gurbani",
            content=quote,
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
            content="This is the main katha content",
            start_time=7.0,
            end_time=100.0
        )
    ]
    
    doc = FormattedDocument(
        title="Test Katha",
        source_file="test.mp3",
        created_at=datetime.now().isoformat(),
        sections=sections,
        metadata={"total_segments": 10, "avg_confidence": 0.85}
    )
    
    doc_dict = doc.to_dict()
    assert doc_dict["title"] == "Test Katha"
    assert len(doc_dict["sections"]) == 3
    assert doc_dict["metadata"]["total_segments"] == 10
    
    # Test JSON serialization
    json_str = json.dumps(doc_dict, ensure_ascii=False, indent=2)
    assert len(json_str) > 0
    
    print("[PASS] FormattedDocument model test passed")
    return doc


def main():
    """Run all tests."""
    print("Testing document formatting models...\n")
    
    test_quote_content()
    test_document_section()
    test_formatted_document()
    
    print("\n[SUCCESS] All model tests passed!")


if __name__ == "__main__":
    main()
