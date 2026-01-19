"""
Data models for the transcription pipeline.

This module defines the core data structures used throughout the system.
"""
from dataclasses import dataclass, field
from enum import Enum
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
class FusionResult:
    """Result from ASR fusion layer."""
    fused_text: str
    fused_confidence: float
    agreement_score: float  # How much engines agreed (0-1)
    hypotheses: List[Dict[str, Any]]
    redecode_attempts: int
    selected_engine: str  # Which engine's text was primarily used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fused_text": self.fused_text,
            "fused_confidence": self.fused_confidence,
            "agreement_score": self.agreement_score,
            "hypotheses": self.hypotheses,
            "redecode_attempts": self.redecode_attempts,
            "selected_engine": self.selected_engine
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
    # Phase 3: Script conversion fields
    roman: Optional[str] = None  # Roman transliteration
    original_script: Optional[str] = None  # Detected original script
    script_confidence: Optional[float] = None  # Script conversion confidence
    # Phase 4: Quote matching fields
    quote_match: Optional['QuoteMatch'] = None  # Matched quote (if this is a scripture quote)
    spoken_text: Optional[str] = None  # Original ASR text (preserved for quotes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
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
        # Add Phase 3 fields if present
        if self.roman is not None:
            result["roman"] = self.roman
        if self.original_script is not None:
            result["original_script"] = self.original_script
        if self.script_confidence is not None:
            result["script_confidence"] = self.script_confidence
        # Add Phase 4 fields if present
        if self.quote_match is not None:
            result["quote_match"] = self.quote_match.to_dict()
        if self.spoken_text is not None:
            result["spoken_text"] = self.spoken_text
        return result


@dataclass
class ConvertedText:
    """Represents text with dual-script output (Gurmukhi + Roman)."""
    original: str                    # Original ASR output
    original_script: str             # Detected script ("shahmukhi", "gurmukhi", "devanagari", "english", "mixed")
    gurmukhi: str                    # Gurmukhi representation
    roman: str                       # Roman transliteration
    confidence: float                # Conversion confidence (0.0-1.0)
    needs_review: bool               # Flag for uncertain conversions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "original": self.original,
            "original_script": self.original_script,
            "gurmukhi": self.gurmukhi,
            "roman": self.roman,
            "confidence": self.confidence,
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


# Phase 4: Scripture and Quote Models

class ScriptureSource(str, Enum):
    """Enumeration of scripture sources."""
    SGGS = "Sri Guru Granth Sahib Ji"
    DasamGranth = "Dasam Granth"
    BhaiGurdas = "Bhai Gurdas Vaaran"
    BhaiNandLal = "Bhai Nand Lal Bani"
    Other = "Other Literature"


@dataclass
class ScriptureLine:
    """Represents a line from scripture with metadata."""
    line_id: str  # Unique identifier for the line
    gurmukhi: str  # Gurmukhi text
    roman: Optional[str] = None  # Roman transliteration (if available)
    source: ScriptureSource = ScriptureSource.SGGS
    ang: Optional[int] = None  # Page number (for SGGS)
    raag: Optional[str] = None  # Musical mode
    author: Optional[str] = None  # Writer/author
    shabad_id: Optional[str] = None  # Shabad identifier (if part of a shabad)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "line_id": self.line_id,
            "gurmukhi": self.gurmukhi,
            "source": self.source.value
        }
        if self.roman is not None:
            result["roman"] = self.roman
        if self.ang is not None:
            result["ang"] = self.ang
        if self.raag is not None:
            result["raag"] = self.raag
        if self.author is not None:
            result["author"] = self.author
        if self.shabad_id is not None:
            result["shabad_id"] = self.shabad_id
        return result


