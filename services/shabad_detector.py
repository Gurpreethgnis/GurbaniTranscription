"""
Shabad Detection Service for Shabad Mode.

Detects if audio is singing (shabad/kirtan) vs speaking (katha),
tracks the current shabad context, and provides next line predictions.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AudioMode(str, Enum):
    """Audio content mode classification."""
    SHABAD = "shabad"      # Singing/kirtan
    KATHA = "katha"        # Speaking/explanation
    MIXED = "mixed"        # Mix of both
    UNKNOWN = "unknown"    # Cannot determine


@dataclass
class ShabadLineInfo:
    """Information about a shabad line."""
    line_id: str
    gurmukhi: str
    roman: Optional[str]
    line_number: int  # Position within the shabad
    total_lines: int  # Total lines in the shabad
    ang: Optional[int]
    raag: Optional[str]
    author: Optional[str]
    shabad_id: str


@dataclass
class ShabadContext:
    """Tracks the current shabad being sung."""
    shabad_id: str
    current_line_index: int
    lines: List[ShabadLineInfo]
    confidence: float
    last_matched_text: str
    
    @property
    def current_line(self) -> Optional[ShabadLineInfo]:
        """Get current line being sung."""
        if 0 <= self.current_line_index < len(self.lines):
            return self.lines[self.current_line_index]
        return None
    
    @property
    def next_line(self) -> Optional[ShabadLineInfo]:
        """Get next line in the shabad."""
        next_idx = self.current_line_index + 1
        if 0 <= next_idx < len(self.lines):
            return self.lines[next_idx]
        return None
    
    @property
    def previous_line(self) -> Optional[ShabadLineInfo]:
        """Get previous line in the shabad."""
        prev_idx = self.current_line_index - 1
        if 0 <= prev_idx < len(self.lines):
            return self.lines[prev_idx]
        return None
    
    def advance_line(self) -> bool:
        """Move to next line in shabad. Returns True if successful."""
        if self.current_line_index < len(self.lines) - 1:
            self.current_line_index += 1
            return True
        return False
    
    def is_at_end(self) -> bool:
        """Check if at the end of shabad."""
        return self.current_line_index >= len(self.lines) - 1


@dataclass
class ShabadDetectionResult:
    """Result of shabad detection."""
    mode: AudioMode
    mode_confidence: float
    matched_line: Optional[ShabadLineInfo]
    match_confidence: float
    shabad_context: Optional[ShabadContext]
    is_new_shabad: bool  # True if this starts a new shabad
    transcribed_text: str


class ShabadDetector:
    """
    Service for detecting shabads in live audio.
    
    Combines:
    - Audio mode detection (singing vs speaking)
    - Line matching against SGGS database
    - Shabad context tracking for continuous kirtan
    """
    
    # Patterns that indicate katha (speaking) rather than shabad
    KATHA_INDICATORS = [
        r'ਜਿਵੇਂ\s+ਕਿ',        # "As in..."
        r'ਇਸ\s+ਦਾ\s+ਅਰਥ',    # "The meaning of this..."
        r'ਇਸ\s+ਵਿੱਚ',        # "In this..."
        r'ਗੁਰੂ\s+ਸਾਹਿਬ\s+ਨੇ', # "Guru Sahib said..."
        r'ਭਾਵ\s+ਹੈ',         # "The meaning is..."
        r'ਦੱਸਿਆ\s+ਹੈ',       # "It is explained..."
        r'ਸਮਝਾਉਂਦੇ\s+ਹਨ',    # "They explain..."
        r'ਵਿਚਾਰ',            # "Reflection/commentary"
    ]
    
    # Patterns that indicate shabad (singing)
    SHABAD_INDICATORS = [
        r'॥\s*ਰਹਾਉ\s*॥',     # Rahao marker
        r'॥\s*\d+\s*॥',      # Verse number marker
        r'॥\s*॥',            # Double danda (end of line)
    ]
    
    # Gurbani vocabulary density threshold
    GURBANI_VOCAB_THRESHOLD = 0.35
    
    # High-frequency Gurbani words (archaic forms)
    GURBANI_VOCABULARY = {
        'ਹਰਿ', 'ਪ੍ਰਭ', 'ਪ੍ਰਭੁ', 'ਨਾਮੁ', 'ਨਾਮਿ', 'ਸਬਦੁ', 'ਸਬਦਿ',
        'ਹੁਕਮੁ', 'ਹੁਕਮਿ', 'ਕਉ', 'ਤਉ', 'ਜਉ', 'ਮੋਹਿ', 'ਤੋਹਿ',
        'ਹੋਇ', 'ਹੋਵੈ', 'ਕਰੈ', 'ਜਪੈ', 'ਮਿਲੈ', 'ਪਾਵੈ', 'ਜੀਉ',
        'ਮੁਕਤਿ', 'ਜੁਗਤਿ', 'ਭਗਤਿ', 'ਬਿਰਤਿ', 'ਸਾਚੁ', 'ਸਾਚਾ',
    }
    
    def __init__(
        self,
        sggs_db=None,
        dasam_db=None,
        match_threshold: float = 0.7,
        context_window: int = 5
    ):
        """
        Initialize shabad detector.
        
        Args:
            sggs_db: SGGS database instance
            dasam_db: Dasam Granth database instance
            match_threshold: Minimum similarity for line matching
            context_window: Number of lines to consider for context
        """
        self.sggs_db = sggs_db
        self.dasam_db = dasam_db
        self.match_threshold = match_threshold
        self.context_window = context_window
        
        # Compile patterns
        self.katha_patterns = [
            re.compile(p, re.UNICODE | re.IGNORECASE)
            for p in self.KATHA_INDICATORS
        ]
        self.shabad_patterns = [
            re.compile(p, re.UNICODE)
            for p in self.SHABAD_INDICATORS
        ]
        
        # Current shabad context (stateful tracking)
        self._current_context: Optional[ShabadContext] = None
        self._consecutive_misses = 0
        self._max_misses_before_reset = 3
    
    def set_databases(self, sggs_db=None, dasam_db=None) -> None:
        """Set database instances after initialization."""
        if sggs_db:
            self.sggs_db = sggs_db
        if dasam_db:
            self.dasam_db = dasam_db
    
    def detect_mode(self, text: str) -> Tuple[AudioMode, float]:
        """
        Detect if text is from shabad (singing) or katha (speaking).
        
        Args:
            text: Transcribed text
        
        Returns:
            Tuple of (AudioMode, confidence)
        """
        if not text or not text.strip():
            return AudioMode.UNKNOWN, 0.0
        
        # Check for katha indicators
        katha_score = 0
        for pattern in self.katha_patterns:
            if pattern.search(text):
                katha_score += 1
        
        # Check for shabad indicators
        shabad_score = 0
        for pattern in self.shabad_patterns:
            if pattern.search(text):
                shabad_score += 2  # Weight shabad markers higher
        
        # Check Gurbani vocabulary density
        vocab_density = self._calculate_gurbani_density(text)
        if vocab_density >= self.GURBANI_VOCAB_THRESHOLD:
            shabad_score += 1
        
        # Determine mode
        if katha_score > shabad_score:
            confidence = min(1.0, 0.5 + katha_score * 0.15)
            return AudioMode.KATHA, confidence
        elif shabad_score > katha_score:
            confidence = min(1.0, 0.5 + shabad_score * 0.15 + vocab_density * 0.2)
            return AudioMode.SHABAD, confidence
        elif vocab_density >= self.GURBANI_VOCAB_THRESHOLD:
            # High Gurbani vocabulary suggests shabad
            return AudioMode.SHABAD, 0.5 + vocab_density * 0.3
        else:
            return AudioMode.MIXED, 0.4
    
    def _calculate_gurbani_density(self, text: str) -> float:
        """Calculate density of Gurbani vocabulary in text."""
        words = set(re.findall(r'[\u0A00-\u0A7F]+', text))
        if not words:
            return 0.0
        
        gurbani_words = words.intersection(self.GURBANI_VOCABULARY)
        return len(gurbani_words) / len(words)
    
    def match_line(
        self,
        text: str,
        use_context: bool = True
    ) -> Tuple[Optional[ShabadLineInfo], float]:
        """
        Match transcribed text to a shabad line.
        
        Args:
            text: Transcribed text
            use_context: Use current shabad context for prediction
        
        Returns:
            Tuple of (matched line info, confidence)
        """
        if not text or not self.sggs_db:
            return None, 0.0
        
        # Clean text for matching
        clean_text = self._clean_for_matching(text)
        if len(clean_text) < 5:
            return None, 0.0
        
        # If we have context, try to match next expected line first
        if use_context and self._current_context:
            context_match, context_conf = self._match_from_context(clean_text)
            if context_match and context_conf >= self.match_threshold:
                return context_match, context_conf
        
        # Search database for best match
        try:
            results = self.sggs_db.search_by_text(clean_text, top_k=5, fuzzy=True)
            if results:
                best_match = results[0]
                confidence = self._calculate_match_confidence(clean_text, best_match.gurmukhi)
                
                if confidence >= self.match_threshold:
                    line_info = self._create_line_info(best_match)
                    return line_info, confidence
        except Exception as e:
            logger.warning(f"Database search failed: {e}")
        
        return None, 0.0
    
    def _match_from_context(
        self,
        text: str
    ) -> Tuple[Optional[ShabadLineInfo], float]:
        """Try to match text against expected lines from context."""
        if not self._current_context:
            return None, 0.0
        
        # Check current line
        current = self._current_context.current_line
        if current:
            conf = self._calculate_match_confidence(text, current.gurmukhi)
            if conf >= self.match_threshold:
                return current, conf
        
        # Check next line
        next_line = self._current_context.next_line
        if next_line:
            conf = self._calculate_match_confidence(text, next_line.gurmukhi)
            if conf >= self.match_threshold:
                # Advance context to next line
                self._current_context.advance_line()
                return next_line, conf
        
        # Check previous line (might be repeating)
        prev_line = self._current_context.previous_line
        if prev_line:
            conf = self._calculate_match_confidence(text, prev_line.gurmukhi)
            if conf >= self.match_threshold:
                return prev_line, conf
        
        return None, 0.0
    
    def _calculate_match_confidence(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using Jaccard similarity."""
        words1 = set(re.findall(r'[\u0A00-\u0A7F]+', text1.lower()))
        words2 = set(re.findall(r'[\u0A00-\u0A7F]+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _clean_for_matching(self, text: str) -> str:
        """Clean text for database matching."""
        # Remove common filler words and normalize
        text = re.sub(r'[॥।\s]+', ' ', text)
        text = text.strip()
        return text
    
    def _create_line_info(self, scripture_line) -> ShabadLineInfo:
        """Create ShabadLineInfo from ScriptureLine."""
        return ShabadLineInfo(
            line_id=scripture_line.line_id,
            gurmukhi=scripture_line.gurmukhi,
            roman=scripture_line.roman,
            line_number=0,  # Will be updated when loading shabad
            total_lines=1,
            ang=scripture_line.ang,
            raag=scripture_line.raag,
            author=scripture_line.author,
            shabad_id=scripture_line.shabad_id or scripture_line.line_id
        )
    
    def load_shabad_context(self, shabad_id: str, starting_line_id: str) -> Optional[ShabadContext]:
        """
        Load full shabad context for tracking.
        
        Args:
            shabad_id: Shabad identifier
            starting_line_id: Line ID to start from
        
        Returns:
            ShabadContext or None if failed
        """
        if not self.sggs_db or not shabad_id:
            return None
        
        try:
            # Query all lines in the shabad
            cursor = self.sggs_db._connection.execute(
                """
                SELECT l.*, t.transliteration as roman
                FROM lines l
                LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                WHERE l.shabad_id = ?
                ORDER BY l.id
                """,
                (shabad_id,)
            )
            
            lines = []
            starting_index = 0
            
            for i, row in enumerate(cursor.fetchall()):
                line_id = str(row['id'])
                
                # Get full line info
                scripture_line = self.sggs_db.get_line_by_id(line_id)
                if scripture_line:
                    line_info = ShabadLineInfo(
                        line_id=line_id,
                        gurmukhi=scripture_line.gurmukhi,
                        roman=scripture_line.roman,
                        line_number=i,
                        total_lines=0,  # Will be updated
                        ang=scripture_line.ang,
                        raag=scripture_line.raag,
                        author=scripture_line.author,
                        shabad_id=shabad_id
                    )
                    lines.append(line_info)
                    
                    if line_id == starting_line_id:
                        starting_index = i
            
            if not lines:
                return None
            
            # Update total_lines for all lines
            for line in lines:
                line.total_lines = len(lines)
            
            context = ShabadContext(
                shabad_id=shabad_id,
                current_line_index=starting_index,
                lines=lines,
                confidence=0.8,
                last_matched_text=""
            )
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to load shabad context: {e}")
            return None
    
    def detect(self, transcribed_text: str) -> ShabadDetectionResult:
        """
        Detect shabad from transcribed text with full context.
        
        Args:
            transcribed_text: Text from ASR
        
        Returns:
            ShabadDetectionResult with all detection info
        """
        # Detect audio mode
        mode, mode_confidence = self.detect_mode(transcribed_text)
        
        # If likely katha, don't try to match
        if mode == AudioMode.KATHA:
            self._consecutive_misses += 1
            if self._consecutive_misses > self._max_misses_before_reset:
                self._current_context = None
            
            return ShabadDetectionResult(
                mode=mode,
                mode_confidence=mode_confidence,
                matched_line=None,
                match_confidence=0.0,
                shabad_context=self._current_context,
                is_new_shabad=False,
                transcribed_text=transcribed_text
            )
        
        # Try to match line
        matched_line, match_confidence = self.match_line(transcribed_text)
        
        is_new_shabad = False
        
        if matched_line:
            self._consecutive_misses = 0
            
            # Check if this is a new shabad
            if (not self._current_context or 
                self._current_context.shabad_id != matched_line.shabad_id):
                # Load new shabad context
                new_context = self.load_shabad_context(
                    matched_line.shabad_id,
                    matched_line.line_id
                )
                if new_context:
                    self._current_context = new_context
                    is_new_shabad = True
            
            # Update context with matched text
            if self._current_context:
                self._current_context.last_matched_text = transcribed_text
                self._current_context.confidence = match_confidence
        else:
            self._consecutive_misses += 1
            if self._consecutive_misses > self._max_misses_before_reset:
                self._current_context = None
        
        return ShabadDetectionResult(
            mode=mode,
            mode_confidence=mode_confidence,
            matched_line=matched_line,
            match_confidence=match_confidence,
            shabad_context=self._current_context,
            is_new_shabad=is_new_shabad,
            transcribed_text=transcribed_text
        )
    
    def get_current_context(self) -> Optional[ShabadContext]:
        """Get current shabad tracking context."""
        return self._current_context
    
    def reset_context(self) -> None:
        """Reset shabad tracking context."""
        self._current_context = None
        self._consecutive_misses = 0
    
    def get_next_line_prediction(self) -> Optional[ShabadLineInfo]:
        """Get predicted next line from current context."""
        if self._current_context:
            return self._current_context.next_line
        return None


# Singleton instance
_shabad_detector: Optional[ShabadDetector] = None


def get_shabad_detector(
    sggs_db=None,
    dasam_db=None
) -> ShabadDetector:
    """
    Get singleton shabad detector instance.
    
    Args:
        sggs_db: SGGS database instance
        dasam_db: Dasam Granth database instance
    
    Returns:
        ShabadDetector instance
    """
    global _shabad_detector
    
    if _shabad_detector is None:
        _shabad_detector = ShabadDetector(
            sggs_db=sggs_db,
            dasam_db=dasam_db
        )
    elif sggs_db or dasam_db:
        _shabad_detector.set_databases(sggs_db, dasam_db)
    
    return _shabad_detector

