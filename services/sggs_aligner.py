"""
SGGS Aligner - Post-ASR Alignment to Canonical Text.

Aligns transcription output to exact SGGS canonical text when a
high-confidence match is found. Handles common ASR errors specific
to Gurmukhi script.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

from core.models import ScriptureLine, ScriptureSource
from quotes.constrained_matcher import (
    ConstrainedQuoteMatcher,
    AlignmentResult,
    get_constrained_matcher,
    levenshtein_distance,
    word_overlap_score
)
import config

logger = logging.getLogger(__name__)


@dataclass  
class SGGSAlignmentResult:
    """Result of SGGS alignment with metadata."""
    original_text: str               # Original transcription
    aligned_text: str                # Aligned/canonical text (same as original if no match)
    was_aligned: bool                # Whether alignment was applied
    confidence: float                # Alignment confidence
    
    # Match details
    matched_line: Optional[ScriptureLine] = None
    alignment_score: float = 0.0
    edit_distance: int = 0
    
    # Metadata from SGGS
    ang: Optional[int] = None
    raag: Optional[str] = None
    author: Optional[str] = None
    source: Optional[ScriptureSource] = None


class SGGSAligner:
    """
    Aligns transcription to canonical SGGS text.
    
    Uses alignment algorithms to "snap" near-correct transcriptions
    to their exact canonical form in SGGS.
    """
    
    # Common ASR error patterns in Gurmukhi
    # Maps common mistranscriptions to likely corrections
    ASR_ERROR_PATTERNS = [
        # Sihari/Bihari confusion
        (r'ਿੀ', 'ੀ'),
        (r'ੀਿ', 'ੀ'),
        
        # Aunkar/Dulaunkar confusion
        (r'ੁੂ', 'ੂ'),
        (r'ੂੁ', 'ੂ'),
        
        # Tippi/Bindi confusion
        (r'ੰੰ', 'ੰ'),
        (r'ੱੱ', 'ੱ'),
        
        # Common word-level errors
        (r'ਹ਼ੈ', 'ਹੈ'),
        (r'ਜ਼ੀ', 'ਜੀ'),
    ]
    
    def __init__(
        self,
        matcher: Optional[ConstrainedQuoteMatcher] = None,
        alignment_threshold: Optional[float] = None,
        auto_align: bool = True
    ):
        """
        Initialize SGGS aligner.
        
        Args:
            matcher: ConstrainedQuoteMatcher instance
            alignment_threshold: Minimum score for auto-alignment
            auto_align: Whether to auto-align above threshold
        """
        self.matcher = matcher
        self.alignment_threshold = (
            alignment_threshold or
            getattr(config, 'QUOTE_ALIGNMENT_THRESHOLD', 0.85)
        )
        self.auto_align = auto_align
        self._matcher_initialized = False
    
    def _ensure_matcher(self) -> Optional[ConstrainedQuoteMatcher]:
        """Ensure matcher is initialized."""
        if self.matcher is None and not self._matcher_initialized:
            try:
                self.matcher = get_constrained_matcher()
                self._matcher_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize matcher: {e}")
                self._matcher_initialized = True
        return self.matcher
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to correct common ASR errors.
        
        Args:
            text: Raw transcription text
        
        Returns:
            Preprocessed text
        """
        result = text
        
        # Apply error correction patterns
        for pattern, replacement in self.ASR_ERROR_PATTERNS:
            result = re.sub(pattern, replacement, result)
        
        # Normalize whitespace
        result = ' '.join(result.split())
        
        return result
    
    def align_to_canonical(
        self,
        transcription: str,
        ang_hint: Optional[int] = None,
        source: Optional[ScriptureSource] = None,
        force_align: bool = False
    ) -> SGGSAlignmentResult:
        """
        Align transcription to canonical SGGS text.
        
        Args:
            transcription: Transcription to align
            ang_hint: Optional Ang number hint
            source: Limit search to specific source
            force_align: Force alignment even below threshold
        
        Returns:
            SGGSAlignmentResult with alignment details
        """
        # Preprocess
        preprocessed = self._preprocess_text(transcription)
        
        # Get matcher
        matcher = self._ensure_matcher()
        if not matcher:
            return SGGSAlignmentResult(
                original_text=transcription,
                aligned_text=transcription,
                was_aligned=False,
                confidence=0.5
            )
        
        # Find best alignment
        alignment = matcher.find_best_alignment(
            preprocessed,
            source=source,
            ang_hint=ang_hint
        )
        
        if alignment is None:
            return SGGSAlignmentResult(
                original_text=transcription,
                aligned_text=transcription,
                was_aligned=False,
                confidence=0.5
            )
        
        # Determine if we should align
        should_align = (
            force_align or
            (self.auto_align and alignment.alignment_score >= self.alignment_threshold)
        )
        
        # Build result
        matched_line = alignment.matched_line
        
        return SGGSAlignmentResult(
            original_text=transcription,
            aligned_text=alignment.canonical_text if should_align else transcription,
            was_aligned=should_align,
            confidence=alignment.confidence,
            matched_line=matched_line,
            alignment_score=alignment.alignment_score,
            edit_distance=alignment.edit_distance,
            ang=matched_line.ang if matched_line else None,
            raag=matched_line.raag if matched_line else None,
            author=matched_line.author if matched_line else None,
            source=matched_line.source if matched_line else None
        )
    
    def align_multiple(
        self,
        segments: List[str],
        ang_hints: Optional[List[Optional[int]]] = None,
        source: Optional[ScriptureSource] = None
    ) -> List[SGGSAlignmentResult]:
        """
        Align multiple segments.
        
        Args:
            segments: List of transcription segments
            ang_hints: Optional list of Ang hints per segment
            source: Source to search
        
        Returns:
            List of SGGSAlignmentResults
        """
        if ang_hints is None:
            ang_hints = [None] * len(segments)
        
        results = []
        for text, ang_hint in zip(segments, ang_hints):
            result = self.align_to_canonical(text, ang_hint, source)
            results.append(result)
        
        return results
    
    def get_alignment_confidence(
        self,
        transcription: str,
        ang_hint: Optional[int] = None
    ) -> float:
        """
        Get alignment confidence without performing alignment.
        
        Args:
            transcription: Transcription to check
            ang_hint: Optional Ang hint
        
        Returns:
            Confidence score (0-1)
        """
        matcher = self._ensure_matcher()
        if not matcher:
            return 0.5
        
        preprocessed = self._preprocess_text(transcription)
        alignment = matcher.find_best_alignment(preprocessed, ang_hint=ang_hint)
        
        return alignment.alignment_score if alignment else 0.0
    
    def should_auto_align(
        self,
        transcription: str,
        ang_hint: Optional[int] = None
    ) -> bool:
        """
        Check if transcription should be auto-aligned.
        
        Args:
            transcription: Transcription to check
            ang_hint: Optional Ang hint
        
        Returns:
            True if confidence is above threshold
        """
        confidence = self.get_alignment_confidence(transcription, ang_hint)
        return confidence >= self.alignment_threshold


# Singleton instance
_aligner: Optional[SGGSAligner] = None


def get_sggs_aligner() -> SGGSAligner:
    """Get singleton aligner instance."""
    global _aligner
    if _aligner is None:
        _aligner = SGGSAligner()
    return _aligner


def align_to_sggs(
    transcription: str,
    ang_hint: Optional[int] = None
) -> SGGSAlignmentResult:
    """
    Convenience function to align to SGGS.
    
    Args:
        transcription: Transcription text
        ang_hint: Optional Ang number hint
    
    Returns:
        SGGSAlignmentResult
    """
    aligner = get_sggs_aligner()
    return aligner.align_to_canonical(transcription, ang_hint)


def snap_to_canonical(
    transcription: str,
    threshold: float = 0.85
) -> Tuple[str, float]:
    """
    Snap transcription to canonical if confidence is high.
    
    Args:
        transcription: Transcription text
        threshold: Minimum confidence to snap
    
    Returns:
        Tuple of (output_text, confidence)
    """
    aligner = SGGSAligner(alignment_threshold=threshold, auto_align=True)
    result = aligner.align_to_canonical(transcription)
    return result.aligned_text, result.confidence

