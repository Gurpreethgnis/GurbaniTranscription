"""
Quote detection and matching module.

Provides high-recall quote candidate detection and assisted matching
for canonical scripture text replacement.

SGGS Enhancement (Phase 14):
- QuoteContextDetector: Real-time quote boundary detection
- ConstrainedQuoteMatcher: Alignment-based quote matching
"""
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from quotes.quote_context_detector import QuoteContextDetector, QuoteContextResult
from quotes.constrained_matcher import ConstrainedQuoteMatcher, AlignmentResult

__all__ = [
    'QuoteCandidateDetector',
    'AssistedMatcher',
    'CanonicalReplacer',
    'QuoteContextDetector',
    'QuoteContextResult',
    'ConstrainedQuoteMatcher',
    'AlignmentResult',
]
