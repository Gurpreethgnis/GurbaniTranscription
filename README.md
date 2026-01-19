# Accuracy-First Katha Transcription System

A production-grade system for transcribing Katha (Sikh religious discourse) with maximum accuracy, featuring multi-ASR ensemble, canonical Gurbani quote detection, audio denoising, and intelligent fusion. Optimized for Punjabi, English, and mixed-language audio with Gurmukhi output.

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

### Phase 6: Live Mode + WebSocket UI ✅
- **WebSocket Server**: Flask-SocketIO integration for real-time communication
- **Live Audio Streaming**: Browser microphone capture with MediaRecorder API
- **Draft Captions**: Immediate ASR-A output (< 2s latency)
- **Verified Updates**: Post-quote-detection updates (< 5s latency)
- **Real-time Display**: Live transcript with Gurmukhi/Roman toggle
- **Quote Highlighting**: Visual distinction with metadata tooltips
- **Session Management**: Multi-session support with error handling

### Phase 7: Audio Denoising Module ✅
- **Multi-Backend Support**: Choose from noisereduce (default), Facebook denoiser, or DeepFilterNet
- **Configurable Strength**: Light, medium, or aggressive noise reduction
- **Batch Mode**: Full file denoising before VAD chunking
- **Live Mode**: Real-time chunk-by-chunk denoising for streaming
- **Auto-Enable**: Automatically enables when noise level exceeds threshold
- **Opt-In Design**: Disabled by default, enable via environment variables

### Phase 8: Evaluation Harness ✅
- **WER/CER Computation**: Word and Character Error Rate metrics using jiwer
- **Ground Truth Management**: Store and manage reference transcriptions
- **Accuracy Reports**: Generate detailed accuracy reports for testing

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
- **Modern Web UI**: Clean, responsive interface with theme support

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
- Enables GPU acceleration (NVIDIA CUDA)

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

