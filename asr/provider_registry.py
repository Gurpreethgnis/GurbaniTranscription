"""
ASR Provider Registry for managing multiple ASR providers.

This module provides a centralized registry for instantiating and managing
different ASR providers (Whisper, IndicConformer, Wav2Vec2, Commercial).
"""
import logging
from typing import Dict, Optional, List, Type, Any
from enum import Enum
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Enumeration of available ASR provider types."""
    WHISPER = "whisper"
    INDICCONFORMER = "indicconformer"
    WAV2VEC2 = "wav2vec2"
    COMMERCIAL = "commercial"


class ProviderCapabilities:
    """Describes the capabilities of an ASR provider."""
    
    def __init__(
        self,
        name: str,
        provider_type: ProviderType,
        supports_timestamps: bool = True,
        supports_word_timestamps: bool = False,
        supported_languages: List[str] = None,
        requires_api_key: bool = False,
        is_available: bool = True,
        model_info: Dict[str, Any] = None
    ):
        self.name = name
        self.provider_type = provider_type
        self.supports_timestamps = supports_timestamps
        self.supports_word_timestamps = supports_word_timestamps
        self.supported_languages = supported_languages or ["pa", "hi", "en"]
        self.requires_api_key = requires_api_key
        self.is_available = is_available
        self.model_info = model_info or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "supports_timestamps": self.supports_timestamps,
            "supports_word_timestamps": self.supports_word_timestamps,
            "supported_languages": self.supported_languages,
            "requires_api_key": self.requires_api_key,
            "is_available": self.is_available,
            "model_info": self.model_info
        }


class ProviderRegistry:
    """
    Registry for ASR providers.
    
    Manages instantiation, caching, and selection of ASR providers.
    Supports lazy loading to avoid loading all models at startup.
    """
    
    _instance = None
    _providers: Dict[str, Any] = {}
    _capabilities: Dict[str, ProviderCapabilities] = {}
    
    def __new__(cls):
        """Singleton pattern for provider registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            import threading
            cls._instance._lock = threading.Lock()
        return cls._instance
    
    def __init__(self):
        """Initialize the provider registry."""
        if self._initialized:
            return
        
        self._providers = {}
        self._capabilities = {}
        self._register_capabilities()
        self._initialized = True
        logger.info("ProviderRegistry initialized")
    
    def _register_capabilities(self):
        """Register capabilities for all known providers."""
        # Whisper (faster-whisper)
        self._capabilities[ProviderType.WHISPER.value] = ProviderCapabilities(
            name="Whisper (faster-whisper)",
            provider_type=ProviderType.WHISPER,
            supports_timestamps=True,
            supports_word_timestamps=True,
            supported_languages=["pa", "hi", "ur", "en", "auto"],
            requires_api_key=False,
            is_available=self._check_whisper_available(),
            model_info={
                "default_model": getattr(config, 'WHISPER_MODEL_SIZE', 'large'),
                "available_models": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
            }
        )
        
        # IndicConformer (AI4Bharat)
        self._capabilities[ProviderType.INDICCONFORMER.value] = ProviderCapabilities(
            name="IndicConformer (AI4Bharat)",
            provider_type=ProviderType.INDICCONFORMER,
            supports_timestamps=True,
            supports_word_timestamps=False,
            supported_languages=["pa", "hi", "bn", "gu", "kn", "ml", "mr", "or", "ta", "te"],
            requires_api_key=False,
            is_available=self._check_indicconformer_available(),
            model_info={
                "default_model": getattr(config, 'INDICCONFORMER_MODEL', 'ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large'),
                "framework": "nemo/transformers"
            }
        )
        
        # Wav2Vec2 Punjabi
        self._capabilities[ProviderType.WAV2VEC2.value] = ProviderCapabilities(
            name="Wav2Vec2 Punjabi",
            provider_type=ProviderType.WAV2VEC2,
            supports_timestamps=False,  # Limited timestamp support
            supports_word_timestamps=False,
            supported_languages=["pa"],
            requires_api_key=False,
            is_available=self._check_wav2vec2_available(),
            model_info={
                "default_model": getattr(config, 'WAV2VEC2_MODEL', 'Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10'),
                "framework": "transformers"
            }
        )
        
        # Commercial (ElevenLabs)
        self._capabilities[ProviderType.COMMERCIAL.value] = ProviderCapabilities(
            name="ElevenLabs Scribe",
            provider_type=ProviderType.COMMERCIAL,
            supports_timestamps=True,
            supports_word_timestamps=True,
            supported_languages=["pa", "hi", "en", "auto"],
            requires_api_key=True,
            is_available=self._check_commercial_available(),
            model_info={
                "provider": getattr(config, 'COMMERCIAL_PROVIDER', 'elevenlabs'),
                "requires_network": True
            }
        )
    
    def _check_whisper_available(self) -> bool:
        """Check if faster-whisper is available."""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False
    
    def _check_indicconformer_available(self) -> bool:
        """Check if IndicConformer dependencies are available."""
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForCTC
            return True
        except ImportError:
            return False
    
    def _check_wav2vec2_available(self) -> bool:
        """Check if Wav2Vec2 dependencies are available."""
        try:
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            return True
        except ImportError:
            return False
    
    def _check_commercial_available(self) -> bool:
        """Check if commercial provider is configured and available."""
        use_commercial = getattr(config, 'USE_COMMERCIAL', False)
        api_key = getattr(config, 'COMMERCIAL_API_KEY', '')
        return use_commercial and bool(api_key)
    
    def get_provider(self, provider_type: str, force_reload: bool = False) -> Any:
        """
        Get an ASR provider instance.
        
        Uses lazy loading - provider is only instantiated when first requested.
        
        Args:
            provider_type: Type of provider (whisper, indicconformer, wav2vec2, commercial)
            force_reload: If True, reload the provider even if cached
        
        Returns:
            ASR provider instance
        
        Raises:
            ValueError: If provider type is unknown or unavailable
        """
        provider_type = provider_type.lower()
        
        # Validate provider type
        if provider_type not in [p.value for p in ProviderType]:
            raise ValueError(f"Unknown provider type: {provider_type}. "
                           f"Available: {[p.value for p in ProviderType]}")
        
        # Check availability
        capabilities = self._capabilities.get(provider_type)
        if not capabilities or not capabilities.is_available:
            raise ValueError(f"Provider '{provider_type}' is not available. "
                           f"Check dependencies or configuration.")
        
        # Return cached provider if available
        with self._lock:
            if provider_type in self._providers and not force_reload:
                logger.debug(f"Returning cached provider: {provider_type}")
                return self._providers[provider_type]
            
            # Instantiate provider
            logger.info(f"Instantiating provider: {provider_type}")
            provider = self._create_provider(provider_type)
            self._providers[provider_type] = provider
            
            return provider
    
    def _create_provider(self, provider_type: str) -> Any:
        """
        Create a new provider instance.
        
        Args:
            provider_type: Type of provider to create
        
        Returns:
            Provider instance
        """
        if provider_type == ProviderType.WHISPER.value:
            from asr.asr_whisper import ASRWhisper
            return ASRWhisper()
        
        elif provider_type == ProviderType.INDICCONFORMER.value:
            from asr.asr_indicconformer import ASRIndicConformer
            return ASRIndicConformer()
        
        elif provider_type == ProviderType.WAV2VEC2.value:
            from asr.asr_wav2vec2 import ASRWav2Vec2
            return ASRWav2Vec2()
        
        elif provider_type == ProviderType.COMMERCIAL.value:
            from asr.asr_commercial import ASRCommercial
            return ASRCommercial()
        
        else:
            raise ValueError(f"Cannot create provider: {provider_type}")
    
    def get_capabilities(self, provider_type: str = None) -> Dict[str, Any]:
        """
        Get capabilities for one or all providers.
        
        Args:
            provider_type: Specific provider type, or None for all
        
        Returns:
            Dictionary of capabilities
        """
        if provider_type:
            cap = self._capabilities.get(provider_type.lower())
            if cap:
                return cap.to_dict()
            return None
        
        # Return all capabilities
        return {
            name: cap.to_dict() 
            for name, cap in self._capabilities.items()
        }
    
    def list_available_providers(self) -> List[str]:
        """
        List all available (usable) providers.
        
        Returns:
            List of provider type names
        """
        return [
            name for name, cap in self._capabilities.items()
            if cap.is_available
        ]
    
    def get_primary_provider(self) -> Any:
        """
        Get the configured primary provider.
        
        Returns:
            Primary ASR provider instance
        """
        primary = getattr(config, 'ASR_PRIMARY_PROVIDER', 'whisper')
        return self.get_provider(primary)
    
    def get_fallback_provider(self) -> Optional[Any]:
        """
        Get the configured fallback provider.
        
        Returns:
            Fallback ASR provider instance, or None if not configured
        """
        fallback = getattr(config, 'ASR_FALLBACK_PROVIDER', None)
        if fallback and fallback in self.list_available_providers():
            return self.get_provider(fallback)
        return None
    
    def refresh_availability(self):
        """Re-check availability of all providers."""
        self._register_capabilities()
        logger.info("Provider availability refreshed")
    
    def clear_cache(self):
        """Clear all cached provider instances."""
        self._providers.clear()
        logger.info("Provider cache cleared")


# Convenience function for getting the singleton registry
def get_registry() -> ProviderRegistry:
    """Get the singleton ProviderRegistry instance."""
    return ProviderRegistry()

