"""
Quote detection and matching module.

Consolidated Structure:
- detection: Quote candidate and context detection (quote_candidates + quote_context_detector)
- matching: Quote matching and replacement (assisted_matcher + constrained_matcher + canonical_replacer)

Legacy modules (kept for backward compatibility):
- quote_candidates: Quote candidate detection
- quote_context_detector: Real-time quote boundary detection  
- assisted_matcher: Assisted multi-stage matching
- constrained_matcher: Alignment-based quote matching
- canonical_replacer: Canonical text replacement
"""
# Keep all original imports for backward compatibility
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from quotes.quote_context_detector import QuoteContextDetector, QuoteContextResult
from quotes.constrained_matcher import ConstrainedQuoteMatcher, AlignmentResult

# Also import from consolidated modules
from quotes.detection import *
from quotes.matching import *

__all__ = [
    # Detection
    'QuoteCandidateDetector',
    'QuoteContextDetector',
    'QuoteContextResult',
    
    # Matching
    'AssistedMatcher',
    'ConstrainedQuoteMatcher',
    'AlignmentResult',
    'CanonicalReplacer',
]
