"""
Core modules for Katha Transcription System.

Contains:
- orchestrator: Main pipeline orchestrator
- models: Data models and schemas
- errors: Custom exceptions
"""

# Import only what's needed to avoid circular imports
# Import models and errors directly (they don't have circular deps)
from . import models
from . import errors

# Don't import orchestrator here to avoid circular imports
# Users should import directly: from core.orchestrator import Orchestrator

__all__ = ['models', 'errors']
