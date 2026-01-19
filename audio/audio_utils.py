"""
Audio utility functions for getting file metadata.
"""
import subprocess
import json
from pathlib import Path
from typing import Optional


def get_audio_duration(audio_path: Path) -> Optional[float]:
    """
    Get audio file duration in seconds using ffprobe.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Duration in seconds, or None if unable to determine
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(audio_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration_str = data.get('format', {}).get('duration')
            if duration_str:
                return float(duration_str)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, ValueError, KeyError):
        pass
    
    return None
