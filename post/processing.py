"""
Post-Processing Module.

Combines transcript merging, annotation, and section classification services
for post-ASR text processing.

Consolidated from:
- transcript_merger.py
- annotator.py
- section_classifier.py
"""
# Re-export from original modules for backward compatibility
from post.transcript_merger import TranscriptMerger
from post.annotator import Annotator
from post.section_classifier import SectionClassifier

__all__ = [
    'TranscriptMerger',
    'Annotator',
    'SectionClassifier',
]

