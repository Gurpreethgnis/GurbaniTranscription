"""
Domain-Constrained Spelling Corrector for Gurbani Transcription.

Provides spelling correction constrained to the domain vocabulary,
ensuring corrections stay within authentic Gurbani linguistic patterns.

Key principles:
- Only correct within small edit distance (Levenshtein <= 2)
- Only if result exists in domain dictionary
- Never "translate" - only normalize spelling variants
- Preserve original if no confident correction
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import config
from data.language_domains import DomainMode, GurmukhiScript
from data.domain_lexicon import get_domain_lexicon, DomainLexicon
from services.script_lock import ScriptLock, enforce_gurmukhi

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein edit distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        Edit distance (minimum number of single-character edits)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost: 0 if same, 1 if different
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


@dataclass
class CorrectionCandidate:
    """A potential spelling correction candidate."""
    word: str                  # Candidate correction
    original: str              # Original word
    edit_distance: int         # Edit distance from original
    frequency: int             # Word frequency in corpus
    confidence: float          # Confidence score (0-1)
    source: str                # Source of candidate (lexicon, particle, etc.)


@dataclass
class CorrectionResult:
    """Result of correction for a single word."""
    original: str              # Original word
    corrected: str             # Corrected word (may be same as original)
    was_corrected: bool        # Whether a correction was made
    candidate: Optional[CorrectionCandidate] = None  # Winning candidate
    all_candidates: List[CorrectionCandidate] = None  # All candidates considered
    
    def __post_init__(self):
        if self.all_candidates is None:
            self.all_candidates = []


class DomainCorrector:
    """
    Domain-constrained spelling corrector.
    
    Corrects spelling errors while staying within the domain vocabulary.
    Does NOT modernize, translate, or paraphrase.
    """
    
    # Gurmukhi word pattern
    GURMUKHI_WORD_PATTERN = re.compile(r'[\u0A00-\u0A7F]+')
    
    # Common Gurmukhi spelling variants (normalization mappings)
    # These are not errors, just alternate spellings to normalize
    SPELLING_VARIANTS = {
        # Older orthography -> Standard
        'ਗੁੜੂ': 'ਗੁਰੂ',
        'ਸੱਚ': 'ਸਚ',
        'ਨੰਾ': 'ਨਾਂ',
    }
    
    # Minimum word length for correction attempts
    MIN_CORRECTION_LENGTH = 2
    
    # Maximum candidates to consider
    MAX_CANDIDATES = 10
    
    def __init__(
        self,
        mode: DomainMode = DomainMode.SGGS,
        max_edit_distance: Optional[int] = None,
        min_confidence: float = 0.5
    ):
        """
        Initialize domain corrector.
        
        Args:
            mode: Domain mode for vocabulary selection
            max_edit_distance: Maximum edit distance for corrections (default from config)
            min_confidence: Minimum confidence to apply correction
        """
        self.mode = mode
        self.max_edit_distance = max_edit_distance or config.MAX_EDIT_DISTANCE
        self.min_confidence = min_confidence
        
        self._lexicon: Optional[DomainLexicon] = None
        self._script_lock = ScriptLock(mode)
        
        # Cache for word lookups
        self._word_cache: Dict[str, bool] = {}
    
    @property
    def lexicon(self) -> DomainLexicon:
        """Get domain lexicon (lazy load)."""
        if self._lexicon is None:
            self._lexicon = get_domain_lexicon()
        return self._lexicon
    
    def _is_in_vocab(self, word: str) -> bool:
        """Check if word is in domain vocabulary (with caching)."""
        if word in self._word_cache:
            return self._word_cache[word]
        
        result = self.lexicon.contains(word, self.mode)
        self._word_cache[word] = result
        return result
    
    def _get_frequency(self, word: str) -> int:
        """Get word frequency in corpus."""
        return self.lexicon.get_frequency(word)
    
    def _find_candidates(self, word: str) -> List[CorrectionCandidate]:
        """
        Find correction candidates for a word.
        
        Searches the domain vocabulary for words within max edit distance.
        
        Args:
            word: Word to find candidates for
        
        Returns:
            List of candidates sorted by confidence (highest first)
        """
        candidates = []
        
        # Skip very short words
        if len(word) < self.MIN_CORRECTION_LENGTH:
            return candidates
        
        # First check if it's already in vocab
        if self._is_in_vocab(word):
            # Already valid, but check for normalization variants
            if word in self.SPELLING_VARIANTS:
                normalized = self.SPELLING_VARIANTS[word]
                candidates.append(CorrectionCandidate(
                    word=normalized,
                    original=word,
                    edit_distance=0,
                    frequency=self._get_frequency(normalized),
                    confidence=0.9,
                    source='normalization',
                ))
            return candidates
        
        # Get combined vocabulary for searching
        vocab = self.lexicon.get_combined_vocab(self.mode)
        
        # Search for candidates within edit distance
        word_len = len(word)
        
        for vocab_word in vocab:
            # Quick length check to avoid unnecessary distance calculations
            len_diff = abs(len(vocab_word) - word_len)
            if len_diff > self.max_edit_distance:
                continue
            
            # Calculate edit distance
            distance = levenshtein_distance(word, vocab_word)
            
            if distance <= self.max_edit_distance and distance > 0:
                frequency = self._get_frequency(vocab_word)
                
                # Calculate confidence based on edit distance and frequency
                # Lower distance = higher confidence
                # Higher frequency = higher confidence
                distance_factor = 1.0 - (distance / (self.max_edit_distance + 1))
                frequency_factor = min(1.0, frequency / 100) if frequency > 0 else 0.1
                confidence = 0.5 * distance_factor + 0.5 * frequency_factor
                
                candidates.append(CorrectionCandidate(
                    word=vocab_word,
                    original=word,
                    edit_distance=distance,
                    frequency=frequency,
                    confidence=confidence,
                    source='lexicon',
                ))
        
        # Sort by confidence (highest first), then by edit distance
        candidates.sort(key=lambda c: (-c.confidence, c.edit_distance))
        
        return candidates[:self.MAX_CANDIDATES]
    
    def correct_word(self, word: str) -> CorrectionResult:
        """
        Correct a single word.
        
        Args:
            word: Word to correct
        
        Returns:
            CorrectionResult with correction details
        """
        # Skip empty or very short
        if not word or len(word) < self.MIN_CORRECTION_LENGTH:
            return CorrectionResult(
                original=word,
                corrected=word,
                was_corrected=False,
            )
        
        # Already in vocabulary - no correction needed
        if self._is_in_vocab(word):
            # But check for normalization
            if word in self.SPELLING_VARIANTS:
                normalized = self.SPELLING_VARIANTS[word]
                return CorrectionResult(
                    original=word,
                    corrected=normalized,
                    was_corrected=True,
                    candidate=CorrectionCandidate(
                        word=normalized,
                        original=word,
                        edit_distance=0,
                        frequency=self._get_frequency(normalized),
                        confidence=0.9,
                        source='normalization',
                    ),
                )
            return CorrectionResult(
                original=word,
                corrected=word,
                was_corrected=False,
            )
        
        # Find candidates
        candidates = self._find_candidates(word)
        
        if not candidates:
            # No candidates found - keep original
            return CorrectionResult(
                original=word,
                corrected=word,
                was_corrected=False,
                all_candidates=[],
            )
        
        # Get best candidate
        best = candidates[0]
        
        # Only correct if confidence is high enough
        if best.confidence >= self.min_confidence:
            return CorrectionResult(
                original=word,
                corrected=best.word,
                was_corrected=True,
                candidate=best,
                all_candidates=candidates,
            )
        
        # Confidence too low - keep original
        return CorrectionResult(
            original=word,
            corrected=word,
            was_corrected=False,
            all_candidates=candidates,
        )
    
    def correct_text(
        self,
        text: str,
        enforce_script: bool = True
    ) -> Tuple[str, List[CorrectionResult]]:
        """
        Correct all words in text.
        
        Args:
            text: Text to correct
            enforce_script: Apply Gurmukhi script lock first
        
        Returns:
            Tuple of (corrected_text, list of CorrectionResults)
        """
        if not text:
            return text, []
        
        # Step 1: Enforce Gurmukhi script if requested
        if enforce_script:
            text, _ = self._script_lock.repair(text)
        
        # Step 2: Find and correct words
        results = []
        corrected_parts = []
        last_end = 0
        
        for match in self.GURMUKHI_WORD_PATTERN.finditer(text):
            # Add text before this word
            corrected_parts.append(text[last_end:match.start()])
            
            word = match.group()
            result = self.correct_word(word)
            results.append(result)
            
            # Add corrected word
            corrected_parts.append(result.corrected)
            last_end = match.end()
        
        # Add remaining text
        corrected_parts.append(text[last_end:])
        
        corrected_text = ''.join(corrected_parts)
        
        # Log corrections made
        corrections_made = [r for r in results if r.was_corrected]
        if corrections_made:
            logger.debug(
                f"Made {len(corrections_made)} corrections in text "
                f"(e.g., '{corrections_made[0].original}' -> '{corrections_made[0].corrected}')"
            )
        
        return corrected_text, results
    
    def get_correction_stats(
        self,
        results: List[CorrectionResult]
    ) -> Dict[str, any]:
        """
        Get statistics about corrections made.
        
        Args:
            results: List of CorrectionResults from correct_text
        
        Returns:
            Dictionary with correction statistics
        """
        total_words = len(results)
        corrected_words = sum(1 for r in results if r.was_corrected)
        
        # Group by source
        sources = {}
        for r in results:
            if r.was_corrected and r.candidate:
                source = r.candidate.source
                sources[source] = sources.get(source, 0) + 1
        
        return {
            'total_words': total_words,
            'corrected_words': corrected_words,
            'correction_rate': corrected_words / total_words if total_words > 0 else 0,
            'corrections_by_source': sources,
        }


class ConservativeCorrector(DomainCorrector):
    """
    Conservative variant of domain corrector.
    
    Only corrects when very confident, suitable for sensitive transcriptions.
    """
    
    def __init__(
        self,
        mode: DomainMode = DomainMode.SGGS,
        max_edit_distance: int = 1,  # Only single-character edits
        min_confidence: float = 0.7   # Higher threshold
    ):
        super().__init__(
            mode=mode,
            max_edit_distance=max_edit_distance,
            min_confidence=min_confidence,
        )


def correct_transcription(
    text: str,
    mode: DomainMode = DomainMode.SGGS,
    conservative: bool = False
) -> str:
    """
    Convenience function to correct transcription text.
    
    Args:
        text: Text to correct
        mode: Domain mode
        conservative: Use conservative corrector
    
    Returns:
        Corrected text
    """
    if conservative:
        corrector = ConservativeCorrector(mode)
    else:
        corrector = DomainCorrector(mode)
    
    corrected, _ = corrector.correct_text(text)
    return corrected


def suggest_corrections(
    word: str,
    mode: DomainMode = DomainMode.SGGS,
    max_suggestions: int = 5
) -> List[Tuple[str, float]]:
    """
    Get spelling suggestions for a word.
    
    Args:
        word: Word to get suggestions for
        mode: Domain mode
        max_suggestions: Maximum number of suggestions
    
    Returns:
        List of (suggestion, confidence) tuples
    """
    corrector = DomainCorrector(mode)
    candidates = corrector._find_candidates(word)
    
    return [(c.word, c.confidence) for c in candidates[:max_suggestions]]

