"""
Alignment Services Module.

Combines N-gram rescoring and SGGS alignment services for improving
ASR output accuracy through language model and canonical text alignment.

Consolidated from:
- ngram_rescorer.py
- sggs_aligner.py
"""
# Re-export from original modules for backward compatibility
from services.ngram_rescorer import (
    NGramRescorer,
    RescoredHypothesis,
    get_ngram_rescorer,
)
from services.sggs_aligner import (
    SGGSAligner,
    SGGSAlignmentResult,
    get_sggs_aligner,
)

__all__ = [
    # N-gram Rescorer
    'NGramRescorer',
    'RescoredHypothesis',
    'get_ngram_rescorer',
    
    # SGGS Aligner
    'SGGSAligner',
    'SGGSAlignmentResult',
    'get_sggs_aligner',
]

