"""
Gurbani Prompt Builder for Whisper ASR.

Builds context-aware prompts to bias Whisper transcription toward authentic
Gurbani vocabulary and patterns. Uses high-frequency words from SGGS corpus.
"""
import logging
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class PromptMode(Enum):
    """Prompt modes for different transcription contexts."""
    SGGS = "sggs"           # Sri Guru Granth Sahib Ji
    DASAM = "dasam"         # Dasam Granth
    KATHA = "katha"         # General Katha (mixed)
    KIRTAN = "kirtan"       # Kirtan/Shabad recitation


# Mool Mantar - the opening of SGGS
MOOL_MANTAR = "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ"

# Common Gurbani vocabulary (high-frequency words from SGGS)
# These words appear frequently and help bias the model
SGGS_HIGH_FREQUENCY_WORDS = [
    # Divine names
    "ਹਰਿ", "ਪ੍ਰਭ", "ਪ੍ਰਭੁ", "ਰਾਮ", "ਗੋਬਿੰਦ", "ਗੋਪਾਲ", "ਵਾਹਿਗੁਰੂ",
    "ਨਾਮ", "ਨਾਮੁ", "ਨਾਮਿ", "ਸਬਦ", "ਸਬਦੁ", "ਸਬਦਿ",
    # Guru references
    "ਗੁਰ", "ਗੁਰੁ", "ਸਤਿਗੁਰ", "ਸਤਿਗੁਰੁ", "ਗੁਰਬਾਣੀ",
    # Core concepts
    "ਮਨ", "ਮਨੁ", "ਮਨਿ", "ਜੀਉ", "ਜੀਅ", "ਹੁਕਮ", "ਹੁਕਮੁ",
    # Common verbs
    "ਹੈ", "ਹੋਇ", "ਹੋਵੈ", "ਕਰ", "ਕਰਿ", "ਕਰੈ", "ਮਿਲੈ", "ਪਾਇ", "ਜਪ", "ਜਪੁ",
    # Particles and conjunctions
    "ਜੀ", "ਜੀਉ", "ਕੋ", "ਕਾ", "ਕੀ", "ਕੇ", "ਤੇ", "ਦਾ", "ਦੀ", "ਦੇ",
    "ਨੂੰ", "ਨੇ", "ਜੋ", "ਸੋ", "ਜੇ", "ਤਾਂ", "ਬਿਨ", "ਬਿਨੁ",
    # Spiritual terms
    "ਭਗਤ", "ਭਗਤਿ", "ਸੇਵ", "ਸੇਵਾ", "ਸਿਮਰ", "ਸਿਮਰਨ",
    "ਮੁਕਤਿ", "ਮੋਖ", "ਸਹਜ", "ਅਨੰਦ", "ਸੁਖ", "ਦੁਖ",
    # Mahala references
    "ਮਹਲਾ", "ਨਾਨਕ", "ਅੰਗਦ", "ਅਮਰਦਾਸ", "ਰਾਮਦਾਸ", "ਅਰਜਨ",
]

# Common SGGS opening patterns (Salok beginnings)
SGGS_OPENING_PATTERNS = [
    "ਸਲੋਕ ਮਹਲਾ",
    "ਪਉੜੀ ॥",
    "ਛੰਤ ॥",
    "ਅਸਟਪਦੀ ॥",
    "ਸੋਹਿਲਾ ॥",
    "ਰਹਾਉ ॥",
    "ਜਪੁ ॥",
]

# Dasam Granth specific vocabulary
DASAM_HIGH_FREQUENCY_WORDS = [
    "ਸ੍ਰੀ", "ਭਗਉਤੀ", "ਅਕਾਲ", "ਪੁਰਖ", "ਕਾਲ",
    "ਖੰਡਾ", "ਚੱਕਰ", "ਬਾਣ", "ਖੜਗ", "ਤੀਰ",
    "ਦੇਵ", "ਦੇਵੀ", "ਚੰਡੀ", "ਦੁਰਗਾ",
    "ਯੁੱਧ", "ਜੁੱਧ", "ਸੂਰ", "ਵੀਰ",
    "ਨਮਸਕਾਰ", "ਵਾਹਿਗੁਰੂ", "ਸਤਿ",
]

# Katha-specific phrases (explanatory speech)
KATHA_PHRASES = [
    "ਜਿਵੇਂ ਬਾਣੀ ਚ ਕਿਹਾ",
    "ਗੁਰੂ ਸਾਹਿਬ ਫੁਰਮਾਉਂਦੇ ਹਨ",
    "ਇਸ ਸ਼ਬਦ ਦਾ ਅਰਥ ਹੈ",
    "ਗੁਰਬਾਣੀ ਦਾ ਫੁਰਮਾਨ ਹੈ",
    "ਅੰਗ ਉੱਤੇ ਲਿਖਿਆ ਹੈ",
]

