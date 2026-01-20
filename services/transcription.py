"""
Transcription Services Module.

Combines Voice Activity Detection (VAD) and Language Identification (LangID)
services for audio chunking and routing.

Consolidated from:
- vad_service.py
- langid_service.py
"""
# Re-export from original modules for backward compatibility
from services.vad_service import VADService
from services.langid_service import (
    LangIDService,
    ROUTE_PUNJABI_SPEECH,
    ROUTE_ENGLISH_SPEECH,
    ROUTE_SCRIPTURE_QUOTE_LIKELY,
    ROUTE_MIXED,
)

__all__ = [
    # VAD
    'VADService',
    
    # LangID
    'LangIDService',
    'ROUTE_PUNJABI_SPEECH',
    'ROUTE_ENGLISH_SPEECH',
    'ROUTE_SCRIPTURE_QUOTE_LIKELY',
    'ROUTE_MIXED',
]

