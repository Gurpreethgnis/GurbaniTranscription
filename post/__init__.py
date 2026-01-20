"""
Post-processing modules for transcript merging and annotation.

Consolidated Structure:
- processing: Transcript merging, annotation, section classification
- formatter: Document formatting

Legacy modules (kept for backward compatibility):
- transcript_merger: Transcript merging with SRT/VTT export
- annotator: Metadata annotation and review queue management
- section_classifier: Section type classification
- document_formatter: Structured document generation
"""
from post.transcript_merger import TranscriptMerger
from post.annotator import Annotator
from post.section_classifier import SectionClassifier
from post.document_formatter import DocumentFormatter

# Also import from consolidated modules
from post.processing import *
from post.formatter import *

__all__ = [
    'TranscriptMerger',
    'Annotator',
    'SectionClassifier',
    'DocumentFormatter',
]
