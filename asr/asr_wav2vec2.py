"""
ASR Wav2Vec2: HuggingFace Wav2Vec2 Punjabi Fine-tuned Model.

This provider uses a Wav2Vec2 model fine-tuned specifically for Punjabi
from HuggingFace, providing direct Punjabi ASR without translation.

Model: Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10 (or similar)
Framework: HuggingFace transformers + torch
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
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor, Wav2Vec2CTCTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers not available. Install with: pip install transformers")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    logger.warning("soundfile not available. Install with: pip install soundfile")


class ASRWav2Vec2:
    """
    Wav2Vec2 Punjabi ASR provider.
    
    Uses a Punjabi-specific fine-tuned Wav2Vec2 model for direct
    Gurmukhi script transcription without intermediate translation.
    
    Note: Limited timestamp support - provides single segment or
    basic word-level timing via CTC alignment.
    """
    
    engine_name = "wav2vec2"
    default_language = "pa"  # Punjabi
    supported_languages = ["pa"]  # Punjabi only
    
    # Known Punjabi Wav2Vec2 models
    known_models = [
        "Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10",
        "facebook/wav2vec2-large-xlsr-53-punjabi",
        "theainerd/Wav2Vec2-large-xlsr-hindi"  # Hindi fallback
    ]
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Wav2Vec2 Punjabi provider.
        
        Args:
            model_name: HuggingFace model identifier (defaults to config.WAV2VEC2_MODEL)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("torch is required for Wav2Vec2. Install with: pip install torch")
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required for Wav2Vec2. Install with: pip install transformers")
        if not SOUNDFILE_AVAILABLE:
            raise ImportError("soundfile is required for Wav2Vec2. Install with: pip install soundfile")
        
        self.model_name = model_name or getattr(
            config, 'WAV2VEC2_MODEL',
            'Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10'
        )
        self.device, self.device_name = detect_device()
        self.model = None
        self.processor = None
        self.sample_rate = 16000  # Standard for Wav2Vec2
        
        self._load_model()
    
    def _load_model(self):
        """Load the Wav2Vec2 model."""
        device_info = f"GPU ({self.device_name})" if self.device == "cuda" else "CPU"
        logger.info(f"Loading Wav2Vec2 model: {self.model_name} on {device_info}")
        
        try:
            # Load processor and model
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
            self.model = Wav2Vec2ForCTC.from_pretrained(self.model_name)
            
            # Move model to device
            if self.device == "cuda":
                self.model = self.model.cuda()
            
            self.model.eval()
            logger.info(f"Wav2Vec2 model {self.model_name} loaded successfully on {self.device.upper()}")
            
        except Exception as e:
            logger.error(f"Failed to load Wav2Vec2 model {self.model_name}: {e}")
            
            # Try fallback models
            for fallback_model in self.known_models:
                if fallback_model != self.model_name:
                    try:
                        logger.info(f"Trying fallback model: {fallback_model}")
                        self.processor = Wav2Vec2Processor.from_pretrained(fallback_model)
                        self.model = Wav2Vec2ForCTC.from_pretrained(fallback_model)
                        
                        if self.device == "cuda":
                            self.model = self.model.cuda()
                        
                        self.model.eval()
                        self.model_name = fallback_model
                        logger.info(f"Loaded fallback model: {fallback_model}")
                        return
                    except Exception as fallback_error:
                        logger.debug(f"Fallback {fallback_model} failed: {fallback_error}")
                        continue
            
            raise RuntimeError(f"Failed to load Wav2Vec2 model: {e}")
    
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
            language: Language code (only 'pa' supported)
            route: Route string (for compatibility with other providers)
        
        Returns:
            ASRResult with transcription
        """
        language = language or self.default_language
        
        # Load audio
        audio = self._load_audio(chunk.audio_path)
        
        # Transcribe
        text, confidence = self._transcribe(audio)
        
        # Create segment (Wav2Vec2 typically provides single segment)
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
    
    def _transcribe(self, audio: np.ndarray) -> tuple:
        """
        Transcribe audio using Wav2Vec2.
        
        Args:
            audio: Audio samples (mono, 16kHz)
        
        Returns:
            Tuple of (text, confidence)
        """
        with torch.no_grad():
            # Prepare input
            inputs = self.processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt",
                padding=True
            )
            
            # Move to device
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Get logits
            logits = self.model(**inputs).logits
            
            # Decode using CTC
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            
            # Calculate confidence from logits
            probs = torch.softmax(logits, dim=-1)
            max_probs = probs.max(dim=-1).values
            # Exclude padding tokens
            non_padding_mask = predicted_ids != self.processor.tokenizer.pad_token_id
            if non_padding_mask.any():
                confidence = max_probs[non_padding_mask].mean().item()
            else:
                confidence = max_probs.mean().item()
        
        return transcription, confidence
    
    def _transcribe_with_timestamps(self, audio: np.ndarray) -> tuple:
        """
        Transcribe audio with word-level timestamps using CTC alignment.
        
        This is experimental and may not work well with all models.
        
        Args:
            audio: Audio samples (mono, 16kHz)
        
        Returns:
            Tuple of (text, confidence, word_timestamps)
        """
        with torch.no_grad():
            inputs = self.processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt",
                padding=True
            )
            
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            logits = self.model(**inputs).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            
            # Get frame-level predictions
            probs = torch.softmax(logits, dim=-1)
            frame_predictions = predicted_ids[0].cpu().numpy()
            frame_probs = probs[0].max(dim=-1).values.cpu().numpy()
            
            # Simple word boundary detection based on blank token
            # This is a basic implementation - production would need better alignment
            words = []
            current_word = []
            word_start = 0
            
            blank_id = self.processor.tokenizer.pad_token_id or 0
            frame_duration = len(audio) / self.sample_rate / len(frame_predictions)
            
            for i, (token_id, prob) in enumerate(zip(frame_predictions, frame_probs)):
                if token_id == blank_id:
                    if current_word:
                        word_text = self.processor.tokenizer.decode(current_word)
                        if word_text.strip():
                            words.append({
                                "word": word_text.strip(),
                                "start": word_start * frame_duration,
                                "end": i * frame_duration,
                                "confidence": float(np.mean([frame_probs[j] for j in range(word_start, i)]))
                            })
                        current_word = []
                else:
                    if not current_word:
                        word_start = i
                    current_word.append(token_id)
            
            # Handle last word
            if current_word:
                word_text = self.processor.tokenizer.decode(current_word)
                if word_text.strip():
                    words.append({
                        "word": word_text.strip(),
                        "start": word_start * frame_duration,
                        "end": len(frame_predictions) * frame_duration,
                        "confidence": float(np.mean([frame_probs[j] for j in range(word_start, len(frame_predictions))]))
                    })
            
            full_text = self.processor.batch_decode(predicted_ids)[0]
            confidence = frame_probs.mean()
            
        return full_text, confidence, words
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        return_timestamps: bool = False
    ) -> ASRResult:
        """
        Transcribe a full audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code (only 'pa' supported)
            return_timestamps: If True, attempt to extract word timestamps
        
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
                
                text, confidence = self._transcribe(chunk_audio)
                
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
            if return_timestamps:
                text, confidence, word_timestamps = self._transcribe_with_timestamps(audio)
                # Convert word timestamps to segments
                segments = [
                    Segment(
                        start=w["start"],
                        end=w["end"],
                        text=w["word"],
                        confidence=w["confidence"],
                        language=language
                    )
                    for w in word_timestamps
                ]
            else:
                text, confidence = self._transcribe(audio)
                segments = [Segment(
                    start=0,
                    end=duration,
                    text=text.strip(),
                    confidence=confidence,
                    language=language
                )]
            
            return ASRResult(
                text=text.strip(),
                language=language,
                confidence=confidence,
                segments=segments,
                engine=self.engine_name
            )
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None and self.processor is not None
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return self.supported_languages.copy()

