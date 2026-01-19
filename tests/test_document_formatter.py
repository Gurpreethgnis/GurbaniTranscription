"""
Test script for DocumentFormatter.

Milestone 3: Verify document formatting works correctly.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    TranscriptionResult,
    ProcessedSegment,
    QuoteMatch,
    QuoteContent,
    ScriptureSource
)
from post.document_formatter import DocumentFormatter
from post.section_classifier import SectionClassifier


def create_test_transcription_result():
    """Create a test TranscriptionResult."""
    # Opening Gurbani
    opening_quote = QuoteMatch(
        source=ScriptureSource.SGGS,
        line_id="123",
        canonical_text="ਵਾਹਿਗੁਰੂ",
        spoken_text="waheguru",
        confidence=0.95,
        canonical_roman="Waheguru",
        ang=1,
        raag="Japji",
        author="Guru Nanak Dev Ji"
    )
    
    opening_seg = ProcessedSegment(
        start=0.0,
        end=5.0,
        route="scripture_quote_likely",
        type="scripture_quote",
        text="ਵਾਹਿਗੁਰੂ",
        confidence=0.95,
        language="pa",
        quote_match=opening_quote,
        roman="Waheguru"
    )
    
    # Fateh
    fateh_seg = ProcessedSegment(
        start=5.0,
        end=7.0,
        route="punjabi_speech",
        type="speech",
        text="Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh",
        confidence=0.9,
        language="pa",
        roman="Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh"
    )
    
    # Topic
    topic_seg = ProcessedSegment(
        start=7.0,
        end=15.0,
        route="punjabi_speech",
        type="speech",
        text="ਅੱਜ ਦੀ ਕਥਾ ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਜੀ ਬਾਰੇ ਹੈ",
        confidence=0.85,
        language="pa",
        roman="Ajj di katha Guru Nanak Dev Ji bare hai"
    )
    
    # Katha content
    katha_seg = ProcessedSegment(
        start=15.0,
        end=30.0,
        route="punjabi_speech",
        type="speech",
        text="ਇਹ ਕਥਾ ਬਹੁਤ ਮਹੱਤਵਪੂਰਨ ਹੈ",
        confidence=0.8,
        language="pa",
        roman="Eh katha bahut mahatvapurn hai"
    )
    
    # Inline quote
    inline_quote = QuoteMatch(
        source=ScriptureSource.SGGS,
        line_id="456",
        canonical_text="ਸਤਿਗੁਰੁ ਪ੍ਰਸਾਦਿ",
        spoken_text="satgur prasad",
        confidence=0.92,
        canonical_roman="Satgur Prasaad",
        ang=2,
        raag="Japji",
        author="Guru Nanak Dev Ji"
    )
    
    quote_seg = ProcessedSegment(
        start=30.0,
        end=35.0,
        route="scripture_quote_likely",
        type="scripture_quote",
        text="ਸਤਿਗੁਰੁ ਪ੍ਰਸਾਦਿ",
        confidence=0.92,
        language="pa",
        quote_match=inline_quote,
        roman="Satgur Prasaad"
    )
    
    segments = [opening_seg, fateh_seg, topic_seg, katha_seg, quote_seg]
    
    result = TranscriptionResult(
        filename="test_katha.mp3",
        segments=segments,
        transcription={
            "gurmukhi": " ".join(s.text for s in segments),
            "roman": " ".join(s.roman or s.text for s in segments if s.roman)
        },
        metrics={
            "total_segments": len(segments),
            "avg_confidence": sum(s.confidence for s in segments) / len(segments),
            "quotes_detected": 2
        }
    )
    
    return result


def test_document_formatting():
    """Test document formatting."""
    formatter = DocumentFormatter()
    result = create_test_transcription_result()
    
    formatted_doc = formatter.format_document(result)
    
    # Verify document structure
    assert formatted_doc.title == "test_katha", f"Expected title 'test_katha', got '{formatted_doc.title}'"
    assert formatted_doc.source_file == "test_katha.mp3"
    assert len(formatted_doc.sections) > 0, "Document should have sections"
    
    # Verify sections
    section_types = [s.section_type for s in formatted_doc.sections]
    assert "opening_gurbani" in section_types, "Should have opening_gurbani section"
    assert "fateh" in section_types, "Should have fateh section"
    assert "quote" in section_types, "Should have quote section"
    
    # Verify quote content structure
    opening_section = next(
        (s for s in formatted_doc.sections if s.section_type == "opening_gurbani"),
        None
    )
    assert opening_section is not None, "Should have opening_gurbani section"
    assert isinstance(opening_section.content, QuoteContent), "Opening should have QuoteContent"
    assert opening_section.content.gurmukhi == "ਵਾਹਿਗੁਰੂ", "Gurmukhi text should match"
    assert opening_section.content.ang == 1, "Ang should be 1"
    
    # Verify metadata
    assert formatted_doc.metadata["total_segments"] == 5
    assert formatted_doc.metadata["quote_count"] >= 1
    assert formatted_doc.metadata["has_fateh"] is True
    
    print("[PASS] Document formatting test passed")
    print(f"  - Title: {formatted_doc.title}")
    print(f"  - Sections: {len(formatted_doc.sections)}")
    print(f"  - Section types: {set(s.section_type for s in formatted_doc.sections)}")
    
    # Clean up
    formatter.close()
    
    return formatted_doc


def test_empty_segments():
    """Test handling of empty segments."""
    formatter = DocumentFormatter()
    
    result = TranscriptionResult(
        filename="empty.mp3",
        segments=[],
        transcription={"gurmukhi": "", "roman": ""},
        metrics={}
    )
    
    try:
        formatted_doc = formatter.format_document(result)
        assert False, "Should raise DocumentFormatError for empty segments"
    except Exception as e:
        assert "no segments" in str(e).lower(), f"Expected error about segments, got: {e}"
        print("[PASS] Empty segments handled correctly")
    
    formatter.close()


def main():
    """Run all tests."""
    print("Testing DocumentFormatter...\n")
    
    test_document_formatting()
    test_empty_segments()
    
    print("\n[SUCCESS] All DocumentFormatter tests passed!")


if __name__ == "__main__":
    main()
