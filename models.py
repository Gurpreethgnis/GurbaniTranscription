"""
Data models for the transcription pipeline.

This module defines the core data structures used throughout the system.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class AudioChunk:
    """Represents a chunk of audio with timing information."""
    start_time: float
    end_time: float
    audio_path: Path  # Path to original file or extracted chunk
    duration: float
    
    def __post_init__(self):
        """Validate chunk data."""
        if self.duration <= 0:
            raise ValueError(f"Chunk duration must be positive, got {self.duration}")
        if self.start_time < 0:
            raise ValueError(f"Start time must be non-negative, got {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(f"End time must be greater than start time")


@dataclass
class Segment:
    """Represents a transcription segment with timing and text."""
    start: float
    end: float
    text: str
    confidence: float
    language: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language
        }


@dataclass
class ASRResult:
    """Result from an ASR engine."""
    text: str
    language: str
    confidence: float  # Overall confidence (0.0 to 1.0)
    segments: List[Segment]
    engine: str = "asr_a_whisper"
    language_probability: Optional[float] = None  # Language detection confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "language": self.language,
            "confidence": self.confidence,
            "segments": [seg.to_dict() for seg in self.segments],
            "engine": self.engine
        }


@dataclass
class ProcessedSegment:
    """A processed segment with routing and metadata."""
    start: float
    end: float
    route: str  # "punjabi_speech", "english_speech", "scripture_quote_likely", "mixed"
    type: str  # "speech" | "scripture_quote"
    text: str  # Gurmukhi text (or English if route is english_speech)
    confidence: float
    language: str
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)  # For future multi-ASR support
    needs_review: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "route": self.route,
            "type": self.type,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "hypotheses": self.hypotheses,
            "needs_review": self.needs_review
        }


@dataclass
class TranscriptionResult:
    """Complete transcription result with all segments."""
    filename: str
    segments: List[ProcessedSegment]
    transcription: Dict[str, str]  # {"gurmukhi": "...", "roman": "..."}
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "transcription": self.transcription,
            "segments": [seg.to_dict() for seg in self.segments],
            "metrics": self.metrics
        }
