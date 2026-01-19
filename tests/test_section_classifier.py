"""
Test script for SectionClassifier.

Milestone 2: Verify section classification works correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ProcessedSegment, QuoteMatch, ScriptureSource
from post.section_classifier import SectionClassifier, ClassifiedSection


def create_test_segments():
    """Create test segments for classification."""
    # Opening Gurbani (with quote match)
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
    
    # Fateh segment
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
    
    # Topic segment (after fateh, contains topic keywords)
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
    
    # Regular katha content
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
    
    # Inline quote (later in katha)
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
    
    return [opening_seg, fateh_seg, topic_seg, katha_seg, quote_seg]


def test_classification():
    """Test section classification."""
    classifier = SectionClassifier()
    segments = create_test_segments()
    
    classified = classifier.classify_segments(segments)
    
    # Verify classifications
    assert len(classified) == 5, f"Expected 5 classified sections, got {len(classified)}"
    
    # Check opening Gurbani
    opening = [c for c in classified if c.section_type == "opening_gurbani"]
    assert len(opening) == 1, f"Expected 1 opening_gurbani, got {len(opening)}"
    assert opening[0].confidence >= 0.9, "Opening Gurbani should have high confidence"
    
    # Check Fateh
    fateh = [c for c in classified if c.section_type == "fateh"]
    assert len(fateh) == 1, f"Expected 1 fateh, got {len(fateh)}"
    
    # Check topic
    topic = [c for c in classified if c.section_type == "topic"]
    assert len(topic) >= 1, f"Expected at least 1 topic, got {len(topic)}"
    
    # Check quote
    quotes = [c for c in classified if c.section_type == "quote"]
    assert len(quotes) == 1, f"Expected 1 quote, got {len(quotes)}"
    
    # Check katha (some segments may be classified as topic instead)
    katha = [c for c in classified if c.section_type == "katha"]
    # We should have at least some non-quote, non-fateh content
    non_special = [c for c in classified if c.section_type in ["katha", "topic"]]
    assert len(non_special) >= 1, f"Expected at least 1 katha/topic, got {len(non_special)}"
    
    print("[PASS] Section classification test passed")
    print(f"  - Opening Gurbani: {len(opening)}")
    print(f"  - Fateh: {len(fateh)}")
    print(f"  - Topic: {len(topic)}")
    print(f"  - Quotes: {len(quotes)}")
    print(f"  - Katha: {len(katha)}")
    
    return classified


def test_helper_methods():
    """Test helper methods."""
    classifier = SectionClassifier()
    segments = create_test_segments()
    classified = classifier.classify_segments(segments)
    
    # Test get_opening_gurbani
    opening = classifier.get_opening_gurbani(classified)
    assert len(opening) == 1, "Should find 1 opening Gurbani"
    
    # Test get_fateh
    fateh = classifier.get_fateh(classified)
    assert fateh is not None, "Should find Fateh"
    assert fateh.section_type == "fateh", "Should be fateh type"
    
    # Test get_topic
    topic = classifier.get_topic(classified)
    assert topic is not None, "Should find topic"
    assert topic.section_type == "topic", "Should be topic type"
    
    print("[PASS] Helper methods test passed")


def main():
    """Run all tests."""
    print("Testing SectionClassifier...\n")
    
    test_classification()
    test_helper_methods()
    
    print("\n[SUCCESS] All SectionClassifier tests passed!")


if __name__ == "__main__":
    main()
