"""
Test suite for Phase 4 Milestone 1: Data Models + Configuration

Tests the new data models and configuration parameters for scripture services
and quote detection.
"""
import pytest
from core.models import (
    ScriptureSource, ScriptureLine, QuoteMatch, QuoteCandidate, ProcessedSegment
)
import config


class TestScriptureSource:
    """Tests for ScriptureSource enum."""
    
    def test_scripture_source_enum_values(self):
        """Test that all expected scripture sources exist."""
        assert ScriptureSource.SGGS == "Sri Guru Granth Sahib Ji"
        assert ScriptureSource.DasamGranth == "Dasam Granth"
        assert ScriptureSource.BhaiGurdas == "Bhai Gurdas Vaaran"
        assert ScriptureSource.BhaiNandLal == "Bhai Nand Lal Bani"
        assert ScriptureSource.Other == "Other Literature"
    
    def test_scripture_source_enum_membership(self):
        """Test enum membership."""
        assert isinstance(ScriptureSource.SGGS, ScriptureSource)
        assert isinstance(ScriptureSource.DasamGranth, ScriptureSource)


class TestScriptureLine:
    """Tests for ScriptureLine dataclass."""
    
    def test_scripture_line_creation(self):
        """Test creating a ScriptureLine with required fields."""
        line = ScriptureLine(
            line_id="sggs_123",
            gurmukhi="ਵਾਹਿਗੁਰੂ"
        )
        assert line.line_id == "sggs_123"
        assert line.gurmukhi == "ਵਾਹਿਗੁਰੂ"
        assert line.roman is None
        assert line.source == ScriptureSource.SGGS
    
    def test_scripture_line_with_all_fields(self):
        """Test creating a ScriptureLine with all fields."""
        line = ScriptureLine(
            line_id="sggs_456",
            gurmukhi="ਸਤਿਗੁਰੂ",
            roman="Satiguru",
            source=ScriptureSource.SGGS,
            ang=1,
            raag="Siri",
            author="Guru Nanak Dev Ji",
            shabad_id="shabad_001"
        )
        assert line.line_id == "sggs_456"
        assert line.gurmukhi == "ਸਤਿਗੁਰੂ"
        assert line.roman == "Satiguru"
        assert line.ang == 1
        assert line.raag == "Siri"
        assert line.author == "Guru Nanak Dev Ji"
        assert line.shabad_id == "shabad_001"
    
    def test_scripture_line_to_dict(self):
        """Test ScriptureLine serialization to dictionary."""
        line = ScriptureLine(
            line_id="sggs_789",
            gurmukhi="ਗੁਰੂ",
            roman="Guru",
            ang=2,
            raag="Majh",
            author="Guru Angad Dev Ji"
        )
        result = line.to_dict()
        assert result["line_id"] == "sggs_789"
        assert result["gurmukhi"] == "ਗੁਰੂ"
        assert result["roman"] == "Guru"
        assert result["ang"] == 2
        assert result["raag"] == "Majh"
        assert result["author"] == "Guru Angad Dev Ji"
        assert result["source"] == "Sri Guru Granth Sahib Ji"
    
    def test_scripture_line_to_dict_optional_fields(self):
        """Test that optional fields are omitted when None."""
        line = ScriptureLine(
            line_id="sggs_999",
            gurmukhi="ਬਾਣੀ"
        )
        result = line.to_dict()
        assert "roman" not in result
        assert "ang" not in result
        assert "raag" not in result
        assert "author" not in result
        assert "shabad_id" not in result


class TestQuoteMatch:
    """Tests for QuoteMatch dataclass."""
    
    def test_quote_match_creation(self):
        """Test creating a QuoteMatch with required fields."""
        match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_123",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            spoken_text="wahiguru",
            confidence=0.95
        )
        assert match.source == ScriptureSource.SGGS
        assert match.line_id == "sggs_123"
        assert match.canonical_text == "ਵਾਹਿਗੁਰੂ"
        assert match.spoken_text == "wahiguru"
        assert match.confidence == 0.95
        assert match.match_method == "fuzzy"
    
    def test_quote_match_with_all_fields(self):
        """Test creating a QuoteMatch with all fields."""
        match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_456",
            canonical_text="ਸਤਿਗੁਰੂ",
            canonical_roman="Satiguru",
            spoken_text="satiguru",
            confidence=0.92,
            ang=1,
            raag="Siri",
            author="Guru Nanak Dev Ji",
            match_method="semantic"
        )
        assert match.ang == 1
        assert match.raag == "Siri"
        assert match.author == "Guru Nanak Dev Ji"
        assert match.match_method == "semantic"
    
    def test_quote_match_to_dict(self):
        """Test QuoteMatch serialization to dictionary."""
        match = QuoteMatch(
            source=ScriptureSource.DasamGranth,
            line_id="dasam_001",
            canonical_text="ਚੰਡੀ",
            spoken_text="chandi",
            confidence=0.88,
            ang=5,
            match_method="fuzzy"
        )
        result = match.to_dict()
        assert result["source"] == "Dasam Granth"
        assert result["line_id"] == "dasam_001"
        assert result["canonical_text"] == "ਚੰਡੀ"
        assert result["spoken_text"] == "chandi"
        assert result["confidence"] == 0.88
        assert result["match_method"] == "fuzzy"
        assert result["ang"] == 5


