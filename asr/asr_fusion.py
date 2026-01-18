"""
ASR Fusion Layer: Voting, Confidence Merge, and Re-decode Policy.

This module implements the fusion logic that merges multiple ASR engine outputs
to produce a single, high-confidence transcription result.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from models import ASRResult, FusionResult, AudioChunk
import config

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available. Install with: pip install rapidfuzz")

try:
    from Levenshtein import distance as levenshtein_distance
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    logger.warning("python-Levenshtein not available. Install with: pip install python-Levenshtein")


class ASRFusion:
    """
    ASR Fusion layer for merging multiple ASR engine outputs.
    
    Implements:
    1. Hypothesis alignment
    2. Voting and confidence merging
    3. Re-decode policy for low-confidence segments
    """
    
    def __init__(
        self,
        agreement_threshold: Optional[float] = None,
        confidence_boost: Optional[float] = None,
        redecode_threshold: Optional[float] = None,
        max_redecode_attempts: Optional[int] = None
    ):
        """
        Initialize fusion layer.
        
        Args:
            agreement_threshold: Text similarity threshold for "agreement" (0-1)
            confidence_boost: Confidence boost when engines agree (0-1)
            redecode_threshold: Trigger re-decode below this confidence (0-1)
            max_redecode_attempts: Maximum re-decode attempts per segment
        """
        self.agreement_threshold = (
            agreement_threshold or 
            getattr(config, 'FUSION_AGREEMENT_THRESHOLD', 0.85)
        )
        self.confidence_boost = (
            confidence_boost or 
            getattr(config, 'FUSION_CONFIDENCE_BOOST', 0.1)
        )
        self.redecode_threshold = (
            redecode_threshold or 
            getattr(config, 'FUSION_REDECODE_THRESHOLD', 0.6)
        )
        self.max_redecode_attempts = (
            max_redecode_attempts or 
            getattr(config, 'FUSION_MAX_REDECODE_ATTEMPTS', 2)
        )
    
    def fuse_hypotheses(
        self,
        hypotheses: List[ASRResult],
        chunk: Optional[AudioChunk] = None
    ) -> FusionResult:
        """
        Fuse multiple ASR hypotheses into a single result.
        
        Args:
            hypotheses: List of ASRResult from different engines
            chunk: Optional AudioChunk for context
        
        Returns:
            FusionResult with fused text and confidence
        """
        if not hypotheses:
            raise ValueError("Cannot fuse empty hypotheses list")
        
        if len(hypotheses) == 1:
            # Single hypothesis - no fusion needed
            result = hypotheses[0]
            return FusionResult(
                fused_text=result.text,
                fused_confidence=result.confidence,
                agreement_score=1.0,
                hypotheses=[{
                    "engine": result.engine,
                    "text": result.text,
                    "confidence": result.confidence,
                    "language": result.language
                }],
                redecode_attempts=0,
                selected_engine=result.engine
            )
        
        # Convert to hypothesis dicts
        hypothesis_dicts = []
        for result in hypotheses:
            hypothesis_dicts.append({
                "engine": result.engine,
                "text": result.text,
                "confidence": result.confidence,
                "language": result.language,
                "segments": result.segments
            })
        
        # Stage 1: Calculate agreement scores
        agreement_scores = self._calculate_agreement_scores(hypotheses)
        
        # Stage 2: Select best hypothesis based on voting and confidence
        selected_idx, agreement_score = self._select_best_hypothesis(
            hypotheses, agreement_scores
        )
        
        selected_result = hypotheses[selected_idx]
        fused_text = selected_result.text
        fused_confidence = selected_result.confidence
        
        # Stage 3: Apply confidence boost if engines agree
        if agreement_score >= self.agreement_threshold:
            fused_confidence = min(1.0, fused_confidence + self.confidence_boost)
        
        return FusionResult(
            fused_text=fused_text,
            fused_confidence=fused_confidence,
            agreement_score=agreement_score,
            hypotheses=hypothesis_dicts,
            redecode_attempts=0,
            selected_engine=selected_result.engine
        )
    
    def _calculate_agreement_scores(
        self,
        hypotheses: List[ASRResult]
    ) -> List[List[float]]:
        """
        Calculate pairwise agreement scores between hypotheses.
        
        Args:
            hypotheses: List of ASRResult
        
        Returns:
            Matrix of agreement scores (symmetric)
        """
        n = len(hypotheses)
        agreement_matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                score = self._text_similarity(
                    hypotheses[i].text,
                    hypotheses[j].text
                )
                agreement_matrix[i][j] = score
                agreement_matrix[j][i] = score
        
        # Self-agreement is always 1.0
        for i in range(n):
            agreement_matrix[i][i] = 1.0
        
        return agreement_matrix
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity score (0-1).
        
        Uses rapidfuzz if available, otherwise Levenshtein distance.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0-1, where 1.0 is identical)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # Normalize whitespace
        text1 = ' '.join(text1.split())
        text2 = ' '.join(text2.split())
        
        if RAPIDFUZZ_AVAILABLE:
            # Use rapidfuzz ratio (normalized similarity)
            ratio = fuzz.ratio(text1, text2) / 100.0
            return ratio
        elif LEVENSHTEIN_AVAILABLE:
            # Use Levenshtein distance
            max_len = max(len(text1), len(text2))
            if max_len == 0:
                return 1.0
            distance = levenshtein_distance(text1, text2)
            similarity = 1.0 - (distance / max_len)
            return similarity
        else:
            # Fallback: simple character overlap
            # This is less accurate but works without dependencies
            set1 = set(text1.lower())
            set2 = set(text2.lower())
            if not set1 and not set2:
                return 1.0
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return intersection / union if union > 0 else 0.0
    
    def _select_best_hypothesis(
        self,
        hypotheses: List[ASRResult],
        agreement_matrix: List[List[float]]
    ) -> Tuple[int, float]:
        """
        Select the best hypothesis based on voting and confidence.
        
        Strategy:
        1. If 2+ engines agree (high similarity), prefer the one with highest confidence
        2. Otherwise, prefer highest confidence
        3. Break ties by preferring ASR-A (primary engine)
        
        Args:
            hypotheses: List of ASRResult
            agreement_matrix: Pairwise agreement scores
        
        Returns:
            Tuple of (selected_index, average_agreement_score)
        """
        n = len(hypotheses)
        
        # Calculate average agreement for each hypothesis
        avg_agreements = []
        for i in range(n):
            avg_agreement = sum(agreement_matrix[i]) / n
            avg_agreements.append(avg_agreement)
        
        # Find hypotheses with high agreement (>= threshold)
        high_agreement_indices = [
            i for i in range(n) 
            if avg_agreements[i] >= self.agreement_threshold
        ]
        
        if high_agreement_indices:
            # Prefer high-agreement hypotheses, then by confidence
            best_idx = max(
                high_agreement_indices,
                key=lambda i: (hypotheses[i].confidence, i == 0)  # Prefer ASR-A on tie
            )
            return best_idx, avg_agreements[best_idx]
        else:
            # No high agreement - select by confidence
            best_idx = max(
                range(n),
                key=lambda i: (hypotheses[i].confidence, i == 0)  # Prefer ASR-A on tie
            )
            return best_idx, avg_agreements[best_idx]
    
    def should_redecode(
        self,
        fusion_result: FusionResult
    ) -> bool:
        """
        Determine if segment should be re-decoded.
        
        Args:
            fusion_result: FusionResult to evaluate
        
        Returns:
            True if re-decode should be triggered
        """
        if fusion_result.redecode_attempts >= self.max_redecode_attempts:
            return False
        
        if fusion_result.fused_confidence < self.redecode_threshold:
            return True
        
        # Also re-decode if agreement is very low (engines disagree strongly)
        if fusion_result.agreement_score < 0.5:
            return True
        
        return False
    
    def apply_redecode(
        self,
        fusion_result: FusionResult,
        redecode_result: ASRResult
    ) -> FusionResult:
        """
        Apply re-decode result to fusion result.
        
        Args:
            fusion_result: Original fusion result
            redecode_result: Result from re-decode pass
        
        Returns:
            Updated FusionResult with re-decode incorporated
        """
        # Add re-decode result to hypotheses
        new_hypotheses = fusion_result.hypotheses + [{
            "engine": redecode_result.engine,
            "text": redecode_result.text,
            "confidence": redecode_result.confidence,
            "language": redecode_result.language,
            "segments": redecode_result.segments
        }]
        
        # Re-fuse with new hypothesis
        all_results = [
            ASRResult(
                text=h["text"],
                language=h.get("language", "unknown"),
                confidence=h["confidence"],
                segments=h.get("segments", []),
                engine=h["engine"]
            )
            for h in new_hypotheses
        ]
        
        # Fuse again
        updated_result = self.fuse_hypotheses(all_results)
        
        # Update re-decode attempts
        updated_result.redecode_attempts = fusion_result.redecode_attempts + 1
        
        return updated_result
