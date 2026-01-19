"""
Annotator for metadata annotation and review queue management.

Adds structured metadata to segments and generates review queues.
"""
import logging
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from models import ProcessedSegment, QuoteMatch

logger = logging.getLogger(__name__)


@dataclass
class AnnotatedSegment:
    """An annotated segment with full metadata."""
    start: float
    end: float
    route: str
    type: str
    text: str
    confidence: float
    language: str
    needs_review: bool
    
    # Metadata
    source: Optional[str] = None  # SGGS, Dasam, etc.
    ang: Optional[int] = None
    raag: Optional[str] = None
    author: Optional[str] = None
    quote_match_confidence: Optional[float] = None
    
    # Processing metadata
    processing_timestamp: Optional[str] = None
    review_priority: Optional[float] = None
    
    # Original fields
    roman: Optional[str] = None
    original_script: Optional[str] = None
    script_confidence: Optional[float] = None
    spoken_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class Annotator:
    """
    Annotates segments with metadata and manages review queues.
    
    Features:
    - Metadata annotation (source, Ang, Raag, Author)
    - Review queue generation
    - Priority scoring
    - Export in multiple formats
    """
    
    def __init__(
        self,
        confidence_threshold: Optional[float] = None,
        quote_confidence_threshold: Optional[float] = None
    ):
        """
        Initialize annotator.
        
        Args:
            confidence_threshold: Confidence threshold for review flagging (default: 0.7)
            quote_confidence_threshold: Quote match confidence threshold (default: 0.9)
        """
        from config import (
            SEGMENT_CONFIDENCE_THRESHOLD,
            QUOTE_MATCH_CONFIDENCE_THRESHOLD
        )
        
        self.confidence_threshold = (
            confidence_threshold or SEGMENT_CONFIDENCE_THRESHOLD
        )
        self.quote_confidence_threshold = (
            quote_confidence_threshold or QUOTE_MATCH_CONFIDENCE_THRESHOLD
        )
    
    def annotate_segments(
        self,
        segments: List[ProcessedSegment]
    ) -> List[AnnotatedSegment]:
        """
        Annotate segments with full metadata.
        
        Args:
            segments: List of ProcessedSegment objects
        
        Returns:
            List of AnnotatedSegment objects
        """
        annotated = []
        processing_time = datetime.now().isoformat()
        
        for seg in segments:
            # Extract metadata from quote match if present
            source = None
            ang = None
            raag = None
            author = None
            quote_match_confidence = None
            
            if seg.quote_match:
                quote_match: QuoteMatch = seg.quote_match
                source = quote_match.source.value
                ang = quote_match.ang
                raag = quote_match.raag
                author = quote_match.author
                quote_match_confidence = quote_match.confidence
            
            # Calculate review priority
            review_priority = self._calculate_priority(seg)
            
            annotated_seg = AnnotatedSegment(
                start=seg.start,
                end=seg.end,
                route=seg.route,
                type=seg.type,
                text=seg.text,
                confidence=seg.confidence,
                language=seg.language,
                needs_review=seg.needs_review,
                source=source,
                ang=ang,
                raag=raag,
                author=author,
                quote_match_confidence=quote_match_confidence,
                processing_timestamp=processing_time,
                review_priority=review_priority,
                roman=seg.roman,
                original_script=seg.original_script,
                script_confidence=seg.script_confidence,
                spoken_text=seg.spoken_text
            )
            
            annotated.append(annotated_seg)
        
        return annotated
    
    def _calculate_priority(self, segment: ProcessedSegment) -> float:
        """
        Calculate review priority score (0.0-1.0, higher = more urgent).
        
        Args:
            segment: ProcessedSegment to score
        
        Returns:
            Priority score
        """
        priority = 0.0
        
        # Low confidence increases priority
        if segment.confidence < self.confidence_threshold:
            priority += 0.4
        
        # Quote match with low confidence increases priority
        if segment.quote_match:
            if segment.quote_match.confidence < self.quote_confidence_threshold:
                priority += 0.3
            else:
                # High confidence quote match - lower priority
                priority -= 0.1
        
        # Script conversion uncertainty increases priority
        if segment.script_confidence is not None:
            if segment.script_confidence < 0.7:
                priority += 0.2
        
        # Needs review flag increases priority
        if segment.needs_review:
            priority += 0.1
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, priority))
    
    def generate_review_queue(
        self,
        segments: List[ProcessedSegment]
    ) -> List[Dict[str, Any]]:
        """
        Generate review queue from segments.
        
        Args:
            segments: List of ProcessedSegment objects
        
        Returns:
            List of review queue entries (dictionaries)
        """
        annotated = self.annotate_segments(segments)
        
        # Filter segments that need review
        review_segments = [
            seg for seg in annotated
            if seg.needs_review or seg.review_priority > 0.3
        ]
        
        # Sort by priority (highest first)
        review_segments.sort(key=lambda s: s.review_priority or 0.0, reverse=True)
        
        # Convert to dictionaries
        queue = []
        for seg in review_segments:
            entry = {
                'start': seg.start,
                'end': seg.end,
                'text': seg.text,
                'confidence': seg.confidence,
                'review_priority': seg.review_priority,
                'reason': self._get_review_reason(seg),
                'source': seg.source,
                'ang': seg.ang,
                'raag': seg.raag,
                'author': seg.author,
                'language': seg.language,
                'route': seg.route,
                'type': seg.type
            }
            queue.append(entry)
        
        return queue
    
    def _get_review_reason(self, segment: AnnotatedSegment) -> str:
        """
        Get human-readable reason for review.
        
        Args:
            segment: AnnotatedSegment
        
        Returns:
            Review reason string
        """
        reasons = []
        
        if segment.confidence < self.confidence_threshold:
            reasons.append(f"Low confidence ({segment.confidence:.2f})")
        
        if segment.quote_match_confidence is not None:
            if segment.quote_match_confidence < self.quote_confidence_threshold:
                reasons.append(f"Low quote match confidence ({segment.quote_match_confidence:.2f})")
        
        if segment.script_confidence is not None:
            if segment.script_confidence < 0.7:
                reasons.append(f"Uncertain script conversion ({segment.script_confidence:.2f})")
        
        if segment.needs_review:
            reasons.append("Flagged for review")
        
        return "; ".join(reasons) if reasons else "High priority"
    
    def export_review_summary(
        self,
        segments: List[ProcessedSegment],
        output_path: Path
    ) -> Path:
        """
        Export review summary to file.
        
        Args:
            segments: List of ProcessedSegment objects
            output_path: Path to save summary
        
        Returns:
            Path to saved file
        """
        annotated = self.annotate_segments(segments)
        review_queue = self.generate_review_queue(segments)
        
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_segments': len(segments),
            'segments_needing_review': len(review_queue),
            'review_queue': review_queue,
            'statistics': {
                'avg_confidence': sum(s.confidence for s in annotated) / len(annotated) if annotated else 0.0,
                'quotes_detected': sum(1 for s in annotated if s.source is not None),
                'low_confidence_count': sum(1 for s in annotated if s.confidence < self.confidence_threshold),
                'high_priority_count': sum(1 for s in annotated if (s.review_priority or 0.0) > 0.5)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported review summary: {output_path}")
        return output_path
    
    def export_review_queue_csv(
        self,
        segments: List[ProcessedSegment],
        output_path: Path
    ) -> Path:
        """
        Export review queue to CSV file.
        
        Args:
            segments: List of ProcessedSegment objects
            output_path: Path to save CSV file
        
        Returns:
            Path to saved file
        """
        review_queue = self.generate_review_queue(segments)
        
        if not review_queue:
            # Create empty CSV with headers
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'start', 'end', 'text', 'confidence', 'review_priority',
                    'reason', 'source', 'ang', 'raag', 'author', 'language', 'route', 'type'
                ])
        else:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=review_queue[0].keys())
                writer.writeheader()
                writer.writerows(review_queue)
        
        logger.info(f"Exported review queue CSV: {output_path}")
        return output_path
    
    def generate_annotation_summary(
        self,
        segments: List[ProcessedSegment]
    ) -> Dict[str, Any]:
        """
        Generate annotation summary statistics.
        
        Args:
            segments: List of ProcessedSegment objects
        
        Returns:
            Summary dictionary
        """
        annotated = self.annotate_segments(segments)
        
        # Count by source
        source_counts = {}
        for seg in annotated:
            source = seg.source or "None"
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Count by route
        route_counts = {}
        for seg in annotated:
            route = seg.route
            route_counts[route] = route_counts.get(route, 0) + 1
        
        # Confidence distribution
        confidences = [seg.confidence for seg in annotated]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        min_confidence = min(confidences) if confidences else 0.0
        max_confidence = max(confidences) if confidences else 0.0
        
        return {
            'total_segments': len(annotated),
            'segments_needing_review': sum(1 for s in annotated if s.needs_review),
            'quotes_detected': sum(1 for s in annotated if s.source is not None),
            'source_breakdown': source_counts,
            'route_breakdown': route_counts,
            'confidence_stats': {
                'average': avg_confidence,
                'min': min_confidence,
                'max': max_confidence
            },
            'review_queue_size': len(self.generate_review_queue(segments))
        }
