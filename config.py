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

# Phase 3: Script Conversion Configuration
# Confidence threshold for script conversion (0.0-1.0)
# Segments below this threshold will be flagged for review
SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD = float(
    os.getenv("SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD", "0.7")
)

# Roman transliteration scheme
# Options: "iso15919" (academic), "iast" (Sanskrit-based), "practical" (simplified)
ROMAN_TRANSLITERATION_SCHEME = os.getenv("ROMAN_TRANSLITERATION_SCHEME", "practical")

# Enable dictionary lookup for common words (improves accuracy)
ENABLE_DICTIONARY_LOOKUP = os.getenv("ENABLE_DICTIONARY_LOOKUP", "true").lower() == "true"

# Unicode normalization form
# Options: "NFC" (Canonical Composition), "NFD" (Canonical Decomposition),
#          "NFKC" (Compatibility Composition), "NFKD" (Compatibility Decomposition)
UNICODE_NORMALIZATION_FORM = os.getenv("UNICODE_NORMALIZATION_FORM", "NFC")

# Phase 4: Scripture Services + Quote Detection Configuration
# Paths to scripture databases
DATA_DIR = BASE_DIR / "data"

# SGGS database path - supports both .db and .sqlite extensions
# Can be overridden with SCRIPTURE_DB_PATH environment variable
_scripture_db_path = os.getenv("SCRIPTURE_DB_PATH")
if _scripture_db_path:
    SCRIPTURE_DB_PATH = Path(_scripture_db_path)
else:
    # Try .sqlite first (common for ShabadOS), then .db
    sggs_sqlite = DATA_DIR / "sggs.sqlite"
    sggs_db = DATA_DIR / "sggs.db"
    if sggs_sqlite.exists():
        SCRIPTURE_DB_PATH = sggs_sqlite
    elif sggs_db.exists():
        SCRIPTURE_DB_PATH = sggs_db
    else:
        # Default to .db if neither exists (will raise error when used)
        SCRIPTURE_DB_PATH = sggs_db

# Dasam Granth database path
DASAM_DB_PATH = Path(os.getenv("DASAM_DB_PATH", str(DATA_DIR / "dasam.db")))

# Quote matching confidence threshold (0.0-1.0)
# Matches with confidence >= this threshold will be auto-replaced with canonical text
# Matches with confidence 0.70-0.89 will be flagged for review
# Matches with confidence < 0.70 will not be replaced
QUOTE_MATCH_CONFIDENCE_THRESHOLD = float(
    os.getenv("QUOTE_MATCH_CONFIDENCE_THRESHOLD", "0.90")
)

# Quote candidate detection settings
QUOTE_CANDIDATE_MIN_WORDS = int(
    os.getenv("QUOTE_CANDIDATE_MIN_WORDS", "3")
)  # Minimum words to consider as quote candidate

# N-gram size for fast fuzzy search in scripture database
NGRAM_SIZE = int(os.getenv("NGRAM_SIZE", "3"))  # Size of n-grams for indexing

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, TRANSCRIPTIONS_DIR, JSON_DIR, LOGS_DIR, DATA_DIR]:
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
