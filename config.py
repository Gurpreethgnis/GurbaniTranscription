"""
Configuration settings for the audio transcription application.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Directories
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TRANSCRIPTIONS_DIR = OUTPUT_DIR / "transcriptions"
JSON_DIR = OUTPUT_DIR / "json"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "processed_files.json"

# Whisper model configuration
WHISPER_MODEL_SIZE = "large"  # Options: tiny, base, small, medium, large
# Using 'large' for best accuracy with Punjabi/Urdu and mixed languages
# With 12GB GPU VRAM, 'large' model fits comfortably (~1.5GB)

# GPU enforcement
# Set to True to prevent CPU fallback for ASR.
REQUIRE_GPU = os.getenv("REQUIRE_GPU", "true").lower() == "true"

# Supported audio formats
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".avi", ".mov"}

# Language hints (for better accuracy with Punjabi/Urdu)
LANGUAGE_HINTS = ["pa", "ur", "en"]  # Punjabi, Urdu, English

# Processing settings
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
PROCESSING_TIMEOUT = 3600  # Timeout in seconds (1 hour)

# VAD (Voice Activity Detection) settings
VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive (default: 2)
VAD_MIN_CHUNK_DURATION = 1.0  # Minimum chunk duration in seconds
VAD_MAX_CHUNK_DURATION = 30.0  # Maximum chunk duration in seconds
VAD_OVERLAP_SECONDS = 0.5  # Overlap between chunks in seconds

# Language Identification settings
LANGID_PUNJABI_THRESHOLD = 0.6  # Confidence threshold for Punjabi detection (0.0-1.0)
LANGID_ENGLISH_THRESHOLD = 0.6  # Confidence threshold for English detection (0.0-1.0)

# Segment confidence threshold
SEGMENT_CONFIDENCE_THRESHOLD = 0.7  # Segments below this confidence will be flagged for review

# Server configuration
# Use 0.0.0.0 for Docker, 127.0.0.1 for local development
HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, TRANSCRIPTIONS_DIR, JSON_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
