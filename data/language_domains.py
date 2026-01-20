"""
Language Domain Definitions for SGGS and Dasam Granth Transcription.

Defines the allowed language registers/domains and their priority weights
for constraining ASR output to authentic Gurbani linguistic patterns.

Core Principle: Treat text domain as "Gurmukhi-script sacred/poetic multilingual"
with a small, known set of languages/registers. Constrain decoding + correction
to this whitelist only.
"""
from enum import Enum
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


class LanguageRegister(Enum):
    """
    Allowed language registers for SGGS and Dasam Granth.
    
    These represent the authentic linguistic layers found in Gurbani,
    NOT modern languages like standard Hindi, English, or Hinglish.
    """
    # SGGS priority registers (highest weight)
    SANT_BHASHA = "sant_bhasha"      # Devotional mixed register (primary in SGGS)
    BRAJ_BHASHA = "braj_bhasha"      # Braj literary language
    OLD_PUNJABI = "old_punjabi"      # Medieval Gurmukhi Punjabi
    AVADHI = "avadhi"                # Eastern Hindi literary form (Kabir, etc.)
    
    # Shared lexical layers (medium weight)
    SANSKRIT_DERIVED = "sanskrit"    # Tatsama / Tadbhava terms
    PERSIAN_DERIVED = "persian"      # Persian loanwords (in Gurmukhi)
    ARABIC_DERIVED = "arabic"        # Arabic loanwords (in Gurmukhi)
    APABHRAMSHA = "apabhramsha"      # Prakritic / Apabhramsha forms (rare)


class DomainMode(Enum):
    """
    Domain modes for transcription.
    
    Each mode sets different priority weights for language registers.
    """
    SGGS = "sggs"           # Sri Guru Granth Sahib Ji mode
    DASAM = "dasam"         # Dasam Granth mode
    GENERIC_PUNJABI = "generic"  # Generic Punjabi fallback


@dataclass
class DomainPriorities:
    """
    Priority weights for each language register within a domain mode.
    
    Weights range from 0.0 to 1.0, where:
    - 1.0 = highest priority (prefer this register)
    - 0.5 = medium priority
    - 0.0 = not applicable
    """
    sant_bhasha: float
    braj_bhasha: float
    old_punjabi: float
    avadhi: float
    sanskrit: float
    persian: float
    arabic: float
    apabhramsha: float
    
    def get_weight(self, register: LanguageRegister) -> float:
        """Get weight for a specific register."""
        weight_map = {
            LanguageRegister.SANT_BHASHA: self.sant_bhasha,
            LanguageRegister.BRAJ_BHASHA: self.braj_bhasha,
            LanguageRegister.OLD_PUNJABI: self.old_punjabi,
            LanguageRegister.AVADHI: self.avadhi,
            LanguageRegister.SANSKRIT_DERIVED: self.sanskrit,
            LanguageRegister.PERSIAN_DERIVED: self.persian,
            LanguageRegister.ARABIC_DERIVED: self.arabic,
            LanguageRegister.APABHRAMSHA: self.apabhramsha,
        }
        return weight_map.get(register, 0.0)
    
    def get_priority_list(self) -> List[Tuple[LanguageRegister, float]]:
        """Get registers sorted by priority (highest first)."""
        weights = [
            (LanguageRegister.SANT_BHASHA, self.sant_bhasha),
            (LanguageRegister.BRAJ_BHASHA, self.braj_bhasha),
            (LanguageRegister.OLD_PUNJABI, self.old_punjabi),
            (LanguageRegister.AVADHI, self.avadhi),
            (LanguageRegister.SANSKRIT_DERIVED, self.sanskrit),
            (LanguageRegister.PERSIAN_DERIVED, self.persian),
            (LanguageRegister.ARABIC_DERIVED, self.arabic),
            (LanguageRegister.APABHRAMSHA, self.apabhramsha),
        ]
        return sorted(weights, key=lambda x: x[1], reverse=True)


# Domain-specific priority configurations
SGGS_PRIORITIES = DomainPriorities(
    sant_bhasha=1.0,    # Highest - dominant in SGGS
    braj_bhasha=0.9,    # Very high - common in SGGS
    old_punjabi=0.9,    # Very high - Guru's native language
    avadhi=0.8,         # High - Kabir, Ravidas, etc.
    sanskrit=0.6,       # Medium - theological terms
    persian=0.5,        # Medium - loanwords
    arabic=0.5,         # Medium - loanwords
    apabhramsha=0.3,    # Lower - rare archaic forms
)

