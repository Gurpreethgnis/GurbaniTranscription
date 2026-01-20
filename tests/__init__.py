"""
Test suite for Katha Transcription Application.

Consolidated Test Structure:
---------------------------
- test_asr.py       : ASR engine tests (ASR-A, B, C, Fusion, BaseASR)
- test_orchestrator.py : Pipeline/orchestrator tests
- test_quotes.py    : Quote detection and matching tests
- test_exports.py   : Export format tests (JSON, Markdown, HTML, DOCX, PDF)
- test_live.py      : Live streaming/WebSocket tests
- test_api.py       : API endpoint tests
- test_utils.py     : Utility function tests
- fixtures/         : Shared test fixtures and sample data

Legacy Test Files:
-----------------
The following files are kept for backwards compatibility but are superseded
by the consolidated tests above:

- test_phase1.py through test_phase6.py
- test_phase3_milestone*.py, test_phase4_milestone*.py
- test_phase4_full_pipeline.py, test_phase4_integration.py, test_phase4_quotes.py
- Individual exporter tests (test_*_exporter.py)
- test_db_*.py, test_matching_debug.py

Running Tests:
-------------
Run all consolidated tests:
    python -m pytest tests/test_asr.py tests/test_orchestrator.py tests/test_quotes.py tests/test_exports.py tests/test_live.py tests/test_api.py tests/test_utils.py

Run a specific test file:
    python -m pytest tests/test_asr.py -v

Run individual test file directly:
    python tests/test_asr.py
"""

from tests.fixtures import (
    create_sample_audio_chunk,
    create_sample_segment,
    create_sample_asr_result,
    create_sample_fusion_result,
    create_sample_document,
    create_sample_transcription_result
)

__all__ = [
    'create_sample_audio_chunk',
    'create_sample_segment',
    'create_sample_asr_result',
    'create_sample_fusion_result',
    'create_sample_document',
    'create_sample_transcription_result'
]
