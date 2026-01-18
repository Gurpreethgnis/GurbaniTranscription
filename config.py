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

# Phase 2: Multi-ASR Configuration
ASR_B_MODEL = "vasista22/whisper-hindi-large-v2"  # Indic-tuned model (HuggingFace identifier)
ASR_B_FALLBACK_MODEL = "large-v3"  # Fallback if Indic model unavailable
ASR_C_MODEL = "medium"  # English model (faster than large)
ASR_C_FORCE_LANGUAGE = "en"  # Always force English for ASR-C

# Fusion Configuration
FUSION_AGREEMENT_THRESHOLD = 0.85  # Text similarity for "agreement" (0-1)
FUSION_CONFIDENCE_BOOST = 0.1  # Boost when engines agree (0-1)
FUSION_REDECODE_THRESHOLD = 0.6  # Trigger re-decode below this confidence (0-1)
FUSION_MAX_REDECODE_ATTEMPTS = 2  # Maximum re-decode attempts per segment

# Hybrid Execution
ASR_PARALLEL_EXECUTION = True  # Run ASR-B/C in parallel
ASR_TIMEOUT_SECONDS = 60  # Per-engine timeout in seconds

# Server configuration
# Use 0.0.0.0 for Docker, 127.0.0.1 for local development
HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, TRANSCRIPTIONS_DIR, JSON_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Setup logging
import logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        *([logging.FileHandler(LOGS_DIR / "transcription.log")] if LOG_FILE_ENABLED else [])
    ]
)