DASAM_PRIORITIES = DomainPriorities(
    sant_bhasha=0.8,    # High but not dominant
    braj_bhasha=1.0,    # Highest - dominant in Dasam
    old_punjabi=0.7,    # Medium-high
    avadhi=0.5,         # Medium
    sanskrit=0.9,       # Very high - heavy Sanskrit influence
    persian=0.5,        # Medium
    arabic=0.4,         # Medium-lower
    apabhramsha=0.3,    # Lower
)

GENERIC_PRIORITIES = DomainPriorities(
    sant_bhasha=0.5,    # Medium
    braj_bhasha=0.4,    # Medium-lower
    old_punjabi=1.0,    # Highest - modern Punjabi base
    avadhi=0.3,         # Lower
    sanskrit=0.4,       # Medium-lower
    persian=0.5,        # Medium
    arabic=0.4,         # Medium-lower
    apabhramsha=0.2,    # Low
)


def get_domain_priorities(mode: DomainMode) -> DomainPriorities:
    """
    Get priority weights for a domain mode.
    
    Args:
        mode: DomainMode enum value
    
    Returns:
        DomainPriorities for the specified mode
    """
    priorities_map = {
        DomainMode.SGGS: SGGS_PRIORITIES,
        DomainMode.DASAM: DASAM_PRIORITIES,
        DomainMode.GENERIC_PUNJABI: GENERIC_PRIORITIES,
    }
    return priorities_map.get(mode, SGGS_PRIORITIES)


# Explicitly NOT allowed as primary targets (blocklist)
BLOCKED_LANGUAGES = {
    "modern_hindi",      # Standard Hindi - not the same as Braj/Avadhi
    "english",           # English
    "hinglish",          # Hindi-English mix
    "urdu_script",       # Urdu in Nastaliq (Shahmukhi is separate feature)
    "gujarati",          # Other Indian languages
    "marathi",
    "bengali",
    "tamil",
    "telugu",
    "kannada",
    "malayalam",
}


# Script constants
class GurmukhiScript:
    """Unicode ranges and characters for Gurmukhi script validation."""
    
    # Main Gurmukhi Unicode block: U+0A00 to U+0A7F
    RANGE_START = 0x0A00
    RANGE_END = 0x0A7F
    
    # Gurmukhi vowels (independent)
    VOWELS = set('ਅਆਇਈਉਊਏਐਓਔ')
    
    # Gurmukhi consonants
    CONSONANTS = set('ਕਖਗਘਙਚਛਜਝਞਟਠਡਢਣਤਥਦਧਨਪਫਬਭਮਯਰਲਵਸਸ਼ਹਖ਼ਗ਼ਜ਼ੜਫ਼ੲੳ')
    
    # Gurmukhi vowel signs (matras)
    VOWEL_SIGNS = set('ਾਿੀੁੂੇੈੋੌ')
    
    # Gurmukhi other marks
    OTHER_MARKS = set('ੰੱੱ਼ੑ੍')
    
    # Gurmukhi digits
    DIGITS = set('੦੧੨੩੪੫੬੭੮੯')
    
    # Gurmukhi punctuation (including traditional marks)
    PUNCTUATION = set('।॥੶')
    
    # Common punctuation and whitespace to allow
    ALLOWED_PUNCTUATION = set(' \t\n,.;:!?-\'\"()[]{}।॥੶')
    
    # ASCII digits (sometimes used)
    ASCII_DIGITS = set('0123456789')
    
    @classmethod
    def get_all_allowed_chars(cls) -> Set[str]:
        """Get set of all allowed characters for Gurmukhi text."""
        return (
            cls.VOWELS | 
            cls.CONSONANTS | 
            cls.VOWEL_SIGNS | 
            cls.OTHER_MARKS | 
            cls.DIGITS | 
            cls.PUNCTUATION |
            cls.ALLOWED_PUNCTUATION |
            cls.ASCII_DIGITS
        )
    
    @classmethod
    def is_gurmukhi_char(cls, char: str) -> bool:
        """Check if a character is in Gurmukhi Unicode block."""
        if len(char) != 1:
            return False
        code_point = ord(char)
        return cls.RANGE_START <= code_point <= cls.RANGE_END
    
    @classmethod
    def is_allowed_char(cls, char: str) -> bool:
        """Check if a character is allowed in Gurbani text."""
        if len(char) != 1:
            return False
        return (
            cls.is_gurmukhi_char(char) or 
            char in cls.ALLOWED_PUNCTUATION or
            char in cls.ASCII_DIGITS
        )


