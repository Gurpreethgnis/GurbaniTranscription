"""
Document Formatting Module.

Re-exports the document formatter for structured output generation.

From:
- document_formatter.py
"""
# Re-export from original module for backward compatibility
from post.document_formatter import DocumentFormatter

__all__ = [
    'DocumentFormatter',
]

