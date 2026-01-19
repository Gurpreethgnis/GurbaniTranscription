"""
Quote Candidate Detection (High Recall).

Detects spans of text that might be scripture quotes using multiple signals:
- Phrase patterns (e.g., "ਜਿਵੇਂ ਬਾਣੀ ਚ ਕਿਹਾ")
- Gurmukhi vocabulary markers
- Route hints from language identification
- Segment characteristics
"""
import logging
import re
from typing import List, Optional
from models import QuoteCandidate, ProcessedSegment
from langid_service import ROUTE_SCRIPTURE_QUOTE_LIKELY
import config

logger = logging.getLogger(__name__)


class QuoteCandidateDetector:
    """
    High-recall detector for scripture quote candidates.
    
    Uses multiple signals to identify spans that might be quotes.
    False positives are acceptable; they'll be verified by the matcher.
    """
    
    def __init__(self):
        """Initialize quote candidate detector."""
        # Common phrase patterns that indicate a quote is coming
        self.quote_intro_patterns = [
            r'ਜਿਵੇਂ\s+ਬਾਣੀ\s+ਚ\s+ਕਿਹਾ',
            r'ਗੁਰਬਾਣੀ\s+ਫੁਰਮਾਉਂਦੀ',
            r'ਬਾਣੀ\s+ਚ\s+ਕਿਹਾ',
            r'ਗੁਰੂ\s+ਸਾਹਿਬ\s+ਫੁਰਮਾਉਂਦੇ',
            r'ਅੰਗ\s+\d+\s+ਚ',
            r'ਰਾਗ\s+\w+\s+ਚ',
            r'ਜਿਵੇਂ\s+ਕਿਹਾ\s+ਹੈ',
            r'ਬਾਣੀ\s+ਚ\s+ਆਇਆ',
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
            for pattern in self.quote_intro_patterns
        ]
        
        # Common Gurmukhi vocabulary markers (archaic words, Sant Bhasha)
        # These are words that are more common in Gurbani than modern speech
        self.gurbani_vocabulary = {
            'ਵਾਹਿਗੁਰੂ', 'ਸਤਿਗੁਰੂ', 'ਗੁਰੂ', 'ਬਾਣੀ', 'ਸ਼ਬਦ',
            'ਅੰਗ', 'ਰਾਗ', 'ਪਾਤਸ਼ਾਹ', 'ਮਹਲਾ', 'ਚਰਨ', 'ਪਦ',
            'ਭਗਤ', 'ਸੰਤ', 'ਗੁਰਮੁਖ', 'ਮਨਮੁਖ', 'ਮਾਇਆ', 'ਮੋਹ',
            'ਅਹੰਕਾਰ', 'ਮਮਤਾ', 'ਵਿਸਾਰ', 'ਸਿਮਰਨ', 'ਨਾਮ', 'ਧਿਆਨ',
            'ਧਰਮ', 'ਕਰਮ', 'ਪ੍ਰਭੂ', 'ਰਾਮ', 'ਹਰਿ', 'ਗੋਬਿੰਦ',
            'ਕਿਰਪਾ', 'ਦਇਆ', 'ਮਿਹਰ', 'ਭਾਣਾ', 'ਹੁਕਮ', 'ਚਿਤ'
        }
        
        self.min_words = config.QUOTE_CANDIDATE_MIN_WORDS
    
    def detect_candidates(
        self,
        segment: ProcessedSegment,
        hypotheses: Optional[List[dict]] = None
    ) -> List[QuoteCandidate]:
        """
        Detect quote candidates in a processed segment.
        
        Args:
            segment: ProcessedSegment to analyze
            hypotheses: Optional list of ASR hypotheses (for multi-hypothesis analysis)
        
        Returns:
            List of QuoteCandidate objects
        """
        candidates: List[QuoteCandidate] = []
        
        # Signal 1: Route hint (already identified as scripture_quote_likely)
        if segment.route == ROUTE_SCRIPTURE_QUOTE_LIKELY:
            confidence = 0.7  # Base confidence from route
            reason = "route_hint"
            
            # Check if text matches quote characteristics
            if self._has_quote_characteristics(segment.text):
                confidence = 0.85
                reason = "route_hint + quote_characteristics"
            
            candidate = QuoteCandidate(
                start=segment.start,
                end=segment.end,
                text=segment.text,
                confidence=confidence,
                detection_reason=reason
            )
            candidates.append(candidate)
            logger.debug(f"Detected candidate via route hint: {segment.text[:50]}")
        
        # Signal 2: Phrase patterns (introductory phrases)
        pattern_matches = self._check_phrase_patterns(segment.text)
        if pattern_matches:
            for match_text, pattern_name in pattern_matches:
                # The quote might be after the pattern
                # For now, mark the whole segment as candidate
                candidate = QuoteCandidate(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    confidence=0.75,
                    detection_reason=f"phrase_pattern: {pattern_name}"
                )
                candidates.append(candidate)
                logger.debug(f"Detected candidate via phrase pattern: {pattern_name}")
        
        # Signal 3: Gurmukhi vocabulary markers
        gurbani_word_count = self._count_gurbani_vocabulary(segment.text)
        total_words = len(segment.text.split())
        
        if total_words > 0:
            gurbani_ratio = gurbani_word_count / total_words
            if gurbani_ratio >= 0.3:  # At least 30% Gurbani vocabulary
                confidence = min(0.6 + (gurbani_ratio * 0.3), 0.9)
                candidate = QuoteCandidate(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    confidence=confidence,
                    detection_reason=f"gurbani_vocabulary (ratio: {gurbani_ratio:.2f})"
                )
                candidates.append(candidate)
                logger.debug(f"Detected candidate via Gurbani vocabulary: {gurbani_ratio:.2f}")
        
        # Signal 4: Segment length (quotes typically 5-30 words)
        word_count = len(segment.text.split())
        if self.min_words <= word_count <= 30:
            # This is a weak signal, only add if not already detected
            if not candidates:
                candidate = QuoteCandidate(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    confidence=0.4,  # Low confidence
                    detection_reason="segment_length"
                )
                candidates.append(candidate)
                logger.debug(f"Detected candidate via segment length: {word_count} words")
        
        # Remove duplicates and merge overlapping candidates
        candidates = self._deduplicate_candidates(candidates)
        
        logger.info(f"Detected {len(candidates)} quote candidate(s) in segment {segment.start:.2f}-{segment.end:.2f}s")
        return candidates
    
    def _has_quote_characteristics(self, text: str) -> bool:
        """
        Check if text has characteristics of a quote.
        
        Args:
            text: Text to check
        
        Returns:
            True if text appears quote-like
        """
        if not text or len(text.strip()) < 5:
            return False
        
        # Check for Gurmukhi script (quotes are in Gurmukhi)
        gurmukhi_chars = sum(1 for char in text if '\u0A00' <= char <= '\u0A7F')
        total_chars = len([c for c in text if c.isalnum()])
        
        if total_chars > 0:
            gurmukhi_ratio = gurmukhi_chars / total_chars
            if gurmukhi_ratio < 0.5:  # Less than 50% Gurmukhi
                return False
        
        # Check for poetic structure (repetition, meter hints)
        # Simple check: look for repeated phrases or words
        words = text.split()
        if len(words) >= 3:
            # Check for repetition (common in Gurbani)
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            max_repetition = max(word_counts.values()) if word_counts else 1
            if max_repetition >= 2 and len(words) <= 15:
                return True
        
        return False
    
    def _check_phrase_patterns(self, text: str) -> List[tuple]:
        """
        Check for introductory phrase patterns.
        
        Args:
            text: Text to check
        
        Returns:
            List of (matched_text, pattern_name) tuples
        """
        matches = []
        for i, pattern in enumerate(self.compiled_patterns):
            match = pattern.search(text)
            if match:
                matches.append((match.group(), self.quote_intro_patterns[i]))
        return matches
    
    def _count_gurbani_vocabulary(self, text: str) -> int:
        """
        Count how many Gurbani vocabulary words appear in text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Number of Gurbani vocabulary words found
        """
        words = set(text.split())
        gurbani_words = words.intersection(self.gurbani_vocabulary)
        return len(gurbani_words)
    
    def _deduplicate_candidates(self, candidates: List[QuoteCandidate]) -> List[QuoteCandidate]:
        """
        Remove duplicate candidates and merge overlapping ones.
        
        Args:
            candidates: List of candidates
        
        Returns:
            Deduplicated list
        """
        if not candidates:
            return []
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        
        # Keep only unique spans (same start/end)
        seen = set()
        unique = []
        for candidate in candidates:
            key = (candidate.start, candidate.end, candidate.text)
            if key not in seen:
                seen.add(key)
                unique.append(candidate)
        
        return unique
