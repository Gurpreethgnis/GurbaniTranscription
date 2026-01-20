"""
Shared test fixtures for Katha Transcription tests.

This module provides reusable test data and mock objects.
"""
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.models import (
    AudioChunk,
    Segment,
    ASRResult,
    FusionResult,
    ProcessedSegment,
    TranscriptionResult,
    FormattedDocument,
    DocumentSection,
    QuoteContent,
    QuoteMatch,
    ScriptureSource
)


def create_sample_audio_chunk(
    start_time: float = 0.0,
    end_time: float = 5.0,
    audio_path: str = "test.mp3"
) -> AudioChunk:
    """Create a sample AudioChunk for testing."""
    return AudioChunk(
        start_time=start_time,
        end_time=end_time,
        audio_path=Path(audio_path),
        duration=end_time - start_time
    )


def create_sample_segment(
    start: float = 0.0,
    end: float = 5.0,
    text: str = "Test transcription",
    confidence: float = 0.85,
    language: str = "pa"
) -> Segment:
    """Create a sample Segment for testing."""
    return Segment(
        start=start,
        end=end,
        text=text,
        confidence=confidence,
        language=language
    )


def create_sample_asr_result(
    text: str = "Test transcription",
    language: str = "pa",
    confidence: float = 0.85,
    engine: str = "asr_a_whisper"
) -> ASRResult:
    """Create a sample ASRResult for testing."""
    return ASRResult(
        text=text,
        language=language,
        confidence=confidence,
        segments=[create_sample_segment(text=text)],
        engine=engine,
        language_probability=0.95
    )


def create_sample_fusion_result(
    fused_text: str = "Test transcription",
    fused_confidence: float = 0.85,
    agreement_score: float = 0.90
) -> FusionResult:
    """Create a sample FusionResult for testing."""
    return FusionResult(
        fused_text=fused_text,
        fused_confidence=fused_confidence,
        agreement_score=agreement_score,
        hypotheses=[
            {"engine": "asr_a", "text": fused_text, "confidence": 0.80},
            {"engine": "asr_b", "text": fused_text, "confidence": 0.90}
        ],
        redecode_attempts=0,
        selected_engine="asr_b"
    )


def create_sample_document() -> FormattedDocument:
    """Create a sample FormattedDocument for testing."""
    quote_content = QuoteContent(
        gurmukhi="ਵਾਹਿਗੁਰੂ",
        roman="Waheguru",
        source="Sri Guru Granth Sahib Ji"
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
            content="This is a test katha section with spoken commentary.",
            start_time=7.0,
            end_time=60.0
        )
    ]
    
    return FormattedDocument(
        title="Test Katha Document",
        source_file="test.mp3",
        created_at=datetime.now().isoformat(),
        sections=sections,
        metadata={
            "duration": 60.0,
            "language": "pa",
            "model": "large"
        }
    )


def create_sample_transcription_result(filename: str = "test.mp3") -> TranscriptionResult:
    """Create a sample TranscriptionResult for testing."""
    segments = [
        ProcessedSegment(
            start=0.0,
            end=5.0,
            route="punjabi_speech",
            type="speech",
            text="ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ",
            confidence=0.92,
            language="pa"
        ),
        ProcessedSegment(
            start=5.0,
            end=10.0,
            route="english_speech",
            type="speech",
            text="Let us begin today's katha",
            confidence=0.88,
            language="en"
        )
    ]
    
    return TranscriptionResult(
        filename=filename,
        segments=segments,
        transcription={
            "gurmukhi": "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ",
            "roman": "Waheguru Ji Ka Khalsa. Let us begin today's katha"
        },
        metrics={
            "total_segments": 2,
            "average_confidence": 0.90,
            "languages": ["pa", "en"]
        }
    )

