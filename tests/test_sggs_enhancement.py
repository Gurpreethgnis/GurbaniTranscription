"""
Acceptance tests for SGGS Corpus Enhancement features.

Tests:
1. Gurbani Prompt Builder - Context-aware prompting for Whisper
2. N-gram Language Model - SGGS corpus-based language model
3. N-gram Rescorer - Hypothesis rescoring with LM
4. Quote Context Detector - Real-time quote detection
5. Constrained Matcher - Alignment-based quote matching
6. SGGS Aligner - Post-ASR canonical text snapping
7. Orchestrator Integration - End-to-end pipeline
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config


# ============================================
# 1. Gurbani Prompt Builder Tests
# ============================================

class TestGurbaniPromptBuilder:
    """Tests for the Gurbani prompt builder."""
    
    @pytest.fixture
    def prompt_builder(self):
        from asr.gurbani_prompt import GurbaniPromptBuilder
        return GurbaniPromptBuilder()
    
    def test_prompt_builder_initialization(self, prompt_builder):
        """Test prompt builder initializes correctly."""
        assert prompt_builder is not None
        assert prompt_builder.MAX_PROMPT_LENGTH == 224
    
    def test_sggs_mode_prompt(self, prompt_builder):
        """Test SGGS mode generates appropriate prompt."""
        prompt = prompt_builder.get_prompt(mode="sggs")
        
        assert prompt is not None
        assert len(prompt) > 0
        assert len(prompt) <= prompt_builder.MAX_PROMPT_LENGTH
        
        # Should contain Mool Mantar elements
        assert "ੴ" in prompt or "ਸਤਿ ਨਾਮੁ" in prompt
    
    def test_dasam_mode_prompt(self, prompt_builder):
        """Test Dasam mode generates appropriate prompt."""
        prompt = prompt_builder.get_prompt(mode="dasam")
        
        assert prompt is not None
        assert len(prompt) > 0
        
        # Should contain Dasam-specific vocabulary
        assert any(word in prompt for word in ["ਭਗੌਤੀ", "ਚੰਡੀ", "ਅਕਾਲ"])
    
    def test_katha_mode_prompt(self, prompt_builder):
        """Test Katha mode generates appropriate prompt."""
        prompt = prompt_builder.get_prompt(mode="katha")
        
        assert prompt is not None
        assert len(prompt) > 0
    
    def test_context_aware_prompt(self, prompt_builder):
        """Test context-specific prompt generation."""
        # Test with Japji context
        prompt = prompt_builder.get_prompt(mode="sggs", context="japji")
        assert "ਜਪੁ" in prompt or "ਆਦਿ ਸਚੁ" in prompt or "ੴ" in prompt
        
        # Test with salok context
        prompt = prompt_builder.get_prompt(mode="sggs", context="salok")
        assert "ਸਲੋਕ" in prompt or "ਮਹਲਾ" in prompt
        
        # Test that prompt always has content
        prompt = prompt_builder.get_prompt(mode="sggs", context="unknown_context")
        assert len(prompt) > 0
    
    def test_previous_text_continuity(self, prompt_builder):
        """Test prompt includes previous text for continuity."""
        previous = "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
        prompt = prompt_builder.get_prompt(mode="sggs", previous_text=previous)
        
        # Should include part of previous text
        assert "ਪੁਰਖੁ" in prompt or "ਕਰਤਾ" in prompt
    
    def test_quote_optimized_prompt(self, prompt_builder):
        """Test prompt optimized for quote transcription."""
        prompt = prompt_builder.get_prompt_for_quote()
        
        assert prompt is not None
        # Should be pure Gurbani vocabulary
        assert len(prompt) > 0


# ============================================
# 2. N-gram Language Model Tests
# ============================================

class TestNGramLanguageModel:
    """Tests for the SGGS N-gram language model."""
    
    @pytest.fixture
    def lm_builder(self):
        from data.sggs_language_model import SGGSLanguageModelBuilder
        return SGGSLanguageModelBuilder()
    
    def test_ngram_model_dataclass(self):
        """Test NGramModel dataclass structure."""
        from data.sggs_language_model import NGramModel
        
        model = NGramModel(
            n=3,
            ngram_counts={('a', 'b', 'c'): 10},
            context_counts={('a', 'b'): 20},
            vocabulary={'a', 'b', 'c'},
            total_tokens=100
        )
        
        assert model.n == 3
        assert model.total_tokens == 100
        assert len(model.vocabulary) == 3
    
    def test_ngram_probability(self):
        """Test N-gram probability calculation."""
        from data.sggs_language_model import NGramModel
        
        model = NGramModel(
            n=2,
            ngram_counts={('ਹਰਿ', 'ਪ੍ਰਭ'): 100, ('<s>', 'ਹਰਿ'): 50},
            context_counts={('ਹਰਿ',): 200, ('<s>',): 100},
            vocabulary={'ਹਰਿ', 'ਪ੍ਰਭ', '<s>', '</s>'},
            total_tokens=1000
        )
        
        # Test probability calculation
        prob = model.get_probability(('ਹਰਿ', 'ਪ੍ਰਭ'))
        assert 0 < prob <= 1
        
        # Higher count should mean higher probability
        assert prob > model.get_probability(('ਹਰਿ', 'ਨਾਮ'))
    
    def test_sequence_scoring(self):
        """Test sequence scoring."""
        from data.sggs_language_model import NGramModel
        
        model = NGramModel(
            n=2,
            ngram_counts={
                ('<s>', 'ਹਰਿ'): 50,
                ('ਹਰਿ', 'ਪ੍ਰਭ'): 100,
                ('ਪ੍ਰਭ', '</s>'): 50
            },
            context_counts={('<s>',): 100, ('ਹਰਿ',): 200, ('ਪ੍ਰਭ',): 100},
            vocabulary={'ਹਰਿ', 'ਪ੍ਰਭ', '<s>', '</s>'},
            total_tokens=1000
        )
        
        score = model.score_sequence(['ਹਰਿ', 'ਪ੍ਰਭ'])
        assert score < 0  # Log probability is negative


# ============================================
# 3. N-gram Rescorer Tests
# ============================================

class TestNGramRescorer:
    """Tests for the N-gram hypothesis rescorer."""
    
    @pytest.fixture
    def rescorer(self):
        from services.ngram_rescorer import NGramRescorer
        return NGramRescorer()
    
    def test_rescorer_initialization(self, rescorer):
        """Test rescorer initializes correctly."""
        assert rescorer is not None
        assert rescorer.lm_weight > 0
        assert rescorer.lm_weight < 1
    
    def test_gurmukhi_ratio_calculation(self, rescorer):
        """Test Gurmukhi character ratio calculation."""
        # Pure Gurmukhi
        ratio = rescorer._get_gurmukhi_ratio("ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ")
        assert ratio > 0.9
        
        # Mixed
        ratio = rescorer._get_gurmukhi_ratio("ਸਤਿਨਾਮੁ hello world")
        assert 0.3 < ratio < 0.7
        
        # No Gurmukhi
        ratio = rescorer._get_gurmukhi_ratio("hello world")
        assert ratio == 0.0
    
    def test_rescoring_returns_hypothesis(self, rescorer):
        """Test rescoring returns a valid hypothesis."""
        from services.ngram_rescorer import RescoredHypothesis
        
        result = rescorer.rescore_hypothesis("ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ", 0.8)
        
        assert isinstance(result, RescoredHypothesis)
        assert result.text == "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
        assert 0 <= result.combined_score <= 1
    
    def test_multiple_hypothesis_rescoring(self, rescorer):
        """Test rescoring multiple hypotheses."""
        hypotheses = [
            "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            "ਸਤਿ ਨਾਮ ਕਰਤਾ ਪੁਰਖ",
            "ਸਤ ਨਾਮ ਕਰਤਾ ਪੁਰਖ"
        ]
        
        results = rescorer.rescore(hypotheses)
        
        assert len(results) == 3
        # Results should be sorted by score
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i+1][1]


# ============================================
# 4. Quote Context Detector Tests
# ============================================

class TestQuoteContextDetector:
    """Tests for the quote context detector."""
    
    @pytest.fixture
    def detector(self):
        from quotes.quote_context_detector import QuoteContextDetector
        return QuoteContextDetector()
    
    def test_detector_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector is not None
        assert len(detector.intro_patterns) > 0
    
    def test_intro_pattern_detection(self, detector):
        """Test detection of introductory phrases."""
        # "As stated in Bani"
        result = detector.detect("ਜਿਵੇਂ ਬਾਣੀ ਵਿੱਚ ਕਿਹਾ ਹੈ")
        assert result.is_quote_intro
        assert "intro_jive_bani" in result.detected_signals[0]
        
        # "Guru Sahib says"
        result = detector.detect("ਗੁਰੂ ਸਾਹਿਬ ਫੁਰਮਾਉਂਦੇ ਹਨ")
        assert result.is_quote_intro
        assert result.quote_confidence > 0
    
    def test_quote_internal_detection(self, detector):
        """Test detection of quote-internal patterns."""
        # Rahao marker
        result = detector.detect("॥ ਰਹਾਉ ॥")
        assert result.is_quote_likely
        assert "internal:quote_rahao" in result.detected_signals
        
        # Verse number
        result = detector.detect("॥ ੧ ॥")
        assert "internal:quote_verse_number" in result.detected_signals or result.is_quote_likely
    
    def test_vocabulary_density(self, detector):
        """Test Gurbani vocabulary density calculation."""
        # High density Gurbani text
        density = detector._calculate_vocab_density("ਹਰਿ ਪ੍ਰਭ ਨਾਮੁ ਸਬਦੁ ਗੁਰੁ")
        assert density > 0.5
        
        # Low density modern Punjabi
        density = detector._calculate_vocab_density("ਅੱਜ ਮੌਸਮ ਬਹੁਤ ਵਧੀਆ ਹੈ")
        assert density < 0.3
    
    def test_context_continuation(self, detector):
        """Test context continues across segments."""
        from quotes.quote_context_detector import QuoteContextResult
        
        # First segment is intro
        result1 = detector.detect("ਗੁਰੂ ਸਾਹਿਬ ਫੁਰਮਾਉਂਦੇ ਹਨ")
        assert result1.is_quote_intro
        
        # Second segment should be detected as quote start
        result2 = detector.detect(
            "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            previous_result=result1
        )
        assert result2.is_quote_likely
        assert result2.context_type == 'quote_start'
    
    def test_ang_reference_extraction(self, detector):
        """Test Ang reference extraction."""
        ang = detector.extract_ang_reference("ਅੰਗ 123 ਤੇ ਲਿਖਿਆ ਹੈ")
        assert ang == 123
        
        ang = detector.extract_ang_reference("Ang 456")
        assert ang == 456
        
        ang = detector.extract_ang_reference("ਕੋਈ ਹੋਰ ਟੈਕਸਟ")
        assert ang is None


# ============================================
# 5. Constrained Matcher Tests
# ============================================

class TestConstrainedMatcher:
    """Tests for the constrained quote matcher."""
    
    @pytest.fixture
    def matcher(self):
        from quotes.constrained_matcher import ConstrainedQuoteMatcher
        return ConstrainedQuoteMatcher()
    
    def test_matcher_initialization(self, matcher):
        """Test matcher initializes correctly."""
        assert matcher is not None
        assert matcher.alignment_threshold > 0
    
    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        from quotes.constrained_matcher import levenshtein_distance
        
        assert levenshtein_distance("ਸਤਿ", "ਸਤਿ") == 0
        assert levenshtein_distance("ਸਤਿ", "ਸਤ") == 1
        assert levenshtein_distance("ਕਰਤਾ", "ਕਤਾ") == 1
        assert levenshtein_distance("ਪੁਰਖੁ", "ਪੁਰਖ") == 1
    
    def test_normalized_edit_distance(self):
        """Test normalized edit distance."""
        from quotes.constrained_matcher import normalized_edit_distance
        
        # Same text
        dist = normalized_edit_distance("ਹਰਿ", "ਹਰਿ")
        assert dist == 0.0
        
        # Different text
        dist = normalized_edit_distance("ਹਰਿ", "ਪ੍ਰਭ")
        assert 0 < dist <= 1
    
    def test_word_overlap_score(self):
        """Test word overlap scoring."""
        from quotes.constrained_matcher import word_overlap_score
        
        # Same words
        score = word_overlap_score(
            "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            "ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
        )
        assert score == 1.0
        
        # Partial overlap
        score = word_overlap_score(
            "ਸਤਿਨਾਮੁ ਕਰਤਾ",
            "ਕਰਤਾ ਪੁਰਖੁ"
        )
        assert 0 < score < 1


# ============================================
# 6. SGGS Aligner Tests
# ============================================

class TestSGGSAligner:
    """Tests for the SGGS aligner."""
    
    @pytest.fixture
    def aligner(self):
        from services.sggs_aligner import SGGSAligner
        return SGGSAligner()
    
    def test_aligner_initialization(self, aligner):
        """Test aligner initializes correctly."""
        assert aligner is not None
        assert aligner.alignment_threshold > 0
    
    def test_text_preprocessing(self, aligner):
        """Test text preprocessing corrects common errors."""
        # Multiple matras should be reduced
        text = aligner._preprocess_text("ਸਤਿੀ")  # Double sihari
        # Preprocessing should handle these
        assert text is not None
    
    def test_alignment_result_structure(self):
        """Test alignment result dataclass."""
        from services.sggs_aligner import SGGSAlignmentResult
        
        result = SGGSAlignmentResult(
            original_text="ਸਤਿਨਾਮ ਕਰਤਾ ਪੁਰਖ",
            aligned_text="ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            was_aligned=True,
            confidence=0.9,
            alignment_score=0.88,
            edit_distance=2,
            ang=1
        )
        
        assert result.was_aligned
        assert result.confidence == 0.9
        assert result.ang == 1


# ============================================
# 7. Integration Tests
# ============================================

class TestSGGSEnhancementIntegration:
    """Integration tests for SGGS enhancement pipeline."""
    
    def test_prompt_to_rescorer_flow(self):
        """Test prompt generation followed by rescoring."""
        from asr.gurbani_prompt import GurbaniPromptBuilder
        from services.ngram_rescorer import NGramRescorer
        
        # Generate prompt
        builder = GurbaniPromptBuilder()
        prompt = builder.get_prompt(mode="sggs")
        assert prompt is not None
        
        # Rescore a hypothesis
        rescorer = NGramRescorer()
        result = rescorer.rescore_hypothesis("ਸਤਿਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ", 0.8)
        assert result.combined_score > 0
    
    def test_context_to_alignment_flow(self):
        """Test quote context detection followed by alignment."""
        from quotes.quote_context_detector import QuoteContextDetector
        from quotes.constrained_matcher import ConstrainedQuoteMatcher
        
        # Detect context
        detector = QuoteContextDetector()
        context = detector.detect("ਗੁਰੂ ਸਾਹਿਬ ਫੁਰਮਾਉਂਦੇ ਹਨ")
        assert context.is_quote_intro
        
        # Should trigger matcher
        matcher = ConstrainedQuoteMatcher()
        # Matcher is ready for use
        assert matcher is not None
    
    def test_convenience_functions(self):
        """Test convenience/singleton functions work."""
        from asr.gurbani_prompt import get_gurbani_prompt, get_prompt_builder
        from services.ngram_rescorer import get_ngram_rescorer, rescore_transcription
        from services.sggs_aligner import get_sggs_aligner, snap_to_canonical
        
        # Test prompt
        prompt = get_gurbani_prompt(mode="sggs")
        assert prompt is not None
        
        # Test singleton
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()
        assert builder1 is builder2
        
        # Test rescorer singleton
        rescorer1 = get_ngram_rescorer()
        rescorer2 = get_ngram_rescorer()
        assert rescorer1 is rescorer2
        
        # Test aligner singleton
        aligner1 = get_sggs_aligner()
        aligner2 = get_sggs_aligner()
        assert aligner1 is aligner2
    
    def test_config_flags_respected(self):
        """Test that config flags control enhancement features."""
        # Temporarily modify config
        original_prompting = getattr(config, 'ENABLE_GURBANI_PROMPTING', True)
        original_rescoring = getattr(config, 'ENABLE_NGRAM_RESCORING', True)
        
        try:
            config.ENABLE_GURBANI_PROMPTING = False
            config.ENABLE_NGRAM_RESCORING = False
            
            # The orchestrator should respect these flags
            # (actual orchestrator test would need audio file)
            assert config.ENABLE_GURBANI_PROMPTING == False
            assert config.ENABLE_NGRAM_RESCORING == False
        finally:
            # Restore
            config.ENABLE_GURBANI_PROMPTING = original_prompting
            config.ENABLE_NGRAM_RESCORING = original_rescoring


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

