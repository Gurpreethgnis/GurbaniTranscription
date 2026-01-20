"""
ASR-B: Indic-Tuned Whisper Automatic Speech Recognition.

This ASR engine uses a Whisper model fine-tuned for Indic languages
(Punjabi, Hindi, Braj) to provide better accuracy for Gurbani and
mixed-language Katha content.
"""
from typing import Optional
import config
from asr.base_asr import BaseASR, WHISPER_AVAILABLE

# Import WhisperModel for fallback loading
if WHISPER_AVAILABLE:
    from faster_whisper import WhisperModel


class ASRIndic(BaseASR):
    """
    ASR-B: Indic-tuned Whisper ASR engine.
    
    Optimized for Punjabi, Hindi, and Braj languages commonly found in Gurbani.
    Uses higher beam size for complex Indic vocabulary.
    """
    
    engine_name = "asr_b_indic"
    default_beam_size = 7  # Higher beam for Indic languages
    default_language = 'hi'  # Default to Hindi for better Indic coverage
    route_to_language = {
        'punjabi_speech': 'hi',  # Use Hindi for better Indic coverage
        'english_speech': 'en',
        'scripture_quote_likely': 'hi',  # Gurbani in Hindi/Braj/Sant Bhasha
        'mixed': 'hi'  # Default to Hindi for mixed Indic content
    }
    
    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize ASR-B Indic service.
        
        Args:
            model_size: Indic-tuned model identifier or Whisper model size
                       Defaults to config.ASR_B_MODEL or falls back to standard Whisper
        """
        self.fallback_model = getattr(config, 'ASR_B_FALLBACK_MODEL', 'large-v3')
        super().__init__(model_size)
    
    def _get_default_model_size(self) -> str:
        """Get the default model size from config."""
        return getattr(config, 'ASR_B_MODEL', None) or self.fallback_model
    
    def _load_model(self):
        """Load the Indic-tuned Whisper model with fallback."""
        compute_type = self._get_compute_type()
        
        # Check if this looks like a HuggingFace model identifier
        is_hf_model = self.model_size and self.model_size not in [
            'tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'
        ]
        
        if is_hf_model:
        # Try to load Indic-specific model first
            try:
                print(f"Loading {self.engine_name} (Indic-tuned): {self.model_size} on {self.device.upper()}")
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type,
                    cpu_threads=4 if self.device == "cpu" else 0
                )
                print(f"{self.engine_name} Indic-tuned model {self.model_size} loaded successfully")
                return
            except Exception as e:
                print(f"Warning: Failed to load Indic model {self.model_size}: {e}")
                print(f"Falling back to standard Whisper {self.fallback_model}")
                self.model_size = self.fallback_model
        
        # Fallback to standard Whisper
        super()._load_model()
