"""
Post-processing modules for transcript merging and annotation.

This module provides:
- Transcript merging with SRT/VTT export
- Metadata annotation and review queue management
"""

from post.transcript_merger import TranscriptMerger
from post.annotator import Annotator

__all__ = [
    'TranscriptMerger',
    'Annotator'
]
