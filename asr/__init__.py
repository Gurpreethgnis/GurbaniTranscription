"""
ASR (Automatic Speech Recognition) module.

Provides multiple ASR engines for multi-engine transcription:
- BaseASR: Abstract base class for all ASR engines
- ASRWhisper (ASR-A): Primary Whisper engine (faster-whisper)
- ASRIndic (ASR-B): Indic-tuned Whisper engine
- ASREnglish (ASR-C): English-specific Whisper engine
- ASRIndicConformer: AI4Bharat IndicConformer for Indic languages
- ASRWav2Vec2: HuggingFace Wav2Vec2 Punjabi model
- ASRCommercial: Commercial API provider (ElevenLabs)
- ASRFusion: Multi-ASR fusion service
- ProviderRegistry: Provider management and selection
- GurbaniPromptBuilder: Context-aware prompts for Gurbani transcription
"""

from .base_asr import BaseASR
from .asr_whisper import ASRWhisper
from .asr_indic import ASRIndic
from .asr_english_fallback import ASREnglish
from .asr_fusion import ASRFusion
from .provider_registry import ProviderRegistry, ProviderType, get_registry
from .gurbani_prompt import GurbaniPromptBuilder, get_prompt_builder, get_gurbani_prompt

# Lazy imports for optional providers
def get_indicconformer():
    """Lazy import for IndicConformer provider."""
    from .asr_indicconformer import ASRIndicConformer
    return ASRIndicConformer

def get_wav2vec2():
    """Lazy import for Wav2Vec2 provider."""
    from .asr_wav2vec2 import ASRWav2Vec2
    return ASRWav2Vec2

def get_commercial():
    """Lazy import for Commercial provider."""
    from .asr_commercial import ASRCommercial
    return ASRCommercial

__all__ = [
    'BaseASR',
    'ASRWhisper',
    'ASRIndic',
    'ASREnglish',
    'ASRFusion',
    'ProviderRegistry',
    'ProviderType',
    'get_registry',
    'get_indicconformer',
    'get_wav2vec2',
    'get_commercial',
    'GurbaniPromptBuilder',
    'get_prompt_builder',
    'get_gurbani_prompt',
]
