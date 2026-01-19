# Accuracy-First Katha Transcription System

A production-grade system for transcribing Katha (Sikh religious discourse) with maximum accuracy, featuring multi-ASR ensemble, canonical Gurbani quote detection, and intelligent fusion. Optimized for Punjabi, English, and mixed-language audio with Gurmukhi output.

## Features

### Phase 1: Baseline Orchestrated Pipeline ✅
- **VAD Chunking**: Voice Activity Detection with overlap buffers
- **Language Identification**: Automatic routing (Punjabi/English/Scripture/Mixed)
- **ASR-A (Whisper Large)**: Primary transcription engine with forced language per segment
- **Structured Output**: JSON with segments, routes, confidence scores

### Phase 2: Multi-ASR Ensemble + Fusion ✅
- **ASR-B (Indic Whisper)**: Indic-tuned model for Punjabi/Hindi/Braj robustness
- **ASR-C (English Whisper)**: English-optimized model for English segments
- **Intelligent Fusion**: Voting, confidence merging, and re-decode policy
- **Hybrid Execution**: ASR-A immediate, ASR-B/C parallel based on route
- **Multi-Hypothesis Storage**: All ASR outputs preserved for review

### Phase 3: Script Conversion ✅
- **Automatic Script Detection**: Detects Shahmukhi, Gurmukhi, English, Devanagari, or mixed
- **Shahmukhi to Gurmukhi Conversion**: Converts Arabic-based Punjabi to Gurmukhi script
- **Gurmukhi to Roman Transliteration**: Transliterates to Roman script (ISO 15919, IAST, or practical)
- **Dual-Output Generation**: Produces both Gurmukhi and Roman transliteration
- **Common Word Dictionary**: Uses dictionary lookup for accurate conversion
- **Confidence Scoring**: Flags uncertain conversions for review
- **Integrated Pipeline**: Automatically applied to all transcription segments

### Phase 4: Scripture Services + Quote Detection ✅
- **Scripture Services**: ShabadOS SGGS + Dasam Granth database integration
- **Unified Scripture API**: Single interface for all scripture sources
- **Quote Candidate Detection**: High-recall detection using multiple signals
- **Assisted Matching**: Multi-stage matching (fuzzy + semantic + verifier)
- **Canonical Replacement**: Exact bani text with metadata (Ang, Raag, author)
- **Provenance Preservation**: Original ASR text preserved alongside canonical

### Phase 5: Normalization + Transliteration Gap Filling ✅
- **Gurmukhi Diacritic Normalization**: Tippi/Bindi, Adhak, Nukta normalization
- **ShabadOS Transliteration Retrieval**: Roman transliteration from database for canonical quotes
- **Consistent Unicode Normalization**: Applied throughout pipeline using config.UNICODE_NORMALIZATION_FORM
- **Canonical Quote Transliteration**: Database transliteration flows through to final output

### General Features
- **Multi-file Processing**: Select and process multiple audio files
- **Two Processing Modes**: 
  - One-by-one: Process files individually with manual control
  - Batch: Process all files automatically
- **Multiple Output Formats**: 
  - Plain text files (.txt)
  - JSON files with metadata (.json)
- **Processing Log**: Track all processed files with timestamps and status
- **Resume Support**: Skip already processed files automatically
- **Modern Web UI**: Clean, responsive interface

## Quick Start with Docker (Recommended)

The easiest way to run the application is using Docker:

1. **Make sure Docker and Docker Compose are installed**

2. **Build and run the container**:
   ```bash
   docker-compose up --build
   ```

3. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

4. **To stop the container**:
   ```bash
   docker-compose down
   ```

The Docker setup automatically:
- Installs all dependencies
- Sets up FFmpeg
- Mounts volumes for uploads, outputs, and logs (data persists)
- Caches Whisper models for faster restarts

## Manual Installation (Without Docker)

### Prerequisites

1. **Python 3.8 or higher**
2. **FFmpeg** (required for audio processing):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg`

### Installation Steps

1. **Clone or navigate to the project directory**:
   ```bash
   cd KathaTranscription
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   **Phase 2 Dependencies** (for multi-ASR fusion):
   ```bash
   pip install rapidfuzz python-Levenshtein
   ```
   
   **Phase 3 Dependencies** (for script conversion):
   - No additional dependencies required (uses standard library)

