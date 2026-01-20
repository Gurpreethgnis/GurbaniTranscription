"""
Service modules for Katha Transcription System.

Consolidated Structure:
- transcription: VAD and Language ID services (vad_service + langid_service)
- script: Script processing services (script_converter + script_lock + drift_detector)
- alignment: Alignment services (ngram_rescorer + sggs_aligner)
- domain_corrector: Domain-constrained spelling correction
- shabad_detector: Shabad detection and tracking
- semantic_praman: Semantic search for related pramans

Legacy modules (kept for backward compatibility):
- vad_service: Voice Activity Detection
- langid_service: Language identification
- script_converter: Script conversion utilities
- script_lock: Gurmukhi script enforcement
- drift_detector: Anti-drift validation
- ngram_rescorer: N-gram LM rescoring
- sggs_aligner: SGGS text alignment
"""

# Don't import here to avoid circular imports
# Users should import directly:
#   from services.transcription import VADService, LangIDService
#   from services.script import ScriptConverter, ScriptLock
#   from services.alignment import NGramRescorer, SGGSAligner
#   from services.shabad_detector import ShabadDetector
#   from services.semantic_praman import SemanticPramanService

__all__ = []
