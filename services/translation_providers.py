"""
Translation provider implementations.

Supports multiple translation backends:
- Google Cloud Translation API
- Azure Translator
- OpenAI GPT (for context-aware spiritual translations)
- LibreTranslate (open-source, self-hosted)
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseTranslationProvider(ABC):
    """Abstract base class for translation providers."""
    
    provider_name: str = "base"
    
    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> str:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate
            source_language: ISO 639-1 source language code
            target_language: ISO 639-1 target language code
            context: Optional context for better translation (e.g., "spiritual", "scripture")
        
        Returns:
            Translated text
        """
        pass
    
    @abstractmethod
    def translate_batch(
        self,
        texts: List[str],
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> List[str]:
        """
        Translate multiple texts efficiently.
        
        Args:
            texts: List of texts to translate
            source_language: ISO 639-1 source language code
            target_language: ISO 639-1 target language code
            context: Optional context for better translation
        
        Returns:
            List of translated texts
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.
        
        Returns:
            List of ISO 639-1 language codes
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is configured and available.
        
        Returns:
            True if provider can be used
        """
        pass
    
    def supports_language(self, language_code: str) -> bool:
        """Check if provider supports a specific language."""
        return language_code.lower() in [lang.lower() for lang in self.get_supported_languages()]


class GoogleTranslateProvider(BaseTranslationProvider):
    """Google Cloud Translation API provider."""
    
    provider_name = "google"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Translate provider.
        
        Args:
            api_key: Google Cloud API key (or from environment)
        """
        self.api_key = api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
        self._client = None
    
    def _get_client(self):
        """Lazy-load the Google Translate client."""
        if self._client is None and self.api_key:
            try:
                from google.cloud import translate_v2 as translate
                self._client = translate.Client()
                logger.info("Google Translate client initialized")
            except ImportError:
                logger.warning("google-cloud-translate not installed. Install with: pip install google-cloud-translate")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize Google Translate client: {e}")
                self._client = None
        return self._client
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> str:
        """Translate using Google Cloud Translation API."""
        if not text.strip():
            return text
        
        # Try using the official client first
        client = self._get_client()
        if client:
            try:
                result = client.translate(
                    text,
                    source_language=source_language,
                    target_language=target_language
                )
                return result['translatedText']
            except Exception as e:
                logger.warning(f"Google Translate API error: {e}")
        
        # Fallback to REST API
        if self.api_key:
            try:
                import requests
                url = "https://translation.googleapis.com/language/translate/v2"
                params = {
                    "key": self.api_key,
                    "q": text,
                    "source": source_language,
                    "target": target_language,
                    "format": "text"
                }
                response = requests.post(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data["data"]["translations"][0]["translatedText"]
            except Exception as e:
                logger.error(f"Google Translate REST API error: {e}")
                raise
        
        raise RuntimeError("Google Translate provider not properly configured")
    
    def translate_batch(
        self,
        texts: List[str],
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Batch translate using Google Cloud Translation API."""
        if not texts:
            return []
        
        client = self._get_client()
        if client:
            try:
                results = client.translate(
                    texts,
                    source_language=source_language,
                    target_language=target_language
                )
                return [r['translatedText'] for r in results]
            except Exception as e:
                logger.warning(f"Google Translate batch API error: {e}")
        
        # Fallback to individual translations
        return [self.translate(text, source_language, target_language, context) for text in texts]
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages from Google Translate."""
        # Common languages - Google supports 100+
        return [
            "en", "hi", "pa", "ur", "es", "fr", "de", "it", "pt", "ru",
            "zh", "ja", "ko", "ar", "bn", "ta", "te", "mr", "gu", "kn",
            "ml", "th", "vi", "id", "ms", "tl", "tr", "pl", "nl", "sv"
        ]
    
    def is_available(self) -> bool:
        """Check if Google Translate is configured."""
        return bool(self.api_key)


class AzureTranslatorProvider(BaseTranslationProvider):
    """Azure Translator provider."""
    
    provider_name = "azure"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize Azure Translator provider.
        
        Args:
            api_key: Azure Translator API key (or from environment)
            region: Azure region (or from environment)
        """
        self.api_key = api_key or os.getenv("AZURE_TRANSLATOR_KEY")
        self.region = region or os.getenv("AZURE_TRANSLATOR_REGION", "global")
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> str:
        """Translate using Azure Translator API."""
        if not text.strip():
            return text
        
        if not self.api_key:
            raise RuntimeError("Azure Translator not configured")
        
        try:
            import requests
            import uuid
            
            path = '/translate'
            constructed_url = self.endpoint + path
            
            params = {
                'api-version': '3.0',
                'from': source_language,
                'to': target_language
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Ocp-Apim-Subscription-Region': self.region,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }
            
            body = [{'text': text}]
            
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result[0]['translations'][0]['text']
            
        except Exception as e:
            logger.error(f"Azure Translator error: {e}")
            raise
    
    def translate_batch(
        self,
        texts: List[str],
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Batch translate using Azure Translator API."""
        if not texts:
            return []
        
        if not self.api_key:
            raise RuntimeError("Azure Translator not configured")
        
        try:
            import requests
            import uuid
            
            path = '/translate'
            constructed_url = self.endpoint + path
            
            params = {
                'api-version': '3.0',
                'from': source_language,
                'to': target_language
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Ocp-Apim-Subscription-Region': self.region,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }
            
            # Azure supports up to 100 texts per request
            body = [{'text': text} for text in texts]
            
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body,
                timeout=60
            )
            response.raise_for_status()
            
            results = response.json()
            return [r['translations'][0]['text'] for r in results]
            
        except Exception as e:
            logger.error(f"Azure Translator batch error: {e}")
            # Fallback to individual translations
            return [self.translate(text, source_language, target_language, context) for text in texts]
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages from Azure Translator."""
        return [
            "en", "hi", "pa", "ur", "es", "fr", "de", "it", "pt", "ru",
            "zh-Hans", "zh-Hant", "ja", "ko", "ar", "bn", "ta", "te", "mr",
            "gu", "kn", "ml", "th", "vi", "id", "ms", "fil", "tr", "pl", "nl"
        ]
    
    def is_available(self) -> bool:
        """Check if Azure Translator is configured."""
        return bool(self.api_key)


class OpenAITranslationProvider(BaseTranslationProvider):
    """OpenAI GPT-based translation provider for context-aware spiritual translations."""
    
    provider_name = "openai"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize OpenAI translation provider.
        
        Args:
            api_key: OpenAI API key (or from environment)
            model: Model to use for translation
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("openai package not installed. Install with: pip install openai")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self._client = None
        return self._client
    
    def _get_language_name(self, code: str) -> str:
        """Convert language code to full name."""
        language_names = {
            "en": "English",
            "hi": "Hindi",
            "pa": "Punjabi",
            "ur": "Urdu",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic"
        }
        return language_names.get(code.lower(), code)
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> str:
        """Translate using OpenAI GPT for context-aware translation."""
        if not text.strip():
            return text
        
        client = self._get_client()
        if not client:
            raise RuntimeError("OpenAI provider not properly configured")
        
        source_name = self._get_language_name(source_language)
        target_name = self._get_language_name(target_language)
        
        # Build context-aware system prompt
        system_prompt = f"""You are an expert translator specializing in Sikh religious texts and spiritual content.
Translate the following text from {source_name} to {target_name}.

Guidelines:
- Preserve the spiritual meaning and reverence
- Keep proper nouns (names of Gurus, places) as transliterations
- Maintain the poetic structure where applicable
- Use appropriate religious terminology for the target language
- If the text contains Gurbani (sacred scripture), translate the meaning while preserving sanctity"""
        
        if context == "scripture":
            system_prompt += "\n- This is sacred Gurbani scripture. Translate with utmost care and accuracy."
        elif context == "katha":
            system_prompt += "\n- This is katha (religious discourse). Maintain the explanatory nature."
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Translate this text:\n\n{text}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=len(text) * 3  # Allow expansion for translation
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI translation error: {e}")
            raise
    
    def translate_batch(
        self,
        texts: List[str],
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Batch translate using OpenAI (processes individually for better quality)."""
        return [self.translate(text, source_language, target_language, context) for text in texts]
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages (GPT supports many languages)."""
        return [
            "en", "hi", "pa", "ur", "es", "fr", "de", "it", "pt", "ru",
            "zh", "ja", "ko", "ar", "bn", "ta", "te", "mr", "gu", "kn",
            "ml", "th", "vi", "id", "ms", "tl", "tr", "pl", "nl", "sv"
        ]
    
    def is_available(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.api_key)


class LibreTranslateProvider(BaseTranslationProvider):
    """LibreTranslate open-source translation provider."""
    
    provider_name = "libre"
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize LibreTranslate provider.
        
        Args:
            api_url: LibreTranslate API URL (or from environment)
            api_key: Optional API key for hosted instances
        """
        self.api_url = api_url or os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com")
        self.api_key = api_key or os.getenv("LIBRETRANSLATE_API_KEY")
        self._supported_languages = None
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> str:
        """Translate using LibreTranslate API."""
        if not text.strip():
            return text
        
        try:
            import requests
            
            url = f"{self.api_url.rstrip('/')}/translate"
            
            payload = {
                "q": text,
                "source": source_language,
                "target": target_language,
                "format": "text"
            }
            
            if self.api_key:
                payload["api_key"] = self.api_key
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("translatedText", text)
            
        except Exception as e:
            logger.error(f"LibreTranslate error: {e}")
            raise
    
    def translate_batch(
        self,
        texts: List[str],
        source_language: str,
        target_language: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Batch translate using LibreTranslate (processes individually)."""
        return [self.translate(text, source_language, target_language, context) for text in texts]
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages from LibreTranslate API."""
        if self._supported_languages is not None:
            return self._supported_languages
        
        try:
            import requests
            
            url = f"{self.api_url.rstrip('/')}/languages"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            languages = response.json()
            self._supported_languages = [lang["code"] for lang in languages]
            return self._supported_languages
            
        except Exception as e:
            logger.warning(f"Failed to fetch LibreTranslate languages: {e}")
            # Return common languages as fallback
            return ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi"]
    
    def is_available(self) -> bool:
        """Check if LibreTranslate is accessible."""
        try:
            import requests
            url = f"{self.api_url.rstrip('/')}/languages"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# Provider Registry
_translation_providers: Dict[str, BaseTranslationProvider] = {}


def register_translation_provider(name: str, provider: BaseTranslationProvider) -> None:
    """Register a translation provider."""
    _translation_providers[name.lower()] = provider
    logger.info(f"Registered translation provider: {name}")


def get_translation_provider(name: str) -> Optional[BaseTranslationProvider]:
    """Get a translation provider by name."""
    return _translation_providers.get(name.lower())


def get_available_translation_providers() -> Dict[str, Dict[str, Any]]:
    """Get information about all available translation providers."""
    providers = {}
    
    for name, provider in _translation_providers.items():
        providers[name] = {
            "name": provider.provider_name,
            "available": provider.is_available(),
            "supported_languages": provider.get_supported_languages() if provider.is_available() else []
        }
    
    return providers


def initialize_translation_providers() -> None:
    """Initialize all translation providers."""
    # Google Translate
    google_provider = GoogleTranslateProvider()
    register_translation_provider("google", google_provider)
    
    # Azure Translator
    azure_provider = AzureTranslatorProvider()
    register_translation_provider("azure", azure_provider)
    
    # OpenAI
    openai_provider = OpenAITranslationProvider()
    register_translation_provider("openai", openai_provider)
    
    # LibreTranslate
    libre_provider = LibreTranslateProvider()
    register_translation_provider("libre", libre_provider)
    
    logger.info("Translation providers initialized")


# Auto-initialize providers when module is imported
initialize_translation_providers()

