# Comprehensive Onboarding Guide

## Katha Transcription System - Feature Guide

Welcome to the Katha Transcription System! This guide provides a comprehensive walkthrough of every feature, explaining **what** it does, **why** it exists, and **how** to use it effectively.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Feature Guide](#feature-guide)
   - [File Transcription](#1-file-transcription)
   - [Live Transcription Mode](#2-live-transcription-mode)
   - [Shabad Mode (Praman Assistant)](#3-shabad-mode-praman-assistant)
   - [Multi-ASR Ensemble System](#4-multi-asr-ensemble-system)
   - [Canonical Quote Detection](#5-canonical-quote-detection--replacement)
   - [Script Conversion](#6-script-conversion-system)
   - [Domain Language Prioritization](#7-domain-language-prioritization)
   - [Audio Denoising](#8-audio-denoising)
   - [Export Formats](#9-export-formats)
   - [CLI Tool](#10-cli-tool)
5. [Configuration Reference](#configuration-reference)
6. [API Endpoints](#api-endpoints)
7. [Troubleshooting](#troubleshooting)
8. [Glossary](#glossary)

---

## Introduction

The Katha Transcription System is a production-grade automatic speech recognition (ASR) system specifically designed for transcribing **Katha** (Sikh religious discourse) with maximum accuracy. It combines multiple state-of-the-art ASR engines, intelligent fusion algorithms, and canonical Gurbani quote detection.

### Who is this for?

- **Gurdwara staff** transcribing weekly katha recordings
- **Researchers** archiving historical kirtan and katha
- **Content creators** adding subtitles to Sikh religious content
- **Developers** building applications for the Sikh community

---

## Quick Start

### Option 1: Web Interface (Recommended for beginners)

1. Start the server:
   ```bash
   python app.py
   ```

2. Open your browser to `http://localhost:5000`

3. Upload an audio file and click "Process"

### Option 2: Command Line

```bash
# Basic transcription
python -m cli.transcribe audio.mp3

# With specific provider and output format
python -m cli.transcribe audio.wav --model indicconformer --out srt
```

### Option 3: Docker

```bash
docker-compose up --build
# Then open http://localhost:5000
```

---

## Core Concepts

### The Processing Pipeline

Understanding the pipeline helps you configure the system effectively:

```
Audio File
    │
    ▼
┌─────────────────┐
│  Audio Denoising │  (Optional) Remove background noise
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VAD Chunking   │  Split audio into speech segments
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Language ID     │  Detect language of each chunk
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Multi-ASR       │  Run multiple ASR engines
│ Ensemble        │  (Whisper, Indic, English)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fusion Layer    │  Merge results intelligently
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Script          │  Convert to Gurmukhi +
│ Conversion      │  Roman transliteration
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Quote Detection │  Find & replace Gurbani quotes
│ & Replacement   │  with canonical text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Document        │  Structure output with
│ Formatting      │  sections & metadata
└────────┬────────┘
         │
         ▼
    Output Files
    (TXT, JSON, PDF, etc.)
```

### Key Terminology

| Term | Description |
|------|-------------|
| **ASR** | Automatic Speech Recognition - converting audio to text |
| **VAD** | Voice Activity Detection - finding speech in audio |
| **Fusion** | Combining results from multiple ASR engines |
| **Canonical Text** | The official, correct text from scripture databases |
| **Praman** | Scripture reference used as evidence/support |
| **Shabad** | A hymn/poem from Gurbani |

---

## Feature Guide

### 1. File Transcription

#### What
Upload audio/video files and get accurate Gurmukhi transcriptions with Roman transliteration.

#### Why
The primary use case - converting recorded katha, kirtan, or lectures into text for archiving, searching, or subtitle creation.

#### How

**Web Interface:**
1. Navigate to `http://localhost:5000`
2. Drag and drop files or click to select
3. Choose processing mode:
   - **One-by-One**: Process files individually with manual control
   - **Batch**: Process all files automatically
4. Click "Process" and view results
5. Download in your preferred format

**Supported Formats:**
- Audio: MP3, WAV, M4A, FLAC, OGG, WebM
- Video: MP4, AVI, MOV

**Advanced Options (expand panel):**
- Enable/disable denoising
- Adjust VAD aggressiveness (0-3)
- Set chunk duration limits
- Enable parallel processing

---

### 2. Live Transcription Mode

#### What
Real-time transcription via microphone with WebSocket streaming. Provides:
- **Draft captions** (<2 second latency) - immediate ASR output
- **Verified updates** (<5 second latency) - after quote detection and refinement

#### Why
Enable live captioning during:
- Gurdwara programs and katha
- Online streaming of kirtan
- Recording sessions where you want to see text in real-time

#### How

1. Navigate to `/live` endpoint
2. Grant microphone permission when prompted
3. Click **"Start Recording"**
4. Speak and watch transcription appear in real-time
5. Toggle between Gurmukhi and Roman display
6. Verified segments show quote matches with Ang numbers

**Key Features:**
- **Draft vs Verified**: Drafts appear immediately; verified updates refine them with quote matching
- **Quote Highlighting**: Detected Gurbani quotes show source metadata (Ang, Raag, Author)
- **Script Toggle**: Switch between Gurmukhi and Roman display

---

### 3. Shabad Mode (Praman Assistant)

#### What
A specialized mode for kirtan transcription that:
- Tracks the current shabad being sung
- Predicts the next line
- Suggests semantically similar pramans (supporting verses)
- Suggests thematically contrasting pramans

#### Why
Helps kirtanis and listeners:
- Follow along with the shabad
- Find related verses for vichar (discussion)
- Discover thematically contrasting perspectives from Gurbani

#### How

1. Navigate to `/shabad` endpoint
2. Start recording kirtan
3. The system will:
   - Detect which shabad is being sung
   - Show the current and next lines
   - Display similar pramans (verses with related themes)
   - Display dissimilar pramans (verses with contrasting themes)

**Understanding Praman Types:**

| Type | Purpose | Example Use |
|------|---------|-------------|
| **Similar** | Verses with related themes/vocabulary | Finding supporting evidence |
| **Dissimilar** | Verses with contrasting themes | Understanding different perspectives |

**Semantic Categories:**
The system understands Gurbani themes:
- Divine Praise (ਹਰਿ, ਪ੍ਰਭ, ਗੋਬਿੰਦ)
- Human Suffering (ਦੁਖ, ਕਸ਼ਟ, ਪੀੜ)
- Liberation (ਮੁਕਤਿ, ਮੋਖ, ਤਰਣ)
- Worldly Attachment (ਮਾਇਆ, ਮੋਹ, ਲੋਭ)
- Devotion (ਭਗਤਿ, ਪ੍ਰੇਮ, ਸੇਵਾ)
- Guru's Grace (ਗੁਰ, ਸਤਿਗੁਰ, ਕਿਰਪਾ)

---

### 4. Multi-ASR Ensemble System

#### What
Combines multiple ASR engines and fuses their results:

| Provider | Best For | Timestamps |
|----------|----------|------------|
| **Whisper** (default) | General multilingual, best all-around | Word-level |
| **IndicConformer** | Indian languages, native Gurmukhi | Segment |
| **Wav2Vec2** | Direct Punjabi transcription | Limited |
| **Commercial** | High accuracy (API-based) | Word-level |

#### Why
Different engines excel at different content:
- Whisper handles mixed languages well
- IndicConformer better understands Gurmukhi phonetics
- Fusion combines strengths and reduces errors

#### How

**Via Settings Page (`/settings`):**
1. Select Primary Provider
2. Optionally select Fallback Provider
3. Configure provider-specific options

**Via CLI:**
```bash
# Use specific provider
python -m cli.transcribe audio.mp3 --model indicconformer

# List available providers
python -m cli.transcribe --list-providers
```

**Via Environment Variables:**
```bash
export ASR_PRIMARY_PROVIDER=indicconformer
export ASR_FALLBACK_PROVIDER=whisper
```

**Fusion Behavior:**
1. ASR-A (primary) runs immediately
2. Additional engines run based on detected language route
3. Results are fused using voting and confidence weighting
4. If confidence is low, re-decode with different parameters

---

### 5. Canonical Quote Detection & Replacement

#### What
Automatically detects when the speaker quotes Gurbani and:
1. Matches it against SGGS and Dasam Granth databases
2. Replaces transcribed text with canonical (correct) text
3. Adds metadata: Ang number, Raag, Author, Line ID

#### Why
- Ensures accuracy of scripture quotes (ASR may mishear archaic vocabulary)
- Provides citation information for references
- Distinguishes between katha (explanation) and Gurbani (scripture)

#### How

**Automatic during transcription:**
- System detects potential quotes based on:
  - Language patterns (Sant Bhasha indicators)
  - N-gram matching against scripture database
  - Semantic similarity search (optional)

**Confidence Thresholds:**
| Confidence | Action |
|------------|--------|
| ≥ 0.95 | Auto-replace without review |
| 0.90-0.94 | Replace but flag for review |
| 0.70-0.89 | Show match but don't replace |
| < 0.70 | No action |

**Configuration:**
```bash
export QUOTE_MATCH_CONFIDENCE_THRESHOLD=0.90
export USE_EMBEDDING_SEARCH=true  # Enable semantic search
```

**Output Example:**
```json
{
  "type": "scripture_quote",
  "text": "ਸਤਿਗੁਰ ਪ੍ਰਸਾਦਿ",
  "quote_match": {
    "source": "SGGS",
    "ang": 1,
    "raag": "Mool Mantar",
    "author": "Guru Nanak Dev Ji",
    "confidence": 0.97
  }
}
```

---

### 6. Script Conversion System

#### What
Handles multiple scripts and provides consistent output:
- **Shahmukhi → Gurmukhi**: Converts Urdu-script Punjabi to Gurmukhi
- **Gurmukhi → Roman**: Generates romanized transliteration
- **Unicode Normalization**: Ensures consistent diacritic handling

#### Why
- Katha often includes Shahmukhi vocabulary
- Roman transliteration helps those learning to read Gurmukhi
- Consistent Unicode prevents display issues

#### How

**Automatic during transcription:**
The system automatically:
1. Detects the source script
2. Converts to Gurmukhi (primary output)
3. Generates Roman transliteration

**Output includes both scripts:**
```json
{
  "gurmukhi": "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ",
  "roman": "Waheguru Ji Ka Khalsa"
}
```

**Transliteration Schemes:**
```bash
export ROMAN_TRANSLITERATION_SCHEME=practical  # Default, simplified
# Options: practical, iso15919 (academic), iast (Sanskrit-based)
```

---

### 7. Domain Language Prioritization

#### What
Three specialized modes optimized for different scripture domains:

| Mode | Optimized For | Vocabulary Focus |
|------|---------------|------------------|
| **SGGS** (default) | Sri Guru Granth Sahib Ji | Sant Bhasha, Braj, Old Punjabi |
| **Dasam** | Dasam Granth | Braj, Sanskrit heavy |
| **Generic** | Modern Punjabi | Contemporary vocabulary |

#### Why
Different scriptures use different vocabulary patterns:
- SGGS contains Sant Bhasha (mixed language of saints)
- Dasam Granth has more Sanskrit influence
- Mode-specific optimizations improve accuracy

#### How

**Strict Gurmukhi Mode:**
When enabled, the system:
1. **Detects drift** - identifies non-Gurmukhi characters in output
2. **Enforces script lock** - removes/repairs non-Gurmukhi
3. **Applies corrections** - uses domain lexicon to fix common errors

**Configuration:**
```bash
# Via environment
export DOMAIN_MODE=sggs
export STRICT_GURMUKHI=true

# Via CLI
python -m cli.transcribe audio.mp3 --mode sggs --strict-gurmukhi
```

**Via Settings Page:**
1. Go to `/settings`
2. Find "Domain Settings" section
3. Select mode and strict Gurmukhi toggle

**Anti-Drift Thresholds:**
```bash
export SCRIPT_PURITY_THRESHOLD=0.95  # Min % Gurmukhi chars
export LATIN_RATIO_THRESHOLD=0.02    # Max % Latin chars
export OOV_RATIO_THRESHOLD=0.35      # Max % out-of-vocabulary
```

---

### 8. Audio Denoising

#### What
Removes background noise from audio before transcription:
- Multiple backends: noisereduce, Facebook denoiser, DeepFilterNet
- Configurable strength: light, medium, aggressive

#### Why
- Gurdwara recordings often have reverb, AC noise, crowd sounds
- Denoising significantly improves ASR accuracy on noisy audio
- Different backends suit different noise types

#### How

**Web Interface:**
1. Expand "Advanced Processing Options"
2. Enable "Audio Denoising"
3. Select backend and strength

**CLI:**
```bash
# Denoising is auto-enabled based on noise detection
export ENABLE_DENOISING=true
export DENOISE_STRENGTH=medium  # light, medium, aggressive
export DENOISE_BACKEND=noisereduce  # noisereduce, facebook, deepfilter
```

**Strength Guide:**
| Strength | Use When |
|----------|----------|
| **Light** | Minor background noise, well-recorded audio |
| **Medium** | Typical gurdwara recording with some reverb |
| **Aggressive** | Very noisy, outdoor, or low-quality recordings |

**Auto-Detection:**
The system can automatically enable denoising based on noise level:
```bash
export DENOISE_AUTO_ENABLE_THRESHOLD=0.4  # Enable if noise > 40%
```

---

### 9. Export Formats

#### What
Export transcriptions in multiple formats:

| Format | Extension | Best For |
|--------|-----------|----------|
| **TXT** | .txt | Simple text, copy-paste |
| **JSON** | .json | Programmatic access, full metadata |
| **Markdown** | .md | Documentation, websites |
| **HTML** | .html | Styled web viewing |
| **DOCX** | .docx | Microsoft Word, editing |
| **PDF** | .pdf | Printing, archiving |
| **SRT** | .srt | Video subtitles (CLI only) |

#### Why
Different use cases need different formats:
- JSON for API integration
- PDF for official archives
- SRT for video captioning

#### How

**Web Interface:**
After transcription, click the export button for your format.

**CLI:**
```bash
python -m cli.transcribe audio.mp3 --out srt
python -m cli.transcribe audio.mp3 --out json
```

**API:**
```bash
# Export existing transcription
GET /export/{filename}/pdf
GET /export/{filename}/docx
GET /export/{filename}/markdown
```

**JSON Structure:**
```json
{
  "title": "filename",
  "source_file": "audio.mp3",
  "created_at": "2024-01-20T10:30:00",
  "sections": [
    {
      "section_type": "opening_gurbani",
      "content": { "gurmukhi": "...", "ang": 1 },
      "start_time": 0.0,
      "end_time": 15.5
    }
  ],
  "metadata": {
    "total_segments": 42,
    "quotes_detected": 5
  }
}
```

---

### 10. CLI Tool

#### What
Full command-line interface for automation and batch processing.

#### Why
- Automate transcription workflows
- Process many files efficiently
- Integrate with scripts and pipelines
- Server-side processing without GUI

#### How

**Basic Usage:**
```bash
# Single file
python -m cli.transcribe audio.mp3

# Directory (batch)
python -m cli.transcribe ./audio_folder/

# With options
python -m cli.transcribe audio.wav \
    --model indicconformer \
    --out srt \
    --language pa \
    --mode sggs \
    --strict-gurmukhi
```

**All Options:**
```
Options:
  --model, -m       ASR provider: whisper, indicconformer, wav2vec2, commercial
  --out, -o         Output format: json, txt, srt
  --language, -l    Language hint (default: pa for Punjabi)
  --timestamps      Include timestamps in output (default: true)
  --output-dir, -d  Output directory
  --mode            Domain mode: sggs, dasam, generic
  --strict-gurmukhi Enforce Gurmukhi-only output
  --list-providers  List available ASR providers
  --verbose, -v     Enable verbose output
```

**Examples:**
```bash
# List available providers
python -m cli.transcribe --list-providers

# Batch process with SRT output
python -m cli.transcribe ./recordings/ --out srt --output-dir ./subtitles/

# High-accuracy mode
python -m cli.transcribe lecture.mp3 \
    --model whisper \
    --mode sggs \
    --strict-gurmukhi \
    --gurbani-prompting \
    --ngram-rescoring
```

---

## Configuration Reference

### Environment Variables

```bash
# === ASR Configuration ===
ASR_PRIMARY_PROVIDER=whisper       # Primary ASR engine
ASR_FALLBACK_PROVIDER=indicconformer
WHISPER_MODEL_SIZE=large           # tiny, base, small, medium, large

# === Processing ===
ENABLE_DENOISING=false
DENOISE_BACKEND=noisereduce
DENOISE_STRENGTH=medium

# === Quote Detection ===
QUOTE_MATCH_CONFIDENCE_THRESHOLD=0.90
USE_EMBEDDING_SEARCH=false

# === Domain Settings ===
DOMAIN_MODE=sggs
STRICT_GURMUKHI=true
ENABLE_DOMAIN_CORRECTION=true

# === Server ===
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### config.py Settings

All settings can be configured in `config.py`. Key sections:
- Core Settings (paths, directories)
- ASR/Model Configuration
- Processing Pipeline (VAD, Language ID, Fusion)
- Scripture/Quote Detection
- Live Streaming
- Audio Processing
- Export/Output

---

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main transcription page |
| `GET` | `/live` | Live transcription page |
| `GET` | `/shabad` | Shabad mode page |
| `GET` | `/settings` | Settings page |
| `GET` | `/history` | Transcription history |
| `POST` | `/upload` | Upload audio file |
| `POST` | `/transcribe-v2` | Transcribe single file |
| `POST` | `/transcribe-batch` | Transcribe multiple files |
| `GET` | `/progress/{filename}` | Get transcription progress |
| `GET` | `/export/{filename}/{format}` | Export transcription |
| `GET` | `/api/providers` | List ASR providers |
| `GET/POST` | `/api/settings` | Get/set settings |

### WebSocket Events

**Client → Server:**
- `audio_chunk` - Send audio for live transcription
- `shabad_audio_chunk` - Send audio for shabad mode
- `shabad_start/stop` - Control shabad session

**Server → Client:**
- `draft_caption` - Immediate ASR result
- `verified_update` - Refined transcription with quotes
- `shabad_update` - Shabad line match
- `praman_suggestions` - Similar/dissimilar pramans

---

## Troubleshooting

### Common Issues

**1. "Orchestrator not available"**
- The ASR models are still loading (can take 1-2 minutes on first run)
- Check console for model download progress
- Ensure sufficient RAM (8GB minimum, 16GB recommended)

**2. Empty transcriptions**
- Audio may be too quiet - check audio levels
- Enable denoising for noisy files
- Try a different ASR provider

**3. Wrong script output (Hindi instead of Gurmukhi)**
- Enable strict Gurmukhi mode
- Set domain mode to `sggs`
- Check that SGGS database is present

**4. Slow processing**
- Use GPU if available (NVIDIA CUDA)
- Reduce model size: `WHISPER_MODEL_SIZE=medium`
- Enable parallel processing

**5. Quote detection not working**
- Ensure SGGS database exists at `data/sggs.sqlite`
- Check confidence threshold isn't too high
- Enable embedding search for better recall

### Logs

Check logs at `logs/transcription.log` for detailed error information.

---

## Glossary

| Term | Definition |
|------|------------|
| **Ang** | Page number in SGGS (1-1430) |
| **Bani** | Sacred composition/hymn |
| **Gurbani** | The sacred scriptures of Sikhi |
| **Katha** | Religious discourse/explanation |
| **Kirtan** | Musical recitation of Gurbani |
| **Praman** | Scripture reference used as evidence |
| **Raag** | Musical mode in which a shabad is composed |
| **Sant Bhasha** | Mixed language of medieval saints |
| **SGGS** | Sri Guru Granth Sahib Ji |
| **Shabad** | A hymn/composition from Gurbani |
| **VAD** | Voice Activity Detection |

---

## Getting Help

- **Issues**: Check the troubleshooting section above
- **Logs**: Review `logs/transcription.log`
- **Tests**: Run `python -m pytest tests/ -v` to verify installation

---

*Last updated: January 2026*