# Common Gurbani function words and particles
COMMON_PARTICLES = {
    # Conjunctions and particles
    'ਤੇ', 'ਕੇ', 'ਕਾ', 'ਕੀ', 'ਕੋ', 'ਨੂੰ', 'ਨੇ', 'ਦਾ', 'ਦੀ', 'ਦੇ',
    'ਜੋ', 'ਸੋ', 'ਜੇ', 'ਹੈ', 'ਹੋ', 'ਹਿ', 'ਹਉ', 'ਹਮ', 'ਤੂੰ', 'ਤੂ',
    'ਮੈ', 'ਮੇਰਾ', 'ਮੇਰੀ', 'ਮੇਰੇ', 'ਤੇਰਾ', 'ਤੇਰੀ', 'ਤੇਰੇ',
    'ਇਹ', 'ਇਸ', 'ਉਹ', 'ਉਸ', 'ਕਿਸ', 'ਜਿਸ', 'ਕਿਉ', 'ਕਿਉਂ',
    'ਨਾ', 'ਨਹੀ', 'ਨਹੀਂ', 'ਬਿਨ', 'ਬਿਨੁ', 'ਬਿਨਾ',
    'ਸਭ', 'ਸਭੁ', 'ਸਭਿ', 'ਸਗਲ', 'ਸਗਲੀ',
    'ਏਕ', 'ਏਕੁ', 'ਇਕ', 'ਇਕੁ', 'ਦੋ', 'ਦੁਇ', 'ਤਿਨ', 'ਤੀਨ',
    
    # Common verbs
    'ਹੋਇ', 'ਹੋਵੈ', 'ਹੋਆ', 'ਹੋਈ', 'ਕਰ', 'ਕਰਿ', 'ਕਰੇ', 'ਕਰੈ', 'ਕੀਆ',
    'ਆਵੈ', 'ਆਇ', 'ਆਇਆ', 'ਜਾਇ', 'ਜਾਵੈ', 'ਗਇਆ', 'ਗਈ',
    'ਦੇਇ', 'ਦੇਵੈ', 'ਦਿਤਾ', 'ਲੇਇ', 'ਲੈ', 'ਲੀਆ',
    'ਮਿਲੈ', 'ਮਿਲਿ', 'ਮਿਲਿਆ', 'ਪਾਇ', 'ਪਾਵੈ', 'ਪਾਇਆ',
    
    # Common nouns and theological terms
    'ਮਨ', 'ਮਨੁ', 'ਮਨਿ', 'ਹਰਿ', 'ਰਾਮ', 'ਪ੍ਰਭ', 'ਪ੍ਰਭੁ',
    'ਗੁਰ', 'ਗੁਰੁ', 'ਸਤਿਗੁਰ', 'ਸਤਿਗੁਰੁ',
    'ਨਾਮ', 'ਨਾਮੁ', 'ਨਾਮਿ', 'ਸਬਦ', 'ਸਬਦੁ', 'ਸਬਦਿ',
    'ਜੀਉ', 'ਜੀਅ', 'ਪ੍ਰਾਣ', 'ਪ੍ਰਾਣੀ', 'ਜਗ', 'ਜਗਤ', 'ਜਗਤੁ',
    'ਸਾਚ', 'ਸਾਚਾ', 'ਸਾਚੀ', 'ਸਾਚੁ', 'ਸਚੁ', 'ਸਚਾ', 'ਸਚੀ',
    'ਪਾਪ', 'ਪੁੰਨ', 'ਧਰਮ', 'ਧਰਮੁ', 'ਕਰਮ', 'ਕਰਮੁ',
    'ਮਾਇਆ', 'ਭਗਤ', 'ਭਗਤਿ', 'ਸੇਵ', 'ਸੇਵਾ', 'ਸਿਮਰ', 'ਸਿਮਰਨ',
}

# Common honorifics in Gurbani
HONORIFICS = {
    'ਜੀ', 'ਜੀਉ', 'ਸਾਹਿਬ', 'ਸ੍ਰੀ', 'ਭਾਈ', 'ਬਾਬਾ',
    'ਮਹਲਾ', 'ਮਹਲ', 'ਗੁਰੂ', 'ਦੇਵ', 'ਦਾਸ', 'ਸੇਵਕ',
    'ਨਾਨਕ', 'ਕਬੀਰ', 'ਰਵਿਦਾਸ', 'ਫਰੀਦ', 'ਨਾਮਦੇਵ',
    'ਤ੍ਰਿਲੋਚਨ', 'ਬੇਣੀ', 'ਧੰਨਾ', 'ਪੀਪਾ', 'ਸੈਣ',
    'ਸੂਰਦਾਸ', 'ਪਰਮਾਨੰਦ', 'ਸਧਨਾ', 'ਰਾਮਾਨੰਦ', 'ਜੈਦੇਵ',
}