@dataclass
class QuoteMatch:
    """Represents a match between transcribed text and canonical scripture."""
    source: ScriptureSource
    line_id: str  # ID of the matched line
    canonical_text: str  # Canonical Gurmukhi text from database
    spoken_text: str  # Original ASR output that was matched
    confidence: float  # Match confidence (0.0-1.0)
    canonical_roman: Optional[str] = None  # Canonical Roman transliteration
    ang: Optional[int] = None  # Page number
    raag: Optional[str] = None  # Musical mode
    author: Optional[str] = None  # Writer/author
    match_method: str = "fuzzy"  # How the match was found: "fuzzy", "semantic", "exact"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "source": self.source.value,
            "line_id": self.line_id,
            "canonical_text": self.canonical_text,
            "spoken_text": self.spoken_text,
            "confidence": self.confidence,
            "match_method": self.match_method
        }
        if self.canonical_roman is not None:
            result["canonical_roman"] = self.canonical_roman
        if self.ang is not None:
            result["ang"] = self.ang
        if self.raag is not None:
            result["raag"] = self.raag
        if self.author is not None:
            result["author"] = self.author
        return result


@dataclass
class QuoteCandidate:
    """Represents a candidate span that might be a scripture quote."""
    start: float  # Start timestamp
    end: float  # End timestamp
    text: str  # Candidate text
    confidence: float  # Detection confidence (0.0-1.0)
    detection_reason: str  # Why this was detected as a candidate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "confidence": self.confidence,
            "detection_reason": self.detection_reason
        }


# Phase 11: Document Formatting Models

@dataclass
class QuoteContent:
    """Represents formatted Gurbani quote content with full metadata."""
    gurmukhi: str  # Primary Gurmukhi text
    roman: str  # Roman transliteration
    source: str  # Scripture source name (e.g., "Sri Guru Granth Sahib Ji")
    english_translation: Optional[str] = None  # English translation (if available)
    ang: Optional[int] = None  # Page number (Ang)
    raag: Optional[str] = None  # Musical mode (Raag)
    author: Optional[str] = None  # Writer/author (Guru name)
    context_lines: List[str] = field(default_factory=list)  # Surrounding lines from shabad
    line_id: Optional[str] = None  # Line identifier from database
    shabad_id: Optional[str] = None  # Shabad identifier
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "gurmukhi": self.gurmukhi,
            "roman": self.roman,
            "source": self.source
        }
        if self.english_translation is not None:
            result["english_translation"] = self.english_translation
        if self.ang is not None:
            result["ang"] = self.ang
        if self.raag is not None:
            result["raag"] = self.raag
        if self.author is not None:
            result["author"] = self.author
        if self.context_lines:
            result["context_lines"] = self.context_lines
        if self.line_id is not None:
            result["line_id"] = self.line_id
        if self.shabad_id is not None:
            result["shabad_id"] = self.shabad_id
        return result


@dataclass
class DocumentSection:
    """Represents a section in a formatted document."""
    section_type: str  # "opening_gurbani", "fateh", "topic", "quote", "katha"
    content: Any  # QuoteContent for quotes, str for text sections
    start_time: float  # Start timestamp in seconds
    end_time: float  # End timestamp in seconds
    confidence: Optional[float] = None  # Confidence score if applicable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "section_type": self.section_type,
            "start_time": self.start_time,
            "end_time": self.end_time
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        
        # Serialize content based on type
        if isinstance(self.content, QuoteContent):
            result["content"] = self.content.to_dict()
        elif isinstance(self.content, str):
            result["content"] = self.content
        else:
            result["content"] = str(self.content)
        
        return result


@dataclass
class FormattedDocument:
    """Represents a formatted document with structured sections."""
    title: str  # Document title (typically filename without extension)
    source_file: str  # Original audio filename
    created_at: str  # ISO format timestamp
    sections: List[DocumentSection]  # Ordered list of document sections
    metadata: Dict[str, Any]  # Additional metadata (transcription metrics, etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "source_file": self.source_file,
            "created_at": self.created_at,
            "sections": [section.to_dict() for section in self.sections],
            "metadata": self.metadata
        }