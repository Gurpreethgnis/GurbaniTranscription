"""
Domain Lexicon Builder for SGGS and Dasam Granth.

Builds and manages a domain-specific vocabulary from scripture databases
for use in constrained decoding and spelling correction.
"""
import json
import logging
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import config
from data.language_domains import (
    COMMON_PARTICLES,
    HONORIFICS,
    RAAG_NAMES,
    DomainMode,
    GurmukhiScript,
    get_domain_priorities,
)

logger = logging.getLogger(__name__)


@dataclass
class DomainLexicon:
    """
    Domain-specific vocabulary for Gurbani transcription.
    
    Contains vocabulary sets extracted from SGGS and Dasam Granth databases,
    plus curated lists of common particles, honorifics, and theological terms.
    """
    # Vocabulary from scripture databases
    sggs_vocab: Set[str] = field(default_factory=set)       # Words from SGGS
    dasam_vocab: Set[str] = field(default_factory=set)      # Words from Dasam Granth
    
    # Curated vocabulary lists
    common_particles: Set[str] = field(default_factory=lambda: set(COMMON_PARTICLES))
    honorifics: Set[str] = field(default_factory=lambda: set(HONORIFICS))
    raag_names: Set[str] = field(default_factory=lambda: set(RAAG_NAMES))
    
    # Theological and domain-specific terms (extracted + curated)
    theological_terms: Set[str] = field(default_factory=set)
    
    # Word frequencies for scoring
    word_frequencies: Dict[str, int] = field(default_factory=dict)
    
    # Build metadata
    build_version: str = "1.0"
    sggs_line_count: int = 0
    dasam_line_count: int = 0
    
    def get_combined_vocab(self, mode: DomainMode = DomainMode.SGGS) -> Set[str]:
        """
        Get combined vocabulary set weighted by domain mode.
        
        Args:
            mode: Domain mode to determine vocabulary weights
        
        Returns:
            Combined vocabulary set
        """
        # Always include common vocabulary
        combined = (
            self.common_particles |
            self.honorifics |
            self.raag_names |
            self.theological_terms
        )
        
        if mode == DomainMode.SGGS:
            # SGGS mode: prioritize SGGS vocab
            combined |= self.sggs_vocab
            combined |= self.dasam_vocab  # Include but don't prioritize
        elif mode == DomainMode.DASAM:
            # Dasam mode: prioritize Dasam vocab
            combined |= self.dasam_vocab
            combined |= self.sggs_vocab  # Include but don't prioritize
        else:
            # Generic mode: include all
            combined |= self.sggs_vocab
            combined |= self.dasam_vocab
        
        return combined
    
    def contains(self, word: str, mode: DomainMode = DomainMode.SGGS) -> bool:
        """Check if word is in domain vocabulary."""
        return word in self.get_combined_vocab(mode)
    
    def get_frequency(self, word: str) -> int:
        """Get word frequency (higher = more common in corpus)."""
        return self.word_frequencies.get(word, 0)
    
    def get_high_frequency_words(self, min_freq: int = 10) -> Set[str]:
        """Get words with frequency above threshold."""
        return {w for w, f in self.word_frequencies.items() if f >= min_freq}
    
    @property
    def total_vocab_size(self) -> int:
        """Total unique vocabulary count."""
        return len(self.get_combined_vocab(DomainMode.SGGS))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'build_version': self.build_version,
            'sggs_vocab': list(self.sggs_vocab),
            'dasam_vocab': list(self.dasam_vocab),
            'common_particles': list(self.common_particles),
            'honorifics': list(self.honorifics),
            'raag_names': list(self.raag_names),
            'theological_terms': list(self.theological_terms),
            'word_frequencies': self.word_frequencies,
            'sggs_line_count': self.sggs_line_count,
            'dasam_line_count': self.dasam_line_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainLexicon':
        """Load from dictionary (JSON deserialization)."""
        return cls(
            build_version=data.get('build_version', '1.0'),
            sggs_vocab=set(data.get('sggs_vocab', [])),
            dasam_vocab=set(data.get('dasam_vocab', [])),
            common_particles=set(data.get('common_particles', COMMON_PARTICLES)),
            honorifics=set(data.get('honorifics', HONORIFICS)),
            raag_names=set(data.get('raag_names', RAAG_NAMES)),
            theological_terms=set(data.get('theological_terms', [])),
            word_frequencies=data.get('word_frequencies', {}),
            sggs_line_count=data.get('sggs_line_count', 0),
            dasam_line_count=data.get('dasam_line_count', 0),
        )
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save lexicon to JSON file."""
        path = path or config.DOMAIN_LEXICON_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved domain lexicon to {path} ({self.total_vocab_size} words)")
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'DomainLexicon':
        """Load lexicon from JSON file."""
        path = path or config.DOMAIN_LEXICON_PATH
        if not path.exists():
            logger.warning(f"Lexicon file not found at {path}, returning empty lexicon")
            return cls()
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lexicon = cls.from_dict(data)
        logger.info(f"Loaded domain lexicon from {path} ({lexicon.total_vocab_size} words)")
        return lexicon


class LexiconBuilder:
    """
    Builds domain lexicon from scripture databases.
    
    Extracts vocabulary from SGGS and Dasam Granth databases and creates
    a unified lexicon for use in constrained decoding and correction.
    """
    
    # Gurmukhi word pattern (matches Gurmukhi words)
    GURMUKHI_WORD_PATTERN = re.compile(r'[\u0A00-\u0A7F]+')
    
    # Minimum word length to include
    MIN_WORD_LENGTH = 2
    
    # Theological terms to always include (high-priority domain vocabulary)
    THEOLOGICAL_TERMS = {
        # Names of God
        'ਵਾਹਿਗੁਰੂ', 'ਅਕਾਲ', 'ਪੁਰਖ', 'ਨਿਰਭਉ', 'ਨਿਰਵੈਰ',
        'ਅਕਾਲ', 'ਮੂਰਤਿ', 'ਅਜੂਨੀ', 'ਸੈਭੰ', 'ਗੁਰਪ੍ਰਸਾਦਿ',
        'ਸਤਿਨਾਮੁ', 'ਕਰਤਾ', 'ਪੁਰਖੁ', 'ਓਅੰਕਾਰ', 'ਏਕੰਕਾਰ',
        
        # Core concepts
        'ਨਾਮ', 'ਨਾਮੁ', 'ਸਬਦ', 'ਸਬਦੁ', 'ਹੁਕਮ', 'ਹੁਕਮੁ',
        'ਗੁਰ', 'ਗੁਰੁ', 'ਸਤਿਗੁਰ', 'ਸਤਿਗੁਰੁ', 'ਗੁਰਬਾਣੀ',
        'ਸੰਗਤ', 'ਸਾਧਸੰਗ', 'ਸੇਵਾ', 'ਸਿਮਰਨ', 'ਭਗਤਿ',
        
        # Spiritual states
        'ਸਹਜ', 'ਅਨੰਦ', 'ਆਨੰਦ', 'ਮੁਕਤਿ', 'ਮੋਖ', 'ਜੀਵਨਮੁਕਤ',
        'ਸੁੰਨ', 'ਸਮਾਧਿ', 'ਸਚਖੰਡ', 'ਧਰਮਖੰਡ', 'ਗਿਆਨਖੰਡ',
        'ਸਰਮਖੰਡ', 'ਕਰਮਖੰਡ',
        
        # Key terms from Mool Mantar and Japji
        'ਇੱਕ', 'ਸਤਿ', 'ਕਰਤਾਰ', 'ਅਕਾਲ', 'ਮੂਰਤਿ', 'ਅਜੂਨੀ',
        'ਸੈਭੰ', 'ਗੁਰ', 'ਪ੍ਰਸਾਦਿ', 'ਜਪੁ', 'ਆਦਿ', 'ਸਚੁ',
        'ਜੁਗਾਦਿ', 'ਹੈ', 'ਭੀ', 'ਨਾਨਕ', 'ਹੋਸੀ',
        
        # Five thieves (vices)
        'ਕਾਮ', 'ਕ੍ਰੋਧ', 'ਲੋਭ', 'ਮੋਹ', 'ਹੰਕਾਰ', 'ਅਹੰਕਾਰ',
        
        # Five virtues
        'ਸਤ', 'ਸੰਤੋਖ', 'ਦਇਆ', 'ਧਰਮ', 'ਨਿਮਰਤਾ',
        
        # Common terms
        'ਮਾਇਆ', 'ਸੰਸਾਰ', 'ਜਗ', 'ਜਗਤ', 'ਜਨਮ', 'ਮਰਣ',
        'ਪ੍ਰਾਣੀ', 'ਜੀਵ', 'ਆਤਮਾ', 'ਮਨ', 'ਤਨ', 'ਧਨ',
        'ਪਾਪ', 'ਪੁੰਨ', 'ਕਰਮ', 'ਧਰਮ', 'ਭਾਗ', 'ਨਸੀਬ',
        
        # Authors/Bhagats
        'ਨਾਨਕ', 'ਅੰਗਦ', 'ਅਮਰਦਾਸ', 'ਰਾਮਦਾਸ', 'ਅਰਜਨ', 'ਅਰਜੁਨ',
        'ਤੇਗ', 'ਬਹਾਦਰ', 'ਗੋਬਿੰਦ', 'ਕਬੀਰ', 'ਫਰੀਦ', 'ਰਵਿਦਾਸ',
        'ਨਾਮਦੇਵ', 'ਤ੍ਰਿਲੋਚਨ', 'ਬੇਣੀ', 'ਧੰਨਾ', 'ਪੀਪਾ', 'ਸੈਣ',
        
        # Dasam Granth specific
        'ਚੰਡੀ', 'ਦੇਵੀ', 'ਦੇਵਤਾ', 'ਅਕਾਲ', 'ਪੁਰਖ', 'ਖੰਡਾ',
        'ਚੱਕਰ', 'ਬਾਣ', 'ਖੜਗ', 'ਜੁੱਧ', 'ਯੁੱਧ', 'ਸੂਰਾ', 'ਵੀਰ',
    }
    
    def __init__(
        self,
        sggs_db_path: Optional[Path] = None,
        dasam_db_path: Optional[Path] = None
    ):
        """
        Initialize lexicon builder.
        
        Args:
            sggs_db_path: Path to SGGS database (defaults to config)
            dasam_db_path: Path to Dasam Granth database (defaults to config)
        """
        self.sggs_db_path = sggs_db_path or config.SCRIPTURE_DB_PATH
        self.dasam_db_path = dasam_db_path or config.DASAM_DB_PATH
    
    def _extract_words_from_line(self, line: str) -> List[str]:
        """
        Extract Gurmukhi words from a text line.
        
        Args:
            line: Text line to extract words from
        
        Returns:
            List of Gurmukhi words
        """
        if not line:
            return []
        
        # Find all Gurmukhi word matches
        words = self.GURMUKHI_WORD_PATTERN.findall(line)
        
        # Filter by minimum length
        return [w for w in words if len(w) >= self.MIN_WORD_LENGTH]
    
    def _extract_from_sggs_db(self) -> Tuple[Set[str], Dict[str, int], int]:
        """
        Extract vocabulary from SGGS database.
        
        Returns:
            Tuple of (vocabulary set, word frequencies, line count)
        """
        vocab = set()
        frequencies = Counter()
        line_count = 0
        
        if not self.sggs_db_path.exists():
            logger.warning(f"SGGS database not found at {self.sggs_db_path}")
            return vocab, dict(frequencies), line_count
        
        try:
            conn = sqlite3.connect(str(self.sggs_db_path))
            conn.row_factory = sqlite3.Row
            
            # Get table and column info
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            # Find lines table
            lines_table = None
            for t in ['lines', 'Lines', 'LINES', 'gurbani', 'Gurbani']:
                if t in tables:
                    lines_table = t
                    break
            
            if not lines_table:
                logger.warning("Could not find lines table in SGGS database")
                conn.close()
                return vocab, dict(frequencies), line_count
            
            # Get columns
            cursor = conn.execute(f"PRAGMA table_info({lines_table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Find text column
            text_column = None
            for col in ['gurmukhi', 'text', 'line', 'gurbani', 'line_text']:
                if col in columns:
                    text_column = col
                    break
            
            if not text_column:
                logger.warning("Could not find text column in SGGS database")
                conn.close()
                return vocab, dict(frequencies), line_count
            
            # Extract words from all lines
            cursor = conn.execute(f"SELECT {text_column} FROM {lines_table}")
            
            for row in cursor:
                text = row[0] if row[0] else ""
                words = self._extract_words_from_line(text)
                vocab.update(words)
                frequencies.update(words)
                line_count += 1
            
            conn.close()
            logger.info(f"Extracted {len(vocab)} unique words from {line_count} SGGS lines")
            
        except sqlite3.Error as e:
            logger.error(f"Error reading SGGS database: {e}")
        
        return vocab, dict(frequencies), line_count
    
    def _extract_from_dasam_db(self) -> Tuple[Set[str], Dict[str, int], int]:
        """
        Extract vocabulary from Dasam Granth database.
        
        Returns:
            Tuple of (vocabulary set, word frequencies, line count)
        """
        vocab = set()
        frequencies = Counter()
        line_count = 0
        
        if not self.dasam_db_path.exists():
            logger.warning(f"Dasam database not found at {self.dasam_db_path}")
            return vocab, dict(frequencies), line_count
        
        try:
            conn = sqlite3.connect(str(self.dasam_db_path))
            conn.row_factory = sqlite3.Row
            
            # Check if lines table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='lines'"
            )
            if not cursor.fetchone():
                logger.warning("Lines table not found in Dasam database")
                conn.close()
                return vocab, dict(frequencies), line_count
            
            # Extract words from all lines
            cursor = conn.execute("SELECT gurmukhi FROM lines")
            
            for row in cursor:
                text = row[0] if row[0] else ""
                words = self._extract_words_from_line(text)
                vocab.update(words)
                frequencies.update(words)
                line_count += 1
            
            conn.close()
            logger.info(f"Extracted {len(vocab)} unique words from {line_count} Dasam lines")
            
        except sqlite3.Error as e:
            logger.error(f"Error reading Dasam database: {e}")
        
        return vocab, dict(frequencies), line_count
    
    def build(self) -> DomainLexicon:
        """
        Build domain lexicon from scripture databases.
        
        Returns:
            DomainLexicon with extracted vocabulary
        """
        logger.info("Building domain lexicon from scripture databases...")
        
        # Extract from SGGS
        sggs_vocab, sggs_freq, sggs_lines = self._extract_from_sggs_db()
        
        # Extract from Dasam
        dasam_vocab, dasam_freq, dasam_lines = self._extract_from_dasam_db()
        
        # Merge frequencies
        combined_freq = Counter(sggs_freq)
        combined_freq.update(dasam_freq)
        
        # Build lexicon
        lexicon = DomainLexicon(
            sggs_vocab=sggs_vocab,
            dasam_vocab=dasam_vocab,
            common_particles=set(COMMON_PARTICLES),
            honorifics=set(HONORIFICS),
            raag_names=set(RAAG_NAMES),
            theological_terms=set(self.THEOLOGICAL_TERMS),
            word_frequencies=dict(combined_freq),
            sggs_line_count=sggs_lines,
            dasam_line_count=dasam_lines,
        )
        
        logger.info(
            f"Built lexicon with {lexicon.total_vocab_size} total words "
            f"(SGGS: {len(sggs_vocab)}, Dasam: {len(dasam_vocab)})"
        )
        
        return lexicon
    
    def build_and_save(self, path: Optional[Path] = None) -> DomainLexicon:
        """
        Build lexicon and save to file.
        
        Args:
            path: Path to save lexicon (defaults to config)
        
        Returns:
            Built DomainLexicon
        """
        lexicon = self.build()
        lexicon.save(path)
        return lexicon


# Singleton instance for global access
_lexicon_instance: Optional[DomainLexicon] = None


def get_domain_lexicon(rebuild: bool = False) -> DomainLexicon:
    """
    Get or build domain lexicon (singleton).
    
    Args:
        rebuild: Force rebuild from databases
    
    Returns:
        DomainLexicon instance
    """
    global _lexicon_instance
    
    if _lexicon_instance is not None and not rebuild:
        return _lexicon_instance
    
    # Try to load from file
    if not rebuild and config.DOMAIN_LEXICON_PATH.exists():
        _lexicon_instance = DomainLexicon.load()
        return _lexicon_instance
    
    # Build from databases
    builder = LexiconBuilder()
    _lexicon_instance = builder.build_and_save()
    return _lexicon_instance


def is_in_domain_vocab(word: str, mode: DomainMode = DomainMode.SGGS) -> bool:
    """
    Check if a word is in the domain vocabulary.
    
    Args:
        word: Word to check
        mode: Domain mode for vocabulary selection
    
    Returns:
        True if word is in domain vocabulary
    """
    lexicon = get_domain_lexicon()
    return lexicon.contains(word, mode)


def get_word_frequency(word: str) -> int:
    """
    Get word frequency in the domain corpus.
    
    Args:
        word: Word to look up
    
    Returns:
        Frequency count (0 if not found)
    """
    lexicon = get_domain_lexicon()
    return lexicon.get_frequency(word)

