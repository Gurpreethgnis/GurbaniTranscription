"""
Quote detection and matching module.

Provides high-recall quote candidate detection and assisted matching
for canonical scripture text replacement.
"""
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer

__all__ = [
    'QuoteCandidateDetector',
    'AssistedMatcher',
    'CanonicalReplacer'
]