4. **Install PyTorch** (if not already installed):
   - For CPU only: `pip install torch`
   - For GPU (CUDA): Visit [pytorch.org](https://pytorch.org/get-started/locally/) for installation instructions

5. **Start the server**:
   ```bash
   python app.py
   ```

6. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## Configuration

Edit `config.py` or set environment variables to customize:

### Core Settings
- **Model Size**: Change `WHISPER_MODEL_SIZE` (options: `tiny`, `base`, `small`, `medium`, `large`)
- **Language Hints**: Modify `LANGUAGE_HINTS` for better detection
- **File Size Limit**: Adjust `MAX_FILE_SIZE_MB`
- **Server Port**: Change `PORT` or set `FLASK_PORT` environment variable

### Audio Denoising (Phase 7)
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_DENOISING` | `false` | Enable denoising for batch mode |
| `LIVE_DENOISE_ENABLED` | `false` | Enable denoising for live mode |
| `DENOISE_STRENGTH` | `medium` | Strength: `light`, `medium`, `aggressive` |
| `DENOISE_BACKEND` | `noisereduce` | Backend: `noisereduce`, `facebook`, `deepfilter` |
| `DENOISE_SAMPLE_RATE` | `16000` | Target sample rate (Hz) |
| `DENOISE_AUTO_ENABLE_THRESHOLD` | `0.4` | Auto-enable if noise level > threshold |

**Enable denoising for noisy recordings:**
```bash
export ENABLE_DENOISING=true
export DENOISE_STRENGTH=medium
```

## Usage

### File Transcription Mode

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

### Live Transcription Mode

1. **Navigate to** `/live` endpoint
2. **Click "Start Recording"** to begin microphone capture
3. **View real-time transcription** with draft and verified updates
4. **Toggle display mode** between Gurmukhi, Roman, or Both

## Project Structure

```
KathaTranscription/
├── app.py                          # Flask backend server
├── orchestrator.py                 # Main pipeline orchestrator
├── vad_service.py                  # Voice Activity Detection
├── langid_service.py               # Language/domain identification
├── whisper_service.py              # Legacy Whisper service
├── script_converter.py             # Script conversion service
├── file_manager.py                 # File operations and logging
├── config.py                       # Configuration settings
├── models.py                       # Data models (Segment, ASRResult, etc.)
├── errors.py                       # Custom exceptions
├── data/
│   ├── __init__.py
│   ├── script_mappings.py          # Unicode mapping tables
│   ├── gurmukhi_normalizer.py      # Gurmukhi diacritic normalization
│   └── vectors/                    # Embedding index files
├── asr/
│   ├── __init__.py
│   ├── asr_whisper.py              # ASR-A: Whisper Large
│   ├── asr_indic.py                # ASR-B: Indic-tuned Whisper
│   ├── asr_english_fallback.py     # ASR-C: English Whisper
│   └── asr_fusion.py               # Fusion layer
├── audio/
│   ├── __init__.py
│   └── denoiser.py                 # Audio denoising service (Phase 7)
├── quotes/
│   ├── __init__.py
│   ├── quote_candidates.py         # Quote candidate detection
│   ├── assisted_matcher.py         # Multi-stage matching
│   └── canonical_replacer.py       # Canonical text replacement
├── scripture/
│   ├── __init__.py
│   ├── sggs_db.py                  # SGGS database interface
│   ├── dasam_db.py                 # Dasam Granth database
│   ├── scripture_service.py        # Unified scripture API
│   ├── embedding_index.py          # Semantic search embeddings
│   └── gurmukhi_to_ascii.py        # Script conversion utilities
├── post/
│   ├── __init__.py
│   ├── annotator.py                # Transcript annotation
│   └── transcript_merger.py        # Transcript merging utilities
├── eval/
│   ├── __init__.py
│   ├── dataset_builder.py          # Evaluation dataset creation
│   ├── wer_cer_reports.py          # WER/CER accuracy reports
│   ├── quote_accuracy_reports.py   # Quote detection accuracy
│   ├── ground_truth/               # Reference transcriptions
│   └── reports/                    # Generated evaluation reports
├── ui/
│   ├── __init__.py
│   └── websocket_server.py         # WebSocket server (Phase 6)
├── static/
│   ├── css/
│   │   ├── style.css               # Main application styles
│   │   └── themes.css              # Theme support
│   └── js/
│       ├── main.js                 # Main frontend JavaScript
│       ├── live.js                 # Live mode JavaScript
│       └── navigation.js           # Navigation utilities
├── templates/
│   ├── base.html                   # Base template
│   ├── index.html                  # Main UI
│   └── live.html                   # Live transcription UI
├── uploads/                        # Temporary upload directory
├── outputs/
│   ├── transcriptions/             # Text files
│   └── json/                       # JSON files
├── logs/
│   └── processed_files.json        # Processing log
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose configuration
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## API Endpoints

### REST API
- `GET /` - Main application page
- `GET /live` - Live transcription page
- `GET /status` - Server and model status
- `POST /upload` - Upload audio file
- `POST /transcribe` - Transcribe single file (legacy)
- `POST /transcribe-v2` - Transcribe with multi-ASR ensemble
- `POST /transcribe-batch` - Transcribe multiple files
- `GET /log` - Get processing log
- `GET /download/<filename>` - Download transcription file

### WebSocket Events

**Client → Server:**
- `audio_chunk` - Send audio chunk for processing
- `ping` - Keep-alive ping

**Server → Client:**
- `connected` - Connection established
- `draft_caption` - Draft transcription (ASR-A output)
- `verified_update` - Verified transcription (after quote detection)
- `error` - Error message
- `chunk_received` - Audio chunk acknowledgment

## Testing

### Run All Tests
```bash
python -m pytest test_*.py -v
```

### Phase-Specific Tests
```bash
# Phase 1: Baseline Pipeline
python test_phase1.py

# Phase 2: Multi-ASR Fusion
python test_phase2.py

# Phase 3: Script Conversion
python test_phase3.py

# Phase 4: Scripture + Quote Detection
python -m pytest test_phase4_*.py -v

# Phase 5: Normalization
python test_phase5.py

# Phase 6: Live Mode
python test_phase6.py

# Phase 7: Audio Denoising
python -m pytest test_denoiser.py -v

# Phase 8: Evaluation
python test_eval.py
```

## Output Files

### Text Files (`outputs/transcriptions/`)
Plain text files containing the transcription.

### JSON Files (`outputs/json/`)
Structured data with:
- `filename`: Original filename
- `transcription`: Object with `gurmukhi` and `roman` fields
- `timestamp`: Processing timestamp
- `segments`: Array of segments, each with:
  - `text`: Gurmukhi text
  - `gurmukhi`: Gurmukhi representation
  - `roman`: Roman transliteration
  - `original_script`: Detected original script
  - `script_confidence`: Conversion confidence
  - `start`, `end`: Timestamps
  - `confidence`: ASR confidence
  - `language`: Detected language
  - `is_quote`: Whether segment is a detected quote
  - `quote_metadata`: Quote info (Ang, Raag, Author) if applicable
- `metadata`: Language, segments, etc.

## Troubleshooting

### Docker Issues

**Container won't start:**
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs`
- Ensure port 5000 is not in use

**GPU not detected:**
- Ensure NVIDIA drivers are installed
- Install NVIDIA Container Toolkit
- Check GPU access: `docker run --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi`

**Model download issues:**
- First run downloads the model (can take time)
- Models are cached in Docker volume `whisper-cache`

### Audio Processing Errors
- Verify FFmpeg is installed and in PATH
- Check audio file format is supported
- Ensure file is not corrupted

### Performance Tips
1. **Use GPU**: Significantly faster than CPU-only
2. **Enable Denoising**: For noisy recordings, enable denoising for better accuracy
3. **Model Size**: Balance between speed and accuracy
   - For quick processing: `tiny` or `base`
   - For better accuracy: `small` or `medium` or `large`

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

## Implementation Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Baseline Orchestrated Pipeline | ✅ Complete |
| 2 | Multi-ASR Ensemble + Fusion | ✅ Complete |
| 3 | Script Conversion | ✅ Complete |
| 4 | Scripture Services + Quote Detection | ✅ Complete |
| 5 | Normalization + Transliteration | ✅ Complete |
| 6 | Live Mode + WebSocket UI | ✅ Complete |
| 7 | Audio Denoising Module | ✅ Complete |
| 8 | Evaluation Harness | ✅ Complete |

## Language Support

Optimized for:
- **Punjabi** (pa) - Gurmukhi and Shahmukhi scripts
- **Hindi** (hi) - Devanagari script
- **English** (en)
- **Mixed languages** (auto-detected)

## License

This project is provided as-is for personal use.

## Notes

- First run will download Whisper models (can take a few minutes)
- Models are cached in `~/.cache/whisper/` (local) or Docker volume (Docker)
- Large audio files may take significant time to process
- See individual `PHASE*_COMPLETION_REPORT.md` files for detailed implementation documentation
