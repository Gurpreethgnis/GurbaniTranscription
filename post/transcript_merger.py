"""
Transcript Merger.

Combines segments into coherent transcript with proper formatting.
Supports plain text, JSON, SRT, and VTT formats.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import timedelta

from core.models import ProcessedSegment

logger = logging.getLogger(__name__)


class TranscriptMerger:
    """
    Merges transcription segments into final output formats.
    
    Supports:
    - Plain text (Gurmukhi + Roman)
    - JSON (structured with metadata)
    - SRT subtitles
    - VTT subtitles
    """
    
    def __init__(self):
        """Initialize transcript merger."""
        pass
    
    def merge_segments(
        self,
        segments: List[ProcessedSegment],
        format: str = "text"
    ) -> str:
        """
        Merge segments into a single transcript string.
        
        Args:
            segments: List of ProcessedSegment objects
            format: Output format ("text", "gurmukhi", "roman", "json")
        
        Returns:
            Merged transcript string
        """
        if not segments:
            return ""
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start)
        
        if format == "text" or format == "gurmukhi":
            # Plain text - Gurmukhi only
            return " ".join(seg.text for seg in sorted_segments)
        
        elif format == "roman":
            # Plain text - Roman only
            return " ".join(
                seg.roman if seg.roman else seg.text
                for seg in sorted_segments
            )
        
        elif format == "json":
            # JSON format
            import json
            return json.dumps(
                {
                    "segments": [seg.to_dict() for seg in sorted_segments],
                    "full_text_gurmukhi": " ".join(seg.text for seg in sorted_segments),
                    "full_text_roman": " ".join(
                        seg.roman if seg.roman else ""
                        for seg in sorted_segments
                        if seg.roman
                    )
                },
                indent=2,
                ensure_ascii=False
            )
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def generate_srt(
        self,
        segments: List[ProcessedSegment],
        output_path: Path
    ) -> Path:
        """
        Generate SRT subtitle file from segments.
        
        Args:
            segments: List of ProcessedSegment objects
            output_path: Path to save SRT file
        
        Returns:
            Path to generated SRT file
        """
        sorted_segments = sorted(segments, key=lambda s: s.start)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(sorted_segments, 1):
                # SRT format: index, timestamps, text
                start_time = self._format_srt_timestamp(seg.start)
                end_time = self._format_srt_timestamp(seg.end)
                
                # Use Gurmukhi text, fallback to Roman if available
                text = seg.text
                if not text and seg.roman:
                    text = seg.roman
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        
        logger.info(f"Generated SRT file: {output_path}")
        return output_path
    
    def generate_vtt(
        self,
        segments: List[ProcessedSegment],
        output_path: Path
    ) -> Path:
        """
        Generate WebVTT subtitle file from segments.
        
        Args:
            segments: List of ProcessedSegment objects
            output_path: Path to save VTT file
        
        Returns:
            Path to generated VTT file
        """
        sorted_segments = sorted(segments, key=lambda s: s.start)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # VTT header
            f.write("WEBVTT\n\n")
            
            for seg in sorted_segments:
                # VTT format: timestamps, text
                start_time = self._format_vtt_timestamp(seg.start)
                end_time = self._format_vtt_timestamp(seg.end)
                
                # Use Gurmukhi text, fallback to Roman if available
                text = seg.text
                if not text and seg.roman:
                    text = seg.roman
                
                # Add metadata as cue settings (optional)
                cue_settings = ""
                if seg.quote_match:
                    cue_settings = f" class=\"quote\""
                
                f.write(f"{start_time} --> {end_time}{cue_settings}\n")
                f.write(f"{text}\n\n")
        
        logger.info(f"Generated VTT file: {output_path}")
        return output_path
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format timestamp for SRT format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_vtt_timestamp(self, seconds: float) -> str:
        """
        Format timestamp for WebVTT format (HH:MM:SS.mmm).
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def handle_overlaps(
        self,
        segments: List[ProcessedSegment]
    ) -> List[ProcessedSegment]:
        """
        Handle overlapping segments by merging or splitting.
        
        Args:
            segments: List of ProcessedSegment objects (may have overlaps)
        
        Returns:
            List of ProcessedSegment objects with overlaps resolved
        """
        sorted_segments = sorted(segments, key=lambda s: s.start)
        merged = []
        
        for seg in sorted_segments:
            if not merged:
                merged.append(seg)
                continue
            
            prev_seg = merged[-1]
            
            # Check for overlap
            if seg.start < prev_seg.end:
                # Overlap detected - merge based on confidence
                if seg.confidence > prev_seg.confidence:
                    # Current segment has higher confidence - extend previous end
                    prev_seg.end = seg.start
                    merged.append(seg)
                else:
                    # Previous segment has higher confidence - skip current start
                    seg.start = prev_seg.end
                    if seg.start < seg.end:
                        merged.append(seg)
            else:
                merged.append(seg)
        
        return merged
    
    def fill_gaps(
        self,
        segments: List[ProcessedSegment],
        gap_marker: str = "[...]"
    ) -> List[ProcessedSegment]:
        """
        Fill gaps between segments with silence markers.
        
        Args:
            segments: List of ProcessedSegment objects
            gap_marker: Text to insert in gaps
        
        Returns:
            List of ProcessedSegment objects with gaps filled
        """
        sorted_segments = sorted(segments, key=lambda s: s.start)
        filled = []
        
        for i, seg in enumerate(sorted_segments):
            filled.append(seg)
            
            # Check for gap before next segment
            if i < len(sorted_segments) - 1:
                next_seg = sorted_segments[i + 1]
                gap_duration = next_seg.start - seg.end
                
                # If gap is significant (> 1 second), add marker
                if gap_duration > 1.0:
                    gap_seg = ProcessedSegment(
                        start=seg.end,
                        end=next_seg.start,
                        route="silence",
                        type="gap",
                        text=gap_marker,
                        confidence=1.0,
                        language="unknown"
                    )
                    filled.append(gap_seg)
        
        return filled