4. **Install PyTorch** (if not already installed):
   - For CPU only: `pip install torch`
   - For GPU (CUDA): Visit [pytorch.org](https://pytorch.org/get-started/locally/) for installation instructions

5. **Choose Whisper implementation**:
   - **OpenAI Whisper** (default): Already in requirements.txt
   - **Faster Whisper** (faster, recommended): 
     ```bash
     pip uninstall openai-whisper
     pip install faster-whisper
     ```
     Then edit `whisper_service.py` to use faster-whisper (code already supports both)

6. **Start the server**:
   ```bash
   python app.py
   ```

7. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## Configuration

Edit `config.py` to customize:

- **Model Size**: Change `WHISPER_MODEL_SIZE` (options: `tiny`, `base`, `small`, `medium`, `large`)
  - `tiny`: Fastest, least accurate
  - `base`: Good balance (default)
  - `small`: Better accuracy
  - `medium`: High accuracy, slower
  - `large`: Best accuracy, slowest
- **Language Hints**: Modify `LANGUAGE_HINTS` for better detection
- **File Size Limit**: Adjust `MAX_FILE_SIZE_MB`
- **Server Port**: Change `PORT` if needed (or set `FLASK_PORT` environment variable)

## Usage

1. **Select audio files**:
   - Click the upload area or drag and drop files
   - Supported formats: MP3, WAV, M4A, FLAC, OGG, WebM, MP4, AVI, MOV

2. **Choose processing mode**:
   - **One by One**: Process files individually
   - **Batch Process**: Process all files automatically

3. **Process files**:
   - Click "Process" on individual files (one-by-one mode)
   - Click "Process All" button (batch mode)

4. **View results**:
   - Click "View" to see transcription in the browser
   - Click "Download" to save text or JSON files

5. **Check processing log**:
   - View all processed files in the log section
   - Click "Refresh" to update the log

## Project Structure

```
KathaTranscription/
├── app.py                          # Flask backend server
├── orchestrator.py                 # Main pipeline orchestrator (Phase 1+2+3)
├── vad_service.py                  # Voice Activity Detection
├── langid_service.py               # Language/domain identification
├── whisper_service.py              # Legacy Whisper service
├── script_converter.py             # Script conversion service (Phase 3)
├── file_manager.py                 # File operations and logging
├── config.py                       # Configuration settings
├── models.py                       # Data models (Segment, ASRResult, etc.)
├── errors.py                       # Custom exceptions
├── data/
│   ├── __init__.py
│   ├── script_mappings.py          # Unicode mapping tables (Phase 3)
│   └── gurmukhi_normalizer.py      # Gurmukhi diacritic normalization (Phase 5)
├── asr/
│   ├── __init__.py
│   ├── asr_whisper.py              # ASR-A: Whisper Large
│   ├── asr_indic.py                # ASR-B: Indic-tuned Whisper (Phase 2)
│   ├── asr_english_fallback.py     # ASR-C: English Whisper (Phase 2)
│   └── asr_fusion.py               # Fusion layer (Phase 2)
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose configuration
├── static/
│   ├── css/
│   │   └── style.css               # Application styles
│   └── js/
│       └── main.js                 # Frontend JavaScript
├── templates/
│   └── index.html                  # Main UI
├── uploads/                        # Temporary upload directory
├── outputs/                        # Generated outputs
│   ├── transcriptions/             # Text files
│   └── json/                       # JSON files
├── logs/
│   └── processed_files.json        # Processing log
├── requirements.txt                # Python dependencies
├── test_phase1.py                  # Phase 1 test suite
├── test_phase2.py                  # Phase 2 test suite
├── test_phase3.py                  # Phase 3 comprehensive test suite
├── test_phase4_milestone1.py       # Phase 4 milestone 1 tests
├── test_phase4_milestone2.py       # Phase 4 milestone 2 tests
├── test_phase4_quotes.py          # Phase 4 quote detection tests
├── test_phase5.py                  # Phase 5 comprehensive test suite
├── PHASE2_COMPLETION_REPORT.md     # Phase 2 completion documentation
├── PHASE2_TEST_RESULTS.md          # Phase 2 test results
├── PHASE3_COMPLETION_REPORT.md     # Phase 3 completion documentation
├── PHASE3_TEST_RESULTS.md          # Phase 3 test results
├── PHASE4_COMPLETION_REPORT.md     # Phase 4 completion documentation
├── PHASE5_COMPLETION_REPORT.md     # Phase 5 completion documentation
└── README.md                       # This file
```

## API Endpoints

- `GET /` - Main application page
- `GET /status` - Server and model status
- `POST /upload` - Upload audio file
- `POST /transcribe` - Transcribe single file (legacy)
- `POST /transcribe-v2` - Transcribe with Phase 2 multi-ASR ensemble
- `POST /transcribe-batch` - Transcribe multiple files
- `GET /log` - Get processing log
- `GET /download/<filename>` - Download transcription file

## Testing

### Phase 1 Tests
```bash
python test_phase1.py
```

### Phase 2 Tests
```bash
python test_phase2.py
```

### Phase 3 Tests
```bash
python test_phase3.py
```

### Phase 4 Tests
```bash
python -m pytest test_phase4_milestone1.py test_phase4_milestone2.py test_phase4_quotes.py -v
```

### Phase 5 Tests
```bash
python test_phase5.py
```

Tests include:
- Module imports
- Data model validation
- Script detection
- Shahmukhi to Gurmukhi conversion
- Gurmukhi to Roman transliteration
- ScriptConverter service
- Orchestrator integration
- End-to-end conversion pipeline

## Output Files

### Text Files (`outputs/transcriptions/`)
Plain text files containing the transcription.

### JSON Files (`outputs/json/`)
Structured data with:
- `filename`: Original filename
- `transcription`: Object with `gurmukhi` and `roman` fields (Phase 3)
- `timestamp`: Processing timestamp
- `segments`: Array of segments, each with:
  - `text`: Gurmukhi text
  - `gurmukhi`: Gurmukhi representation (Phase 3)
  - `roman`: Roman transliteration (Phase 3)
  - `original_script`: Detected original script (Phase 3)
  - `script_confidence`: Conversion confidence (Phase 3)
  - `start`, `end`: Timestamps
  - `confidence`: ASR confidence
  - `language`: Detected language
- `metadata`: Language, segments, etc.

### Log File (`logs/processed_files.json`)
JSON array tracking all processed files with:
- Filename and hash
- Processing timestamp
- Status (success/error)
- Language detected
- Output file paths
- Error messages (if any)

## Troubleshooting

### Docker Issues

**Container won't start:**
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs`
- Ensure port 5000 is not in use: Change port in `docker-compose.yml`

**Model download issues:**
- First run downloads the model (can take time)
- Check internet connection
- Models are cached in Docker volume `whisper-cache`

**Permission errors:**
- On Linux/Mac, you may need to adjust file permissions:
  ```bash
  chmod -R 755 uploads outputs logs
  ```

### Model Loading Issues
- Ensure PyTorch is installed correctly
- Check available disk space (models can be 100MB-3GB)
- Try a smaller model size first (`tiny` or `base`)

### Audio Processing Errors
- Verify FFmpeg is installed and in PATH
- Check audio file format is supported
- Ensure file is not corrupted

### Server Not Starting
- Check if port 5000 is already in use
- Change port in `config.py` or set `FLASK_PORT` environment variable
- Ensure all dependencies are installed

### Slow Processing
- Use `faster-whisper` instead of `openai-whisper`
- Use a smaller model size
- Process files one at a time instead of batch
- Consider GPU acceleration (CUDA) - requires custom Dockerfile

## Performance Tips

1. **Use Faster Whisper**: Significantly faster than OpenAI Whisper
2. **Model Size**: Balance between speed and accuracy
   - For quick processing: `tiny` or `base`
   - For better accuracy: `small` or `medium`
3. **GPU Acceleration**: Install CUDA-enabled PyTorch for faster processing (requires custom Dockerfile)
4. **Batch Processing**: More efficient for multiple files

## Language Support

Whisper supports 99 languages. The application is optimized for:
- **Punjabi** (pa)
- **Urdu** (ur)
- **English** (en)
- Mixed languages (auto-detected)

## Docker Commands

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Remove volumes (clears cached models)
docker-compose down -v
```

## License

This project is provided as-is for personal use.

## Implementation Phases

### Phase 1: Baseline Orchestrated Pipeline ✅
- VAD chunking with overlap buffers
- Language/domain identification
- ASR-A (Whisper Large) with forced language
- Structured segment output with confidence scores

### Phase 2: Multi-ASR Ensemble + Fusion ✅
- ASR-B (Indic-tuned Whisper) for Punjabi/Hindi/Braj
- ASR-C (English Whisper) for English segments
- Intelligent fusion with voting and confidence merging
- Re-decode policy for low-confidence segments
- Hybrid execution (ASR-A immediate, ASR-B/C parallel)

### Phase 3: Script Conversion ✅
- Automatic script detection (Shahmukhi, Gurmukhi, English, Devanagari, mixed)
- Shahmukhi to Gurmukhi conversion with common word dictionary
- Gurmukhi to Roman transliteration (ISO 15919, IAST, practical schemes)
- Dual-output generation (Gurmukhi + Roman)
- Integrated into transcription pipeline
- Confidence scoring and review flagging

### Phase 4: Scripture Services + Quote Detection ✅
- ShabadOS SGGS database integration with flexible schema detection
- Dasam Granth database with auto-creation
- Unified scripture service API for all sources
- High-recall quote candidate detection (route, patterns, vocabulary)
- Assisted matching with 3-stage verification (fuzzy + semantic + verifier)
- Canonical text replacement with metadata (Ang, Raag, Author, Source)
- Provenance preservation (original spoken text kept)

### Phase 5: Normalization + Transliteration Gap Filling ✅
- Comprehensive Gurmukhi diacritic normalization (tippi/bindi, adhak, nukta)
- ShabadOS transliteration retrieval for canonical quotes
- Consistent Unicode normalization using config.UNICODE_NORMALIZATION_FORM
- Canonical quote transliteration flows through to final output

## Notes

- First run will download Whisper models (can take a few minutes)
- Models are cached in `~/.cache/whisper/` (local) or Docker volume (Docker)
- Phase 2 uses multiple ASR engines - may require more GPU memory
- Phase 3 script conversion is automatic and adds minimal processing time
- Large audio files may take significant time to process
- Processing time depends on model size, number of ASR engines, and hardware
- See `PHASE2_COMPLETION_REPORT.md` for Phase 2 implementation details
- See `PHASE3_COMPLETION_REPORT.md` for Phase 3 implementation details
