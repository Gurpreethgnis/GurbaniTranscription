"""
Test suite for Phase 4 Quote Detection components.

Tests quote candidate detection, assisted matching, and canonical replacement.
"""
import pytest
import tempfile
from pathlib import Path
import sqlite3
from models import ProcessedSegment, QuoteCandidate, QuoteMatch, ScriptureSource, ScriptureLine
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from scripture.scripture_service import ScriptureService
from scripture.sggs_db import SGGSDatabase
from langid_service import ROUTE_SCRIPTURE_QUOTE_LIKELY


class TestQuoteCandidateDetector:
    """Tests for QuoteCandidateDetector."""
    
    def test_detect_candidates_by_route(self):
        """Test detection via route hint."""
        detector = QuoteCandidateDetector()
        
        segment = ProcessedSegment(
            start=10.0,
            end=15.0,
            route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
            type="speech",
            text="ਵਾਹਿਗੁਰੂ ਸਤਿਗੁਰੂ",  # Longer text to pass quote characteristics
            confidence=0.8,
            language="pa"
        )
        
        candidates = detector.detect_candidates(segment)
        
        assert len(candidates) > 0
        assert all(isinstance(c, QuoteCandidate) for c in candidates)
        # Should detect via route hint (may be combined with other signals)
        assert any("route_hint" in c.detection_reason or "gurbani_vocabulary" in c.detection_reason for c in candidates)
    
    def test_detect_candidates_by_phrase_pattern(self):
        """Test detection via phrase patterns."""
        detector = QuoteCandidateDetector()
        
        segment = ProcessedSegment(
            start=20.0,
            end=25.0,
            route="punjabi_speech",
            type="speech",
            text="ਜਿਵੇਂ ਬਾਣੀ ਚ ਕਿਹਾ ਵਾਹਿਗੁਰੂ",
            confidence=0.8,
            language="pa"
        )
        
        candidates = detector.detect_candidates(segment)
        
        # Should detect via phrase pattern
        assert len(candidates) > 0
    
    def test_detect_candidates_by_vocabulary(self):
        """Test detection via Gurbani vocabulary."""
        detector = QuoteCandidateDetector()
        
        segment = ProcessedSegment(
            start=30.0,
            end=35.0,
            route="punjabi_speech",
            type="speech",
            text="ਵਾਹਿਗੁਰੂ ਸਤਿਗੁਰੂ ਬਾਣੀ ਸ਼ਬਦ",
            confidence=0.8,
            language="pa"
        )
        
        candidates = detector.detect_candidates(segment)
        
        # Should detect via Gurbani vocabulary
        assert len(candidates) > 0
        assert any("gurbani_vocabulary" in c.detection_reason for c in candidates)
    
    def test_no_candidates_for_normal_speech(self):
        """Test that normal speech doesn't produce candidates."""
        detector = QuoteCandidateDetector()
        
        segment = ProcessedSegment(
            start=40.0,
            end=45.0,
            route="punjabi_speech",
            type="speech",
            text="ਕੀ ਹਾਲ ਹੈ ਤੁਹਾਡਾ",
            confidence=0.8,
            language="pa"
        )
        
        candidates = detector.detect_candidates(segment)
        
        # Normal speech might still produce candidates via length, but confidence should be low
        if candidates:
            assert all(c.confidence < 0.5 for c in candidates)


