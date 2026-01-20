"""
ASR Commercial: ElevenLabs Scribe API Provider.

This provider uses the ElevenLabs Scribe API for high-quality commercial
speech-to-text. Only enabled when USE_COMMERCIAL=true and API key is set.

Provider: ElevenLabs (or other commercial APIs)
Features: High accuracy, word-level timestamps, multiple languages
"""
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

import config
from core.models import AudioChunk, ASRResult, Segment
from core.errors import ASREngineError

logger = logging.getLogger(__name__)

# Try to import HTTP client
HTTPX_AVAILABLE = False
REQUESTS_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    pass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    pass

if not HTTPX_AVAILABLE and not REQUESTS_AVAILABLE:
    logger.warning("No HTTP client available. Install httpx or requests for commercial provider.")


class ASRCommercial:
    """
    Commercial ASR provider using ElevenLabs Scribe API.
    
    Only activated when:
    - USE_COMMERCIAL=true in config
    - COMMERCIAL_API_KEY is set
    
    Falls back to open-source provider on API failure.
    """
    
    engine_name = "commercial"
    default_language = "pa"  # Punjabi
    supported_languages = ["pa", "hi", "en", "auto"]
    
    # ElevenLabs API endpoints
    ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
    ELEVENLABS_TRANSCRIBE_ENDPOINT = "/speech-to-text"
    
    # Language mapping for ElevenLabs
    language_map = {
        "pa": "punjabi",
        "hi": "hindi",
        "en": "english",
        "auto": None  # Let API auto-detect
    }
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        """
        Initialize the commercial ASR provider.
        
        Args:
            api_key: API key (defaults to config.COMMERCIAL_API_KEY)
            provider: Provider name (defaults to config.COMMERCIAL_PROVIDER)
        """
        self.api_key = api_key or getattr(config, 'COMMERCIAL_API_KEY', '')
        self.provider = provider or getattr(config, 'COMMERCIAL_PROVIDER', 'elevenlabs')
        self.timeout = getattr(config, 'COMMERCIAL_TIMEOUT', 120)
        
        # Validate configuration
        if not self.api_key:
            raise ValueError(
                "Commercial API key not configured. "
                "Set COMMERCIAL_API_KEY environment variable or config."
            )
        
        if not HTTPX_AVAILABLE and not REQUESTS_AVAILABLE:
            raise ImportError(
                "HTTP client required for commercial provider. "
                "Install with: pip install httpx"
            )
        
        # Use httpx if available (better async support), otherwise requests
        self._use_httpx = HTTPX_AVAILABLE
        
        logger.info(f"Commercial ASR provider initialized: {self.provider}")
    
    def _make_request(
        self,
        method: str,
        url: str,
        files: Dict = None,
        data: Dict = None,
        json_data: Dict = None
    ) -> Dict:
        """
        Make HTTP request to commercial API.
        
        Args:
            method: HTTP method (GET, POST)
            url: Full URL
            files: Files to upload
            data: Form data
            json_data: JSON data
        
        Returns:
            Response JSON
        """
        headers = {
            "xi-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        try:
            if self._use_httpx:
                with httpx.Client(timeout=self.timeout) as client:
                    if method.upper() == "POST":
                        response = client.post(
                            url,
                            headers=headers,
                            files=files,
                            data=data,
                            json=json_data
                        )
                    else:
                        response = client.get(url, headers=headers)
                    
                    response.raise_for_status()
                    return response.json()
            else:
                if method.upper() == "POST":
                    response = requests.post(
                        url,
                        headers=headers,
                        files=files,
                        data=data,
                        json=json_data,
                        timeout=self.timeout
                    )
                else:
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Commercial API request failed: {e}")
            raise ASREngineError(self.engine_name, str(e))
    
    def _transcribe_elevenlabs(
        self,
        audio_path: Path,
        language: str
    ) -> Dict:
        """
        Transcribe using ElevenLabs Scribe API.
        
        Args:
            audio_path: Path to audio file
            language: Language code
        
        Returns:
            API response dict
        """
        url = f"{self.ELEVENLABS_BASE_URL}{self.ELEVENLABS_TRANSCRIBE_ENDPOINT}"
        
        # Prepare language parameter
        lang_param = self.language_map.get(language, language)
        
        # Read audio file
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        
        # Prepare request
        files = {
            "audio": (audio_path.name, audio_bytes, "audio/wav")
        }
        
        data = {}
        if lang_param:
            data["language"] = lang_param
        
        # Add model selection for better Punjabi support
        data["model"] = "scribe_v1"  # Or specific model for Indic
        
        response = self._make_request("POST", url, files=files, data=data)
        
        return response
    
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        route: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe an audio chunk using commercial API.
        
        Args:
            chunk: AudioChunk to transcribe
            language: Language code
            route: Route string (for compatibility)
        
        Returns:
            ASRResult with transcription
        """
        language = language or self.default_language
        
        try:
            if self.provider == "elevenlabs":
                response = self._transcribe_elevenlabs(chunk.audio_path, language)
            else:
                raise ValueError(f"Unsupported commercial provider: {self.provider}")
            
            # Parse response
            text = response.get("text", "")
            segments_data = response.get("words", []) or response.get("segments", [])
            
            # Build segments
            segments = []
            if segments_data:
                for seg_data in segments_data:
                    # Handle different response formats
                    if "word" in seg_data:
                        # Word-level format
                        segments.append(Segment(
                            start=seg_data.get("start", 0),
                            end=seg_data.get("end", 0),
                            text=seg_data.get("word", ""),
                            confidence=seg_data.get("confidence", 0.9),
                            language=language
                        ))
                    else:
                        # Segment-level format
                        segments.append(Segment(
                            start=seg_data.get("start", 0),
                            end=seg_data.get("end", 0),
                            text=seg_data.get("text", ""),
                            confidence=seg_data.get("confidence", 0.9),
                            language=language
                        ))
            else:
                # Single segment from full text
                segments.append(Segment(
                    start=0,
                    end=chunk.duration,
                    text=text,
                    confidence=0.9,
                    language=language
                ))
            
            # Calculate overall confidence
            confidence = response.get("confidence", 0.9)
            if not confidence and segments:
                confidence = sum(s.confidence for s in segments) / len(segments)
            
            return ASRResult(
                text=text.strip(),
                language=language,
                confidence=confidence,
                segments=segments,
                engine=self.engine_name
            )
            
        except Exception as e:
            logger.error(f"Commercial transcription failed: {e}")
            # Return error result instead of raising - allows fallback
            return ASRResult(
                text="[Commercial API error]",
                language=language,
                confidence=0.0,
                segments=[Segment(
                    start=0,
                    end=chunk.duration,
                    text="[Commercial API error]",
                    confidence=0.0,
                    language=language
                )],
                engine=self.engine_name
            )
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe a full audio file using commercial API.
        
        Args:
            audio_path: Path to audio file
            language: Language code
        
        Returns:
            ASRResult with transcription
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        language = language or self.default_language
        
        try:
            if self.provider == "elevenlabs":
                response = self._transcribe_elevenlabs(audio_path, language)
            else:
                raise ValueError(f"Unsupported commercial provider: {self.provider}")
            
            # Parse response (same logic as transcribe_chunk)
            text = response.get("text", "")
            segments_data = response.get("words", []) or response.get("segments", [])
            
            segments = []
            if segments_data:
                for seg_data in segments_data:
                    if "word" in seg_data:
                        segments.append(Segment(
                            start=seg_data.get("start", 0),
                            end=seg_data.get("end", 0),
                            text=seg_data.get("word", ""),
                            confidence=seg_data.get("confidence", 0.9),
                            language=language
                        ))
                    else:
                        segments.append(Segment(
                            start=seg_data.get("start", 0),
                            end=seg_data.get("end", 0),
                            text=seg_data.get("text", ""),
                            confidence=seg_data.get("confidence", 0.9),
                            language=language
                        ))
            else:
                # Estimate duration from file
                try:
                    import soundfile as sf
                    audio_info = sf.info(str(audio_path))
                    duration = audio_info.duration
                except Exception:
                    duration = 0
                
                segments.append(Segment(
                    start=0,
                    end=duration,
                    text=text,
                    confidence=0.9,
                    language=language
                ))
            
            confidence = response.get("confidence", 0.9)
            if not confidence and segments:
                confidence = sum(s.confidence for s in segments) / len(segments)
            
            return ASRResult(
                text=text.strip(),
                language=language,
                confidence=confidence,
                segments=segments,
                engine=self.engine_name
            )
            
        except Exception as e:
            logger.error(f"Commercial transcription failed: {e}")
            raise ASREngineError(self.engine_name, str(e))
    
    def is_model_loaded(self) -> bool:
        """Check if provider is configured and ready."""
        return bool(self.api_key)
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return self.supported_languages.copy()
    
    def check_api_health(self) -> bool:
        """
        Check if the commercial API is accessible.
        
        Returns:
            True if API is healthy
        """
        try:
            # Simple health check - try to access API
            if self.provider == "elevenlabs":
                url = f"{self.ELEVENLABS_BASE_URL}/user"
                headers = {
                    "xi-api-key": self.api_key,
                    "Accept": "application/json"
                }
                
                if self._use_httpx:
                    with httpx.Client(timeout=10) as client:
                        response = client.get(url, headers=headers)
                        return response.status_code == 200
                else:
                    response = requests.get(url, headers=headers, timeout=10)
                    return response.status_code == 200
            
            return False
        except Exception as e:
            logger.debug(f"API health check failed: {e}")
            return False
    
    def get_remaining_quota(self) -> Optional[Dict]:
        """
        Get remaining API quota/credits.
        
        Returns:
            Dict with quota info, or None if unavailable
        """
        try:
            if self.provider == "elevenlabs":
                url = f"{self.ELEVENLABS_BASE_URL}/user/subscription"
                headers = {
                    "xi-api-key": self.api_key,
                    "Accept": "application/json"
                }
                
                if self._use_httpx:
                    with httpx.Client(timeout=10) as client:
                        response = client.get(url, headers=headers)
                        if response.status_code == 200:
                            data = response.json()
                            return {
                                "character_count": data.get("character_count", 0),
                                "character_limit": data.get("character_limit", 0),
                                "tier": data.get("tier", "unknown")
                            }
                else:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "character_count": data.get("character_count", 0),
                            "character_limit": data.get("character_limit", 0),
                            "tier": data.get("tier", "unknown")
                        }
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get quota: {e}")
            return None

