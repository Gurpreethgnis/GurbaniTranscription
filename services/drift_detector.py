"""
Anti-Drift Validator for Gurbani Transcription.

Detects when ASR output drifts from the expected Gurbani domain into
modern slang, English, or unrelated languages. Provides diagnostic
metrics and remediation recommendations.
"""
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import config
from data.language_domains import DomainMode, GurmukhiScript
from data.domain_lexicon import get_domain_lexicon, DomainLexicon
from services.script_lock import ScriptLock, ScriptAnalysis

logger = logging.getLogger(__name__)


class DriftSeverity(Enum):
    """Severity levels for drift detection."""
    NONE = "none"           # No drift detected
    LOW = "low"             # Minor drift, likely acceptable
    MEDIUM = "medium"       # Moderate drift, correction recommended
    HIGH = "high"           # Significant drift, re-decode recommended
    CRITICAL = "critical"   # Critical drift, likely garbage output


class DriftType(Enum):
    """Types of drift detected."""
    SCRIPT_MIX = "script_mix"           # Mixed scripts (Latin, Devanagari)
    ENGLISH_DRIFT = "english_drift"     # English words/phrases
    HIGH_OOV = "high_oov"               # High out-of-vocabulary ratio
    URL_PATTERN = "url_pattern"         # URLs or email addresses
    HINGLISH = "hinglish"               # Hindi-English mix patterns
    MODERN_SLANG = "modern_slang"       # Modern slang/colloquialisms
    EMOJI_SPECIAL = "emoji_special"     # Emojis and special characters
    LOW_PURITY = "low_purity"           # Low script purity


@dataclass
class DriftDiagnostic:
    """
    Diagnostic results from drift detection.
    
    Contains all metrics and analysis for a piece of text.
    """
    # Core metrics
    script_purity: float              # Gurmukhi chars / total script chars
    latin_ratio: float                # Latin chars / total chars
    oov_ratio: float                  # Out-of-vocabulary words / total words
    
    # Script analysis
    script_analysis: Optional[ScriptAnalysis] = None
    
    # Drift classification
    severity: DriftSeverity = DriftSeverity.NONE
    drift_types: List[DriftType] = field(default_factory=list)
    
    # Detailed findings
    english_sequences: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    oov_words: List[str] = field(default_factory=list)
    
    # Recommendations
    should_redecode: bool = False
    should_correct: bool = False
    should_reject: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'script_purity': self.script_purity,
            'latin_ratio': self.latin_ratio,
            'oov_ratio': self.oov_ratio,
            'severity': self.severity.value,
            'drift_types': [dt.value for dt in self.drift_types],
            'english_sequences': self.english_sequences[:10],  # Limit
            'url_patterns': self.url_patterns,
            'oov_words': self.oov_words[:20],  # Limit
            'should_redecode': self.should_redecode,
            'should_correct': self.should_correct,
            'should_reject': self.should_reject,
        }


