"""
Assisted Matching (Multi-Stage).

Implements a 3-stage matching process:
- Stage A: Fast fuzzy retrieval using rapidfuzz
- Stage B: Semantic verification (word overlap, key vocabulary)
- Stage C: Verifier rules (word count, position, confidence)

Phase 5: Added Unicode normalization support
"""
import logging
import unicodedata
from typing import List, Optional, Dict, Any, Set
from rapidfuzz import fuzz, process
from models import QuoteMatch, QuoteCandidate, ScriptureLine, ScriptureSource
from scripture.scripture_service import ScriptureService
from scripture.gurmukhi_to_ascii import try_ascii_search
import config

logger = logging.getLogger(__name__)


class AssistedMatcher:
    """
    Multi-stage matcher for finding canonical scripture matches.
    
    Uses fuzzy matching, semantic verification, and strict verifier rules
    to match transcribed text to canonical scripture lines.
    """
    
    def __init__(self, scripture_service: Optional[ScriptureService] = None):
        """
        Initialize assisted matcher.
        
        Args:
            scripture_service: ScriptureService instance (created if None)
        """
        self.scripture_service = scripture_service or ScriptureService()
        self.confidence_threshold = config.QUOTE_MATCH_CONFIDENCE_THRESHOLD
        self.review_threshold = 0.70  # Below this, no replacement
    
    def find_match(
        self,
        candidates: List[QuoteCandidate],
        hypotheses: Optional[List[Dict[str, Any]]] = None,
        source: Optional[ScriptureSource] = None
    ) -> Optional[QuoteMatch]:
        """
        Find the best match for quote candidates.
        
        Args:
            candidates: List of quote candidates to match
            hypotheses: Optional list of ASR hypotheses (for multi-hypothesis search)
            source: Optional scripture source to search (None = search all)
        
        Returns:
            QuoteMatch if a good match is found, None otherwise
        """
        if not candidates:
            logger.debug("No candidates provided for matching")
            return None
        
        # Use the highest confidence candidate as primary
        primary_candidate = max(candidates, key=lambda c: c.confidence)
        search_texts = [primary_candidate.text]
        
        # Add alternative texts from hypotheses if available
        if hypotheses:
            for hyp in hypotheses:
                if isinstance(hyp, dict) and 'text' in hyp:
                    alt_text = hyp['text']
                    if alt_text and alt_text != primary_candidate.text:
                        search_texts.append(alt_text)
        
        logger.debug(f"Searching for match with {len(search_texts)} text variants")
        
        # Stage A: Fast fuzzy retrieval
        stage_a_results = self._stage_a_fuzzy_retrieval(
            search_texts,
            source=source,
            top_k=20  # Get more candidates for verification
        )
        
        if not stage_a_results:
            logger.debug("Stage A: No fuzzy matches found")
            return None
        
        logger.debug(f"Stage A: Found {len(stage_a_results)} fuzzy matches")
        
        # Stage B: Semantic verification
        stage_b_results = self._stage_b_semantic_verification(
            search_texts,
            stage_a_results
        )
        
        if not stage_b_results:
            logger.debug("Stage B: No matches passed semantic verification")
            return None
        
        logger.debug(f"Stage B: {len(stage_b_results)} matches passed semantic verification")
        
        # Stage C: Verifier rules
        best_match = self._stage_c_verifier(
            primary_candidate.text,
            stage_b_results,
            search_texts
        )
        
        if best_match:
            logger.info(f"Found match: {best_match.line_id} (confidence: {best_match.confidence:.2f})")
        else:
            logger.debug("Stage C: No match passed verifier rules")
        
        return best_match
    
    def _stage_a_fuzzy_retrieval(
        self,
        search_texts: List[str],
        source: Optional[ScriptureSource] = None,
        top_k: int = 20
    ) -> List[tuple]:
        """
        Stage A: Fast fuzzy retrieval using rapidfuzz.
        
        Args:
            search_texts: List of text variants to search
            source: Optional scripture source
            top_k: Maximum number of candidates per text
        
        Returns:
            List of (ScriptureLine, similarity_score) tuples, sorted by score
        """
        all_matches: List[tuple] = []
        
        # Search scripture database for each text variant
        for search_text in search_texts:
            if not search_text or not search_text.strip():
                continue
            
            # Get candidates from scripture service
            scripture_lines = self.scripture_service.search_candidates(
                text=search_text,
                source=source,
                top_k=top_k,
                fuzzy=True
            )
            
            # Calculate fuzzy similarity scores
            # Convert search_text to ASCII for comparison (database uses ASCII)
            ascii_search_text = try_ascii_search(search_text)
            for line in scripture_lines:
                # Use token_sort_ratio for better handling of word order differences
                similarity = fuzz.token_sort_ratio(
                    ascii_search_text,
                    line.gurmukhi,
                    score_cutoff=50  # Minimum 50% similarity
                )
                
                if similarity > 0:
                    all_matches.append((line, similarity / 100.0))  # Convert to 0-1 scale
        
        # Sort by similarity (highest first) and remove duplicates
        all_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Deduplicate by line_id
        seen = set()
        unique_matches = []
        for line, score in all_matches:
            if line.line_id not in seen:
                seen.add(line.line_id)
                unique_matches.append((line, score))
        
        return unique_matches[:top_k]  # Return top K
    
    def _stage_b_semantic_verification(
        self,
        search_texts: List[str],
        fuzzy_matches: List[tuple]
    ) -> List[tuple]:
        """
        Stage B: Semantic verification using word overlap and key vocabulary.
        
        Args:
            search_texts: Original search texts
            fuzzy_matches: Results from Stage A
        
        Returns:
            List of (ScriptureLine, combined_score) tuples that passed verification
        """
        verified_matches = []
        
        for line, fuzzy_score in fuzzy_matches:
            # Calculate word overlap score
            # Convert search texts to ASCII for comparison with database (which uses ASCII)
            search_words = set()
            for text in search_texts:
                # Convert to ASCII for word comparison
                ascii_text = try_ascii_search(text)
                words = self._normalize_and_tokenize(ascii_text)
                search_words.update(words)
            
            # Database text is already in ASCII format
            line_words = set(self._normalize_and_tokenize(line.gurmukhi))
            
            if not search_words or not line_words:
                continue
            
            # Word overlap ratio
            overlap = search_words.intersection(line_words)
            overlap_ratio = len(overlap) / max(len(search_words), len(line_words))
            
            # Check for critical keywords (common Gurbani words in ASCII format)
            # Database uses ASCII transliteration, so use ASCII keywords
            critical_keywords = {
                'vwhgurU', 'siqgurU', 'gurU', 'bwxI', 'sbd',
                'pRBU', 'rwm', 'hir', 'goibMd', 'kirpw', 'mihr',
                'siq', 'nwmu', 'krqw', 'purKu'  # Common words
            }
            
            search_keywords = search_words.intersection(critical_keywords)
            line_keywords = line_words.intersection(critical_keywords)
            
            keyword_match = 1.0 if search_keywords == line_keywords else 0.5
            
            # Combined score: fuzzy score + word overlap + keyword match
            combined_score = (
                fuzzy_score * 0.5 +  # Fuzzy similarity weight
                overlap_ratio * 0.3 +  # Word overlap weight
                keyword_match * 0.2  # Keyword match weight
            )
            
            # Only keep matches with combined score >= 0.6
            if combined_score >= 0.6:
                verified_matches.append((line, combined_score))
                logger.debug(
                    f"Stage B: Verified match {line.line_id} "
                    f"(fuzzy: {fuzzy_score:.2f}, overlap: {overlap_ratio:.2f}, "
                    f"combined: {combined_score:.2f})"
                )
        
        # Sort by combined score
        verified_matches.sort(key=lambda x: x[1], reverse=True)
        return verified_matches
    
    def _stage_c_verifier(
        self,
        primary_text: str,
        semantic_matches: List[tuple],
        all_search_texts: List[str]
    ) -> Optional[QuoteMatch]:
        """
        Stage C: Verifier rules - strict validation before matching.
        
        Args:
            primary_text: Primary candidate text
            semantic_matches: Results from Stage B
            all_search_texts: All text variants
        
        Returns:
            QuoteMatch if verification passes, None otherwise
        """
        if not semantic_matches:
            return None
        
        # Get the best match from Stage B
        best_line, combined_score = semantic_matches[0]
        
        # Rule 1: Word count match (within 20%)
        primary_words = len(primary_text.split())
        line_words = len(best_line.gurmukhi.split())
        
        if line_words > 0:
            word_count_ratio = min(primary_words, line_words) / max(primary_words, line_words)
            if word_count_ratio < 0.8:  # More than 20% difference
                logger.debug(
                    f"Stage C: Word count mismatch "
                    f"(primary: {primary_words}, line: {line_words}, ratio: {word_count_ratio:.2f})"
                )
                # Don't reject, but lower confidence
                combined_score *= 0.8
        
        # Rule 2: Key vocabulary presence
        primary_words_set = set(self._normalize_and_tokenize(primary_text))
        line_words_set = set(self._normalize_and_tokenize(best_line.gurmukhi))
        
        # Check if important words from primary appear in line
        important_words = {
            'ਵਾਹਿਗੁਰੂ', 'ਸਤਿਗੁਰੂ', 'ਗੁਰੂ', 'ਬਾਣੀ', 'ਸ਼ਬਦ',
            'ਪ੍ਰਭੂ', 'ਰਾਮ', 'ਹਰਿ', 'ਗੋਬਿੰਦ'
        }
        
        primary_important = primary_words_set.intersection(important_words)
        line_important = line_words_set.intersection(important_words)
        
        if primary_important:
            if not primary_important.issubset(line_important):
                # Some important words missing
                logger.debug(
                    f"Stage C: Important words mismatch "
                    f"(primary: {primary_important}, line: {line_important})"
                )
                combined_score *= 0.9
        
        # Rule 3: Position of key words (basic check)
        # If key words appear in similar positions, boost confidence
        # This is a simple implementation - can be enhanced
        
        # Rule 4: Final confidence threshold check
        if combined_score < self.review_threshold:
            logger.debug(f"Stage C: Confidence too low ({combined_score:.2f} < {self.review_threshold})")
            return None
        
        # Create QuoteMatch
        match_method = "fuzzy" if combined_score < 0.85 else "semantic"
        
        quote_match = QuoteMatch(
            source=best_line.source,
            line_id=best_line.line_id,
            canonical_text=best_line.gurmukhi,
            canonical_roman=best_line.roman,
            spoken_text=primary_text,
            confidence=combined_score,
            ang=best_line.ang,
            raag=best_line.raag,
            author=best_line.author,
            match_method=match_method
        )
        
        logger.info(
            f"Stage C: Match verified - {best_line.line_id} "
            f"(confidence: {combined_score:.2f}, method: {match_method})"
        )
        
        return quote_match
    
    def _normalize_and_tokenize(self, text: str) -> List[str]:
        """
        Normalize and tokenize text for comparison.
        
        Args:
            text: Text to normalize
        
        Returns:
            List of normalized tokens
        """
        if not text:
            return []
        
        # Phase 5: Apply Unicode normalization using config
        try:
            unicode_form = getattr(config, 'UNICODE_NORMALIZATION_FORM', 'NFC')
        except (ImportError, AttributeError):
            unicode_form = 'NFC'
        
        text = unicodedata.normalize(unicode_form, text)
        
        # Remove punctuation and normalize whitespace
        import re
        normalized = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Split into words
        words = normalized.strip().split()
        
        # Remove empty strings
        words = [w for w in words if w]
        
        return words
    
    def close(self) -> None:
        """Close scripture service connections."""
        if self.scripture_service:
            self.scripture_service.close()
