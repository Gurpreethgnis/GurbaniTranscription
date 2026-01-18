# Audio Transcription Application

A web-based application for transcribing audio files using locally hosted Whisper models. Optimized for Punjabi, Urdu, and mixed-language audio files.

## Features

- **Multi-file Processing**: Select and process multiple audio files
- **Two Processing Modes**: 
  - One-by-one: Process files individually with manual control
  - Batch: Process all files automatically
- **Multiple Output Formats**: 
  - Plain text files (.txt)
  - JSON files with metadata (.json)
- **Processing Log**: Track all processed files with timestamps and status
- **Resume Support**: Skip already processed files automatically
- **Language Detection**: Automatic detection of Punjabi, Urdu, and other languages
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
├── app.py                 # Flask backend server
├── whisper_service.py     # Whisper model wrapper
├── file_manager.py        # File operations and logging
├── config.py              # Configuration settings
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── static/
│   ├── css/
│   │   └── style.css      # Application styles
│   └── js/
│       └── main.js        # Frontend JavaScript
├── templates/
│   └── index.html         # Main UI
├── uploads/               # Temporary upload directory
├── outputs/               # Generated outputs
│   ├── transcriptions/    # Text files
│   └── json/             # JSON files
├── logs/
│   └── processed_files.json  # Processing log
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## API Endpoints

- `GET /` - Main application page
- `GET /status` - Server and model status
- `POST /upload` - Upload audio file
- `POST /transcribe` - Transcribe single file
- `POST /transcribe-batch` - Transcribe multiple files
- `GET /log` - Get processing log
- `GET /download/<filename>` - Download transcription file

## Output Files

### Text Files (`outputs/transcriptions/`)
Plain text files containing the transcription.

### JSON Files (`outputs/json/`)
Structured data with:
- `filename`: Original filename
- `transcription`: Transcription text
- `timestamp`: Processing timestamp
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

## Notes

- First run will download the Whisper model (can take a few minutes)
- Models are cached in `~/.cache/whisper/` (local) or Docker volume (Docker)
- Large audio files may take significant time to process
- Processing time depends on model size and hardware
