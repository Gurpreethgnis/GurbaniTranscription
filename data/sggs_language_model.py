"""
SGGS N-gram Language Model.

Builds word-level and character-level N-gram language models from the
SGGS corpus for rescoring ASR hypotheses.
"""
import logging
import math
import pickle
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import config

logger = logging.getLogger(__name__)


@dataclass
class NGramModel:
    """
    N-gram language model data structure.
    
    Stores N-gram counts and provides probability calculations.
    """
    n: int                                      # N-gram order (e.g., 3 for trigram)
    ngram_counts: Dict[tuple, int]              # (n-1 context, word) -> count
    context_counts: Dict[tuple, int]            # context -> total count
    vocabulary: set                             # Set of all words/chars
    total_tokens: int                           # Total token count
    
    # Smoothing parameters
    alpha: float = 0.01                         # Additive smoothing parameter
    
    def get_probability(self, ngram: tuple) -> float:
        """
        Get probability of an N-gram using additive smoothing.
        
        Args:
            ngram: Tuple of N tokens (context + current)
        
        Returns:
            Smoothed probability P(current | context)
        """
        if len(ngram) != self.n:
            raise ValueError(f"Expected {self.n}-gram, got {len(ngram)}")
        
        context = ngram[:-1]
        current = ngram[-1]
        
        # Get counts
        ngram_count = self.ngram_counts.get(ngram, 0)
        context_count = self.context_counts.get(context, 0)
        vocab_size = len(self.vocabulary)
        
        # Additive (Laplace) smoothing
        prob = (ngram_count + self.alpha) / (context_count + self.alpha * vocab_size)
        
        return prob
    
    def get_log_probability(self, ngram: tuple) -> float:
        """Get log probability of an N-gram."""
        prob = self.get_probability(ngram)
        return math.log(prob) if prob > 0 else float('-inf')
    
    def score_sequence(self, tokens: List[str]) -> float:
        """
        Score a sequence of tokens using the N-gram model.
        
        Args:
            tokens: List of tokens (words or characters)
        
        Returns:
            Log probability of the sequence
        """
        if len(tokens) < self.n:
            return 0.0
        
        # Pad with start tokens
        padded = ['<s>'] * (self.n - 1) + tokens + ['</s>']
        
        log_prob = 0.0
        for i in range(self.n - 1, len(padded)):
            ngram = tuple(padded[i - self.n + 1:i + 1])
            log_prob += self.get_log_probability(ngram)
        
        return log_prob
    
    def perplexity(self, tokens: List[str]) -> float:
        """
        Calculate perplexity of a sequence.
        
        Lower perplexity = better fit to the model.
        """
        log_prob = self.score_sequence(tokens)
        n_tokens = len(tokens) + 1  # +1 for </s>
        
        if n_tokens == 0:
            return float('inf')
        
        return math.exp(-log_prob / n_tokens)


