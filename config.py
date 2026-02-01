"""
Configuration settings for Shabad Guru (ਸ਼ਬਦ ਗੁਰੂ)
Gurbani Transcription & Praman Discovery Platform

Organized into logical sections:
1. Core Settings (paths, directories)
2. ASR / Model Configuration
3. Processing Pipeline (VAD, Language ID, Fusion)
4. Scripture / Quote Detection
5. Live Streaming
6. Audio Processing (Denoising)
7. Export / Output
8. Evaluation
9. Server & Logging
"""
import os
from pathlib import Path

# ============================================
# CORE SETTINGS
# ============================================

# Base directory
BASE_DIR = Path(__file__).parent

# Directory structure
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TRANSCRIPTIONS_DIR = OUTPUT_DIR / "transcriptions"
JSON_DIR = OUTPUT_DIR / "json"
FORMATTED_DOCS_DIR = OUTPUT_DIR / "formatted"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "processed_files.json"
DATA_DIR = BASE_DIR / "data"

# Supported audio formats
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".avi", ".mov"}

# Processing limits
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
PROCESSING_TIMEOUT = 3600  # Timeout in seconds (1 hour)

# ============================================
# ASR / MODEL CONFIGURATION
# ============================================

# Dynamic GPU detection
def _detect_gpu():
    """Detect if CUDA GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

GPU_AVAILABLE = _detect_gpu()

# Primary Whisper model (ASR-A) - dynamic selection based on GPU availability
# Options: tiny, base, small, medium, large, large-v2, large-v3
_env_model = os.getenv("WHISPER_MODEL_SIZE")
if _env_model:
    WHISPER_MODEL_SIZE = _env_model  # Use environment variable if set
elif GPU_AVAILABLE:
    WHISPER_MODEL_SIZE = "large-v3"  # Best accuracy with GPU
else:
    WHISPER_MODEL_SIZE = "small"  # Good balance of speed/accuracy for CPU

# GPU enforcement - auto-detect if not explicitly set
_require_gpu_env = os.getenv("REQUIRE_GPU")
if _require_gpu_env is not None:
    REQUIRE_GPU = _require_gpu_env.lower() == "true"
else:
    REQUIRE_GPU = False  # Don't require GPU, allow CPU fallback

# Language hints (for better accuracy with Punjabi/Urdu)
LANGUAGE_HINTS = ["pa", "ur", "en"]  # Punjabi, Urdu, English

# ASR-B: Indic-tuned model
ASR_B_MODEL = "large-v3"  # Use large-v3 (excellent for Indic, already cached)
ASR_B_FALLBACK_MODEL = "large-v3"  # Fallback if Indic model unavailable

# ASR-C: English-optimized model
ASR_C_MODEL = "medium"  # English model (faster than large)
ASR_C_FORCE_LANGUAGE = "en"  # Always force English for ASR-C

# Parallel ASR execution
ASR_PARALLEL_EXECUTION = True  # Run ASR-B/C in parallel
ASR_PARALLEL_WORKERS = int(os.getenv("ASR_PARALLEL_WORKERS", "2"))
ASR_TIMEOUT_SECONDS = 60  # Per-engine timeout in seconds

# ============================================
# ASR PROVIDER SELECTION (Multi-Provider Support)
# ============================================

# Primary provider: whisper | indicconformer | wav2vec2 | commercial
ASR_PRIMARY_PROVIDER = os.getenv("ASR_PRIMARY_PROVIDER", "whisper")

# Fallback provider (used when primary fails or for ensemble)
ASR_FALLBACK_PROVIDER = os.getenv("ASR_FALLBACK_PROVIDER", "indicconformer")

# IndicConformer (AI4Bharat) settings
INDICCONFORMER_MODEL = os.getenv(
    "INDICCONFORMER_MODEL",
    "ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large"
)
INDICCONFORMER_LANGUAGE = os.getenv("INDICCONFORMER_LANGUAGE", "pa")  # pa, hi, etc.

# Wav2Vec2 Punjabi settings
WAV2VEC2_MODEL = os.getenv(
    "WAV2VEC2_MODEL",
    "Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10"
)

# Commercial Provider (ElevenLabs Scribe) - Optional
USE_COMMERCIAL = os.getenv("USE_COMMERCIAL", "false").lower() == "true"
COMMERCIAL_API_KEY = os.getenv("COMMERCIAL_API_KEY", "")
COMMERCIAL_PROVIDER = os.getenv("COMMERCIAL_PROVIDER", "elevenlabs")  # elevenlabs | other
COMMERCIAL_TIMEOUT = int(os.getenv("COMMERCIAL_TIMEOUT", "120"))  # API timeout in seconds

# Provider-specific settings storage path (for UI persistence)
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

# ============================================
# PROCESSING PIPELINE
# ============================================

# VAD (Voice Activity Detection) settings
VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive
VAD_MIN_CHUNK_DURATION = 1.0  # Minimum chunk duration in seconds
VAD_MAX_CHUNK_DURATION = 30.0  # Maximum chunk duration in seconds
VAD_OVERLAP_SECONDS = 0.5  # Overlap between chunks in seconds

# Language Identification settings
LANGID_PUNJABI_THRESHOLD = 0.6  # Confidence threshold for Punjabi detection (0.0-1.0)
LANGID_ENGLISH_THRESHOLD = 0.6  # Confidence threshold for English detection (0.0-1.0)

# Segment confidence threshold
SEGMENT_CONFIDENCE_THRESHOLD = 0.7  # Segments below this confidence will be flagged for review

# Multi-ASR Fusion Configuration
FUSION_AGREEMENT_THRESHOLD = 0.85  # Text similarity for "agreement" (0-1)
FUSION_CONFIDENCE_BOOST = 0.1  # Boost when engines agree (0-1)
FUSION_REDECODE_THRESHOLD = 0.6  # Trigger re-decode below this confidence (0-1)
FUSION_MAX_REDECODE_ATTEMPTS = 2  # Maximum re-decode attempts per segment

# Segment Reliability Configuration
SEGMENT_RETRY_ON_EMPTY = os.getenv("SEGMENT_RETRY_ON_EMPTY", "true").lower() == "true"
SEGMENT_MAX_RETRIES = int(os.getenv("SEGMENT_MAX_RETRIES", "2"))
SEGMENT_RETRY_BEAM_SIZE_MULTIPLIER = float(os.getenv("SEGMENT_RETRY_BEAM_SIZE_MULTIPLIER", "2.0"))

# Script Conversion Configuration
SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD = float(
    os.getenv("SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD", "0.7")
)
ROMAN_TRANSLITERATION_SCHEME = os.getenv("ROMAN_TRANSLITERATION_SCHEME", "practical")
# Options: "iso15919" (academic), "iast" (Sanskrit-based), "practical" (simplified)
ENABLE_DICTIONARY_LOOKUP = os.getenv("ENABLE_DICTIONARY_LOOKUP", "true").lower() == "true"
UNICODE_NORMALIZATION_FORM = os.getenv("UNICODE_NORMALIZATION_FORM", "NFC")
# Options: "NFC", "NFD", "NFKC", "NFKD"

# ============================================
# DOMAIN LANGUAGE SETTINGS (Gurbani Prioritization)
# ============================================

# Domain mode: sggs | dasam | generic
# - sggs: Optimized for Sri Guru Granth Sahib Ji (Sant Bhasha, Braj, Old Punjabi)
# - dasam: Optimized for Dasam Granth (Braj, Sanskrit heavy)
# - generic: Generic Punjabi mode (modern Punjabi base)
DOMAIN_MODE = os.getenv("DOMAIN_MODE", "sggs")

# Strict Gurmukhi enforcement - reject/repair non-Gurmukhi output
STRICT_GURMUKHI = os.getenv("STRICT_GURMUKHI", "true").lower() == "true"

# Anti-drift thresholds
# If output falls below these, re-decode or apply correction
SCRIPT_PURITY_THRESHOLD = float(os.getenv("SCRIPT_PURITY_THRESHOLD", "0.95"))  # Minimum % Gurmukhi chars
LATIN_RATIO_THRESHOLD = float(os.getenv("LATIN_RATIO_THRESHOLD", "0.02"))       # Maximum % Latin chars allowed
OOV_RATIO_THRESHOLD = float(os.getenv("OOV_RATIO_THRESHOLD", "0.35"))           # Maximum % out-of-vocabulary

# Domain correction settings
ENABLE_DOMAIN_CORRECTION = os.getenv("ENABLE_DOMAIN_CORRECTION", "true").lower() == "true"
MAX_EDIT_DISTANCE = int(os.getenv("MAX_EDIT_DISTANCE", "2"))  # Max Levenshtein distance for corrections

# Lexicon paths (built from SGGS/Dasam databases)
DOMAIN_LEXICON_PATH = DATA_DIR / "domain_lexicon.json"

# ============================================
# SGGS CORPUS ENHANCEMENT SETTINGS
# ============================================

# Enable Gurbani-specific prompting for Whisper
ENABLE_GURBANI_PROMPTING = os.getenv("ENABLE_GURBANI_PROMPTING", "true").lower() == "true"

# N-gram language model settings
ENABLE_NGRAM_RESCORING = os.getenv("ENABLE_NGRAM_RESCORING", "true").lower() == "true"
NGRAM_RESCORE_WEIGHT = float(os.getenv("NGRAM_RESCORE_WEIGHT", "0.3"))  # LM weight in interpolation
SGGS_NGRAM_MODEL_PATH = DATA_DIR / "sggs_ngram.pkl"

# Quote alignment settings
ENABLE_QUOTE_ALIGNMENT = os.getenv("ENABLE_QUOTE_ALIGNMENT", "true").lower() == "true"
QUOTE_ALIGNMENT_THRESHOLD = float(os.getenv("QUOTE_ALIGNMENT_THRESHOLD", "0.85"))  # Min confidence to snap

# ============================================
# SCRIPTURE / QUOTE DETECTION
# ============================================

# SGGS database path - supports both .db and .sqlite extensions
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
        SCRIPTURE_DB_PATH = sggs_db  # Default (will raise error when used)

# Dasam Granth database path
DASAM_DB_PATH = Path(os.getenv("DASAM_DB_PATH", str(DATA_DIR / "dasam.db")))

# Quote matching settings
QUOTE_MATCH_CONFIDENCE_THRESHOLD = float(os.getenv("QUOTE_MATCH_CONFIDENCE_THRESHOLD", "0.90"))
# Matches >= 0.90: auto-replace | 0.70-0.89: flag for review | < 0.70: no replacement

QUOTE_CANDIDATE_MIN_WORDS = int(os.getenv("QUOTE_CANDIDATE_MIN_WORDS", "3"))
NGRAM_SIZE = int(os.getenv("NGRAM_SIZE", "3"))

# Embedding-Based Semantic Search (Optional)
USE_EMBEDDING_SEARCH = os.getenv("USE_EMBEDDING_SEARCH", "false").lower() == "true"
EMBEDDING_INDEX_PATH = DATA_DIR / "vectors" / "scripture_index.faiss"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# ============================================
# LIVE STREAMING
# ============================================

LIVE_CHUNK_DURATION_MS = int(os.getenv("LIVE_CHUNK_DURATION_MS", "1000"))
LIVE_DRAFT_DELAY_MS = int(os.getenv("LIVE_DRAFT_DELAY_MS", "100"))
LIVE_VERIFIED_DELAY_S = float(os.getenv("LIVE_VERIFIED_DELAY_S", "2.0"))
WEBSOCKET_PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "25"))
WEBSOCKET_PING_TIMEOUT = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "120"))

# ============================================
# AUDIO PROCESSING (Denoising)
# ============================================

ENABLE_DENOISING = os.getenv("ENABLE_DENOISING", "false").lower() == "true"  # Opt-in for batch
DENOISE_STRENGTH = os.getenv("DENOISE_STRENGTH", "medium")  # "light", "medium", "aggressive"
DENOISE_BACKEND = os.getenv("DENOISE_BACKEND", "noisereduce")  # "noisereduce", "facebook", "deepfilter"
LIVE_DENOISE_ENABLED = os.getenv("LIVE_DENOISE_ENABLED", "false").lower() == "true"
DENOISE_SAMPLE_RATE = int(os.getenv("DENOISE_SAMPLE_RATE", "16000"))  # Standard for ASR
DENOISE_AUTO_ENABLE_THRESHOLD = float(os.getenv("DENOISE_AUTO_ENABLE_THRESHOLD", "0.4"))

# ============================================
# SHABAD MODE SETTINGS (Phase 15)
# ============================================

# Shabad mode denoising - more aggressive for kirtan with instruments
SHABAD_MODE_DENOISE_STRENGTH = os.getenv("SHABAD_MODE_DENOISE_STRENGTH", "aggressive")

# Default number of pramans to suggest
PRAMAN_DEFAULT_SIMILAR_COUNT = int(os.getenv("PRAMAN_DEFAULT_SIMILAR_COUNT", "5"))
PRAMAN_DEFAULT_DISSIMILAR_COUNT = int(os.getenv("PRAMAN_DEFAULT_DISSIMILAR_COUNT", "3"))

# Semantic embedding model for praman search
EMBEDDING_MODEL_SEMANTIC = os.getenv(
    "EMBEDDING_MODEL_SEMANTIC",
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# Semantic index path for praman search
SEMANTIC_INDEX_PATH = DATA_DIR / "vectors" / "semantic_praman_index.faiss"

# Shabad detection settings
SHABAD_MATCH_THRESHOLD = float(os.getenv("SHABAD_MATCH_THRESHOLD", "0.70"))
SHABAD_CONTEXT_WINDOW = int(os.getenv("SHABAD_CONTEXT_WINDOW", "5"))

# ============================================
# TRANSLATION SETTINGS
# ============================================

# Primary translation provider: google | azure | openai | libre
TRANSLATION_PRIMARY_PROVIDER = os.getenv("TRANSLATION_PRIMARY_PROVIDER", "google")

# Fallback translation provider (used when primary fails)
TRANSLATION_FALLBACK_PROVIDER = os.getenv("TRANSLATION_FALLBACK_PROVIDER", "libre")

# Translation API Keys (from environment variables)
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY", "")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "global")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LibreTranslate settings (open-source self-hosted option)
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com")
LIBRETRANSLATE_API_KEY = os.getenv("LIBRETRANSLATE_API_KEY", "")

# Translation caching settings
TRANSLATION_CACHE_ENABLED = os.getenv("TRANSLATION_CACHE_ENABLED", "true").lower() == "true"
TRANSLATION_USE_SGGS_ENGLISH = os.getenv("TRANSLATION_USE_SGGS_ENGLISH", "true").lower() == "true"

# Translation output directory
TRANSLATIONS_OUTPUT_DIR = OUTPUT_DIR / "translations"

# ============================================
# DOCUMENT FORMATTING / OUTPUT
# ============================================

OPENING_GURBANI_TIME_WINDOW = float(os.getenv("OPENING_GURBANI_TIME_WINDOW", "120.0"))
TOPIC_EXTRACTION_TIME_WINDOW = float(os.getenv("TOPIC_EXTRACTION_TIME_WINDOW", "300.0"))
FATEH_PATTERNS = [
    "waheguru ji ka khalsa",
    "waheguru ji ki fateh",
    "bole so nihal",
    "sat sri akal",
    "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ",
    "ਵਾਹਿਗੁਰੂ ਜੀ ਕੀ ਫਤਿਹ"
]

# ============================================
# EVALUATION
# ============================================

EVAL_GROUND_TRUTH_DIR = BASE_DIR / "eval" / "ground_truth"
EVAL_REPORTS_DIR = BASE_DIR / "eval" / "reports"
EVAL_WER_THRESHOLD = float(os.getenv("EVAL_WER_THRESHOLD", "0.15"))  # Target WER: 15%
EVAL_CER_THRESHOLD = float(os.getenv("EVAL_CER_THRESHOLD", "0.10"))  # Target CER: 10%

# ============================================
# SERVER & LOGGING
# ============================================

# Server configuration
HOST = os.getenv("FLASK_HOST", "0.0.0.0")  # Use 0.0.0.0 for Docker, 127.0.0.1 for local
PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"

# ============================================
# INITIALIZATION
# ============================================

# Create required directories
for directory in [
    UPLOAD_DIR,
    TRANSCRIPTIONS_DIR,
    JSON_DIR,
    FORMATTED_DOCS_DIR,
    TRANSLATIONS_OUTPUT_DIR,
    LOGS_DIR,
    DATA_DIR,
    EVAL_GROUND_TRUTH_DIR,
    EVAL_REPORTS_DIR
]:
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