# Common Raag names (for biasing)
RAAG_NAMES = [
    "ਸਿਰੀ ਰਾਗੁ", "ਮਾਝ", "ਗਉੜੀ", "ਆਸਾ", "ਗੂਜਰੀ",
    "ਦੇਵਗੰਧਾਰੀ", "ਬਿਹਾਗੜਾ", "ਵਡਹੰਸ", "ਸੋਰਠਿ", "ਧਨਾਸਰੀ",
    "ਜੈਤਸਰੀ", "ਟੋਡੀ", "ਬੈਰਾੜੀ", "ਤਿਲੰਗ", "ਸੂਹੀ",
    "ਬਿਲਾਵਲ", "ਗੋਂਡ", "ਰਾਮਕਲੀ", "ਨਟ", "ਮਾਲੀ ਗਉੜਾ",
    "ਮਾਰੂ", "ਤੁਖਾਰੀ", "ਕੇਦਾਰਾ", "ਭੈਰਉ", "ਬਸੰਤ",
    "ਸਾਰੰਗ", "ਮਲਾਰ", "ਕਾਨੜਾ", "ਕਲਿਆਣ", "ਪ੍ਰਭਾਤੀ",
]


class GurbaniPromptBuilder:
    """
    Builds context-aware prompts for Whisper ASR.
    
    Prompts bias the Whisper model toward authentic Gurbani vocabulary
    and speech patterns, improving transcription accuracy.
    """
    
    # Maximum prompt length (Whisper has token limits)
    MAX_PROMPT_LENGTH = 224  # ~224 tokens is safe for Whisper
    
    def __init__(self):
        """Initialize prompt builder."""
        self._sggs_prompt_cache: Optional[str] = None
        self._dasam_prompt_cache: Optional[str] = None
        self._katha_prompt_cache: Optional[str] = None
    
    def get_prompt(
        self,
        mode: str = "sggs",
        context: Optional[str] = None,
        previous_text: Optional[str] = None
    ) -> str:
        """
        Get a Gurbani-biased prompt for transcription.
        
        Args:
            mode: Prompt mode (sggs, dasam, katha, kirtan)
            context: Optional context hint (e.g., "raag_asa", "salok")
            previous_text: Text from previous segment for continuity
        
        Returns:
            Prompt string to pass to Whisper's initial_prompt
        """
        # Start with base prompt for mode
        if mode == "sggs" or mode == PromptMode.SGGS.value:
            base_prompt = self._get_sggs_prompt()
        elif mode == "dasam" or mode == PromptMode.DASAM.value:
            base_prompt = self._get_dasam_prompt()
        elif mode == "kirtan" or mode == PromptMode.KIRTAN.value:
            base_prompt = self._get_kirtan_prompt()
        else:  # katha or generic
            base_prompt = self._get_katha_prompt()
        
        # Add context-specific elements
        if context:
            context_addition = self._get_context_prompt(context)
            if context_addition:
                base_prompt = f"{context_addition} {base_prompt}"
        
        # Add previous segment for continuity (last ~50 chars)
        if previous_text:
            prev_snippet = previous_text[-50:].strip()
            if prev_snippet:
                base_prompt = f"{prev_snippet} {base_prompt}"
        
        # Truncate if too long
        if len(base_prompt) > self.MAX_PROMPT_LENGTH:
            base_prompt = base_prompt[:self.MAX_PROMPT_LENGTH]
        
        return base_prompt
    
    def _get_sggs_prompt(self) -> str:
        """Get SGGS-mode prompt."""
        if self._sggs_prompt_cache:
            return self._sggs_prompt_cache
        
        # Build prompt with high-frequency words and patterns
        words = " ".join(SGGS_HIGH_FREQUENCY_WORDS[:30])
        patterns = " ".join(SGGS_OPENING_PATTERNS[:3])
        
        # Include a snippet of Mool Mantar (very recognizable pattern)
        mool_snippet = "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
        
        prompt = f"{mool_snippet} {patterns} {words}"
        
        self._sggs_prompt_cache = prompt
        return prompt
    
    def _get_dasam_prompt(self) -> str:
        """Get Dasam Granth-mode prompt."""
        if self._dasam_prompt_cache:
            return self._dasam_prompt_cache
        
        # Dasam vocabulary + common SGGS words
        dasam_words = " ".join(DASAM_HIGH_FREQUENCY_WORDS)
        common_words = " ".join(SGGS_HIGH_FREQUENCY_WORDS[:15])
        
        # Chandi Di Var opening
        chandi_opening = "ਪ੍ਰਿਥਮ ਭਗੌਤੀ ਸਿਮਰਿ ਕੈ"
        
        prompt = f"{chandi_opening} {dasam_words} {common_words}"
        
        self._dasam_prompt_cache = prompt
        return prompt
    
    def _get_katha_prompt(self) -> str:
        """Get Katha-mode prompt (mixed Punjabi/Gurbani)."""
        if self._katha_prompt_cache:
            return self._katha_prompt_cache
        
        # Mix of Katha phrases and Gurbani vocabulary
        katha = " ".join(KATHA_PHRASES[:3])
        gurbani_words = " ".join(SGGS_HIGH_FREQUENCY_WORDS[:20])
        
        prompt = f"{katha} {gurbani_words}"
        
        self._katha_prompt_cache = prompt
        return prompt
    
    def _get_kirtan_prompt(self) -> str:
        """Get Kirtan-mode prompt (shabad recitation)."""
        # Kirtan is pure Gurbani recitation, use SGGS prompt + raag names
        sggs_prompt = self._get_sggs_prompt()
        raags = " ".join(RAAG_NAMES[:5])
        
        return f"{raags} {sggs_prompt}"
    
    def _get_context_prompt(self, context: str) -> Optional[str]:
        """Get context-specific prompt addition."""
        context_lower = context.lower()
        
        # Raag-specific context
        if context_lower.startswith("raag_") or context_lower.startswith("ਰਾਗ"):
            raag_name = context.replace("raag_", "").replace("ਰਾਗ", "").strip()
            for raag in RAAG_NAMES:
                if raag_name.lower() in raag.lower():
                    return f"ਰਾਗ {raag}"
        
        # Salok context
        if "salok" in context_lower or "ਸਲੋਕ" in context:
            return "ਸਲੋਕ ਮਹਲਾ"
        
        # Japji context
        if "japji" in context_lower or "ਜਪੁ" in context:
            return "ਜਪੁ ॥ ਆਦਿ ਸਚੁ ਜੁਗਾਦਿ ਸਚੁ"
        
        # Rehras context
        if "rehras" in context_lower:
            return "ਸੋਦਰੁ ਰਾਗੁ ਆਸਾ"
        
        # Sukhmani context
        if "sukhmani" in context_lower or "ਸੁਖਮਨੀ" in context:
            return "ਗਉੜੀ ਸੁਖਮਨੀ ਮਹਲਾ ੫"
        
        return None
    
    def get_prompt_for_quote(self, quote_hint: Optional[str] = None) -> str:
        """
        Get optimized prompt when a quote is expected.
        
        Args:
            quote_hint: Optional hint about the quote (e.g., first few words)
        
        Returns:
            Prompt optimized for quote transcription
        """
        # When we expect a quote, use pure SGGS vocabulary
        base = self._get_sggs_prompt()
        
        if quote_hint:
            # Put the hint first for better continuity
            return f"{quote_hint} {base}"
        
        return base
    
    def get_prompt_with_vocabulary(
        self,
        mode: str = "sggs",
        extra_vocabulary: Optional[List[str]] = None
    ) -> str:
        """
        Get prompt with additional vocabulary terms.
        
        Args:
            mode: Base mode
            extra_vocabulary: Additional words to include in prompt
        
        Returns:
            Enhanced prompt
        """
        base = self.get_prompt(mode)
        
        if extra_vocabulary:
            extra = " ".join(extra_vocabulary[:10])
            return f"{extra} {base}"
        
        return base


# Singleton instance
_prompt_builder: Optional[GurbaniPromptBuilder] = None


def get_prompt_builder() -> GurbaniPromptBuilder:
    """Get singleton prompt builder instance."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = GurbaniPromptBuilder()
    return _prompt_builder


def get_gurbani_prompt(
    mode: str = "sggs",
    context: Optional[str] = None,
    previous_text: Optional[str] = None
) -> str:
    """
    Convenience function to get a Gurbani prompt.
    
    Args:
        mode: Prompt mode (sggs, dasam, katha, kirtan)
        context: Optional context hint
        previous_text: Previous segment text
    
    Returns:
        Prompt string for Whisper
    """
    builder = get_prompt_builder()
    return builder.get_prompt(mode, context, previous_text)
