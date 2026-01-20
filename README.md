# 🎙️ Accuracy-First Katha Transcription System

<div align="center">

![Status](https://img.shields.io/badge/status-production-green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-personal%20use-lightgrey)

**Multi-ASR Ensemble** | **Gurbani Detection** | **Live Mode** | **Script Conversion** | **Audio Denoising** | **CLI Tool**

[Quick Start](#-quick-start) • [Features](#-key-features) • [Installation](#-installation) • [API Docs](#-api-documentation) • [Troubleshooting](#-troubleshooting)

</div>

---

## 📖 What is this?

A **production-grade automatic speech recognition (ASR) system** specifically designed for transcribing **Katha** (Sikh religious discourse) with maximum accuracy. This system combines multiple state-of-the-art ASR engines, intelligent fusion algorithms, and canonical Gurbani quote detection to produce highly accurate transcriptions in Gurmukhi script with Roman transliteration.

**Perfect for:**
- Transcribing Sikh religious lectures and discourses
- Converting Punjabi audio (Gurmukhi/Shahmukhi) to text
- Real-time live transcription with WebSocket support
- Detecting and replacing Gurbani quotes with canonical text
- Multi-language audio processing (Punjabi, Hindi, English, mixed)

---

## ✨ Key Features

### 🎯 Core Capabilities

- **Multi-ASR Ensemble**: Combines Whisper Large, Indic-tuned Whisper, and English Whisper for optimal accuracy
- **Multiple ASR Providers**: Choose from faster-whisper, AI4Bharat IndicConformer, Wav2Vec2 Punjabi, or commercial APIs
- **Intelligent Fusion**: Voting algorithms and confidence merging across multiple ASR engines
- **Canonical Gurbani Detection**: Automatically detects and replaces Gurbani quotes with exact canonical text from SGGS and Dasam Granth databases
- **Script Conversion**: Automatic Shahmukhi → Gurmukhi conversion and Gurmukhi → Roman transliteration
- **Live Transcription**: Real-time WebSocket-based transcription with <2s draft latency and <5s verified updates
- **Audio Denoising**: Optional noise reduction for improved accuracy on noisy recordings
- **Multi-Format Export**: Export transcriptions as TXT, JSON, Markdown, HTML, DOCX, or PDF
- **CLI Tool**: Full command-line interface for batch processing and scripting

### 🌐 Language & Script Support

- **Punjabi** (Gurmukhi & Shahmukhi scripts)
- **Hindi** (Devanagari script)
- **English**
- **Mixed languages** (auto-detected and routed)

### 🔧 Technical Features

- **Voice Activity Detection (VAD)**: Intelligent audio chunking with overlap buffers
- **Language Identification**: Automatic routing based on detected language/domain
- **Unicode Normalization**: Consistent Gurmukhi diacritic handling
- **Semantic Search**: Optional embedding-based quote matching for improved recall
- **Evaluation Tools**: WER/CER computation and accuracy reporting

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd KathaTranscription

# Start the application
docker-compose up --build

# Open in browser
# http://localhost:5000
```

The Docker setup automatically handles dependencies, FFmpeg, GPU acceleration, and model caching.

### Manual Installation

```bash
# 1. Install Python 3.8+ and FFmpeg
# Windows: Download FFmpeg from ffmpeg.org and add to PATH
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg

# 2. Clone and setup
git clone <repository-url>
cd KathaTranscription
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start server
python app.py

# 5. Open browser
# http://127.0.0.1:5000
```

---

## 📦 Installation

### Prerequisites

- **Python 3.8+**
- **FFmpeg** (for audio processing)
- **NVIDIA GPU** (optional, but recommended for faster processing)
- **8GB+ RAM** (16GB recommended)

### Step-by-Step Setup

1. **Install FFmpeg**:
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`

2. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd KathaTranscription
   ```

3. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Install PyTorch** (if not included):
   - CPU: `pip install torch`
   - GPU: Visit [pytorch.org](https://pytorch.org/get-started/locally/) for CUDA installation

6. **Start Server**:
   ```bash
   python app.py
   ```

7. **Access Web UI**: Open `http://127.0.0.1:5000` in your browser

---

## 💻 Usage

### File Transcription Mode

1. **Upload Audio Files**: Drag and drop or click to select files
   - Supported formats: MP3, WAV, M4A, FLAC, OGG, WebM, MP4, AVI, MOV

2. **Choose Processing Mode**:
   - **One-by-One**: Process files individually with manual control
   - **Batch**: Process all files automatically

3. **Process & Download**:
   - Click "Process" to transcribe
   - View results in browser or download as TXT/JSON
   - Export in multiple formats (Markdown, HTML, DOCX, PDF)

### Live Transcription Mode

1. Navigate to `/live` endpoint
2. Click "Start Recording" to begin microphone capture
3. View real-time transcription with:
   - Draft captions (<2s latency)
   - Verified updates (<5s latency)
   - Gurmukhi/Roman toggle
   - Quote highlighting with metadata

### CLI Tool

Use the command-line interface for batch processing:

```bash
# Basic usage
python -m cli.transcribe audio.wav

# Choose ASR provider
python -m cli.transcribe audio.mp3 --model indicconformer

# Output formats (json, txt, srt)
python -m cli.transcribe folder/ --out srt

# Full options
python -m cli.transcribe audio.wav --model wav2vec2 --language pa --out txt

# List available providers
python -m cli.transcribe --list-providers
```

**CLI Options:**
| Option | Description |
|--------|-------------|
| `--model`, `-m` | ASR provider: `whisper`, `indicconformer`, `wav2vec2`, `commercial` |
| `--out`, `-o` | Output format: `json`, `txt`, `srt` |
| `--language`, `-l` | Language hint (default: `pa` for Punjabi) |
| `--timestamps/--no-timestamps` | Include timestamps in output |
| `--output-dir`, `-d` | Output directory |
| `--list-providers` | List available ASR providers |

---

## 🎤 ASR Provider Options

The system supports multiple ASR providers for different use cases:

| Provider | Model | Best For | Timestamps |
|----------|-------|----------|------------|
| **Whisper** | faster-whisper (large) | General multilingual, best all-around | ✓ Word-level |
| **IndicConformer** | AI4Bharat | Indian languages, native Gurmukhi | ✓ Segment |
| **Wav2Vec2** | Punjabi fine-tuned | Direct Punjabi transcription | Limited |
| **Commercial** | ElevenLabs Scribe | High accuracy, API-based | ✓ Word-level |

### Provider Configuration

Configure providers via environment variables or the Settings page (`/settings`):

```bash
# Set primary provider
export ASR_PRIMARY_PROVIDER=indicconformer

# Set fallback provider
export ASR_FALLBACK_PROVIDER=whisper

# Commercial API (optional)
export USE_COMMERCIAL=true
export COMMERCIAL_API_KEY=your_api_key
```

---

## ⚙️ Configuration

Edit `config.py` or set environment variables:

### Core Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Model Size | `WHISPER_MODEL_SIZE` | `large` | Options: `tiny`, `base`, `small`, `medium`, `large` |
| Server Port | `FLASK_PORT` | `5000` | Flask server port |
| Max File Size | `MAX_FILE_SIZE_MB` | `500` | Maximum upload size (MB) |

### Audio Denoising

Enable denoising for noisy recordings:

```bash
export ENABLE_DENOISING=true
export DENOISE_STRENGTH=medium  # light, medium, aggressive
export DENOISE_BACKEND=noisereduce  # noisereduce, facebook, deepfilter
```

### Quote Detection

Adjust quote matching sensitivity:

```bash
export QUOTE_MATCH_CONFIDENCE_THRESHOLD=0.90  # 0.0-1.0
export USE_EMBEDDING_SEARCH=false  # Enable semantic search
```

### Full Configuration

See `config.py` for all available settings including:
- VAD (Voice Activity Detection) parameters
- Language identification thresholds
- ASR fusion settings
- Script conversion options
- Unicode normalization

---

## 📡 API Documentation

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main application page |
| `GET` | `/live` | Live transcription page |
| `GET` | `/settings` | Settings configuration page |
| `GET` | `/status` | Server and model status |
| `POST` | `/upload` | Upload audio file |
| `POST` | `/transcribe-v2` | Transcribe with multi-ASR ensemble |
| `POST` | `/transcribe-batch` | Transcribe multiple files |
| `GET` | `/log` | Get processing log |
| `GET` | `/download/<filename>` | Download transcription file |
| `GET` | `/export/<filename>/<format>` | Export in format (txt, json, markdown, html, docx, pdf) |
| `GET` | `/api/providers` | List available ASR providers |
| `GET` | `/api/settings` | Get current settings |
| `POST` | `/api/settings` | Update settings |
| `POST` | `/api/test-commercial` | Test commercial API connection |

### WebSocket Events

**Client → Server:**
- `audio_chunk` - Send audio chunk for processing
- `ping` - Keep-alive ping

**Server → Client:**
- `connected` - Connection established
- `draft_caption` - Draft transcription (ASR-A output)
- `verified_update` - Verified transcription (after quote detection)
- `error` - Error message

### Example API Usage

```python
import requests

# Upload file
with open('audio.mp3', 'rb') as f:
    response = requests.post('http://localhost:5000/upload', files={'file': f})
    data = response.json()
    filename = data['filename']

# Transcribe
response = requests.post('http://localhost:5000/transcribe-v2', 
                          json={'filename': filename})
result = response.json()

# Download transcription
response = requests.get(f'http://localhost:5000/download/{filename}.txt')
```

---

## 🏗️ Project Structure

```
KathaTranscription/
├── app.py                    # Flask backend server (main entry point)
├── config.py                 # Configuration settings
├── core/                     # Core modules
│   ├── orchestrator.py       # Main pipeline orchestrator
│   ├── models.py             # Data models and schemas
│   └── errors.py             # Custom exceptions
├── services/                 # Service modules
│   ├── whisper_service.py    # Legacy Whisper service
│   ├── vad_service.py        # Voice Activity Detection
│   ├── langid_service.py     # Language identification
│   └── script_converter.py   # Script conversion
├── utils/                    # Utility modules
│   └── file_manager.py       # File operations and logging
├── scripts/                  # Utility scripts
│   ├── build_embedding_index.py
│   └── start_server.bat
├── asr/                      # ASR engines
│   ├── asr_whisper.py        # ASR-A: Whisper Large (faster-whisper)
│   ├── asr_indic.py          # ASR-B: Indic-tuned Whisper
│   ├── asr_english_fallback.py  # ASR-C: English Whisper
│   ├── asr_indicconformer.py # AI4Bharat IndicConformer
│   ├── asr_wav2vec2.py       # Wav2Vec2 Punjabi
│   ├── asr_commercial.py     # ElevenLabs commercial API
│   ├── asr_fusion.py         # Fusion layer
│   └── provider_registry.py  # Multi-provider management
├── cli/                      # Command-line interface
│   └── transcribe.py         # CLI transcription tool
├── audio/                    # Audio processing
│   ├── denoiser.py           # Audio denoising
│   └── audio_utils.py        # Audio utilities
├── quotes/                   # Quote detection
│   ├── quote_candidates.py   # Candidate detection
│   ├── assisted_matcher.py   # Multi-stage matching
│   └── canonical_replacer.py # Canonical replacement
├── scripture/                # Scripture databases
│   ├── sggs_db.py           # SGGS database
│   ├── dasam_db.py          # Dasam Granth database
│   ├── scripture_service.py  # Unified scripture API
│   └── embedding_index.py   # Semantic search
├── post/                     # Post-processing
│   ├── annotator.py          # Transcript annotation
│   ├── document_formatter.py # Document formatting
│   ├── section_classifier.py # Section classification
│   └── transcript_merger.py  # Transcript merging
├── exports/                  # Export formats
│   ├── json_exporter.py
│   ├── markdown_exporter.py
│   ├── html_exporter.py
│   ├── docx_exporter.py
│   └── pdf_exporter.py
├── eval/                     # Evaluation tools
│   ├── wer_cer_reports.py   # WER/CER metrics
│   └── quote_accuracy_reports.py
├── ui/                       # UI components
│   └── websocket_server.py   # WebSocket server
├── static/                   # Web assets (CSS, JS)
├── templates/                # HTML templates
├── tests/                    # Test suite
│   ├── test_phase*.py        # Phase-specific tests
│   ├── test_*.py             # Component tests
│   └── __init__.py
├── data/                     # Data files
│   ├── script_mappings.py   # Unicode mappings
│   └── gurmukhi_normalizer.py
├── outputs/                  # Transcription outputs
│   ├── transcriptions/       # Text files
│   ├── json/                 # JSON files
│   └── formatted/            # Formatted documents
├── uploads/                  # Uploaded audio files
└── logs/                     # Log files
```

---

## 🧪 Testing

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Component Tests

```bash
# ASR engines
python -m pytest tests/test_phase2.py -v

# Script conversion
python -m pytest tests/test_phase3.py -v

# Quote detection
python -m pytest tests/test_phase4_*.py -v

# Live mode
python -m pytest tests/test_phase6.py -v

# Audio denoising
python -m pytest tests/test_denoiser.py -v
```

---

## 🔧 Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker ps  # Check Docker is running
docker-compose logs  # Check logs
```

**GPU not detected:**
- Ensure NVIDIA drivers are installed
- Install NVIDIA Container Toolkit
- Verify: `docker run --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi`

### Audio Processing

**FFmpeg errors:**
- Verify FFmpeg is installed: `ffmpeg -version`
- Ensure FFmpeg is in PATH
- Check audio file format is supported

**Processing errors:**
- Verify file is not corrupted
- Check file size is within limits (default: 500MB)
- Ensure sufficient disk space

### Performance

**Slow processing:**
- Use GPU acceleration (NVIDIA CUDA)
- Reduce model size for faster processing (`small` or `medium`)
- Enable parallel processing: `ASR_PARALLEL_WORKERS=2`

**Memory issues:**
- Reduce model size
- Process smaller audio chunks
- Increase system RAM

### Model Download

**First run downloads models:**
- Initial download can take 5-10 minutes
- Models are cached in `~/.cache/whisper/`
- Docker: Models cached in volume `whisper-cache`

---

## 📊 Output Formats

### Text Files (`outputs/transcriptions/`)
Plain text transcriptions in Gurmukhi script.

### JSON Files (`outputs/json/`)
Structured data with:
- Full transcription (Gurmukhi and Roman)
- Segments with timestamps
- Language detection results
- Quote metadata (Ang, Raag, Author)
- Confidence scores
- Processing metrics

### Formatted Exports
- **Markdown**: Clean, readable format
- **HTML**: Styled with embedded CSS
- **DOCX**: Microsoft Word documents
- **PDF**: Professional PDF output

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 🔑 Keywords & Topics

This project is optimized for discovery by search engines and AI tools. Key terms:

**Primary Keywords:**
- Punjabi transcription
- Gurmukhi ASR
- Sikh katha transcription
- Gurbani detection
- Multi-language speech recognition
- Indic ASR
- Shahmukhi to Gurmukhi conversion
- Real-time transcription
- WebSocket transcription
- Whisper transcription
- Canonical quote matching

**GitHub Topics:**
`punjabi` `gurmukhi` `asr` `speech-recognition` `whisper` `transcription` `sikh` `katha` `gurbani` `indic-languages` `multilingual` `websocket` `real-time` `audio-processing` `script-conversion` `shahmukhi` `devanagari` `audio-denoiser` `flask` `python`

**Technical Stack:**
- Python 3.8+
- Flask & Flask-SocketIO
- OpenAI Whisper (Large, Indic-tuned, English)
- PyTorch
- FAISS (semantic search)
- FFmpeg
- Docker

---

## 📝 License

This project is provided as-is for personal use.

---

## 📌 Notes

- **First run**: Downloads Whisper models (5-10 minutes, one-time)
- **Model caching**: Models cached locally or in Docker volume
- **Processing time**: Varies by file size and model (typically 0.5-2x realtime with GPU)
- **GPU recommended**: Significantly faster than CPU-only processing
- **Database files**: SGGS and Dasam Granth databases required for quote detection (not included)

---

<div align="center">

**Built with ❤️ for the Sikh community**

[Report Issue](https://github.com/your-repo/issues) • [Request Feature](https://github.com/your-repo/issues) • [Documentation](#-api-documentation)

</div>
