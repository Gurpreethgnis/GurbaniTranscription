"""
Consolidated orchestrator/pipeline tests.

Tests for:
- Orchestrator initialization
- Pipeline stages
- Processing options
- Document formatting integration

Replaces: test_orchestrator_direct.py, test_phase3.py, test_phase3_milestone*.py,
          test_phase4_full_pipeline.py, test_phase4_integration.py, test_phase5.py
"""
import sys
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestOrchestratorImports(unittest.TestCase):
    """Test orchestrator imports."""
    
    def test_import_orchestrator(self):
        """Test Orchestrator import."""
        from core.orchestrator import Orchestrator
        self.assertTrue(hasattr(Orchestrator, 'transcribe_file'))
    
    def test_import_models(self):
        """Test pipeline model imports."""
        from core.models import (
            TranscriptionResult,
            ProcessedSegment,
            FormattedDocument
        )
        self.assertTrue(TranscriptionResult)
        self.assertTrue(ProcessedSegment)
        self.assertTrue(FormattedDocument)


class TestOrchestratorConfig(unittest.TestCase):
    """Test orchestrator configuration."""
    
    def test_vad_config(self):
        """Test VAD configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'VAD_AGGRESSIVENESS'))
        self.assertTrue(hasattr(config, 'VAD_MIN_CHUNK_DURATION'))
        self.assertTrue(hasattr(config, 'VAD_MAX_CHUNK_DURATION'))
    
    def test_fusion_config(self):
        """Test fusion configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'FUSION_AGREEMENT_THRESHOLD'))
        self.assertTrue(hasattr(config, 'FUSION_CONFIDENCE_BOOST'))
        self.assertTrue(hasattr(config, 'FUSION_REDECODE_THRESHOLD'))
    
    def test_parallel_config(self):
        """Test parallel processing configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'ASR_PARALLEL_EXECUTION'))
        self.assertTrue(hasattr(config, 'ASR_PARALLEL_WORKERS'))


class TestProcessingOptions(unittest.TestCase):
    """Test processing options handling."""
    
    def test_default_options(self):
        """Test default processing options."""
        # Processing options are passed to orchestrator.transcribe_file
        # Verify the config defaults are reasonable
        import config
        
        self.assertGreaterEqual(config.VAD_AGGRESSIVENESS, 0)
        self.assertLessEqual(config.VAD_AGGRESSIVENESS, 3)
        self.assertGreater(config.VAD_MIN_CHUNK_DURATION, 0)
        self.assertGreater(config.VAD_MAX_CHUNK_DURATION, config.VAD_MIN_CHUNK_DURATION)
    
    def test_denoising_options(self):
        """Test denoising options."""
        import config
        
        self.assertTrue(hasattr(config, 'ENABLE_DENOISING'))
        self.assertTrue(hasattr(config, 'DENOISE_STRENGTH'))
        self.assertIn(config.DENOISE_STRENGTH, ['light', 'medium', 'aggressive'])


class TestPipelineModels(unittest.TestCase):
    """Test pipeline data models."""
    
    def test_processed_segment(self):
        """Test ProcessedSegment model."""
        from core.models import ProcessedSegment
        
        segment = ProcessedSegment(
            start=0.0,
            end=5.0,
            route='punjabi_speech',
            type='speech',
            text='Test',
            confidence=0.9,
            language='pa'
        )
        
        self.assertEqual(segment.route, 'punjabi_speech')
        self.assertEqual(segment.type, 'speech')
    
    def test_transcription_result(self):
        """Test TranscriptionResult model."""
        from core.models import TranscriptionResult, ProcessedSegment
        
        segment = ProcessedSegment(
            start=0.0,
            end=5.0,
            route='punjabi_speech',
            type='speech',
            text='Test',
            confidence=0.9,
            language='pa'
        )
        
        result = TranscriptionResult(
            filename='test.mp3',
            segments=[segment],
            transcription={'gurmukhi': 'Test'},
            metrics={'total_segments': 1}
        )
        
        self.assertEqual(result.filename, 'test.mp3')
        self.assertEqual(len(result.segments), 1)


class TestDocumentFormatting(unittest.TestCase):
    """Test document formatting integration."""
    
    def test_formatted_document_model(self):
        """Test FormattedDocument model."""
        from core.models import FormattedDocument, DocumentSection
        from datetime import datetime
        
        section = DocumentSection(
            section_type='katha',
            content='Test content',
            start_time=0.0,
            end_time=60.0
        )
        
        doc = FormattedDocument(
            title='Test',
            source_file='test.mp3',
            created_at=datetime.now().isoformat(),
            sections=[section],
            metadata={}
        )
        
        self.assertEqual(doc.title, 'Test')
        self.assertEqual(len(doc.sections), 1)
    
    def test_document_section_types(self):
        """Test various document section types."""
        from core.models import DocumentSection, QuoteContent
        
        # Opening Gurbani section
        quote = QuoteContent(
            gurmukhi='ਵਾਹਿਗੁਰੂ',
            roman='Waheguru',
            source='SGGS'
        )
        
        section = DocumentSection(
            section_type='opening_gurbani',
            content=quote,
            start_time=0.0,
            end_time=5.0
        )
        
        self.assertEqual(section.section_type, 'opening_gurbani')
        self.assertIsInstance(section.content, QuoteContent)


class TestScriptConversion(unittest.TestCase):
    """Test script conversion integration."""
    
    def test_script_converter_import(self):
        """Test ScriptConverter import."""
        from services.script_converter import ScriptConverter
        self.assertTrue(hasattr(ScriptConverter, 'convert'))
    
    def test_script_conversion_config(self):
        """Test script conversion configuration."""
        import config
        
        self.assertTrue(hasattr(config, 'SCRIPT_CONVERSION_CONFIDENCE_THRESHOLD'))
        self.assertTrue(hasattr(config, 'ROMAN_TRANSLITERATION_SCHEME'))


def run_tests():
    """Run all orchestrator tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorImports))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestProcessingOptions))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineModels))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestScriptConversion))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

