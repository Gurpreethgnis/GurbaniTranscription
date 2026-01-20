# Test Organization

This directory contains the test suite for the Gurbani Transcription System.

## Test Categories

### Core Tests (Primary)
- `test_api.py` - API endpoint tests
- `test_orchestrator.py` - Main orchestrator integration tests
- `test_live.py` - WebSocket/live mode tests
- `test_asr.py` - ASR engine tests

### Service Tests
- `test_language_priority.py` - Language prioritization tests
- `test_section_classifier.py` - Section classification tests
- `test_denoiser.py` - Audio denoising tests

### Quote Tests
- `test_quotes.py` - Quote detection and matching tests
- `test_matching_debug.py` - Debugging tests for matching

### Export Tests
- `test_exports.py` - Combined export tests
- `test_base_exporter.py` - Base exporter functionality
- `test_json_exporter.py` - JSON export
- `test_markdown_exporter.py` - Markdown export
- `test_html_exporter.py` - HTML export
- `test_docx_exporter.py` - DOCX export
- `test_pdf_exporter.py` - PDF export

### Post-Processing Tests
- `test_document_formatter.py` - Document formatting
- `test_document_models.py` - Document model tests

### Database Tests
- `test_db_*.py` - Database-related tests

### Phase Tests (Development/Integration)
These are historical phase-based tests from development:
- `test_phase1.py` through `test_phase6.py` - Main phase tests
- `test_phase*_milestone*.py` - Milestone-specific tests
- `test_phase*_*.py` - Additional phase variants

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run core tests only
python -m pytest tests/test_api.py tests/test_orchestrator.py tests/test_asr.py -v

# Run export tests
python -m pytest tests/test_*exporter*.py -v

# Run quote tests
python -m pytest tests/test_quotes.py tests/test_phase4*.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Structure

Each test file follows pytest conventions:
- Classes prefixed with `Test`
- Methods prefixed with `test_`
- Fixtures defined in `fixtures/` or within test files

