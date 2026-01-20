"""
Quote Matching Module.

Combines quote matching and canonical replacement services for finding
and replacing detected quotes with canonical scripture text.

Consolidated from:
- assisted_matcher.py
- constrained_matcher.py
- canonical_replacer.py
"""
# Re-export from original modules for backward compatibility
from quotes.assisted_matcher import (
    AssistedMatcher,
)
from quotes.constrained_matcher import (
    ConstrainedQuoteMatcher,
    AlignmentResult,
    get_constrained_matcher,
    levenshtein_distance,
    word_overlap_score,
)
from quotes.canonical_replacer import (
    CanonicalReplacer,
)

__all__ = [
    # Assisted Matcher
    'AssistedMatcher',
    
    # Constrained Matcher
    'ConstrainedQuoteMatcher',
    'AlignmentResult',
    'get_constrained_matcher',
    'levenshtein_distance',
    'word_overlap_score',
    
    # Canonical Replacer
    'CanonicalReplacer',
]