class SGGSLanguageModel:
    """
    Language model built from SGGS corpus.
    
    Provides both word-level and character-level N-gram models
    for rescoring ASR hypotheses.
    """
    
    # Gurmukhi word pattern
    GURMUKHI_WORD_PATTERN = re.compile(r'[\u0A00-\u0A7F]+')
    
    def __init__(
        self,
        word_model: Optional[NGramModel] = None,
        char_model: Optional[NGramModel] = None
    ):
        """
        Initialize SGGS language model.
        
        Args:
            word_model: Pre-built word-level N-gram model
            char_model: Pre-built character-level N-gram model
        """
        self.word_model = word_model
        self.char_model = char_model
        
        # Build metadata
        self.line_count = 0
        self.word_count = 0
        self.build_version = "1.0"
    
    def is_loaded(self) -> bool:
        """Check if models are loaded."""
        return self.word_model is not None or self.char_model is not None
    
    def score_text(
        self,
        text: str,
        use_word_model: bool = True,
        use_char_model: bool = False
    ) -> float:
        """
        Score text using the language model.
        
        Args:
            text: Text to score (Gurmukhi)
            use_word_model: Use word-level model
            use_char_model: Use character-level model
        
        Returns:
            Log probability score (higher = better)
        """
        score = 0.0
        
        if use_word_model and self.word_model:
            words = self._tokenize_words(text)
            if words:
                score += self.word_model.score_sequence(words)
        
        if use_char_model and self.char_model:
            chars = list(text.replace(' ', ''))
            if chars:
                score += self.char_model.score_sequence(chars)
        
        return score
    
    def get_perplexity(self, text: str, use_word_model: bool = True) -> float:
        """
        Get perplexity of text.
        
        Args:
            text: Text to evaluate
            use_word_model: Use word model (else char model)
        
        Returns:
            Perplexity (lower = better fit)
        """
        if use_word_model and self.word_model:
            tokens = self._tokenize_words(text)
            return self.word_model.perplexity(tokens)
        elif self.char_model:
            chars = list(text.replace(' ', ''))
            return self.char_model.perplexity(chars)
        return float('inf')
    
    def _tokenize_words(self, text: str) -> List[str]:
        """Extract Gurmukhi words from text."""
        return self.GURMUKHI_WORD_PATTERN.findall(text)
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save model to file."""
        path = path or getattr(config, 'SGGS_NGRAM_MODEL_PATH', config.DATA_DIR / "sggs_ngram.pkl")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'word_model': self.word_model,
            'char_model': self.char_model,
            'line_count': self.line_count,
            'word_count': self.word_count,
            'build_version': self.build_version,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved SGGS language model to {path}")
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'SGGSLanguageModel':
        """Load model from file."""
        path = path or getattr(config, 'SGGS_NGRAM_MODEL_PATH', config.DATA_DIR / "sggs_ngram.pkl")
        
        if not path.exists():
            logger.warning(f"Model file not found at {path}")
            return cls()
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        model = cls(
            word_model=data.get('word_model'),
            char_model=data.get('char_model')
        )
        model.line_count = data.get('line_count', 0)
        model.word_count = data.get('word_count', 0)
        model.build_version = data.get('build_version', '1.0')
        
        logger.info(f"Loaded SGGS language model from {path}")
        return model


class SGGSLanguageModelBuilder:
    """
    Builds N-gram language models from SGGS database.
    """
    
    GURMUKHI_WORD_PATTERN = re.compile(r'[\u0A00-\u0A7F]+')
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize builder.
        
        Args:
            db_path: Path to SGGS SQLite database
        """
        self.db_path = db_path or config.SCRIPTURE_DB_PATH
    
    def build(
        self,
        word_ngram_order: int = 3,
        char_ngram_order: int = 4,
        build_char_model: bool = False
    ) -> SGGSLanguageModel:
        """
        Build N-gram models from SGGS corpus.
        
        Args:
            word_ngram_order: Order for word-level model (default: trigram)
            char_ngram_order: Order for char-level model (default: 4-gram)
            build_char_model: Whether to build character model
        
        Returns:
            SGGSLanguageModel with trained models
        """
        logger.info(f"Building SGGS language model from {self.db_path}...")
        
        # Extract lines from database
        lines = self._extract_lines()
        logger.info(f"Extracted {len(lines)} lines from SGGS")
        
        # Tokenize all lines
        all_words = []
        all_chars = []
        
        for line in lines:
            words = self.GURMUKHI_WORD_PATTERN.findall(line)
            all_words.extend(words)
            
            if build_char_model:
                chars = list(line.replace(' ', ''))
                all_chars.extend(chars)
        
        logger.info(f"Total words: {len(all_words)}, unique: {len(set(all_words))}")
        
        # Build word model
        word_model = self._build_ngram_model(all_words, word_ngram_order)
        logger.info(f"Built word {word_ngram_order}-gram model")
        
        # Build char model (optional)
        char_model = None
        if build_char_model and all_chars:
            char_model = self._build_ngram_model(all_chars, char_ngram_order)
            logger.info(f"Built char {char_ngram_order}-gram model")
        
        # Create model
        model = SGGSLanguageModel(word_model, char_model)
        model.line_count = len(lines)
        model.word_count = len(all_words)
        
        return model
    
    def _extract_lines(self) -> List[str]:
        """Extract all lines from SGGS database."""
        if not self.db_path.exists():
            logger.error(f"Database not found at {self.db_path}")
            return []
        
        lines = []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            # Find lines table
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            lines_table = None
            for t in ['lines', 'Lines', 'LINES', 'gurbani']:
                if t in tables:
                    lines_table = t
                    break
            
            if not lines_table:
                logger.error("Could not find lines table")
                conn.close()
                return []
            
            # Get column info
            cursor = conn.execute(f"PRAGMA table_info({lines_table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Find text column
            text_column = None
            for col in ['gurmukhi', 'text', 'line', 'gurbani']:
                if col in columns:
                    text_column = col
                    break
            
            if not text_column:
                logger.error("Could not find text column")
                conn.close()
                return []
            
            # Extract lines
            cursor = conn.execute(f"SELECT {text_column} FROM {lines_table}")
            for row in cursor:
                text = row[0]
                if text and text.strip():
                    lines.append(text.strip())
            
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
        
        return lines
    
    def _build_ngram_model(self, tokens: List[str], n: int) -> NGramModel:
        """Build N-gram model from tokens."""
        ngram_counts = Counter()
        context_counts = Counter()
        vocabulary = set(tokens)
        vocabulary.add('<s>')
        vocabulary.add('</s>')
        
        # Process each "sentence" (we treat each line as a sentence)
        # For simplicity, process as one long sequence with padding
        padded = ['<s>'] * (n - 1) + tokens + ['</s>']
        
        for i in range(n - 1, len(padded)):
            ngram = tuple(padded[i - n + 1:i + 1])
            context = ngram[:-1]
            
            ngram_counts[ngram] += 1
            context_counts[context] += 1
        
        return NGramModel(
            n=n,
            ngram_counts=dict(ngram_counts),
            context_counts=dict(context_counts),
            vocabulary=vocabulary,
            total_tokens=len(tokens)
        )
    
    def build_and_save(
        self,
        path: Optional[Path] = None,
        **kwargs
    ) -> SGGSLanguageModel:
        """Build model and save to file."""
        model = self.build(**kwargs)
        model.save(path)
        return model


# Singleton instance
_sggs_lm: Optional[SGGSLanguageModel] = None


def get_sggs_language_model(rebuild: bool = False) -> SGGSLanguageModel:
    """
    Get SGGS language model (singleton).
    
    Args:
        rebuild: Force rebuild from database
    
    Returns:
        SGGSLanguageModel instance
    """
    global _sggs_lm
    
    if _sggs_lm is not None and not rebuild:
        return _sggs_lm
    
    # Try to load from file
    model_path = getattr(config, 'SGGS_NGRAM_MODEL_PATH', config.DATA_DIR / "sggs_ngram.pkl")
    
    if not rebuild and model_path.exists():
        _sggs_lm = SGGSLanguageModel.load(model_path)
        return _sggs_lm
    
    # Build from database
    logger.info("Building SGGS language model (this may take a moment)...")
    builder = SGGSLanguageModelBuilder()
    _sggs_lm = builder.build_and_save(model_path)
    
    return _sggs_lm


def score_text_with_sggs_lm(text: str) -> float:
    """
    Score text using SGGS language model.
    
    Args:
        text: Text to score
    
    Returns:
        Log probability score
    """
    lm = get_sggs_language_model()
    return lm.score_text(text)

