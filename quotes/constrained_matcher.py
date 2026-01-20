"""
Constrained Quote Matcher with Alignment.

Matches transcription to SGGS candidates using alignment algorithms
to find the best canonical match for quote segments.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.models import ScriptureLine, ScriptureSource
from scripture.scripture_service import ScriptureService
import config

logger = logging.getLogger(__name__)


@dataclass
class AlignmentResult:
    """Result of aligning transcription to canonical text."""
    canonical_text: str              # Canonical SGGS text
    canonical_roman: Optional[str]   # Roman transliteration
    alignment_score: float           # Alignment score (0-1)
    confidence: float                # Overall confidence
    matched_line: Optional[ScriptureLine]  # Matched scripture line
    edit_distance: int               # Edit distance from original
    edit_ratio: float                # Edit distance / max length
    is_confident_match: bool         # Whether to auto-replace


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalized_edit_distance(s1: str, s2: str) -> float:
    """Calculate normalized edit distance (0-1)."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0.0
    return levenshtein_distance(s1, s2) / max_len


def word_overlap_score(text1: str, text2: str) -> float:
    """Calculate word overlap score between two texts."""
    words1 = set(re.findall(r'[\u0A00-\u0A7F]+', text1.lower()))
    words2 = set(re.findall(r'[\u0A00-\u0A7F]+', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


class ConstrainedQuoteMatcher:
    """
    Matches transcription to SGGS candidates with alignment.
    
    Uses multiple matching strategies:
    1. Exact matching (fast)
    2. Fuzzy matching (edit distance)
    3. Word overlap (semantic)
    4. Combined scoring
    """
    
    # Gurmukhi text normalization patterns
    NORMALIZATION_RULES = [
        # Common variant spellings
        (r'ੁ', 'ੁ'),   # Aunkar normalization
        (r'ਿ', 'ਿ'),   # Sihari normalization
        (r'॥', '॥'),  # Danda normalization
    ]
    
    def __init__(
        self,
        scripture_service: Optional[ScriptureService] = None,
        alignment_threshold: Optional[float] = None
    ):
        """
        Initialize constrained matcher.
        
        Args:
            scripture_service: ScriptureService for SGGS access
            alignment_threshold: Minimum alignment score for confident match
        """
        self.scripture_service = scripture_service
        self.alignment_threshold = (
            alignment_threshold or 
            getattr(config, 'QUOTE_ALIGNMENT_THRESHOLD', 0.85)
        )
        self._service_initialized = False
    
    def _ensure_service(self) -> Optional[ScriptureService]:
        """Ensure scripture service is initialized."""
        if self.scripture_service is None and not self._service_initialized:
            try:
                self.scripture_service = ScriptureService()
                self._service_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize ScriptureService: {e}")
                self._service_initialized = True  # Don't retry
        return self.scripture_service
    
    def _normalize_text(self, text: str) -> str:
        """Normalize Gurmukhi text for comparison."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Apply normalization rules
        for pattern, replacement in self.NORMALIZATION_RULES:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def find_candidates(
        self,
        transcription: str,
        source: Optional[ScriptureSource] = None,
        top_k: int = 10,
        ang_hint: Optional[int] = None
    ) -> List[ScriptureLine]:
        """
        Find SGGS candidate lines for a transcription.
        
        Args:
            transcription: Transcribed text
            source: Limit search to specific source
            top_k: Maximum candidates to return
            ang_hint: Optional Ang number hint
        
        Returns:
            List of candidate ScriptureLines
        """
        service = self._ensure_service()
        if not service:
            return []
        
        # Normalize transcription
        normalized = self._normalize_text(transcription)
        
        # Search for candidates
        candidates = service.search_candidates(
            normalized,
            source=source,
            top_k=top_k,
            fuzzy=True
        )
        
        # If we have an Ang hint, boost candidates from that Ang
        if ang_hint and candidates:
            candidates.sort(
                key=lambda c: (0 if c.ang == ang_hint else 1, -len(c.gurmukhi))
            )
        
        return candidates
    
    def align_to_candidate(
        self,
        transcription: str,
        candidate: ScriptureLine
    ) -> AlignmentResult:
        """
        Align transcription to a single candidate.
        
        Args:
            transcription: Transcribed text
            candidate: Candidate scripture line
        
        Returns:
            AlignmentResult with alignment details
        """
        # Normalize both texts
        norm_trans = self._normalize_text(transcription)
        norm_canon = self._normalize_text(candidate.gurmukhi)
        
        # Calculate edit distance
        edit_dist = levenshtein_distance(norm_trans, norm_canon)
        max_len = max(len(norm_trans), len(norm_canon))
        edit_ratio = edit_dist / max_len if max_len > 0 else 0.0
        
        # Calculate word overlap
        word_score = word_overlap_score(norm_trans, norm_canon)
        
        # Combined alignment score
        # Lower edit ratio = better, higher word overlap = better
        alignment_score = (1 - edit_ratio) * 0.6 + word_score * 0.4
        
        # Determine confidence
        confidence = alignment_score
        is_confident = alignment_score >= self.alignment_threshold
        
        return AlignmentResult(
            canonical_text=candidate.gurmukhi,
            canonical_roman=candidate.roman,
            alignment_score=alignment_score,
            confidence=confidence,
            matched_line=candidate,
            edit_distance=edit_dist,
            edit_ratio=edit_ratio,
            is_confident_match=is_confident
        )
    
    def find_best_alignment(
        self,
        transcription: str,
        candidates: Optional[List[ScriptureLine]] = None,
        source: Optional[ScriptureSource] = None,
        ang_hint: Optional[int] = None
    ) -> Optional[AlignmentResult]:
        """
        Find the best alignment for a transcription.
        
        Args:
            transcription: Transcribed text
            candidates: Pre-fetched candidates (fetched if None)
            source: Source to search
            ang_hint: Ang number hint
        
        Returns:
            Best AlignmentResult, or None if no good match
        """
        # Get candidates if not provided
        if candidates is None:
            candidates = self.find_candidates(
                transcription,
                source=source,
                ang_hint=ang_hint
            )
        
        if not candidates:
            return None
        
        # Align to each candidate
        alignments = []
        for candidate in candidates:
            result = self.align_to_candidate(transcription, candidate)
            alignments.append(result)
        
        # Sort by alignment score
        alignments.sort(key=lambda a: a.alignment_score, reverse=True)
        
        # Return best if it meets threshold
        best = alignments[0]
        if best.alignment_score >= 0.5:  # Minimum threshold to return anything
            return best
        
        return None
    
    def match_and_align(
        self,
        transcription: str,
        source: Optional[ScriptureSource] = None,
        ang_hint: Optional[int] = None,
        auto_replace_threshold: Optional[float] = None
    ) -> Tuple[str, float, Optional[AlignmentResult]]:
        """
        Match transcription to SGGS and optionally replace.
        
        Args:
            transcription: Transcribed text
            source: Source to search
            ang_hint: Ang number hint
            auto_replace_threshold: Override threshold for auto-replace
        
        Returns:
            Tuple of (output_text, confidence, alignment_result)
        """
        threshold = auto_replace_threshold or self.alignment_threshold
        
        # Find best alignment
        result = self.find_best_alignment(
            transcription,
            source=source,
            ang_hint=ang_hint
        )
        
        if result is None:
            # No match found
            return transcription, 0.5, None
        
        if result.alignment_score >= threshold:
            # High confidence - return canonical
            return result.canonical_text, result.confidence, result
        
        # Lower confidence - return original but include result
        return transcription, result.confidence, result


# Singleton instance
_matcher: Optional[ConstrainedQuoteMatcher] = None


def get_constrained_matcher() -> ConstrainedQuoteMatcher:
    """Get singleton matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = ConstrainedQuoteMatcher()
    return _matcher


def align_to_sggs(
    transcription: str,
    ang_hint: Optional[int] = None
) -> Optional[AlignmentResult]:
    """
    Convenience function to align transcription to SGGS.
    
    Args:
        transcription: Transcribed text
        ang_hint: Optional Ang number hint
    
    Returns:
        AlignmentResult if match found
    """
    matcher = get_constrained_matcher()
    return matcher.find_best_alignment(
        transcription,
        source=ScriptureSource.SGGS,
        ang_hint=ang_hint
    )

