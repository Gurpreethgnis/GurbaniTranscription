"""
Quote Detection Module.

Combines quote candidate detection and quote context detection services
for identifying potential scripture quotes in transcription output.

Consolidated from:
- quote_candidates.py
- quote_context_detector.py
"""
# Re-export from original modules for backward compatibility
from quotes.quote_candidates import (
    QuoteCandidateDetector,
)
from quotes.quote_context_detector import (
    QuoteContextDetector,
    QuoteContextResult,
)

__all__ = [
    # Quote Candidates
    'QuoteCandidateDetector',
    
    # Quote Context
    'QuoteContextDetector',
    'QuoteContextResult',
]

