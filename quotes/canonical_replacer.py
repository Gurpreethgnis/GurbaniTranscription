"""
Canonical Replacer.

Replaces transcribed text spans with canonical scripture text when
a high-confidence match is found, while preserving provenance.
"""
import logging
from typing import Optional
from core.models import ProcessedSegment, QuoteMatch
import config

logger = logging.getLogger(__name__)


class CanonicalReplacer:
    """
    Replaces transcribed text with canonical scripture text.
    
    Preserves provenance (original spoken text) and adds metadata
    (Ang, Raag, Author, etc.) when replacing with canonical text.
    """
    
    def __init__(self):
        """Initialize canonical replacer."""
        self.confidence_threshold = config.QUOTE_MATCH_CONFIDENCE_THRESHOLD
    
    def replace_with_canonical(
        self,
        segment: ProcessedSegment,
        quote_match: QuoteMatch
    ) -> ProcessedSegment:
        """
        Replace segment text with canonical scripture text.
        
        Args:
            segment: ProcessedSegment to update
            quote_match: QuoteMatch containing canonical text and metadata
        
        Returns:
            Updated ProcessedSegment with canonical text
        """
        if quote_match.confidence < self.confidence_threshold:
            logger.warning(
                f"Match confidence ({quote_match.confidence:.2f}) below threshold "
                f"({self.confidence_threshold}), not replacing"
            )
            # Still update segment with match info, but don't replace text
            segment.quote_match = quote_match
            segment.spoken_text = segment.text  # Preserve original
            segment.needs_review = True
            return segment
        
        # Replace text with canonical
        logger.info(
            f"Replacing text with canonical: {quote_match.line_id} "
            f"(confidence: {quote_match.confidence:.2f})"
        )
        
        # Preserve original spoken text
        original_text = segment.text
        if segment.spoken_text is None:
            segment.spoken_text = original_text
        
        # Update segment with canonical text
        segment.text = quote_match.canonical_text
        
        # Update Roman transliteration if available
        if quote_match.canonical_roman:
            segment.roman = quote_match.canonical_roman
        
        # Update segment type
        segment.type = "scripture_quote"
        
        # Add quote match metadata
        segment.quote_match = quote_match
        
        # Update confidence (use match confidence, but don't lower it)
        if quote_match.confidence > segment.confidence:
            segment.confidence = quote_match.confidence
        
        # Set needs_review based on confidence
        if quote_match.confidence < 0.95:
            # High confidence but not perfect - flag for review
            segment.needs_review = True
            logger.debug(f"Flagging for review (confidence: {quote_match.confidence:.2f})")
        else:
            # Very high confidence - auto-replace
            segment.needs_review = False
        
        logger.debug(
            f"Replaced: '{original_text[:50]}...' -> "
            f"'{quote_match.canonical_text[:50]}...' "
            f"(source: {quote_match.source.value}, ang: {quote_match.ang})"
        )
        
        return segment
    
    def should_replace(
        self,
        quote_match: Optional[QuoteMatch]
    ) -> bool:
        """
        Determine if a quote match should be used for replacement.
        
        Args:
            quote_match: QuoteMatch to evaluate
        
        Returns:
            True if match should be used for replacement
        """
        if quote_match is None:
            return False
        
        if quote_match.confidence < self.confidence_threshold:
            return False
        
        # Additional checks can be added here
        # For example, check if canonical text is significantly different
        # from spoken text (might indicate wrong match)
        
        return True
