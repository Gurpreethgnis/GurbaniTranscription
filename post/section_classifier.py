"""
Section Classifier for Document Formatting.

Analyzes transcription segments and classifies them into semantic sections:
- Opening Gurbani (scripture quotes at the beginning)
- Fateh (traditional greetings)
- Topic (subject/theme of the katha)
- Quote (Gurbani quotes during katha)
- Katha (regular commentary/explanation)
"""
import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.models import ProcessedSegment, QuoteMatch
import config

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedSection:
    """A classified section with its type and metadata."""
    section_type: str  # "opening_gurbani", "fateh", "topic", "quote", "katha"
    segment: ProcessedSegment
    confidence: float  # Classification confidence (0.0-1.0)
    metadata: Dict[str, Any] = None  # Additional metadata
    
    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


class SectionClassifier:
    """
    Classifies transcription segments into semantic document sections.
    
    Uses pattern matching, timing analysis, and existing quote detection
    to identify different types of content in a katha transcription.
    """
    
    def __init__(
        self,
        opening_window: Optional[float] = None,
        topic_window: Optional[float] = None,
        fateh_patterns: Optional[List[str]] = None
    ):
        """
        Initialize section classifier.
        
        Args:
            opening_window: Time window (seconds) to check for opening Gurbani (default: config)
            topic_window: Time window (seconds) to extract topic (default: config)
            fateh_patterns: List of patterns to detect Fateh (default: config)
        """
        self.opening_window = (
            opening_window or config.OPENING_GURBANI_TIME_WINDOW
        )
        self.topic_window = (
            topic_window or config.TOPIC_EXTRACTION_TIME_WINDOW
        )
        self.fateh_patterns = (
            fateh_patterns or config.FATEH_PATTERNS
        )
        
        # Compile regex patterns for case-insensitive matching
        self.fateh_regexes = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
            for pattern in self.fateh_patterns
        ]
        
        logger.info(
            f"SectionClassifier initialized: "
            f"opening_window={self.opening_window}s, "
            f"topic_window={self.topic_window}s, "
            f"fateh_patterns={len(self.fateh_patterns)}"
        )
    
    def classify_segments(
        self,
        segments: List[ProcessedSegment]
    ) -> List[ClassifiedSection]:
        """
        Classify all segments into document sections.
        
        Args:
            segments: List of ProcessedSegment objects (should be sorted by start time)
        
        Returns:
            List of ClassifiedSection objects in chronological order
        """
        if not segments:
            logger.warning("Empty segments list provided")
            return []
        
        # Sort segments by start time to ensure chronological order
        sorted_segments = sorted(segments, key=lambda s: s.start)
        
        classified = []
        
        for i, segment in enumerate(sorted_segments):
            section_type, confidence, metadata = self._classify_segment(
                segment, i, sorted_segments
            )
            
            classified_section = ClassifiedSection(
                section_type=section_type,
                segment=segment,
                confidence=confidence,
                metadata=metadata
            )
            
            classified.append(classified_section)
        
        logger.info(
            f"Classified {len(segments)} segments: "
            f"{sum(1 for c in classified if c.section_type == 'opening_gurbani')} opening_gurbani, "
            f"{sum(1 for c in classified if c.section_type == 'fateh')} fateh, "
            f"{sum(1 for c in classified if c.section_type == 'topic')} topic, "
            f"{sum(1 for c in classified if c.section_type == 'quote')} quote, "
            f"{sum(1 for c in classified if c.section_type == 'katha')} katha"
        )
        
        return classified
    
    def _classify_segment(
        self,
        segment: ProcessedSegment,
        index: int,
        all_segments: List[ProcessedSegment]
    ) -> tuple[str, float, Dict[str, Any]]:
        """
        Classify a single segment.
        
        Args:
            segment: ProcessedSegment to classify
            index: Index of segment in sorted list
            all_segments: All segments for context
        
        Returns:
            Tuple of (section_type, confidence, metadata)
        """
        # First, find if there's a fateh before this segment
        fateh_found_before = False
        for prev_seg in all_segments[:index]:
            if self._detect_fateh(prev_seg):
                fateh_found_before = True
                break
        
        # Priority 1: Check if it's a quote (already detected by Phase 4)
        if segment.quote_match is not None:
            # Opening Gurbani: quotes BEFORE fateh (or if no fateh, in first window)
            is_opening = (
                not fateh_found_before and
                segment.start < self.opening_window
            )
            
            if is_opening:
                return ("opening_gurbani", 0.95, {
                    "quote_match": segment.quote_match.to_dict(),
                    "is_opening": True
                })
            else:
                return ("quote", 0.95, {
                    "quote_match": segment.quote_match.to_dict(),
                    "is_opening": False
                })
        
        # Priority 2: Check for Fateh patterns
        fateh_match = self._detect_fateh(segment)
        if fateh_match:
            return ("fateh", 0.90, {
                "matched_pattern": fateh_match,
                "text": segment.text
            })
        
        # Priority 3: Check if it's in topic window and looks like topic
        if segment.start < self.topic_window:
            topic_score = self._score_topic_likelihood(segment, index, all_segments)
            if topic_score > 0.6:
                return ("topic", topic_score, {
                    "topic_text": segment.text,
                    "position_in_window": segment.start / self.topic_window
                })
        
        # Default: Regular katha content
        return ("katha", 0.8, {
            "route": segment.route,
            "type": segment.type
        })
    
    def _detect_fateh(self, segment: ProcessedSegment) -> Optional[str]:
        """
        Detect if segment contains Fateh/greeting patterns.
        
        Args:
            segment: ProcessedSegment to check
        
        Returns:
            Matched pattern string if found, None otherwise
        """
        text = segment.text.lower().strip()
        
        for pattern, regex in zip(self.fateh_patterns, self.fateh_regexes):
            if regex.search(text):
                logger.debug(f"Fateh pattern matched: {pattern} in segment at {segment.start:.2f}s")
                return pattern
        
        return None
    
    def _score_topic_likelihood(
        self,
        segment: ProcessedSegment,
        index: int,
        all_segments: List[ProcessedSegment]
    ) -> float:
        """
        Score how likely a segment is to contain the topic/theme.
        
        Args:
            segment: ProcessedSegment to score
            index: Index in sorted segments
            all_segments: All segments for context
        
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        
        # Topic usually comes after fateh
        # Check if there's a fateh before this segment
        has_fateh_before = False
        for prev_seg in all_segments[:index]:
            if self._detect_fateh(prev_seg):
                has_fateh_before = True
                break
        
        if has_fateh_before:
            score += 0.3
        
        # Topic is usually in first few segments after fateh
        if index < 10:
            score += 0.2
        
        # Topic often contains certain keywords (in Gurmukhi/Roman)
        topic_keywords = [
            "katha", "ਕਥਾ", "about", "subject", "topic", "theme",
            "today", "ਅੱਜ", "discuss", "discussion"
        ]
        text_lower = segment.text.lower()
        for keyword in topic_keywords:
            if keyword in text_lower:
                score += 0.2
                break
        
        # Topic is usually longer than a single word
        word_count = len(segment.text.split())
        if word_count >= 5:
            score += 0.2
        elif word_count >= 3:
            score += 0.1
        
        # Clamp to [0.0, 1.0]
        return min(1.0, max(0.0, score))
    
    def get_opening_gurbani(
        self,
        classified: List[ClassifiedSection]
    ) -> List[ClassifiedSection]:
        """Get all opening Gurbani sections."""
        return [c for c in classified if c.section_type == "opening_gurbani"]
    
    def get_fateh(
        self,
        classified: List[ClassifiedSection]
    ) -> Optional[ClassifiedSection]:
        """Get the first Fateh section (if any)."""
        fateh_sections = [c for c in classified if c.section_type == "fateh"]
        return fateh_sections[0] if fateh_sections else None
    
    def get_topic(
        self,
        classified: List[ClassifiedSection]
    ) -> Optional[ClassifiedSection]:
        """Get the topic section (first high-confidence topic, if any)."""
        topic_sections = [
            c for c in classified
            if c.section_type == "topic" and c.confidence > 0.6
        ]
        return topic_sections[0] if topic_sections else None
    