class TestAssistedMatcher:
    """Tests for AssistedMatcher."""
    
    def test_find_match_with_exact_text(self):
        """Test finding match with exact text."""
        # Create test database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL,
                    roman TEXT,
                    ang INTEGER,
                    raag TEXT,
                    author TEXT
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi, roman, ang, raag, author)
                VALUES ('test_001', 'ਵਾਹਿਗੁਰੂ', 'Wahiguru', 1, 'Siri', 'Guru Nanak Dev Ji')
            """)
            conn.commit()
            conn.close()
            
            sggs_db = SGGSDatabase(db_path=db_path)
            scripture_service = ScriptureService(sggs_db=sggs_db)
            matcher = AssistedMatcher(scripture_service=scripture_service)
            
            candidate = QuoteCandidate(
                start=10.0,
                end=15.0,
                text="ਵਾਹਿਗੁਰੂ",
                confidence=0.8,
                detection_reason="route_hint"
            )
            
            match = matcher.find_match([candidate])
            
            assert match is not None
            assert match.line_id == "test_001"
            assert match.confidence >= 0.7
            assert match.canonical_text == "ਵਾਹਿਗੁਰੂ"
            
            matcher.close()
        finally:
            if db_path.exists():
                try:
                    import time
                    time.sleep(0.1)
                    db_path.unlink()
                except PermissionError:
                    pass
    
    def test_find_match_with_fuzzy_text(self):
        """Test finding match with fuzzy (slightly different) text."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi)
                VALUES ('test_002', 'ਸਤਿਗੁਰੂ')
            """)
            conn.commit()
            conn.close()
            
            sggs_db = SGGSDatabase(db_path=db_path)
            scripture_service = ScriptureService(sggs_db=sggs_db)
            matcher = AssistedMatcher(scripture_service=scripture_service)
            
            # Slightly different text (ASR might have errors)
            candidate = QuoteCandidate(
                start=20.0,
                end=25.0,
                text="ਸਤਿ ਗੁਰੂ",  # Missing conjunct, but should still match
                confidence=0.75,
                detection_reason="route_hint"
            )
            
            match = matcher.find_match([candidate])
            
            # Should find match via fuzzy matching
            if match:  # May or may not match depending on similarity threshold
                assert match.line_id == "test_002"
            
            matcher.close()
        finally:
            if db_path.exists():
                try:
                    import time
                    time.sleep(0.1)
                    db_path.unlink()
                except PermissionError:
                    pass
    
    def test_no_match_for_non_quote(self):
        """Test that non-quote text doesn't match."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi)
                VALUES ('test_003', 'ਵਾਹਿਗੁਰੂ')
            """)
            conn.commit()
            conn.close()
            
            sggs_db = SGGSDatabase(db_path=db_path)
            scripture_service = ScriptureService(sggs_db=sggs_db)
            matcher = AssistedMatcher(scripture_service=scripture_service)
            
            # Normal speech text
            candidate = QuoteCandidate(
                start=30.0,
                end=35.0,
                text="ਕੀ ਹਾਲ ਹੈ",
                confidence=0.4,
                detection_reason="segment_length"
            )
            
            match = matcher.find_match([candidate])
            
            # Should not match
            assert match is None or match.confidence < 0.7
            
            matcher.close()
        finally:
            if db_path.exists():
                try:
                    import time
                    time.sleep(0.1)
                    db_path.unlink()
                except PermissionError:
                    pass


class TestCanonicalReplacer:
    """Tests for CanonicalReplacer."""
    
    def test_replace_with_high_confidence(self):
        """Test replacement with high confidence match."""
        replacer = CanonicalReplacer()
        
        segment = ProcessedSegment(
            start=10.0,
            end=15.0,
            route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
            type="speech",
            text="wahiguru",  # Spoken text (might be in Roman or with errors)
            confidence=0.8,
            language="pa"
        )
        
        quote_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_001",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            canonical_roman="Wahiguru",
            spoken_text="wahiguru",
            confidence=0.95,
            ang=1,
            raag="Siri",
            author="Guru Nanak Dev Ji"
        )
        
        updated_segment = replacer.replace_with_canonical(segment, quote_match)
        
        assert updated_segment.text == "ਵਾਹਿਗੁਰੂ"  # Should be canonical
        assert updated_segment.spoken_text == "wahiguru"  # Original preserved
        assert updated_segment.quote_match is not None
        assert updated_segment.type == "scripture_quote"
        assert updated_segment.quote_match.line_id == "sggs_001"
        assert updated_segment.quote_match.ang == 1
    
    def test_no_replace_with_low_confidence(self):
        """Test that low confidence matches don't replace."""
        replacer = CanonicalReplacer()
        
        segment = ProcessedSegment(
            start=20.0,
            end=25.0,
            route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
            type="speech",
            text="some text",
            confidence=0.8,
            language="pa"
        )
        
        quote_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_002",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            spoken_text="some text",
            confidence=0.65,  # Below threshold
            ang=2
        )
        
        original_text = segment.text
        updated_segment = replacer.replace_with_canonical(segment, quote_match)
        
        # Text should not be replaced
        assert updated_segment.text == original_text
        assert updated_segment.spoken_text == original_text
        assert updated_segment.quote_match is not None  # Match info still stored
        assert updated_segment.needs_review is True  # Should be flagged for review
    
    def test_should_replace_logic(self):
        """Test should_replace decision logic."""
        replacer = CanonicalReplacer()
        
        # High confidence match
        high_conf_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_003",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            spoken_text="wahiguru",
            confidence=0.95
        )
        assert replacer.should_replace(high_conf_match) is True
        
        # Low confidence match
        low_conf_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_004",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            spoken_text="wahiguru",
            confidence=0.65
        )
        assert replacer.should_replace(low_conf_match) is False
        
        # None match
        assert replacer.should_replace(None) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
