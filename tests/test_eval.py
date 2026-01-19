"""
Regression tests for evaluation harness.

Tests WER/CER calculation and quote accuracy metrics.
"""
import unittest
from pathlib import Path
from typing import Dict, Any

from core.models import (
    TranscriptionResult, ProcessedSegment, QuoteMatch, ScriptureSource
)
from eval.wer_cer_reports import calculate_wer_cer
from eval.quote_accuracy_reports import calculate_quote_metrics
from eval.dataset_builder import DatasetBuilder


class TestWERCER(unittest.TestCase):
    """Tests for WER/CER calculation."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample transcription result
        self.predicted_segments = [
            ProcessedSegment(
                start=0.0,
                end=5.0,
                route="punjabi_speech",
                type="speech",
                text="ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
                confidence=0.9,
                language="pa"
            ),
            ProcessedSegment(
                start=5.0,
                end=10.0,
                route="punjabi_speech",
                type="speech",
                text="ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਜੀ",
                confidence=0.85,
                language="pa"
            )
        ]
        
        self.predicted = TranscriptionResult(
            filename="test.mp3",
            segments=self.predicted_segments,
            transcription={
                "gurmukhi": "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਜੀ",
                "roman": "satinām vāhigurū gurū nānak dev jī"
            },
            metrics={}
        )
        
        # Create ground truth
        self.ground_truth = {
            "audio_file": "test.mp3",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "ground_truth_gurmukhi": "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
                    "ground_truth_roman": "satinām vāhigurū"
                },
                {
                    "start": 5.0,
                    "end": 10.0,
                    "ground_truth_gurmukhi": "ਗੁਰੂ ਨਾਨਕ ਦੇਵ ਜੀ",
                    "ground_truth_roman": "gurū nānak dev jī"
                }
            ]
        }
    
    def test_perfect_match(self):
        """Test WER/CER calculation with perfect match."""
        try:
            metrics = calculate_wer_cer(self.predicted, self.ground_truth)
            
            # Perfect match should have WER and CER of 0
            self.assertEqual(metrics['overall_wer'], 0.0)
            self.assertEqual(metrics['overall_cer'], 0.0)
            self.assertEqual(metrics['total_substitutions'], 0)
            self.assertEqual(metrics['total_insertions'], 0)
            self.assertEqual(metrics['total_deletions'], 0)
        except ImportError:
            self.skipTest("jiwer not available")
    
    def test_with_errors(self):
        """Test WER/CER calculation with errors."""
        try:
            # Modify predicted text to have errors
            self.predicted_segments[0].text = "ਸਤਿਨਾਮ ਵਾਹਿਗੁਰੂ"  # Missing ੁ (missing character)
            self.predicted_segments[1].text = "ਗੁਰੂ ਨਾਨਕ"  # Missing words
            
            metrics = calculate_wer_cer(self.predicted, self.ground_truth)
            
            # Should have non-zero WER and CER
            self.assertGreater(metrics['overall_wer'], 0.0)
            self.assertGreater(metrics['overall_cer'], 0.0)
            self.assertGreater(metrics['total_deletions'], 0)
        except ImportError:
            self.skipTest("jiwer not available")
    
    def test_language_filter(self):
        """Test language filtering."""
        try:
            # Add English segment
            self.predicted_segments.append(
                ProcessedSegment(
                    start=10.0,
                    end=15.0,
                    route="english_speech",
                    type="speech",
                    text="Hello world",
                    confidence=0.9,
                    language="en"
                )
            )
            
            # Calculate metrics for Punjabi only
            metrics = calculate_wer_cer(self.predicted, self.ground_truth, language="pa")
            
            # Should only include Punjabi segments
            self.assertEqual(len(metrics['segment_metrics']), 2)
        except ImportError:
            self.skipTest("jiwer not available")


class TestQuoteMetrics(unittest.TestCase):
    """Tests for quote accuracy metrics."""
    
    def setUp(self):
        """Set up test data."""
        # Create segment with quote match
        quote_match = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_1234",
            canonical_text="ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
            spoken_text="ਸਤਿਨਾਮ ਵਾਹਿਗੁਰੂ",
            confidence=0.95,
            ang=1,
            raag="Japji",
            author="Guru Nanak Dev Ji"
        )
        
        self.predicted_segments = [
            ProcessedSegment(
                start=0.0,
                end=5.0,
                route="scripture_quote_likely",
                type="scripture_quote",
                text="ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
                confidence=0.95,
                language="pa",
                quote_match=quote_match
            )
        ]
        
        self.predicted = TranscriptionResult(
            filename="test.mp3",
            segments=self.predicted_segments,
            transcription={"gurmukhi": "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ", "roman": ""},
            metrics={}
        )
        
        # Create ground truth with quote annotation
        self.ground_truth = {
            "audio_file": "test.mp3",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "ground_truth_gurmukhi": "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
                    "quotes": [
                        {
                            "start": 0.0,
                            "end": 5.0,
                            "canonical_line_id": "sggs_1234",
                            "expected_ang": 1,
                            "expected_source": "Sri Guru Granth Sahib Ji"
                        }
                    ]
                }
            ]
        }
    
    def test_perfect_quote_match(self):
        """Test quote metrics with perfect match."""
        metrics = calculate_quote_metrics(self.predicted, self.ground_truth)
        
        # Perfect match should have precision and recall of 1.0
        self.assertEqual(metrics['precision'], 1.0)
        self.assertEqual(metrics['recall'], 1.0)
        self.assertEqual(metrics['f1_score'], 1.0)
        self.assertEqual(metrics['true_positives'], 1)
        self.assertEqual(metrics['false_positives'], 0)
        self.assertEqual(metrics['false_negatives'], 0)
        self.assertEqual(metrics['replacement_accuracy'], 1.0)
    
    def test_false_positive(self):
        """Test quote metrics with false positive."""
        # Add a quote that doesn't exist in ground truth
        quote_match2 = QuoteMatch(
            source=ScriptureSource.SGGS,
            line_id="sggs_5678",
            canonical_text="ਗੁਰੂ ਨਾਨਕ",
            spoken_text="ਗੁਰੂ ਨਾਨਕ",
            confidence=0.9,
            ang=2
        )
        
        self.predicted_segments.append(
            ProcessedSegment(
                start=5.0,
                end=10.0,
                route="scripture_quote_likely",
                type="scripture_quote",
                text="ਗੁਰੂ ਨਾਨਕ",
                confidence=0.9,
                language="pa",
                quote_match=quote_match2
            )
        )
        
        metrics = calculate_quote_metrics(self.predicted, self.ground_truth)
        
        # Should have false positive
        self.assertGreater(metrics['false_positives'], 0)
        self.assertLess(metrics['precision'], 1.0)
    
    def test_false_negative(self):
        """Test quote metrics with false negative."""
        # Remove quote match from predicted
        self.predicted_segments[0].quote_match = None
        self.predicted_segments[0].type = "speech"
        
        metrics = calculate_quote_metrics(self.predicted, self.ground_truth)
        
        # Should have false negative
        self.assertGreater(metrics['false_negatives'], 0)
        self.assertLess(metrics['recall'], 1.0)


class TestDatasetBuilder(unittest.TestCase):
    """Tests for dataset builder."""
    
    def setUp(self):
        """Set up test data."""
        self.builder = DatasetBuilder()
        self.test_audio = Path("test_audio.mp3")
    
    def test_create_template(self):
        """Test template creation."""
        template_path = self.builder.create_template(self.test_audio)
        
        self.assertTrue(template_path.exists())
        
        data = self.builder.load_ground_truth(template_path)
        self.assertEqual(data['audio_file'], str(self.test_audio))
        self.assertEqual(len(data['segments']), 0)
        
        # Cleanup
        template_path.unlink()
    
    def test_add_segment(self):
        """Test adding segments."""
        ground_truth = {
            "audio_file": str(self.test_audio),
            "segments": []
        }
        
        ground_truth = self.builder.add_segment(
            ground_truth,
            start=0.0,
            end=5.0,
            ground_truth_gurmukhi="ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ",
            ground_truth_roman="satinām vāhigurū"
        )
        
        self.assertEqual(len(ground_truth['segments']), 1)
        self.assertEqual(ground_truth['segments'][0]['ground_truth_gurmukhi'], "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ")
    
    def test_validation(self):
        """Test ground truth validation."""
        # Valid data
        valid_data = {
            "audio_file": str(self.test_audio),
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "ground_truth_gurmukhi": "ਸਤਿਨਾਮੁ"
                }
            ]
        }
        
        # Should not raise
        self.builder._validate_ground_truth(valid_data)
        
        # Invalid data - missing field
        invalid_data = {
            "audio_file": str(self.test_audio),
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0
                    # Missing ground_truth_gurmukhi
                }
            ]
        }
        
        with self.assertRaises(ValueError):
            self.builder._validate_ground_truth(invalid_data)
        
        # Invalid data - start >= end
        invalid_data2 = {
            "audio_file": str(self.test_audio),
            "segments": [
                {
                    "start": 5.0,
                    "end": 0.0,  # Invalid
                    "ground_truth_gurmukhi": "ਸਤਿਨਾਮੁ"
                }
            ]
        }
        
        with self.assertRaises(ValueError):
            self.builder._validate_ground_truth(invalid_data2)


if __name__ == '__main__':
    unittest.main()
