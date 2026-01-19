"""
Full Pipeline Test for Phase 4 Quote Detection.

Tests the complete flow from ProcessedSegment through quote detection,
matching, and canonical replacement.
"""
import pytest
import tempfile
import sqlite3
from pathlib import Path
from core.models import ProcessedSegment, ASRResult, Segment, FusionResult
from core.orchestrator import Orchestrator
from services.langid_service import ROUTE_SCRIPTURE_QUOTE_LIKELY
from scripture.scripture_service import ScriptureService
from scripture.sggs_db import SGGSDatabase
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer


class TestFullPipeline:
    """Test the complete quote detection pipeline."""
    
    def test_full_quote_detection_flow(self):
        """Test complete flow: detection → matching → replacement."""
        # Create test database with known Gurbani
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            # Create database with test data
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    shabad_id TEXT,
                    source_page INTEGER,
                    source_line INTEGER,
                    gurmukhi TEXT NOT NULL,
                    pronunciation TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE shabads (
                    id TEXT PRIMARY KEY,
                    writer_id INTEGER,
                    section_id INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE writers (
                    id INTEGER PRIMARY KEY,
                    name_english TEXT
                )
            """)
            
            # Insert test data (using ASCII transliteration format)
            conn.execute("""
                INSERT INTO lines (id, shabad_id, source_page, source_line, gurmukhi)
                VALUES 
                    ('test_001', 'shabad_001', 1, 1, 'siq nwmu krqw purKu inrBau inrvYru'),
                    ('test_002', 'shabad_001', 1, 2, 'Akwl mUriq AjUnI sYBM gur pRswid ]'),
                    ('test_003', 'shabad_002', 4, 1, 'vwhgurU guru sbdu lY; iprm ipAwlw cuip cbolw [')
            """)
            conn.execute("""
                INSERT INTO shabads (id, writer_id, section_id)
                VALUES 
                    ('shabad_001', 1, 1),
                    ('shabad_002', 1, 1)
            """)
            conn.execute("""
                INSERT INTO writers (id, name_english)
                VALUES (1, 'Guru Nanak Dev Ji')
            """)
            conn.commit()
            conn.close()
            
            # Initialize services
            sggs_db = SGGSDatabase(db_path=db_path)
            scripture_service = ScriptureService(sggs_db=sggs_db)
            detector = QuoteCandidateDetector()
            matcher = AssistedMatcher(scripture_service=scripture_service)
            replacer = CanonicalReplacer()
            
            # Create a segment that should be detected as a quote
            # Using Unicode Gurmukhi (as ASR would output)
            segment = ProcessedSegment(
                start=10.0,
                end=15.0,
                route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
                type="speech",
                text="ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",  # Unicode Gurmukhi
                confidence=0.85,
                language="pa"
            )
            
            print(f"\nOriginal segment text: {segment.text}")
            print(f"Route: {segment.route}")
            
            # Step 1: Detect candidates
            candidates = detector.detect_candidates(segment)
            print(f"\nStep 1 - Quote Detection: Found {len(candidates)} candidate(s)")
            assert len(candidates) > 0, "Should detect at least one candidate"
            
            # Step 2: Find match
            match = matcher.find_match(candidates)
            print(f"\nStep 2 - Matching: {'Match found' if match else 'No match'}")
            if match:
                print(f"  Match ID: {match.line_id}")
                print(f"  Confidence: {match.confidence:.2f}")
                print(f"  Canonical text: {match.canonical_text[:50]}")
                print(f"  Ang: {match.ang}")
                print(f"  Author: {match.author}")
            
            # Step 3: Replace if match found
            if match:
                updated_segment = replacer.replace_with_canonical(segment, match)
                print(f"\nStep 3 - Replacement:")
                print(f"  Original: {segment.text}")
                print(f"  Replaced: {updated_segment.text[:50]}")
                print(f"  Spoken text preserved: {updated_segment.spoken_text}")
                print(f"  Type: {updated_segment.type}")
                print(f"  Quote match stored: {updated_segment.quote_match is not None}")
                
                assert updated_segment.type == "scripture_quote", "Type should be updated"
                assert updated_segment.quote_match is not None, "Quote match should be stored"
                assert updated_segment.spoken_text == segment.text, "Original should be preserved"
            
            matcher.close()
            scripture_service.close()
            
        finally:
            if db_path.exists():
                try:
                    import time
                    time.sleep(0.1)
                    db_path.unlink()
                except PermissionError:
                    pass
    
    def test_pipeline_with_orchestrator_integration(self):
        """Test that orchestrator can process segments with quote detection."""
        # Create minimal test database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    source_page INTEGER,
                    gurmukhi TEXT NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, source_page, gurmukhi)
                VALUES ('test_004', 1, 'siq nwmu krqw purKu')
            """)
            conn.commit()
            conn.close()
            
            # Create orchestrator with test database
            sggs_db = SGGSDatabase(db_path=db_path)
            
            # Note: We can't easily test full orchestrator without audio files,
            # but we can verify the components are integrated
            from orchestrator import Orchestrator
            
            # Create orchestrator - it should initialize quote detection services
            orch = Orchestrator()
            
            assert hasattr(orch, 'quote_detector'), "Orchestrator should have quote_detector"
            assert hasattr(orch, 'quote_matcher'), "Orchestrator should have quote_matcher"
            assert hasattr(orch, 'quote_replacer'), "Orchestrator should have quote_replacer"
            
            print("\nOrchestrator integration verified:")
            print("  - quote_detector: OK")
            print("  - quote_matcher: OK")
            print("  - quote_replacer: OK")
            
        finally:
            if db_path.exists():
                try:
                    import time
                    time.sleep(0.1)
                    db_path.unlink()
                except PermissionError:
                    pass
    
    def test_search_with_real_database(self):
        """Test search with the actual sggs.sqlite database."""
        from pathlib import Path
        import config
        
        db_path = config.SCRIPTURE_DB_PATH
        
        if not db_path.exists():
            pytest.skip(f"Database not found at {db_path}")
        
        print(f"\nTesting with real database: {db_path.name}")
        print(f"Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
        
        db = SGGSDatabase(db_path=db_path)
        service = ScriptureService(sggs_db=db)
        
        # Test search with Unicode Gurmukhi (as ASR would output)
        search_text = "ਸਤਿ ਨਾਮੁ"  # Unicode Gurmukhi
        results = service.search_candidates(search_text, top_k=5)
        
        print(f"\nSearch for Unicode Gurmukhi text: Found {len(results)} results")
        
        if results:
            print("\nFirst result:")
            r = results[0]
            print(f"  Line ID: {r.line_id}")
            print(f"  Gurmukhi (ASCII): {r.gurmukhi[:60]}")
            print(f"  Ang: {r.ang}")
            print(f"  Author: {r.author}")
            print(f"  Shabad ID: {r.shabad_id}")
            
            assert r.ang is not None, "Should have Ang (page number)"
            assert len(r.gurmukhi) > 0, "Should have Gurmukhi text"
        
        service.close()
        print("\nReal database test complete!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
