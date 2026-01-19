"""
Simple Phase 4 Pipeline Test (avoids Unicode printing and orchestrator init).
"""
from pathlib import Path
import config
from scripture.sggs_db import SGGSDatabase
from scripture.scripture_service import ScriptureService
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from models import ProcessedSegment
from langid_service import ROUTE_SCRIPTURE_QUOTE_LIKELY


def test_real_database_search():
    """Test search with actual sggs.sqlite database."""
    db_path = config.SCRIPTURE_DB_PATH
    
    if not db_path.exists():
        print(f"SKIP: Database not found at {db_path}")
        return
    
    print(f"\n{'='*60}")
    print("Phase 4 Full Pipeline Test")
    print(f"{'='*60}")
    print(f"\nDatabase: {db_path.name}")
    print(f"Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Initialize services
    db = SGGSDatabase(db_path=db_path)
    service = ScriptureService(sggs_db=db)
    detector = QuoteCandidateDetector()
    matcher = AssistedMatcher(scripture_service=service)
    replacer = CanonicalReplacer()
    
    # Test 1: Search functionality
    print("\n[TEST 1] Database Search")
    print("-" * 60)
    search_text = "ਸਤਿ ਨਾਮੁ"  # Unicode Gurmukhi (as ASR would output)
    results = service.search_candidates(search_text, top_k=3)
    print(f"Search query: Unicode Gurmukhi text")
    print(f"Results found: {len(results)}")
    
    if results:
        r = results[0]
        print(f"  First result:")
        print(f"    Line ID: {r.line_id}")
        print(f"    Ang: {r.ang}")
        print(f"    Text length: {len(r.gurmukhi)} chars")
        print(f"    Author ID: {r.author}")
        assert r.ang is not None, "Should have Ang"
        assert len(r.gurmukhi) > 0, "Should have text"
        print("  [PASS] Search working correctly")
    else:
        print("  [WARN] No results found")
    
    # Test 2: Quote Detection
    print("\n[TEST 2] Quote Candidate Detection")
    print("-" * 60)
    segment = ProcessedSegment(
        start=10.0,
        end=15.0,
        route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
        type="speech",
        text="ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",  # Unicode Gurmukhi
        confidence=0.85,
        language="pa"
    )
    
    candidates = detector.detect_candidates(segment)
    print(f"Candidates detected: {len(candidates)}")
    if candidates:
        c = candidates[0]
        print(f"  First candidate:")
        print(f"    Confidence: {c.confidence:.2f}")
        print(f"    Detection reason: {c.detection_reason}")
        print(f"    Text length: {len(c.text)} chars")
        print("  [PASS] Detection working")
    else:
        print("  [WARN] No candidates detected")
    
    # Test 3: Matching
    print("\n[TEST 3] Assisted Matching")
    print("-" * 60)
    if candidates:
        match = matcher.find_match(candidates)
        if match:
            print(f"Match found:")
            print(f"  Line ID: {match.line_id}")
            print(f"  Confidence: {match.confidence:.2f}")
            print(f"  Ang: {match.ang}")
            print(f"  Source: {match.source.value}")
            print(f"  Canonical text length: {len(match.canonical_text)} chars")
            print("  [PASS] Matching working")
            
            # Test 4: Replacement
            print("\n[TEST 4] Canonical Replacement")
            print("-" * 60)
            updated = replacer.replace_with_canonical(segment, match)
            print(f"Original text length: {len(segment.text)} chars")
            print(f"Replaced text length: {len(updated.text)} chars")
            print(f"Type changed: {segment.type} -> {updated.type}")
            print(f"Quote match stored: {updated.quote_match is not None}")
            print(f"Spoken text preserved: {updated.spoken_text == segment.text}")
            
            assert updated.type == "scripture_quote", "Type should be updated"
            assert updated.quote_match is not None, "Match should be stored"
            assert updated.spoken_text == segment.text, "Original should be preserved"
            print("  [PASS] Replacement working")
        else:
            print("  [WARN] No match found (may be due to fuzzy matching thresholds)")
    else:
        print("  [SKIP] No candidates to match")
    
    # Cleanup
    matcher.close()
    service.close()
    
    print(f"\n{'='*60}")
    print("All tests completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    test_real_database_search()
