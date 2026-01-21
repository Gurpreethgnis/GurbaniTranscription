# ਸ਼ਬਦ ਗੁਰੂ | Shabad Guru

<div align="center">

<img src="static/logo.svg" alt="Shabad Guru Logo" width="200" height="200">

### *Voice to Sacred Text*

**Transform spoken Gurbani into accurate, canonical Gurmukhi transcription**

![Python](https://img.shields.io/badge/python-3.11%2B-1f2a6d)
![Flask](https://img.shields.io/badge/flask-websocket-d6a21f)
![License](https://img.shields.io/badge/license-personal-f6f0e2)

[Quick Start](#-quick-start) • [Features](#-features) • [Modes](#-modes) • [API](#-api) • [📖 Full Guide](docs/ONBOARDING_GUIDE.md)

</div>

---

## ੴ What is Shabad Guru?

**Shabad Guru** (ਸ਼ਬਦ ਗੁਰੂ — "The Word is the Guru") transforms spoken Punjabi and Gurbani into accurate Gurmukhi text. It combines multiple speech recognition engines with intelligent quote detection to produce transcriptions that automatically replace detected Gurbani with canonical scripture text.

**Built for:**
- Transcribing Sikh religious lectures (*katha*)
- Real-time live transcription of discourses
- Kirtan transcription with praman (scriptural evidence) suggestions
- Converting Punjabi/Hindi/English audio to text with Gurmukhi output

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Multi-ASR Ensemble** | Whisper Large + Indic-tuned + English models with intelligent fusion |
| **Canonical Quote Detection** | Auto-detects Gurbani and replaces with exact SGGS/Dasam Granth text |
| **Live Transcription** | WebSocket-based real-time transcription with <2s latency |
| **Shabad Mode** | Kirtan transcription with praman suggestions |
| **Script Conversion** | Shahmukhi → Gurmukhi, Gurmukhi → Roman transliteration |
| **Domain Modes** | SGGS, Dasam Granth, or Generic vocabulary optimization |
| **Audio Denoising** | Built-in noise reduction for clearer input |
| **Multi-Format Export** | TXT, JSON, Markdown, HTML, DOCX, PDF, SRT |

---

## 🎯 Modes

### 📄 File Transcription
Upload audio files (MP3, WAV, M4A, FLAC, etc.) for batch processing with full quote detection and export options.

### 🎙️ Live Transcription
Real-time microphone capture with:
- Draft captions (<2 seconds)
- Verified updates with quote detection (<5 seconds)
- Gurmukhi/Roman toggle

### 🎵 Shabad Mode
Specialized kirtan transcription that:
- Tracks the current shabad being sung
- Predicts the next line
- Suggests **similar pramans** (supporting verses)
- Suggests **contrasting pramans** (different perspectives)

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone <repository-url>
cd GurbaniTranscription
docker-compose up --build
# Open http://localhost:5000
```

### Manual

```bash
# Install FFmpeg first (brew install ffmpeg / apt install ffmpeg)
git clone <repository-url>
cd GurbaniTranscription
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

---

## 🔧 Configuration

Key settings via environment variables:

```bash
# ASR
WHISPER_MODEL_SIZE=large          # tiny, base, small, medium, large
ASR_PRIMARY_PROVIDER=whisper      # whisper, indicconformer, wav2vec2

# Domain
DOMAIN_MODE=sggs                  # sggs, dasam, generic
STRICT_GURMUKHI=true              # Enforce Gurmukhi-only output

# Quote Detection
QUOTE_MATCH_CONFIDENCE_THRESHOLD=0.90
ENABLE_GURBANI_PROMPTING=true
ENABLE_NGRAM_RESCORING=true
```

See `config.py` for all options.

---

## 📡 API

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main app |
| `GET` | `/live` | Live transcription |
| `GET` | `/shabad` | Shabad mode |
| `POST` | `/upload` | Upload audio |
| `POST` | `/transcribe-v2` | Transcribe with multi-ASR |
| `GET` | `/download/<file>` | Download transcription |
| `POST` | `/api/praman/similar` | Get similar pramans |
| `POST` | `/api/praman/dissimilar` | Get contrasting pramans |

### WebSocket Events

**Client → Server:** `audio_chunk`, `shabad_audio_chunk`, `shabad_start`/`shabad_stop`

**Server → Client:** `draft_caption`, `verified_update`, `shabad_update`, `praman_suggestions`

---

## 💻 CLI

```bash
# Basic
python -m cli.transcribe audio.wav

# With options
python -m cli.transcribe audio.mp3 --model indicconformer --mode sggs --strict-gurmukhi --out json

# List providers
python -m cli.transcribe --list-providers
```

---

## 🏗️ Project Structure

```
GurbaniTranscription/
├── app.py                 # Flask server
├── config.py              # Configuration
├── core/orchestrator.py   # Main pipeline
├── asr/                   # ASR engines (Whisper, IndicConformer, Wav2Vec2)
├── quotes/                # Gurbani quote detection & matching
├── scripture/             # SGGS & Dasam Granth databases
├── services/              # VAD, language ID, script conversion
├── post/                  # Post-processing & formatting
├── exports/               # Export formats (JSON, DOCX, PDF, etc.)
├── ui/                    # WebSocket server
├── cli/                   # Command-line interface
├── static/                # CSS, JS, logo
├── templates/             # HTML templates
└── tests/                 # Test suite
```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

---

## 📋 Requirements

- **Python 3.11+**
- **FFmpeg** (audio processing)
- **8GB+ RAM** (16GB recommended)
- **NVIDIA GPU** (optional, recommended)

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| FFmpeg errors | Verify: `ffmpeg -version` |
| Slow processing | Use GPU, or reduce model size |
| Wrong script output | Enable `STRICT_GURMUKHI=true` |
| Quote detection fails | Check `data/sggs.sqlite` exists |

---

<div align="center">

**Built with ❤️ for the Sikh community**

*ਸ਼ਬਦ ਗੁਰੂ ਸੁਰਤਿ ਧੁਨਿ ਚੇਲਾ*

</div>
