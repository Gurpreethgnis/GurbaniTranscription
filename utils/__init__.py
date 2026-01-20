"""
Utility modules for Katha Transcription System.

Contains:
- file_manager: File operations and logging
- device_utils: GPU/CPU device detection
"""

from .file_manager import FileManager
from .device_utils import detect_device

__all__ = ['FileManager', 'detect_device']
