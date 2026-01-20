"""
Root-level models re-export for backward compatibility.

All models are defined in core.models - this module provides a convenient
top-level import path.

Usage:
    from models import TranscriptionResult, ProcessedSegment
    # or
    from core.models import TranscriptionResult, ProcessedSegment
"""
from core.models import (
    # Core data structures
    AudioChunk,
    Segment,
    ASRResult,
    FusionResult,
    ProcessedSegment,
    ConvertedText,
    TranscriptionResult,
    
    # Scripture models
    ScriptureSource,
    ScriptureLine,
    QuoteMatch,
    QuoteCandidate,
    
    # Document models
    QuoteContent,
    DocumentSection,
    FormattedDocument,
)

__all__ = [
    # Core data structures
    'AudioChunk',
    'Segment',
    'ASRResult',
    'FusionResult',
    'ProcessedSegment',
    'ConvertedText',
    'TranscriptionResult',
    
    # Scripture models
    'ScriptureSource',
    'ScriptureLine',
    'QuoteMatch',
    'QuoteCandidate',
    
    # Document models
    'QuoteContent',
    'DocumentSection',
    'FormattedDocument',
]

