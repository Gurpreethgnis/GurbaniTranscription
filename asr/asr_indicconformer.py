"""
ASR IndicConformer: AI4Bharat's Multilingual Indic ASR.

This provider uses AI4Bharat's IndicConformer model, which is specifically
designed for Indian languages including Punjabi, Hindi, and other Indic scripts.

Model: ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large (or Punjabi variant)
Framework: HuggingFace transformers (alternative to NeMo for easier setup)
"""
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np

import config
from core.models import AudioChunk, ASRResult, Segment
from utils.device_utils import detect_device

logger = logging.getLogger(__name__)

# Try to import required dependencies
TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
SOUNDFILE_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("torch not available. Install with: pip install torch")

try:
    from transformers import (
        AutoProcessor,
        AutoModelForCTC,
        AutoModelForSpeechSeq2Seq,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers not available. Install with: pip install transformers")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    logger.warning("soundfile not available. Install with: pip install soundfile")


class ASRIndicConformer:
    """
    AI4Bharat IndicConformer ASR provider.
    
    Supports multiple Indic languages with native script output.
    Better accuracy for Punjabi/Hindi compared to general-purpose models.
    """
    
    engine_name = "indicconformer"
    default_language = "pa"  # Punjabi
    supported_languages = ["pa", "hi", "bn", "gu", "kn", "ml", "mr", "or", "ta", "te"]
    
    # Language code mapping for AI4Bharat models
    language_map = {
        "pa": "punjabi",
        "hi": "hindi",
        "bn": "bengali",
        "gu": "gujarati",
        "kn": "kannada",
        "ml": "malayalam",
        "mr": "marathi",
        "or": "odia",
        "ta": "tamil",
        "te": "telugu"
    }
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the IndicConformer provider.
        
        Args:
            model_name: HuggingFace model identifier (defaults to config.INDICCONFORMER_MODEL)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("torch is required for IndicConformer. Install with: pip install torch")
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required for IndicConformer. Install with: pip install transformers")
        if not SOUNDFILE_AVAILABLE:
            raise ImportError("soundfile is required for IndicConformer. Install with: pip install soundfile")
        
        self.model_name = model_name or getattr(
            config, 'INDICCONFORMER_MODEL',
            'ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large'
        )
        self.device, self.device_name = detect_device()
        self.model = None
        self.processor = None
        self.pipe = None
        self.sample_rate = 16000  # Standard for ASR
        
        self._load_model()
    
    def _load_model(self):
        """Load the IndicConformer model."""
        device_info = f"GPU ({self.device_name})" if self.device == "cuda" else "CPU"
        logger.info(f"Loading IndicConformer model: {self.model_name} on {device_info}")
        
        try:
            # Try to load as a CTC model first (most common for IndicConformer)
            try:
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self.model = AutoModelForCTC.from_pretrained(self.model_name)
                self._model_type = "ctc"
                logger.info(f"Loaded {self.model_name} as CTC model")
            except Exception as e:
                logger.debug(f"CTC loading failed: {e}, trying Seq2Seq...")
                # Try as Seq2Seq model
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self.model = AutoModelForSpeechSeq2Seq.from_pretrained(self.model_name)
                self._model_type = "seq2seq"
                logger.info(f"Loaded {self.model_name} as Seq2Seq model")
            
            # Move model to device
            if self.device == "cuda":
                self.model = self.model.cuda()
            
            self.model.eval()
            logger.info(f"IndicConformer model loaded successfully on {self.device.upper()}")
            
        except Exception as e:
            logger.error(f"Failed to load IndicConformer model: {e}")
            # Try using pipeline as fallback
            try:
                logger.info("Attempting to load via pipeline...")
                self.pipe = pipeline(
                    "automatic-speech-recognition",
                    model=self.model_name,
                    device=0 if self.device == "cuda" else -1
                )
                self._model_type = "pipeline"
                logger.info("IndicConformer loaded via pipeline")
            except Exception as pipe_error:
                logger.error(f"Pipeline loading also failed: {pipe_error}")
                raise RuntimeError(f"Failed to load IndicConformer model: {e}")
    
    def _load_audio(self, audio_path: Path) -> np.ndarray:
        """
        Load and preprocess audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Audio samples as numpy array (mono, 16kHz)
        """
        # Load audio using soundfile
        audio, sr = sf.read(str(audio_path))
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Resample to 16kHz if needed
        if sr != self.sample_rate:
            try:
                from scipy import signal
                num_samples = int(len(audio) * self.sample_rate / sr)
                audio = signal.resample(audio, num_samples)
            except ImportError:
                logger.warning("scipy not available for resampling, using simple decimation")
                ratio = self.sample_rate / sr
                indices = np.arange(0, len(audio), 1/ratio).astype(int)
                indices = indices[indices < len(audio)]
                audio = audio[indices]
        
        return audio.astype(np.float32)
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code (pa, hi, etc.)
            route: Route string (for compatibility with other providers)
        
        Returns:
            ASRResult with transcription
        """
        language = language or self.default_language
        
        # Load audio
        audio = self._load_audio(chunk.audio_path)
        
        # Transcribe based on model type
        if self.pipe is not None:
            # Using pipeline
            result = self.pipe(audio)
            text = result.get("text", "")
            confidence = 0.8  # Pipeline doesn't provide confidence
        else:
            # Using direct model inference
            text, confidence = self._transcribe_direct(audio, language)
        
        # Create segment
        segment = Segment(
            start=0,
            end=chunk.duration,
            text=text.strip(),
            confidence=confidence,
            language=language
        )
        
        return ASRResult(
            text=text.strip(),
            language=language,
            confidence=confidence,
            segments=[segment],
            engine=self.engine_name
        )
    
    def _transcribe_direct(
        self,
        audio: np.ndarray,
        language: str
    ) -> tuple:
        """
        Transcribe using direct model inference.
        
        Args:
            audio: Audio samples
            language: Language code
        
        Returns:
            Tuple of (text, confidence)
        """
        with torch.no_grad():
            # Prepare input features
            inputs = self.processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt"
            )
            
            # Move to device
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            if self._model_type == "ctc":
                # CTC inference
                logits = self.model(**inputs).logits
                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = self.processor.batch_decode(predicted_ids)[0]
                
                # Calculate confidence from logits
                probs = torch.softmax(logits, dim=-1)
                max_probs = probs.max(dim=-1).values
                confidence = max_probs.mean().item()
                
            else:
                # Seq2Seq inference
                generated_ids = self.model.generate(
                    inputs["input_features"] if "input_features" in inputs else inputs["input_values"],
                    max_new_tokens=256
                )
                transcription = self.processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )[0]
                confidence = 0.8  # Seq2Seq doesn't easily provide confidence
        
        return transcription, confidence
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code (pa, hi, etc.)
        
        Returns:
            ASRResult with transcription
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        language = language or self.default_language
        
        # Load audio
        audio = self._load_audio(audio_path)
        duration = len(audio) / self.sample_rate
        
        # For long audio, split into chunks
        max_chunk_seconds = 30
        max_chunk_samples = max_chunk_seconds * self.sample_rate
        
        if len(audio) > max_chunk_samples:
            segments = []
            full_text = ""
            
            # Process in chunks
            for start_sample in range(0, len(audio), max_chunk_samples):
                end_sample = min(start_sample + max_chunk_samples, len(audio))
                chunk_audio = audio[start_sample:end_sample]
                
                start_time = start_sample / self.sample_rate
                end_time = end_sample / self.sample_rate
                
                if self.pipe is not None:
                    result = self.pipe(chunk_audio)
                    text = result.get("text", "")
                    confidence = 0.8
                else:
                    text, confidence = self._transcribe_direct(chunk_audio, language)
                
                if text.strip():
                    segments.append(Segment(
                        start=start_time,
                        end=end_time,
                        text=text.strip(),
                        confidence=confidence,
                        language=language
                    ))
                    full_text += text + " "
            
            overall_confidence = (
                sum(seg.confidence for seg in segments) / len(segments)
                if segments else 0.0
            )
            
            return ASRResult(
                text=full_text.strip(),
                language=language,
                confidence=overall_confidence,
                segments=segments,
                engine=self.engine_name
            )
        else:
            # Single chunk processing
            if self.pipe is not None:
                result = self.pipe(audio)
                text = result.get("text", "")
                confidence = 0.8
            else:
                text, confidence = self._transcribe_direct(audio, language)
            
            segment = Segment(
                start=0,
                end=duration,
                text=text.strip(),
                confidence=confidence,
                language=language
            )
            
            return ASRResult(
                text=text.strip(),
                language=language,
                confidence=confidence,
                segments=[segment],
                engine=self.engine_name
            )
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None or self.pipe is not None
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return self.supported_languages.copy()