class TestQuoteCandidate:
    """Tests for QuoteCandidate dataclass."""
    
    def test_quote_candidate_creation(self):
        """Test creating a QuoteCandidate."""
        candidate = QuoteCandidate(
            start=10.5,
            end=15.2,
            text="ਵਾਹਿਗੁਰੂ",
            confidence=0.75,
            detection_reason="phrase_pattern"
        )
        assert candidate.start == 10.5
        assert candidate.end == 15.2
        assert candidate.text == "ਵਾਹਿਗੁਰੂ"
        assert candidate.confidence == 0.75
        assert candidate.detection_reason == "phrase_pattern"
    
    def test_quote_candidate_to_dict(self):
        """Test QuoteCandidate serialization to dictionary."""
        candidate = QuoteCandidate(
            start=20.0,
            end=25.5,
            text="ਸਤਿਗੁਰੂ",
            confidence=0.80,
            detection_reason="gurmukhi_vocabulary"
        )
        result = candidate.to_dict()
        assert result["start"] == 20.0
        assert result["end"] == 25.5
        assert result["text"] == "ਸਤਿਗੁਰੂ"
        assert result["confidence"] == 0.80
        assert result["detection_reason"] == "gurmukhi_vocabulary"


class TestProcessedSegmentPhase4:
    """Tests for ProcessedSegment Phase 4 fields."""
    
    def test_processed_segment_with_quote_match(self):
        """Test ProcessedSegment with quote match."""
        quote_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_123",
            canonical_text="ਵਾਹਿਗੁਰੂ",
            spoken_text="wahiguru",
            confidence=0.95
        )
        segment = ProcessedSegment(
            start=10.0,
            end=15.0,
            route="scripture_quote_likely",
            type="scripture_quote",
            text="ਵਾਹਿਗੁਰੂ",  # Canonical text
            confidence=0.95,
            language="pa",
            spoken_text="wahiguru",  # Original ASR text
            quote_match=quote_match
        )
        assert segment.quote_match is not None
        assert segment.spoken_text == "wahiguru"
        assert segment.text == "ਵਾਹਿਗੁਰੂ"  # Should be canonical
    
    def test_processed_segment_to_dict_with_quote(self):
        """Test ProcessedSegment serialization with quote match."""
        quote_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_456",
            canonical_text="ਸਤਿਗੁਰੂ",
            spoken_text="satiguru",
            confidence=0.92,
            ang=1
        )
        segment = ProcessedSegment(
            start=20.0,
            end=25.0,
            route="scripture_quote_likely",
            type="scripture_quote",
            text="ਸਤਿਗੁਰੂ",
            confidence=0.92,
            language="pa",
            spoken_text="satiguru",
            quote_match=quote_match
        )
        result = segment.to_dict()
        assert "quote_match" in result
        assert result["quote_match"]["line_id"] == "sggs_456"
        assert result["quote_match"]["ang"] == 1
        assert "spoken_text" in result
        assert result["spoken_text"] == "satiguru"
    
    def test_processed_segment_without_quote(self):
        """Test ProcessedSegment without quote (normal speech)."""
        segment = ProcessedSegment(
            start=30.0,
            end=35.0,
            route="punjabi_speech",
            type="speech",
            text="ਕੀ ਹਾਲ ਹੈ",
            confidence=0.85,
            language="pa"
        )
        assert segment.quote_match is None
        assert segment.spoken_text is None
        result = segment.to_dict()
        assert "quote_match" not in result
        assert "spoken_text" not in result


class TestConfiguration:
    """Tests for Phase 4 configuration parameters."""
    
    def test_scripture_db_path_config(self):
        """Test that SCRIPTURE_DB_PATH is configured."""
        assert hasattr(config, 'SCRIPTURE_DB_PATH')
        assert config.SCRIPTURE_DB_PATH is not None
    
    def test_dasam_db_path_config(self):
        """Test that DASAM_DB_PATH is configured."""
        assert hasattr(config, 'DASAM_DB_PATH')
        assert config.DASAM_DB_PATH is not None
    
    def test_quote_match_confidence_threshold(self):
        """Test that QUOTE_MATCH_CONFIDENCE_THRESHOLD is configured."""
        assert hasattr(config, 'QUOTE_MATCH_CONFIDENCE_THRESHOLD')
        assert 0.0 <= config.QUOTE_MATCH_CONFIDENCE_THRESHOLD <= 1.0
        assert config.QUOTE_MATCH_CONFIDENCE_THRESHOLD == 0.90  # Default value
    
    def test_quote_candidate_min_words(self):
        """Test that QUOTE_CANDIDATE_MIN_WORDS is configured."""
        assert hasattr(config, 'QUOTE_CANDIDATE_MIN_WORDS')
        assert isinstance(config.QUOTE_CANDIDATE_MIN_WORDS, int)
        assert config.QUOTE_CANDIDATE_MIN_WORDS >= 1
    
    def test_ngram_size_config(self):
        """Test that NGRAM_SIZE is configured."""
        assert hasattr(config, 'NGRAM_SIZE')
        assert isinstance(config.NGRAM_SIZE, int)
        assert config.NGRAM_SIZE >= 2  # N-grams should be at least 2
    
    def test_data_dir_created(self):
        """Test that DATA_DIR exists."""
        assert hasattr(config, 'DATA_DIR')
        assert config.DATA_DIR.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
