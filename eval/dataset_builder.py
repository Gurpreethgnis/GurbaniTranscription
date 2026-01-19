"""
Ground Truth Dataset Builder.

Tool for creating and managing ground truth datasets for evaluation.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """
    Tool for creating and managing ground truth datasets.
    
    Supports:
    - Manual annotation (JSON format)
    - Import/export ground truth data
    - Validation of timestamps and structure
    """
    
    def __init__(self, ground_truth_dir: Optional[Path] = None):
        """
        Initialize dataset builder.
        
        Args:
            ground_truth_dir: Directory to store ground truth files (default: eval/ground_truth)
        """
        if ground_truth_dir is None:
            from config import EVAL_GROUND_TRUTH_DIR
            ground_truth_dir = EVAL_GROUND_TRUTH_DIR
        
        self.ground_truth_dir = Path(ground_truth_dir)
        self.ground_truth_dir.mkdir(parents=True, exist_ok=True)
    
    def create_template(
        self,
        audio_file: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Create a template ground truth file for an audio file.
        
        Args:
            audio_file: Path to audio file
            output_path: Optional output path (default: ground_truth_dir/{audio_file.stem}.json)
        
        Returns:
            Path to created template file
        """
        if output_path is None:
            output_path = self.ground_truth_dir / f"{audio_file.stem}.json"
        
        template = {
            "audio_file": str(audio_file),
            "created_at": datetime.now().isoformat(),
            "segments": []
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created ground truth template: {output_path}")
        return output_path
    
    def load_ground_truth(
        self,
        ground_truth_path: Path
    ) -> Dict[str, Any]:
        """
        Load ground truth data from JSON file.
        
        Args:
            ground_truth_path: Path to ground truth JSON file
        
        Returns:
            Ground truth data dictionary
        """
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        self._validate_ground_truth(data)
        
        return data
    
    def save_ground_truth(
        self,
        ground_truth: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """
        Save ground truth data to JSON file.
        
        Args:
            ground_truth: Ground truth data dictionary
            output_path: Path to save file
        
        Returns:
            Path to saved file
        """
        # Validate before saving
        self._validate_ground_truth(ground_truth)
        
        # Update timestamp
        ground_truth['updated_at'] = datetime.now().isoformat()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ground_truth, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved ground truth: {output_path}")
        return output_path
    
    def add_segment(
        self,
        ground_truth: Dict[str, Any],
        start: float,
        end: float,
        ground_truth_gurmukhi: str,
        ground_truth_roman: Optional[str] = None,
        quotes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Add a segment to ground truth data.
        
        Args:
            ground_truth: Ground truth data dictionary
            start: Start timestamp in seconds
            end: End timestamp in seconds
            ground_truth_gurmukhi: Ground truth Gurmukhi text
            ground_truth_roman: Optional ground truth Roman transliteration
            quotes: Optional list of quote annotations
        
        Returns:
            Updated ground truth dictionary
        """
        segment = {
            "start": start,
            "end": end,
            "ground_truth_gurmukhi": ground_truth_gurmukhi,
        }
        
        if ground_truth_roman:
            segment["ground_truth_roman"] = ground_truth_roman
        
        if quotes:
            segment["quotes"] = quotes
        
        ground_truth['segments'].append(segment)
        
        # Sort segments by start time
        ground_truth['segments'].sort(key=lambda s: s['start'])
        
        return ground_truth
    
    def add_quote_annotation(
        self,
        segment: Dict[str, Any],
        start: float,
        end: float,
        canonical_line_id: str,
        expected_ang: Optional[int] = None,
        expected_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a quote annotation to a segment.
        
        Args:
            segment: Segment dictionary
            start: Quote start timestamp (relative to segment)
            end: Quote end timestamp (relative to segment)
            canonical_line_id: Expected canonical line ID
            expected_ang: Expected Ang number
            expected_source: Expected source (SGGS, Dasam, etc.)
        
        Returns:
            Updated segment dictionary
        """
        if 'quotes' not in segment:
            segment['quotes'] = []
        
        quote = {
            "start": start,
            "end": end,
            "canonical_line_id": canonical_line_id
        }
        
        if expected_ang is not None:
            quote["expected_ang"] = expected_ang
        
        if expected_source:
            quote["expected_source"] = expected_source
        
        segment['quotes'].append(quote)
        return segment
    
    def _validate_ground_truth(self, data: Dict[str, Any]) -> None:
        """
        Validate ground truth data structure.
        
        Args:
            data: Ground truth data dictionary
        
        Raises:
            ValueError: If validation fails
        """
        if 'audio_file' not in data:
            raise ValueError("Missing 'audio_file' field")
        
        if 'segments' not in data:
            raise ValueError("Missing 'segments' field")
        
        if not isinstance(data['segments'], list):
            raise ValueError("'segments' must be a list")
        
        for i, segment in enumerate(data['segments']):
            if 'start' not in segment or 'end' not in segment:
                raise ValueError(f"Segment {i} missing 'start' or 'end'")
            
            if segment['start'] >= segment['end']:
                raise ValueError(f"Segment {i}: start ({segment['start']}) >= end ({segment['end']})")
            
            if 'ground_truth_gurmukhi' not in segment:
                raise ValueError(f"Segment {i} missing 'ground_truth_gurmukhi'")
            
            # Validate quotes if present
            if 'quotes' in segment:
                for j, quote in enumerate(segment['quotes']):
                    if 'start' not in quote or 'end' not in quote:
                        raise ValueError(f"Segment {i}, quote {j} missing 'start' or 'end'")
                    
                    if quote['start'] >= quote['end']:
                        raise ValueError(f"Segment {i}, quote {j}: start >= end")
                    
                    if 'canonical_line_id' not in quote:
                        raise ValueError(f"Segment {i}, quote {j} missing 'canonical_line_id'")
    
    def validate_timestamps(
        self,
        ground_truth: Dict[str, Any],
        audio_duration: Optional[float] = None
    ) -> List[str]:
        """
        Validate that timestamps align with audio duration.
        
        Args:
            ground_truth: Ground truth data dictionary
            audio_duration: Optional audio duration in seconds
        
        Returns:
            List of validation warnings/errors (empty if valid)
        """
        warnings = []
        
        for i, segment in enumerate(ground_truth['segments']):
            start = segment['start']
            end = segment['end']
            
            if audio_duration and end > audio_duration:
                warnings.append(
                    f"Segment {i}: end time ({end}) exceeds audio duration ({audio_duration})"
                )
            
            if start < 0:
                warnings.append(f"Segment {i}: start time ({start}) is negative")
            
            # Check for overlaps with previous segment
            if i > 0:
                prev_end = ground_truth['segments'][i-1]['end']
                if start < prev_end:
                    warnings.append(
                        f"Segment {i}: overlaps with previous segment "
                        f"(start: {start}, prev_end: {prev_end})"
                    )
        
        return warnings
    
    def list_ground_truth_files(self) -> List[Path]:
        """
        List all ground truth files in the ground truth directory.
        
        Returns:
            List of ground truth file paths
        """
        return list(self.ground_truth_dir.glob("*.json"))