# Common Raag names (for context)
RAAG_NAMES = {
    'ਸਿਰੀ', 'ਮਾਝ', 'ਗਉੜੀ', 'ਆਸਾ', 'ਗੂਜਰੀ', 'ਦੇਵਗੰਧਾਰੀ',
    'ਬਿਹਾਗੜਾ', 'ਵਡਹੰਸ', 'ਸੋਰਠਿ', 'ਧਨਾਸਰੀ', 'ਜੈਤਸਰੀ',
    'ਟੋਡੀ', 'ਬੈਰਾੜੀ', 'ਤਿਲੰਗ', 'ਸੂਹੀ', 'ਬਿਲਾਵਲ',
    'ਗੋਂਡ', 'ਰਾਮਕਲੀ', 'ਨਟ', 'ਮਾਲੀ', 'ਮਾਰੂ',
    'ਤੁਖਾਰੀ', 'ਕੇਦਾਰਾ', 'ਭੈਰਉ', 'ਬਸੰਤ', 'ਸਾਰੰਗ',
    'ਮਲਾਰ', 'ਕਾਨੜਾ', 'ਕਲਿਆਣ', 'ਪ੍ਰਭਾਤੀ', 'ਜੈਜਾਵੰਤੀ',
}

# Output policy settings
@dataclass
class OutputPolicy:
    """
    Output policy for transcription.
    
    Controls how the output is formatted and what transformations are allowed.
    """
    # Script settings
    output_script: str = "gurmukhi"  # Only gurmukhi supported
    strict_gurmukhi: bool = True     # Enforce Gurmukhi-only output
    
    # Normalization settings
    preserve_verse_punctuation: bool = True
    modernize_spelling: bool = False  # Do NOT modernize to standard Punjabi
    expand_abbreviations: bool = False  # Do NOT expand
    paraphrase: bool = False  # Do NOT paraphrase
    
    # Domain settings
    domain_mode: DomainMode = DomainMode.SGGS
    
    @classmethod
    def for_sggs(cls) -> 'OutputPolicy':
        """Get output policy for SGGS mode."""
        return cls(
            domain_mode=DomainMode.SGGS,
            strict_gurmukhi=True,
            modernize_spelling=False,
        )
    
    @classmethod
    def for_dasam(cls) -> 'OutputPolicy':
        """Get output policy for Dasam Granth mode."""
        return cls(
            domain_mode=DomainMode.DASAM,
            strict_gurmukhi=True,
            modernize_spelling=False,
        )
    
    @classmethod
    def for_generic(cls) -> 'OutputPolicy':
        """Get output policy for generic Punjabi mode."""
        return cls(
            domain_mode=DomainMode.GENERIC_PUNJABI,
            strict_gurmukhi=True,  # Still enforce Gurmukhi
            modernize_spelling=False,
        )


def get_output_policy(mode: DomainMode) -> OutputPolicy:
    """Get output policy for a domain mode."""
    policy_map = {
        DomainMode.SGGS: OutputPolicy.for_sggs,
        DomainMode.DASAM: OutputPolicy.for_dasam,
        DomainMode.GENERIC_PUNJABI: OutputPolicy.for_generic,
    }
    factory = policy_map.get(mode, OutputPolicy.for_sggs)
    return factory()


# Priority lists for use in rescoring/biasing
PRIORITY_SGGS = [
    LanguageRegister.SANT_BHASHA,
    LanguageRegister.BRAJ_BHASHA,
    LanguageRegister.OLD_PUNJABI,
    LanguageRegister.AVADHI,
    LanguageRegister.SANSKRIT_DERIVED,
    LanguageRegister.PERSIAN_DERIVED,
    LanguageRegister.ARABIC_DERIVED,
    LanguageRegister.APABHRAMSHA,
]

PRIORITY_DASAM = [
    LanguageRegister.BRAJ_BHASHA,
    LanguageRegister.SANSKRIT_DERIVED,
    LanguageRegister.SANT_BHASHA,
    LanguageRegister.OLD_PUNJABI,
    LanguageRegister.PERSIAN_DERIVED,
    LanguageRegister.ARABIC_DERIVED,
    LanguageRegister.APABHRAMSHA,
]


def get_priority_list(mode: DomainMode) -> List[LanguageRegister]:
    """Get priority list for a domain mode."""
    if mode == DomainMode.DASAM:
        return PRIORITY_DASAM
    return PRIORITY_SGGS  # Default to SGGS

