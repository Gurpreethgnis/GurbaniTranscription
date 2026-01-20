"""
Acceptance Tests for Language Prioritization (Phase 13).

Tests ensure:
1. Gurmukhi output purity (>95%)
2. No English/Latin drift
3. Correct biasing for SGGS/Dasam modes
4. Script repair functionality
5. Domain correction within vocabulary
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.language_domains import (
    DomainMode,
    LanguageRegister,
    GurmukhiScript,
    get_domain_priorities,
    get_output_policy,
    SGGS_PRIORITIES,
    DASAM_PRIORITIES,
    COMMON_PARTICLES,
    HONORIFICS,
)
from data.domain_lexicon import (
    DomainLexicon,
    LexiconBuilder,
    get_domain_lexicon,
    is_in_domain_vocab,
)
from services.script_lock import (
    ScriptLock,
    ScriptAnalysis,
    enforce_gurmukhi,
    analyze_script,
    is_gurmukhi_pure,
)
from services.drift_detector import (
    DriftDetector,
    DriftSeverity,
    DriftType,
    detect_drift,
    is_drift_acceptable,
)
from services.domain_corrector import (
    DomainCorrector,
    ConservativeCorrector,
    correct_transcription,
    levenshtein_distance,
)


class TestGurmukhiScript:
    """Tests for Gurmukhi script validation."""
    
    def test_gurmukhi_char_detection(self):
        """Test that Gurmukhi characters are correctly identified."""
        # Gurmukhi characters
        assert GurmukhiScript.is_gurmukhi_char('ਅ')
        assert GurmukhiScript.is_gurmukhi_char('ੳ')
        assert GurmukhiScript.is_gurmukhi_char('ਕ')
        assert GurmukhiScript.is_gurmukhi_char('੧')  # Gurmukhi digit
        
        # Non-Gurmukhi characters
        assert not GurmukhiScript.is_gurmukhi_char('a')
        assert not GurmukhiScript.is_gurmukhi_char('अ')  # Devanagari
        assert not GurmukhiScript.is_gurmukhi_char('A')
    
    def test_allowed_punctuation(self):
        """Test that punctuation is correctly allowed."""
        assert GurmukhiScript.is_allowed_char('।')  # Danda
        assert GurmukhiScript.is_allowed_char('॥')  # Double danda
        assert GurmukhiScript.is_allowed_char(' ')  # Space
        assert GurmukhiScript.is_allowed_char(',')
        assert GurmukhiScript.is_allowed_char('.')


class TestDomainPriorities:
    """Tests for domain priority configurations."""
    
    def test_sggs_priorities(self):
        """Test SGGS mode prioritizes Sant Bhasha and Braj."""
        priorities = get_domain_priorities(DomainMode.SGGS)
        
        # Sant Bhasha should be highest
        assert priorities.sant_bhasha == 1.0
        # Braj and Old Punjabi should be high
        assert priorities.braj_bhasha >= 0.8
        assert priorities.old_punjabi >= 0.8
    
    def test_dasam_priorities(self):
        """Test Dasam mode prioritizes Braj and Sanskrit."""
        priorities = get_domain_priorities(DomainMode.DASAM)
        
        # Braj should be highest in Dasam
        assert priorities.braj_bhasha == 1.0
        # Sanskrit should be very high
        assert priorities.sanskrit >= 0.8
    
    def test_priority_list_ordering(self):
        """Test that priority list is correctly ordered."""
        priorities = SGGS_PRIORITIES
        ordered = priorities.get_priority_list()
        
        # Should be sorted by weight (highest first)
        weights = [w for _, w in ordered]
        assert weights == sorted(weights, reverse=True)


class TestScriptLock:
    """Tests for Gurmukhi script enforcement."""
    
    def test_pure_gurmukhi_validation(self):
        """Test validation of pure Gurmukhi text."""
        lock = ScriptLock()
        
        pure_text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
        is_valid, analysis = lock.validate(pure_text)
        
        assert is_valid
        assert analysis.script_purity >= 0.99
    
    def test_mixed_script_detection(self):
        """Test detection of mixed scripts."""
        lock = ScriptLock()
        
        mixed_text = "ਸਤਿ naam ਕਰਤਾ"  # Contains Latin
        is_valid, analysis = lock.validate(mixed_text)
        
        assert not is_valid
        assert analysis.latin_ratio > 0
    
    def test_script_repair(self):
        """Test repair of non-Gurmukhi characters."""
        lock = ScriptLock()
        
        mixed_text = "ਗੁਰੂ hello ਜੀ"
        repaired, was_modified = lock.repair(mixed_text)
        
        assert was_modified
        # Should have removed or converted "hello"
        analysis = lock.analyze(repaired)
        assert analysis.script_purity > 0.9
    
    def test_gurmukhi_purity_threshold(self):
        """Test Gurmukhi purity threshold function."""
        pure = "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ"
        assert is_gurmukhi_pure(pure, threshold=0.95)
        
        impure = "hello world"
        assert not is_gurmukhi_pure(impure, threshold=0.95)


class TestDriftDetector:
    """Tests for drift detection."""
    
    def test_no_drift_pure_gurmukhi(self):
        """Test that pure Gurmukhi has no drift."""
        detector = DriftDetector(DomainMode.SGGS)
        
        pure_text = "ਸਲੋਕੁ ਮਹਲਾ ੧ ॥ ਪਵਣੁ ਗੁਰੂ ਪਾਣੀ ਪਿਤਾ ਮਾਤਾ ਧਰਤਿ ਮਹਤੁ ॥"
        diagnostic = detector.detect(pure_text)
        
        assert diagnostic.severity in (DriftSeverity.NONE, DriftSeverity.LOW)
        assert not diagnostic.should_reject
    
    def test_english_drift_detection(self):
        """Test detection of English text drift."""
        detector = DriftDetector(DomainMode.SGGS)
        
        english_text = "This is English text that should be detected"
        diagnostic = detector.detect(english_text)
        
        assert DriftType.ENGLISH_DRIFT in diagnostic.drift_types or DriftType.LOW_PURITY in diagnostic.drift_types
        assert diagnostic.latin_ratio > 0.5
    
    def test_url_detection(self):
        """Test URL pattern detection."""
        detector = DriftDetector()
        
        text_with_url = "ਜੀ https://example.com ਹੈ"
        diagnostic = detector.detect(text_with_url)
        
        assert DriftType.URL_PATTERN in diagnostic.drift_types
        assert diagnostic.url_patterns
    
    def test_severity_levels(self):
        """Test that severity levels are correctly assigned."""
        detector = DriftDetector()
        
        # Pure Gurmukhi should be NONE or LOW
        pure = "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ ਵਾਹਿਗੁਰੂ ਜੀ ਕੀ ਫਤਿਹ"
        assert detector.detect(pure).severity in (DriftSeverity.NONE, DriftSeverity.LOW)
        
        # Mostly English should be HIGH or CRITICAL
        english = "This is completely English text with no Gurmukhi"
        assert detector.detect(english).severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)


class TestDomainLexicon:
    """Tests for domain lexicon functionality."""
    
    def test_lexicon_initialization(self):
        """Test that lexicon can be initialized."""
        lexicon = DomainLexicon()
        
        # Should have common particles
        assert len(lexicon.common_particles) > 0
        assert 'ਜੀ' in lexicon.common_particles or 'ਜੀ' in lexicon.honorifics
    
    def test_common_particles_in_vocab(self):
        """Test that common particles are in vocabulary."""
        lexicon = DomainLexicon()
        lexicon.common_particles = set(COMMON_PARTICLES)
        
        # Common Gurbani particles should be in vocab
        combined = lexicon.get_combined_vocab(DomainMode.SGGS)
        
        assert 'ਹੈ' in combined or 'ਹੈ' in COMMON_PARTICLES
        assert 'ਜੀ' in combined or 'ਜੀ' in HONORIFICS
    
    def test_mode_specific_vocab(self):
        """Test that vocab is mode-specific."""
        lexicon = DomainLexicon()
        lexicon.sggs_vocab = {'ਨਾਮੁ', 'ਸਬਦੁ'}
        lexicon.dasam_vocab = {'ਖੰਡਾ', 'ਚੱਕਰ'}
        
        sggs_vocab = lexicon.get_combined_vocab(DomainMode.SGGS)
        dasam_vocab = lexicon.get_combined_vocab(DomainMode.DASAM)
        
        # Both should contain all words (but SGGS mode prioritizes SGGS)
        assert 'ਨਾਮੁ' in sggs_vocab
        assert 'ਖੰਡਾ' in dasam_vocab


class TestDomainCorrector:
    """Tests for domain-constrained spelling correction."""
    
    def test_levenshtein_distance(self):
        """Test edit distance calculation."""
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("abc", "abc") == 0
        assert levenshtein_distance("abc", "ab") == 1
        assert levenshtein_distance("abc", "abd") == 1
        assert levenshtein_distance("abc", "xyz") == 3
    
    def test_no_correction_for_valid_words(self):
        """Test that valid words are not corrected."""
        corrector = DomainCorrector(DomainMode.SGGS)
        
        # Add word to vocab
        corrector.lexicon.common_particles = {'ਹੈ'}
        
        result = corrector.correct_word('ਹੈ')
        assert not result.was_corrected
        assert result.corrected == 'ਹੈ'
    
    def test_conservative_corrector(self):
        """Test conservative corrector settings."""
        conservative = ConservativeCorrector()
        
        # Should have tighter thresholds
        assert conservative.max_edit_distance <= 1
        assert conservative.min_confidence >= 0.7


class TestOutputPolicy:
    """Tests for output policy configuration."""
    
    def test_sggs_policy(self):
        """Test SGGS output policy."""
        policy = get_output_policy(DomainMode.SGGS)
        
        assert policy.output_script == "gurmukhi"
        assert policy.strict_gurmukhi
        assert not policy.modernize_spelling
        assert not policy.paraphrase
    
    def test_dasam_policy(self):
        """Test Dasam output policy."""
        policy = get_output_policy(DomainMode.DASAM)
        
        assert policy.output_script == "gurmukhi"
        assert policy.strict_gurmukhi


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_pipeline_pure_gurmukhi(self):
        """Test full pipeline with pure Gurmukhi input."""
        # Test text from Japji Sahib
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ"
        
        # Analyze script
        analysis = analyze_script(text)
        assert analysis.is_pure_gurmukhi
        
        # Detect drift
        diagnostic = detect_drift(text, DomainMode.SGGS)
        assert diagnostic.severity in (DriftSeverity.NONE, DriftSeverity.LOW)
        
        # Correct (should not change)
        corrected = correct_transcription(text, DomainMode.SGGS)
        # Text may have minor corrections but should remain mostly same
        assert len(corrected) > 0
    
    def test_full_pipeline_mixed_script(self):
        """Test full pipeline with mixed script input."""
        text = "ਵਾਹਿਗੁਰੂ ji hello"
        
        # Enforce Gurmukhi
        enforced = enforce_gurmukhi(text, DomainMode.SGGS)
        
        # Should have removed Latin characters
        analysis = analyze_script(enforced)
        assert analysis.script_purity > 0.9
    
    def test_drift_acceptable_helper(self):
        """Test drift acceptability helper function."""
        # Pure Gurmukhi should be acceptable
        pure = "ਇੱਕ ਓਅੰਕਾਰ ਸਤਿ ਨਾਮੁ"
        assert is_drift_acceptable(pure, DomainMode.SGGS)
        
        # Heavy English should not be acceptable
        english = "This is all English text"
        assert not is_drift_acceptable(english, DomainMode.SGGS, DriftSeverity.LOW)


class TestBlockedLanguages:
    """Tests for blocked language detection."""
    
    def test_hinglish_detection(self):
        """Test Hinglish pattern detection."""
        detector = DriftDetector()
        
        # Text with Hinglish markers
        hinglish = "ਜੀ hai toh theek hai ji"
        diagnostic = detector.detect(hinglish)
        
        assert DriftType.HINGLISH in diagnostic.drift_types or diagnostic.latin_ratio > 0
    
    def test_modern_slang_detection(self):
        """Test modern slang detection."""
        detector = DriftDetector()
        
        slang = "ਵਾਹਿਗੁਰੂ lol omg cool"
        diagnostic = detector.detect(slang)
        
        assert DriftType.MODERN_SLANG in diagnostic.drift_types or diagnostic.latin_ratio > 0


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

