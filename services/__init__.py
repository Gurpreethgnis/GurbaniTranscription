"""
Service modules for Katha Transcription System.

Contains:
- whisper_service: Legacy Whisper service
- vad_service: Voice Activity Detection
- langid_service: Language identification
- script_converter: Script conversion utilities
- script_lock: Gurmukhi script enforcement
- drift_detector: Anti-drift validation
- domain_corrector: Domain-constrained spelling correction
- ngram_rescorer: N-gram LM rescoring for ASR hypotheses
"""

# Don't import here to avoid circular imports
# Users should import directly: from services.vad_service import VADService

__all__ = []
