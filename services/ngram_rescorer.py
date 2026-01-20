"""
N-gram Language Model Rescorer for ASR Hypotheses.

Rescores ASR transcription hypotheses using an N-gram language model
built from the SGGS corpus to improve accuracy for Gurbani content.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import config
from data.sggs_language_model import get_sggs_language_model, SGGSLanguageModel

logger = logging.getLogger(__name__)


@dataclass
class RescoredHypothesis:
    """A rescored ASR hypothesis."""
    text: str                    # Original hypothesis text
    asr_score: float             # Original ASR confidence
    lm_score: float              # Language model log probability
    combined_score: float        # Interpolated final score
    perplexity: float            # LM perplexity (lower = better)


class NGramRescorer:
    """
    Rescores ASR hypotheses using SGGS N-gram language model.
    
    Uses interpolation between ASR confidence and LM probability
    to select the best hypothesis or improve confidence estimates.
    """
    
    # Gurmukhi text pattern
    GURMUKHI_PATTERN = re.compile(r'[\u0A00-\u0A7F]')
    
    def __init__(
        self,
        lm_weight: Optional[float] = None,
        min_gurmukhi_ratio: float = 0.3
    ):
        """
        Initialize rescorer.
        
        Args:
            lm_weight: Weight for LM score in interpolation (0-1)
                      Higher = more influence from LM
            min_gurmukhi_ratio: Minimum Gurmukhi character ratio to apply rescoring
        """
        self.lm_weight = lm_weight or getattr(config, 'NGRAM_RESCORE_WEIGHT', 0.3)
        self.min_gurmukhi_ratio = min_gurmukhi_ratio
        
        self._language_model: Optional[SGGSLanguageModel] = None
        self._model_loaded = False
    
    @property
    def language_model(self) -> SGGSLanguageModel:
        """Get language model (lazy load)."""
        if self._language_model is None:
            try:
                self._language_model = get_sggs_language_model()
                self._model_loaded = self._language_model.is_loaded()
                if self._model_loaded:
                    logger.info("SGGS language model loaded for rescoring")
                else:
                    logger.warning("SGGS language model not available")
            except Exception as e:
                logger.error(f"Failed to load SGGS language model: {e}")
                self._language_model = SGGSLanguageModel()
                self._model_loaded = False
        
        return self._language_model
    
    def _get_gurmukhi_ratio(self, text: str) -> float:
        """Calculate ratio of Gurmukhi characters in text."""
        if not text:
            return 0.0
        
        gurmukhi_chars = len(self.GURMUKHI_PATTERN.findall(text))
        total_chars = len(text.replace(' ', ''))
        
        return gurmukhi_chars / total_chars if total_chars > 0 else 0.0
    
    def should_rescore(self, text: str) -> bool:
        """
        Check if text should be rescored.
        
        Only rescores text with sufficient Gurmukhi content.
        """
        if not self._model_loaded and self.language_model:
            # Try to load model
            self._model_loaded = self.language_model.is_loaded()
        
        if not self._model_loaded:
            return False
        
        ratio = self._get_gurmukhi_ratio(text)
        return ratio >= self.min_gurmukhi_ratio
    
    def rescore_hypothesis(
        self,
        text: str,
        asr_confidence: float = 0.8
    ) -> RescoredHypothesis:
        """
        Rescore a single hypothesis.
        
        Args:
            text: Transcription hypothesis
            asr_confidence: Original ASR confidence (0-1)
        
        Returns:
            RescoredHypothesis with combined score
        """
        # Get LM score
        lm_score = 0.0
        perplexity = float('inf')
        
        if self.should_rescore(text):
            try:
                lm_score = self.language_model.score_text(text)
                perplexity = self.language_model.get_perplexity(text)
            except Exception as e:
                logger.debug(f"LM scoring failed: {e}")
        
        # Normalize LM score to 0-1 range (sigmoid of log probability / 100)
        import math
        normalized_lm = 1.0 / (1.0 + math.exp(-lm_score / 100))
        
        # Interpolate scores
        combined = (
            (1 - self.lm_weight) * asr_confidence +
            self.lm_weight * normalized_lm
        )
        
        return RescoredHypothesis(
            text=text,
            asr_score=asr_confidence,
            lm_score=lm_score,
            combined_score=combined,
            perplexity=perplexity
        )
    
    def rescore(
        self,
        hypotheses: List[str],
        asr_confidences: Optional[List[float]] = None
    ) -> List[Tuple[str, float]]:
        """
        Rescore multiple hypotheses.
        
        Args:
            hypotheses: List of transcription hypotheses
            asr_confidences: Optional list of ASR confidences
        
        Returns:
            List of (text, combined_score) tuples sorted by score (highest first)
        """
        if not hypotheses:
            return []
        
        # Default confidences
        if asr_confidences is None:
            asr_confidences = [0.8] * len(hypotheses)
        
        # Rescore each hypothesis
        rescored = []
        for text, conf in zip(hypotheses, asr_confidences):
            result = self.rescore_hypothesis(text, conf)
            rescored.append((result.text, result.combined_score))
        
        # Sort by combined score (highest first)
        rescored.sort(key=lambda x: x[1], reverse=True)
        
        return rescored
    
    def select_best(
        self,
        hypotheses: List[str],
        asr_confidences: Optional[List[float]] = None
    ) -> Tuple[str, float]:
        """
        Select the best hypothesis after rescoring.
        
        Args:
            hypotheses: List of transcription hypotheses
            asr_confidences: Optional list of ASR confidences
        
        Returns:
            Tuple of (best_text, score)
        """
        if not hypotheses:
            return "", 0.0
        
        rescored = self.rescore(hypotheses, asr_confidences)
        return rescored[0] if rescored else (hypotheses[0], 0.5)
    
    def boost_if_gurbani(
        self,
        text: str,
        asr_confidence: float,
        boost_factor: float = 0.1
    ) -> float:
        """
        Boost confidence if text fits SGGS language model well.
        
        Args:
            text: Transcription text
            asr_confidence: Original ASR confidence
            boost_factor: Maximum boost amount (0-1)
        
        Returns:
            Adjusted confidence
        """
        if not self.should_rescore(text):
            return asr_confidence
        
        try:
            perplexity = self.language_model.get_perplexity(text)
            
            # Low perplexity (< 50) indicates good fit
            # High perplexity (> 500) indicates poor fit
            if perplexity < 50:
                boost = boost_factor
            elif perplexity < 100:
                boost = boost_factor * 0.5
            elif perplexity < 200:
                boost = boost_factor * 0.25
            else:
                boost = 0.0
            
            return min(1.0, asr_confidence + boost)
            
        except Exception as e:
            logger.debug(f"Boost calculation failed: {e}")
            return asr_confidence


# Singleton instance
_rescorer: Optional[NGramRescorer] = None


def get_ngram_rescorer() -> NGramRescorer:
    """Get singleton rescorer instance."""
    global _rescorer
    if _rescorer is None:
        _rescorer = NGramRescorer()
    return _rescorer


def rescore_transcription(
    text: str,
    confidence: float = 0.8
) -> Tuple[str, float]:
    """
    Convenience function to rescore a transcription.
    
    Args:
        text: Transcription text
        confidence: Original ASR confidence
    
    Returns:
        Tuple of (text, adjusted_confidence)
    """
    rescorer = get_ngram_rescorer()
    result = rescorer.rescore_hypothesis(text, confidence)
    return result.text, result.combined_score

