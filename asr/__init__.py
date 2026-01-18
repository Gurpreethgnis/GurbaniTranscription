"""
ASR (Automatic Speech Recognition) module.

This module contains ASR engines for the transcription pipeline.
"""

from .asr_whisper import ASRWhisper

__all__ = ['ASRWhisper']