class DriftDetector:
    """
    Detects and diagnoses drift in ASR output.
    
    Uses multiple heuristics to identify when transcription output has
    drifted from the expected Gurbani linguistic domain.
    """
    
    # Blocklist patterns
    URL_PATTERN = re.compile(
        r'https?://[^\s]+|'
        r'www\.[^\s]+|'
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    # English word pattern (consecutive Latin letters)
    ENGLISH_WORD_PATTERN = re.compile(r'[A-Za-z]{3,}')
    
    # English sequence pattern (multiple English words together)
    ENGLISH_SEQUENCE_PATTERN = re.compile(r'(?:[A-Za-z]+\s+){2,}[A-Za-z]+')
    
    # Hinglish markers (Hindi words in Latin script)
    HINGLISH_MARKERS = {
        'hai', 'hain', 'ho', 'tha', 'thi', 'the',
        'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'par',
        'aur', 'lekin', 'toh', 'bhi', 'kya', 'kyun',
        'nahi', 'nahin', 'ji', 'jee', 'bahut', 'achha',
        'acha', 'theek', 'thik', 'ok', 'okay',
    }
    
    # Modern slang markers (avoid in Gurbani)
    MODERN_SLANG = {
        'lol', 'omg', 'btw', 'brb', 'idk', 'fyi',
        'cool', 'bro', 'dude', 'guys', 'like',
        'literally', 'basically', 'actually', 'random',
    }
    
    # Emoji and special character pattern
    EMOJI_PATTERN = re.compile(
        r'[\U0001F600-\U0001F64F]|'  # Emoticons
        r'[\U0001F300-\U0001F5FF]|'  # Symbols & Pictographs
        r'[\U0001F680-\U0001F6FF]|'  # Transport & Map
        r'[\U0001F1E0-\U0001F1FF]|'  # Flags
        r'[\U00002702-\U000027B0]|'  # Dingbats
        r'[\U0001F900-\U0001F9FF]'   # Supplemental Symbols
    )
    
    # Gurmukhi word pattern
    GURMUKHI_WORD_PATTERN = re.compile(r'[\u0A00-\u0A7F]+')
    
    def __init__(
        self,
        mode: DomainMode = DomainMode.SGGS,
        script_purity_threshold: Optional[float] = None,
        latin_ratio_threshold: Optional[float] = None,
        oov_ratio_threshold: Optional[float] = None
    ):
        """
        Initialize drift detector.
        
        Args:
            mode: Domain mode for vocabulary lookup
            script_purity_threshold: Minimum script purity (default from config)
            latin_ratio_threshold: Maximum Latin ratio (default from config)
            oov_ratio_threshold: Maximum OOV ratio (default from config)
        """
        self.mode = mode
        self.script_lock = ScriptLock(mode)
        self._lexicon: Optional[DomainLexicon] = None
        
        # Thresholds
        self.script_purity_threshold = (
            script_purity_threshold or config.SCRIPT_PURITY_THRESHOLD
        )
        self.latin_ratio_threshold = (
            latin_ratio_threshold or config.LATIN_RATIO_THRESHOLD
        )
        self.oov_ratio_threshold = (
            oov_ratio_threshold or config.OOV_RATIO_THRESHOLD
        )
    
    @property
    def lexicon(self) -> DomainLexicon:
        """Get domain lexicon (lazy load)."""
        if self._lexicon is None:
            self._lexicon = get_domain_lexicon()
        return self._lexicon
    
    def _extract_gurmukhi_words(self, text: str) -> List[str]:
        """Extract Gurmukhi words from text."""
        return self.GURMUKHI_WORD_PATTERN.findall(text)
    
    def _calculate_oov_ratio(self, text: str) -> Tuple[float, List[str]]:
        """
        Calculate out-of-vocabulary ratio.
        
        Args:
            text: Text to analyze
        
        Returns:
            Tuple of (oov_ratio, list of OOV words)
        """
        words = self._extract_gurmukhi_words(text)
        
        if not words:
            return 0.0, []
        
        oov_words = []
        for word in words:
            if len(word) >= 2 and not self.lexicon.contains(word, self.mode):
                oov_words.append(word)
        
        oov_ratio = len(oov_words) / len(words)
        return oov_ratio, oov_words
    
    def _find_english_sequences(self, text: str) -> List[str]:
        """Find English word sequences (3+ consecutive words)."""
        sequences = self.ENGLISH_SEQUENCE_PATTERN.findall(text)
        return [s.strip() for s in sequences if len(s.split()) >= 3]
    
    def _find_urls(self, text: str) -> List[str]:
        """Find URL and email patterns."""
        return self.URL_PATTERN.findall(text)
    
    def _detect_hinglish(self, text: str) -> bool:
        """Detect Hinglish patterns (Hindi in Latin script)."""
        words_lower = set(text.lower().split())
        hinglish_count = len(words_lower & self.HINGLISH_MARKERS)
        return hinglish_count >= 2
    
    def _detect_modern_slang(self, text: str) -> bool:
        """Detect modern slang."""
        words_lower = set(text.lower().split())
        slang_count = len(words_lower & self.MODERN_SLANG)
        return slang_count >= 1
    
    def _detect_emojis(self, text: str) -> bool:
        """Detect emojis and special characters."""
        return bool(self.EMOJI_PATTERN.search(text))
    
    def _classify_severity(
        self,
        script_purity: float,
        latin_ratio: float,
        oov_ratio: float,
        drift_types: List[DriftType]
    ) -> DriftSeverity:
        """
        Classify drift severity based on metrics.
        
        Returns:
            DriftSeverity classification
        """
        # Critical: Very low purity or URLs/high English
        if script_purity < 0.5 or DriftType.URL_PATTERN in drift_types:
            return DriftSeverity.CRITICAL
        
        # High: Multiple drift types or significant metric failures
        high_conditions = [
            script_purity < 0.80,
            latin_ratio > 0.10,
            len(drift_types) >= 3,
            DriftType.ENGLISH_DRIFT in drift_types and latin_ratio > 0.05,
        ]
        if sum(high_conditions) >= 2:
            return DriftSeverity.HIGH
        
        # Medium: Some drift detected
        medium_conditions = [
            script_purity < self.script_purity_threshold,
            latin_ratio > self.latin_ratio_threshold,
            oov_ratio > self.oov_ratio_threshold,
            len(drift_types) >= 2,
        ]
        if sum(medium_conditions) >= 2:
            return DriftSeverity.MEDIUM
        
        # Low: Minor issues
        if drift_types or script_purity < 0.98:
            return DriftSeverity.LOW
        
        return DriftSeverity.NONE
    
    def detect(self, text: str) -> DriftDiagnostic:
        """
        Detect drift in transcription output.
        
        Args:
            text: Text to analyze
        
        Returns:
            DriftDiagnostic with all metrics and recommendations
        """
        if not text or not text.strip():
            return DriftDiagnostic(
                script_purity=1.0,
                latin_ratio=0.0,
                oov_ratio=0.0,
                severity=DriftSeverity.NONE,
            )
        
        # Script analysis
        script_analysis = self.script_lock.analyze(text)
        script_purity = script_analysis.script_purity
        latin_ratio = script_analysis.latin_ratio
        
        # OOV analysis
        oov_ratio, oov_words = self._calculate_oov_ratio(text)
        
        # Detect drift types
        drift_types = []
        
        # Script mix
        if script_purity < self.script_purity_threshold:
            drift_types.append(DriftType.LOW_PURITY)
        
        if script_analysis.devanagari_chars > 0 or script_analysis.arabic_chars > 0:
            drift_types.append(DriftType.SCRIPT_MIX)
        
        # English/Latin detection
        english_sequences = self._find_english_sequences(text)
        if english_sequences or latin_ratio > self.latin_ratio_threshold:
            drift_types.append(DriftType.ENGLISH_DRIFT)
        
        # URL patterns
        url_patterns = self._find_urls(text)
        if url_patterns:
            drift_types.append(DriftType.URL_PATTERN)
        
        # Hinglish
        if self._detect_hinglish(text):
            drift_types.append(DriftType.HINGLISH)
        
        # Modern slang
        if self._detect_modern_slang(text):
            drift_types.append(DriftType.MODERN_SLANG)
        
        # Emojis
        if self._detect_emojis(text):
            drift_types.append(DriftType.EMOJI_SPECIAL)
        
        # High OOV
        if oov_ratio > self.oov_ratio_threshold:
            drift_types.append(DriftType.HIGH_OOV)
        
        # Classify severity
        severity = self._classify_severity(
            script_purity, latin_ratio, oov_ratio, drift_types
        )
        
        # Determine recommendations
        should_reject = severity == DriftSeverity.CRITICAL
        should_redecode = severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)
        should_correct = severity in (DriftSeverity.MEDIUM, DriftSeverity.LOW)
        
        return DriftDiagnostic(
            script_purity=script_purity,
            latin_ratio=latin_ratio,
            oov_ratio=oov_ratio,
            script_analysis=script_analysis,
            severity=severity,
            drift_types=drift_types,
            english_sequences=english_sequences,
            url_patterns=url_patterns,
            oov_words=oov_words,
            should_redecode=should_redecode,
            should_correct=should_correct,
            should_reject=should_reject,
        )
    
    def is_acceptable(self, text: str, max_severity: DriftSeverity = DriftSeverity.LOW) -> bool:
        """
        Check if text is acceptable (below max severity).
        
        Args:
            text: Text to check
            max_severity: Maximum acceptable severity
        
        Returns:
            True if text is acceptable
        """
        diagnostic = self.detect(text)
        
        severity_order = [
            DriftSeverity.NONE,
            DriftSeverity.LOW,
            DriftSeverity.MEDIUM,
            DriftSeverity.HIGH,
            DriftSeverity.CRITICAL,
        ]
        
        return severity_order.index(diagnostic.severity) <= severity_order.index(max_severity)
    
    def validate_thresholds(
        self,
        text: str
    ) -> Tuple[bool, bool, bool]:
        """
        Validate against configured thresholds.
        
        Returns:
            Tuple of (script_ok, latin_ok, oov_ok)
        """
        diagnostic = self.detect(text)
        
        script_ok = diagnostic.script_purity >= self.script_purity_threshold
        latin_ok = diagnostic.latin_ratio <= self.latin_ratio_threshold
        oov_ok = diagnostic.oov_ratio <= self.oov_ratio_threshold
        
        return script_ok, latin_ok, oov_ok


def detect_drift(
    text: str,
    mode: DomainMode = DomainMode.SGGS
) -> DriftDiagnostic:
    """
    Convenience function to detect drift in text.
    
    Args:
        text: Text to analyze
        mode: Domain mode
    
    Returns:
        DriftDiagnostic with analysis
    """
    detector = DriftDetector(mode)
    return detector.detect(text)


def is_drift_acceptable(
    text: str,
    mode: DomainMode = DomainMode.SGGS,
    max_severity: DriftSeverity = DriftSeverity.LOW
) -> bool:
    """
    Check if drift level is acceptable.
    
    Args:
        text: Text to check
        mode: Domain mode
        max_severity: Maximum acceptable severity
    
    Returns:
        True if drift is acceptable
    """
    detector = DriftDetector(mode)
    return detector.is_acceptable(text, max_severity)


def get_drift_metrics(text: str) -> Dict[str, float]:
    """
    Get simple drift metrics dictionary.
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary with script_purity, latin_ratio, oov_ratio
    """
    diagnostic = detect_drift(text)
    return {
        'script_purity': diagnostic.script_purity,
        'latin_ratio': diagnostic.latin_ratio,
        'oov_ratio': diagnostic.oov_ratio,
    }

