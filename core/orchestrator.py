"""
Orchestrator for the transcription pipeline.

Coordinates VAD chunking, language identification, and ASR processing
to produce structured transcription results.

Phase 2: Supports multi-ASR ensemble with fusion.
Phase 12: Supports dynamic provider selection via ProviderRegistry.
"""
import logging
import uuid
import tempfile
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
import config
from core.models import (
    AudioChunk, ASRResult, ProcessedSegment, TranscriptionResult, Segment
)
from services.vad_service import VADService
from services.langid_service import LangIDService, ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH, ROUTE_SCRIPTURE_QUOTE_LIKELY, ROUTE_MIXED
from asr.asr_whisper import ASRWhisper
from asr.asr_indic import ASRIndic
from asr.asr_english_fallback import ASREnglish
from asr.asr_fusion import ASRFusion
from asr.provider_registry import ProviderRegistry, ProviderType, get_registry
from services.script_converter import ScriptConverter
from services.script_lock import ScriptLock, enforce_gurmukhi
from services.drift_detector import DriftDetector, DriftSeverity, detect_drift
from services.domain_corrector import DomainCorrector, correct_transcription
from data.language_domains import DomainMode, get_output_policy
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from quotes.quote_context_detector import QuoteContextDetector, QuoteContextResult
from quotes.constrained_matcher import ConstrainedQuoteMatcher
from post.transcript_merger import TranscriptMerger
# SGGS Enhancement imports
from asr.gurbani_prompt import GurbaniPromptBuilder, get_gurbani_prompt
from services.ngram_rescorer import NGramRescorer, get_ngram_rescorer
from services.sggs_aligner import SGGSAligner, get_sggs_aligner
from post.annotator import Annotator
from post.document_formatter import DocumentFormatter
from core.errors import ASREngineError, VADError, FusionError, AudioDenoiseError
# Shabad Mode imports
from services.shabad_detector import ShabadDetector, get_shabad_detector, ShabadDetectionResult, AudioMode
from services.semantic_praman import SemanticPramanService, get_semantic_praman_service, PramanSearchResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator for the transcription pipeline.
    
    Coordinates:
    1. VAD chunking
    2. Language/domain identification
    3. Multi-ASR processing with fusion (Phase 2)
    4. Result aggregation
    """
    
    def __init__(
        self,
        vad_service: Optional[VADService] = None,
        langid_service: Optional[LangIDService] = None,
        asr_service: Optional[ASRWhisper] = None,
        asr_indic: Optional[ASRIndic] = None,
        asr_english: Optional[ASREnglish] = None,
        fusion_service: Optional[ASRFusion] = None,
        live_callback: Optional[Callable] = None,
        primary_provider: Optional[str] = None,
        fallback_provider: Optional[str] = None
    ):
        """
        Initialize orchestrator with services.
        
        Args:
            vad_service: VAD service instance (created if None)
            langid_service: LangID service instance (created if None)
            asr_service: ASR-A service instance (created if None)
            asr_indic: ASR-B Indic service instance (created if None)
            asr_english: ASR-C English service instance (created if None)
            fusion_service: Fusion service instance (created if None)
            live_callback: Callback for live mode events
                          Signature: (event_type: str, data: Dict[str, Any]) -> None
                          event_type: "draft" or "verified"
            primary_provider: Primary ASR provider type (whisper, indicconformer, wav2vec2, commercial)
            fallback_provider: Fallback ASR provider type
        """
        self.vad_service = vad_service or VADService(
            aggressiveness=config.VAD_AGGRESSIVENESS if hasattr(config, 'VAD_AGGRESSIVENESS') else 2,
            min_chunk_duration=config.VAD_MIN_CHUNK_DURATION if hasattr(config, 'VAD_MIN_CHUNK_DURATION') else 1.0,
            max_chunk_duration=config.VAD_MAX_CHUNK_DURATION if hasattr(config, 'VAD_MAX_CHUNK_DURATION') else 30.0,
            overlap_seconds=config.VAD_OVERLAP_SECONDS if hasattr(config, 'VAD_OVERLAP_SECONDS') else 0.5
        )
        
        # Phase 12: Initialize provider registry for dynamic provider selection
        self.provider_registry = get_registry()
        self.primary_provider_type = primary_provider or getattr(config, 'ASR_PRIMARY_PROVIDER', 'whisper')
        self.fallback_provider_type = fallback_provider or getattr(config, 'ASR_FALLBACK_PROVIDER', None)
        
        # Initialize primary ASR service using registry or provided service
        if asr_service is not None:
            self.asr_service = asr_service
        else:
            self.asr_service = self._get_primary_asr_service()
        
        # Initialize ASR-B (Indic) and ASR-C (English) for Phase 2
        # These are still used for multi-ASR fusion when primary is whisper
        self.asr_indic = asr_indic
        self.asr_english = asr_english
        
        # Store additional providers for new provider types
        self._indicconformer_provider = None
        self._wav2vec2_provider = None
        self._commercial_provider = None
        
        # Initialize fusion service
        self.fusion_service = fusion_service or ASRFusion()
        
        # Phase 3: Initialize script converter
        self.script_converter = ScriptConverter(
            roman_scheme=getattr(config, 'ROMAN_TRANSLITERATION_SCHEME', 'practical'),
            enable_dictionary_lookup=getattr(config, 'ENABLE_DICTIONARY_LOOKUP', True)
        )
        logger.info("ScriptConverter initialized for Phase 3")
        
        # Phase 4: Initialize quote detection services
        self.quote_detector = QuoteCandidateDetector()
        self.quote_matcher = AssistedMatcher()
        self.quote_replacer = CanonicalReplacer()
        logger.info("Quote detection services initialized for Phase 4")
        
        # Phase 9: Initialize post-processing services
        self.transcript_merger = TranscriptMerger()
        self.annotator = Annotator()
        logger.info("Post-processing services initialized for Phase 9")
        
        # Phase 11: Initialize document formatting
        self.document_formatter = DocumentFormatter()
        logger.info("Document formatting service initialized for Phase 11")
        
        # Phase 14: Initialize SGGS enhancement services
        self._enable_gurbani_prompting = getattr(config, 'ENABLE_GURBANI_PROMPTING', True)
        self._enable_ngram_rescoring = getattr(config, 'ENABLE_NGRAM_RESCORING', True)
        self._enable_quote_alignment = getattr(config, 'ENABLE_QUOTE_ALIGNMENT', True)
        
        if self._enable_gurbani_prompting:
            self.prompt_builder = GurbaniPromptBuilder()
            logger.info("Gurbani prompt builder initialized for SGGS enhancement")
        else:
            self.prompt_builder = None
        
        if self._enable_ngram_rescoring:
            try:
                self.ngram_rescorer = get_ngram_rescorer()
                logger.info("N-gram rescorer initialized for SGGS enhancement")
            except Exception as e:
                logger.warning(f"Failed to initialize N-gram rescorer: {e}")
                self.ngram_rescorer = None
        else:
            self.ngram_rescorer = None
        
        self.quote_context_detector = QuoteContextDetector()
        self.constrained_matcher = ConstrainedQuoteMatcher()
        
        if self._enable_quote_alignment:
            try:
                self.sggs_aligner = get_sggs_aligner()
                logger.info("SGGS aligner initialized for quote snapping")
            except Exception as e:
                logger.warning(f"Failed to initialize SGGS aligner: {e}")
                self.sggs_aligner = None
        else:
            self.sggs_aligner = None
        
        # Phase 13: Initialize domain language prioritization services
        self._domain_mode = DomainMode(getattr(config, 'DOMAIN_MODE', 'sggs'))
        self._strict_gurmukhi = getattr(config, 'STRICT_GURMUKHI', True)
        self._enable_domain_correction = getattr(config, 'ENABLE_DOMAIN_CORRECTION', True)
        self.script_lock = ScriptLock(self._domain_mode)
        self.drift_detector = DriftDetector(self._domain_mode)
        self.domain_corrector = DomainCorrector(self._domain_mode)
        logger.info(f"Domain language prioritization initialized (mode: {self._domain_mode.value})")
        
        # Create LangID service with ASR-A for quick detection
        if langid_service is None:
            self.langid_service = LangIDService(
                quick_asr_service=self.asr_service,
                punjabi_threshold=config.LANGID_PUNJABI_THRESHOLD if hasattr(config, 'LANGID_PUNJABI_THRESHOLD') else 0.6,
                english_threshold=config.LANGID_ENGLISH_THRESHOLD if hasattr(config, 'LANGID_ENGLISH_THRESHOLD') else 0.6
            )
        else:
            self.langid_service = langid_service
        
        # Parallel execution settings
        self.parallel_execution = getattr(config, 'ASR_PARALLEL_EXECUTION', True)
        self.asr_timeout = getattr(config, 'ASR_TIMEOUT_SECONDS', 60)
        
        # Phase 6: Live mode callback
        self.live_callback = live_callback
        
        # Phase 7: Initialize audio denoiser (if enabled)
        self.denoiser = None
        if getattr(config, 'ENABLE_DENOISING', False):
            try:
                from audio.denoiser import AudioDenoiser
                self.denoiser = AudioDenoiser(
                    backend=getattr(config, 'DENOISE_BACKEND', 'noisereduce'),
                    strength=getattr(config, 'DENOISE_STRENGTH', 'medium'),
                    sample_rate=getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
                )
                logger.info("AudioDenoiser initialized for Phase 7")
            except Exception as e:
                logger.warning(f"Failed to initialize AudioDenoiser: {e}. Denoising disabled.")
                self.denoiser = None
        
        # Store current processing options
        self.current_processing_options = None
        
        # Shabad Mode: Initialize shabad detection and praman services
        self.shabad_detector = None
        self.semantic_praman_service = None
        self._shabad_mode_enabled = False
        logger.info("Shabad mode services will be initialized on first use")
        
        logger.info(f"Orchestrator initialized with primary provider: {self.primary_provider_type}")
    
    def _get_primary_asr_service(self):
        """
        Get the primary ASR service based on configured provider type.
        
        Returns:
            ASR provider instance
        """
        try:
            # For whisper, use the existing ASRWhisper
            if self.primary_provider_type == "whisper":
                return ASRWhisper()
            
            # For other providers, use the registry
            return self.provider_registry.get_provider(self.primary_provider_type)
        except Exception as e:
            logger.warning(f"Failed to load primary provider {self.primary_provider_type}: {e}")
            logger.info("Falling back to Whisper")
            return ASRWhisper()
    
    def get_provider(self, provider_type: str):
        """
        Get an ASR provider by type.
        
        Args:
            provider_type: Provider type (whisper, indicconformer, wav2vec2, commercial)
        
        Returns:
            ASR provider instance
        """
        if provider_type == "whisper":
            return self.asr_service
        
        # Use cached providers for efficiency
        if provider_type == "indicconformer":
            if self._indicconformer_provider is None:
                self._indicconformer_provider = self.provider_registry.get_provider("indicconformer")
            return self._indicconformer_provider
        
        if provider_type == "wav2vec2":
            if self._wav2vec2_provider is None:
                self._wav2vec2_provider = self.provider_registry.get_provider("wav2vec2")
            return self._wav2vec2_provider
        
        if provider_type == "commercial":
            if self._commercial_provider is None:
                self._commercial_provider = self.provider_registry.get_provider("commercial")
            return self._commercial_provider
        
        # Fallback to registry
        return self.provider_registry.get_provider(provider_type)
    
    def set_primary_provider(self, provider_type: str):
        """
        Change the primary ASR provider at runtime.
        
        Args:
            provider_type: New primary provider type
        """
        self.primary_provider_type = provider_type
        self.asr_service = self._get_primary_asr_service()
        logger.info(f"Primary provider changed to: {provider_type}")
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available ASR providers.
        
        Returns:
            List of provider type names
        """
        return self.provider_registry.list_available_providers()
    
    def get_provider_capabilities(self, provider_type: str = None) -> Dict[str, Any]:
        """
        Get capabilities for one or all providers.
        
        Args:
            provider_type: Specific provider, or None for all
        
        Returns:
            Dictionary of capabilities
        """
        return self.provider_registry.get_capabilities(provider_type)
    
    def set_domain_mode(self, mode: str, strict_gurmukhi: bool = True) -> None:
        """
        Set domain mode for language prioritization.
        
        Args:
            mode: Domain mode (sggs, dasam, generic)
            strict_gurmukhi: Whether to enforce strict Gurmukhi output
        """
        self._domain_mode = DomainMode(mode)
        self._strict_gurmukhi = strict_gurmukhi
        
        # Re-initialize domain services with new mode
        self.script_lock = ScriptLock(self._domain_mode)
        self.drift_detector = DriftDetector(self._domain_mode)
        self.domain_corrector = DomainCorrector(self._domain_mode)
        
        logger.info(f"Domain mode changed to: {mode}, strict_gurmukhi: {strict_gurmukhi}")
    
    def get_domain_mode(self) -> Dict[str, Any]:
        """
        Get current domain mode settings.
        
        Returns:
            Dictionary with domain_mode, strict_gurmukhi, enable_domain_correction
        """
        return {
            'domain_mode': self._domain_mode.value,
            'strict_gurmukhi': self._strict_gurmukhi,
            'enable_domain_correction': self._enable_domain_correction,
        }
    
    def _apply_processing_options(self, options: Dict[str, Any], job_id: Optional[str] = None) -> None:
        """
        Apply processing options to orchestrator services.
        
        Args:
            options: Dict with processing options
            job_id: Optional job identifier for logging
        """
        self.current_processing_options = options
        
        # Update VAD service settings
        if 'vadAggressiveness' in options:
            self.vad_service.vad = None  # Reset VAD to reinitialize
            import webrtcvad
            self.vad_service.vad = webrtcvad.Vad(options['vadAggressiveness'])
            logger.debug(f"[{job_id}] VAD aggressiveness set to {options['vadAggressiveness']}")
        
        if 'vadMinChunkDuration' in options:
            self.vad_service.min_chunk_duration = options['vadMinChunkDuration']
        
        if 'vadMaxChunkDuration' in options:
            self.vad_service.max_chunk_duration = options['vadMaxChunkDuration']
        
        # Update denoiser if options specify it
        if options.get('denoiseEnabled', False):
            try:
                from audio.denoiser import AudioDenoiser
                backend = options.get('denoiseBackend', 'noisereduce')
                strength = options.get('denoiseStrength', 'medium')
                sample_rate = getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
                
                # Reinitialize denoiser with new settings
                self.denoiser = AudioDenoiser(
                    backend=backend,
                    strength=strength,
                    sample_rate=sample_rate
                )
                logger.info(f"[{job_id}] Denoiser initialized: backend={backend}, strength={strength}")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to initialize denoiser with options: {e}")
        elif options.get('denoiseEnabled') is False:
            # Explicitly disable denoising
            self.denoiser = None
        
        # Update parallel execution settings
        if 'parallelProcessingEnabled' in options:
            self.parallel_execution = options['parallelProcessingEnabled']
        
        # Note: parallelWorkers is stored in options for use during processing
    
    def transcribe_file(
        self,
        audio_path: Path,
        mode: str = "batch",
        job_id: Optional[str] = None,
        processing_options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
        domain_mode: Optional[str] = None,
        strict_gurmukhi: Optional[bool] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file using the orchestrated pipeline.
        
        Args:
            audio_path: Path to audio file
            mode: Processing mode ("batch" or "live")
            job_id: Optional job identifier for logging (auto-generated if None)
            processing_options: Optional dict with processing configuration:
                - denoiseEnabled: bool
                - denoiseBackend: str
                - denoiseStrength: str
                - vadAggressiveness: int
                - vadMinChunkDuration: float
                - vadMaxChunkDuration: float
                - segmentRetryEnabled: bool
                - maxSegmentRetries: int
                - parallelProcessingEnabled: bool
                - parallelWorkers: int
            progress_callback: Optional callback function with signature:
                callback(step: str, step_progress: int, overall_progress: int, message: str, details: Optional[dict])
            domain_mode: Domain mode for language prioritization (sggs, dasam, generic)
            strict_gurmukhi: Enforce strict Gurmukhi-only output
        
        Returns:
            TranscriptionResult with structured segments and metadata
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Generate job ID if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())[:8]
        
        filename = audio_path.name
        logger.info(f"[{job_id}] Starting transcription: {filename} (mode: {mode})")
        
        # Apply processing options
        if processing_options:
            self._apply_processing_options(processing_options, job_id)
        
        # Phase 13: Configure domain mode for this transcription
        current_domain_mode = (
            DomainMode(domain_mode) if domain_mode 
            else self._domain_mode
        )
        current_strict_gurmukhi = (
            strict_gurmukhi if strict_gurmukhi is not None 
            else self._strict_gurmukhi
        )
        logger.info(f"[{job_id}] Domain mode: {current_domain_mode.value}, strict Gurmukhi: {current_strict_gurmukhi}")
        
        # Store for use in _process_chunk_with_fusion
        self._current_domain_mode = current_domain_mode
        self._current_strict_gurmukhi = current_strict_gurmukhi
        
        # Step 0: Audio denoising (Phase 7) - if enabled
        working_audio_path = audio_path
        denoise_enabled = (
            processing_options.get('denoiseEnabled', False) if processing_options
            else getattr(config, 'ENABLE_DENOISING', False)
        )
        
        if progress_callback:
            progress_callback("denoising", 0, 0, "Checking if denoising is needed...", None)
        
        if denoise_enabled and self.denoiser is not None:
            # Check if auto-enable based on noise level
            auto_enable = getattr(config, 'DENOISE_AUTO_ENABLE_THRESHOLD', 0.4)
            try:
                if progress_callback:
                    progress_callback("denoising", 10, 2, "Estimating noise level...", None)
                noise_level = self.denoiser.estimate_noise_level(audio_path)
                if noise_level >= auto_enable:
                    logger.info(f"[{job_id}] Step 0: Noise level {noise_level:.2f} >= {auto_enable}, applying denoising...")
                    if progress_callback:
                        progress_callback("denoising", 30, 5, f"Denoising audio file... (noise level: {noise_level:.2f})", None)
                    try:
                        # Create temporary file for denoised audio
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                            tmp_path = Path(tmp_file.name)
                        working_audio_path = self.denoiser.denoise_file(audio_path, tmp_path)
                        logger.info(f"[{job_id}] Denoised audio saved to temporary file")
                        if progress_callback:
                            progress_callback("denoising", 100, 10, "Denoising complete", None)
                    except Exception as e:
                        logger.warning(f"[{job_id}] Denoising failed: {e}. Using original audio.")
                        working_audio_path = audio_path
                else:
                    logger.debug(f"[{job_id}] Noise level {noise_level:.2f} < {auto_enable}, skipping denoising")
                    if progress_callback:
                        progress_callback("denoising", 100, 10, f"Noise level acceptable ({noise_level:.2f}), skipping denoising", None)
            except Exception as e:
                logger.warning(f"[{job_id}] Noise level estimation failed: {e}. Skipping denoising.")
                working_audio_path = audio_path
                if progress_callback:
                    progress_callback("denoising", 100, 10, "Skipping denoising", None)
        elif getattr(config, 'ENABLE_DENOISING', False):
            # Denoising enabled but not initialized - try to denoise anyway
            logger.info(f"[{job_id}] Step 0: Denoising enabled, applying...")
            if progress_callback:
                progress_callback("denoising", 30, 5, "Denoising audio file...", None)
            try:
                from audio.denoiser import AudioDenoiser
                denoiser = AudioDenoiser(
                    backend=getattr(config, 'DENOISE_BACKEND', 'noisereduce'),
                    strength=getattr(config, 'DENOISE_STRENGTH', 'medium'),
                    sample_rate=getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
                )
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    tmp_path = Path(tmp_file.name)
                working_audio_path = denoiser.denoise_file(audio_path, tmp_path)
                logger.info(f"[{job_id}] Denoised audio saved to temporary file")
                if progress_callback:
                    progress_callback("denoising", 100, 10, "Denoising complete", None)
            except Exception as e:
                logger.warning(f"[{job_id}] Denoising failed: {e}. Using original audio.")
                working_audio_path = audio_path
        else:
            # Denoising not enabled
            if progress_callback:
                progress_callback("denoising", 100, 10, "Denoising disabled", None)
        
        # Step 1: VAD chunking
        logger.info(f"[{job_id}] Step 1: Chunking audio with VAD...")
        if progress_callback:
            progress_callback("chunking", 0, 10, "Creating audio chunks with VAD...", None)
        try:
            # Use options for VAD chunking if provided
            vad_min = None
            vad_max = None
            if processing_options:
                vad_min = processing_options.get('vadMinChunkDuration')
                vad_max = processing_options.get('vadMaxChunkDuration')
            
            chunks = self.vad_service.chunk_audio(
                working_audio_path,
                min_chunk_duration=vad_min,
                max_chunk_duration=vad_max
            )
            logger.info(f"[{job_id}] Created {len(chunks)} audio chunks")
            if progress_callback:
                progress_callback("chunking", 100, 20, f"Created {len(chunks)} audio chunks", {"chunk_count": len(chunks)})
        except Exception as e:
            logger.error(f"[{job_id}] VAD chunking failed: {e}")
            raise VADError(f"Failed to chunk audio: {e}")
        finally:
            # Clean up temporary denoised file if created
            if working_audio_path != audio_path and working_audio_path.exists():
                try:
                    working_audio_path.unlink()
                    logger.debug(f"[{job_id}] Cleaned up temporary denoised file")
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to clean up temp file: {e}")
        
        # Step 2: Process each chunk
        processed_segments = []
        total_gurmukhi_text = ""
        total_roman_text = ""  # Will be populated in later phases
        
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            logger.info(f"[{job_id}] Processing chunk {i+1}/{len(chunks)} (time: {chunk.start_time:.2f}-{chunk.end_time:.2f}s)")
            
            # Update progress for chunk processing
            if progress_callback:
                chunk_progress = int((i / total_chunks) * 100) if total_chunks > 0 else 0
                overall_progress = 20 + int((i / total_chunks) * 70) if total_chunks > 0 else 20
                progress_callback("transcribing", chunk_progress, overall_progress, 
                                f"Transcribing chunk {i+1} of {total_chunks}", 
                                {"current_chunk": i+1, "total_chunks": total_chunks})
            
            # Step 2a: Language/domain identification
            route = self.langid_service.identify_segment(chunk)
            logger.debug(f"[{job_id}] Chunk {i+1} route: {route}")
            
            # Step 2b: Get language code for ASR
            language = self.langid_service.get_language_code(route)
            
            # Step 2c: Multi-ASR processing with fusion (Phase 2)
            try:
                processed_segment = self._process_chunk_with_fusion(
                    chunk, route, language, job_id
                )
                
                processed_segments.append(processed_segment)
                total_gurmukhi_text += processed_segment.text + " "
                # Add roman text if available
                if processed_segment.roman:
                    total_roman_text += processed_segment.roman + " "
                
                if processed_segment.needs_review:
                    logger.warning(f"[{job_id}] Chunk {i+1} flagged for review (confidence: {processed_segment.confidence:.2f})")
                
            except Exception as e:
                logger.error(f"[{job_id}] Error processing chunk {i+1}: {e}", exc_info=True)
                # Create error segment
                error_segment = ProcessedSegment(
                    start=chunk.start_time,
                    end=chunk.end_time,
                    route=route,
                    type="speech",
                    text="[Transcription error]",
                    confidence=0.0,
                    language="unknown",
                    needs_review=True
                )
                processed_segments.append(error_segment)
        
        # Step 2d: Validate all segments have transcriptions
        logger.info(f"[{job_id}] Validating segment transcriptions...")
        if progress_callback:
            progress_callback("transcribing", 100, 90, "Validating transcriptions...", None)
        segments_with_empty_text = []
        for i, seg in enumerate(processed_segments):
            if not seg.text or not seg.text.strip() or seg.text.strip() == "[Transcription error]":
                segments_with_empty_text.append(i + 1)
                # Ensure segment is marked for review
                seg.needs_review = True
                if not seg.text or not seg.text.strip():
                    seg.text = "[Transcription failed - review audio]"
                    logger.warning(f"[{job_id}] Segment {i+1} has empty transcription, marked for review")
        
        if segments_with_empty_text:
            logger.warning(
                f"[{job_id}] Found {len(segments_with_empty_text)} segment(s) with empty/failed transcriptions: "
                f"{segments_with_empty_text}. These segments are marked for review."
            )
        else:
            logger.info(f"[{job_id}] All {len(processed_segments)} segments have valid transcriptions")
        
        # Step 3: Post-processing
        if progress_callback:
            progress_callback("post_processing", 10, 90, "Merging transcriptions...", None)
        
        # Step 3a: Aggregate results using TranscriptMerger (Phase 9)
        transcription = {
            "gurmukhi": self.transcript_merger.merge_segments(processed_segments, format="gurmukhi"),
            "roman": self.transcript_merger.merge_segments(processed_segments, format="roman")
        }
        
        if progress_callback:
            progress_callback("post_processing", 50, 93, "Detecting quotes...", None)
        
        # Calculate metrics
        segments_needing_review = sum(1 for seg in processed_segments if seg.needs_review)
        avg_confidence = (
            sum(seg.confidence for seg in processed_segments) / len(processed_segments)
            if processed_segments else 0.0
        )
        
        # Calculate quote statistics (Phase 4)
        quotes_detected = sum(1 for seg in processed_segments if seg.quote_match is not None)
        quotes_replaced = sum(
            1 for seg in processed_segments 
            if seg.quote_match is not None and seg.type == "scripture_quote"
        )
        quotes_flagged_review = sum(
            1 for seg in processed_segments 
            if seg.quote_match is not None and seg.needs_review
        )
        
        metrics = {
            "mode": mode,
            "job_id": job_id,
            "total_chunks": len(chunks),
            "total_segments": len(processed_segments),
            "segments_needing_review": segments_needing_review,
            "average_confidence": avg_confidence,
            "routes": {
                route: sum(1 for seg in processed_segments if seg.route == route)
                for route in [ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH, "scripture_quote_likely", "mixed"]
            },
            "quotes_detected": quotes_detected,
            "quotes_replaced": quotes_replaced,
            "quotes_flagged_review": quotes_flagged_review
        }
        
        logger.info(f"[{job_id}] Transcription completed: {len(processed_segments)} segments, "
                   f"avg confidence: {avg_confidence:.2f}, review needed: {segments_needing_review}")
        
        result = TranscriptionResult(
            filename=filename,
            segments=processed_segments,
            transcription=transcription,
            metrics=metrics
        )
        
        # Phase 11: Auto-generate formatted document (JSON format)
        if progress_callback:
            progress_callback("post_processing", 80, 97, "Formatting document...", None)
        try:
            formatted_doc = self.document_formatter.format_document(result)
            # Store formatted document in result metadata for later export
            result.metrics["formatted_document"] = formatted_doc.to_dict()
            logger.info(f"[{job_id}] Formatted document generated")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to generate formatted document: {e}")
            # Don't fail the transcription if formatting fails
        
        if progress_callback:
            progress_callback("post_processing", 100, 100, "Transcription complete", None)
        
        return result
    
    def format_document(
        self,
        result: TranscriptionResult
    ) -> 'FormattedDocument':
        """
        Format a transcription result into a structured document.
        
        Phase 11: Document formatting functionality.
        
        Args:
            result: TranscriptionResult to format
        
        Returns:
            FormattedDocument
        """
        from models import FormattedDocument
        return self.document_formatter.format_document(result)
    
    def process_live_audio_chunk(
        self,
        audio_bytes: bytes,
        start_time: float,
        end_time: float,
        session_id: str,
        job_id: Optional[str] = None
    ) -> Optional[ProcessedSegment]:
        """
        Process a single audio chunk for live mode.
        
        Phase 6: Live mode processing that emits draft and verified events.
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            start_time: Start timestamp in seconds (relative to session start)
            end_time: End timestamp in seconds
            session_id: Client session identifier
            job_id: Optional job identifier for logging
        
        Returns:
            ProcessedSegment if successful, None on error
        """
        # Store session_id for callback
        self._current_session_id = session_id
        """
        Process a single audio chunk for live mode.
        
        Phase 6: Live mode processing that emits draft and verified events.
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            start_time: Start timestamp in seconds (relative to session start)
            end_time: End timestamp in seconds
            session_id: Client session identifier
            job_id: Optional job identifier for logging
        
        Returns:
            ProcessedSegment if successful, None on error
        """
        if job_id is None:
            job_id = f"live_{session_id[:8]}"
        
        logger.debug(f"[{job_id}] Processing live audio chunk: {start_time:.2f}-{end_time:.2f}s")
        
        # Phase 7: Denoise audio chunk if enabled for live mode
        working_audio_bytes = audio_bytes
        if getattr(config, 'LIVE_DENOISE_ENABLED', False):
            try:
                if self.denoiser is None:
                    # Initialize denoiser on-demand for live mode
                    from audio.denoiser import AudioDenoiser
                    self.denoiser = AudioDenoiser(
                        backend=getattr(config, 'DENOISE_BACKEND', 'noisereduce'),
                        strength=getattr(config, 'DENOISE_STRENGTH', 'medium'),
                        sample_rate=getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
                    )
                    logger.debug(f"[{job_id}] AudioDenoiser initialized for live mode")
                
                # Get sample rate from chunk_data or use default
                sample_rate = getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
                working_audio_bytes = self.denoiser.denoise_chunk(audio_bytes, sample_rate)
                logger.debug(f"[{job_id}] Audio chunk denoised")
            except Exception as e:
                logger.warning(f"[{job_id}] Live denoising failed: {e}. Using original audio.")
                working_audio_bytes = audio_bytes
        
        # Create temporary file from audio bytes (ensure it's a valid WAV for faster-whisper)
        try:
            import io
            import wave
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                # Wrap raw pcm bytes in a WAV container (assuming 16kHz, mono, 16-bit)
                with wave.open(tmp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(16000)
                    wav_file.writeframes(working_audio_bytes)
                tmp_path = Path(tmp_file.name)
            
            # Create AudioChunk
            duration = end_time - start_time
            chunk = AudioChunk(
                start_time=start_time,
                end_time=end_time,
                audio_path=tmp_path,
                duration=duration
            )
            
            # Identify route
            route = self.langid_service.identify_segment(chunk)
            language = self.langid_service.get_language_code(route)
            
            # Process chunk (will emit draft/verified via callback)
            processed_segment = self._process_chunk_with_fusion(
                chunk, route, language, job_id
            )
            
            # Clean up temporary file
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to delete temp file: {e}")
            
            return processed_segment
            
        except Exception as e:
            logger.error(f"[{job_id}] Error processing live audio chunk: {e}", exc_info=True)
            if self.live_callback:
                self.live_callback("error", {
                    "message": f"Processing error: {str(e)}",
                    "start": start_time,
                    "end": end_time
                })
            return None
    
    def _init_shabad_services(self) -> bool:
        """
        Initialize shabad mode services on first use.
        
        Returns:
            True if services initialized successfully
        """
        if self._shabad_mode_enabled:
            return True
        
        try:
            # Initialize shabad detector with SGGS database
            from scripture.sggs_db import SGGSDatabase
            try:
                sggs_db = SGGSDatabase()
            except Exception as e:
                logger.warning(f"Failed to load SGGS database for shabad mode: {e}")
                sggs_db = None
            
            self.shabad_detector = get_shabad_detector(sggs_db=sggs_db)
            logger.info("Shabad detector initialized for shabad mode")
            
            # Initialize semantic praman service
            semantic_index_path = getattr(config, 'SEMANTIC_INDEX_PATH', None)
            self.semantic_praman_service = get_semantic_praman_service(semantic_index_path)
            
            # Build index if not already built
            if self.semantic_praman_service.index is None and sggs_db:
                logger.info("Building semantic praman index (this may take a moment)...")
                self.semantic_praman_service.build_index(sggs_db=sggs_db)
            
            logger.info("Semantic praman service initialized for shabad mode")
            
            self._shabad_mode_enabled = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize shabad mode services: {e}", exc_info=True)
            return False
    
    def process_shabad_audio_chunk(
        self,
        audio_bytes: bytes,
        start_time: float,
        end_time: float,
        session_id: str,
        similar_count: int = 5,
        dissimilar_count: int = 3,
        job_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process audio chunk for shabad mode with praman suggestions.
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            session_id: Client session identifier
            similar_count: Number of similar pramans to return
            dissimilar_count: Number of dissimilar pramans to return
            job_id: Optional job identifier for logging
        
        Returns:
            Dictionary with shabad detection and praman results, or None on error
        """
        # Initialize shabad services if needed
        if not self._init_shabad_services():
            logger.error("Shabad mode services not available")
            return None
        
        # Store session_id for callback
        self._current_session_id = session_id
        
        if job_id is None:
            job_id = f"shabad_{session_id[:8]}"
        
        logger.debug(f"[{job_id}] Processing shabad audio chunk: {start_time:.2f}-{end_time:.2f}s")
        
        # Apply aggressive denoising for shabad mode (kirtan has musical instruments)
        working_audio_bytes = audio_bytes
        shabad_denoise_strength = getattr(config, 'SHABAD_MODE_DENOISE_STRENGTH', 'aggressive')
        
        try:
            from audio.denoiser import AudioDenoiser
            denoiser = AudioDenoiser(
                backend=getattr(config, 'DENOISE_BACKEND', 'noisereduce'),
                strength=shabad_denoise_strength,
                sample_rate=getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
            )
            sample_rate = getattr(config, 'DENOISE_SAMPLE_RATE', 16000)
            working_audio_bytes = denoiser.denoise_chunk(audio_bytes, sample_rate)
            logger.debug(f"[{job_id}] Audio denoised with strength: {shabad_denoise_strength}")
        except Exception as e:
            logger.warning(f"[{job_id}] Shabad mode denoising failed: {e}. Using original audio.")
            working_audio_bytes = audio_bytes
        
        try:
            import io
            import wave
            
            # Create temporary file from audio bytes (ensure it's a valid WAV for faster-whisper)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                # Wrap raw pcm bytes in a WAV container (assuming 16kHz, mono, 16-bit)
                with wave.open(tmp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(16000)
                    wav_file.writeframes(working_audio_bytes)
                tmp_path = Path(tmp_file.name)
            
            # Create AudioChunk
            duration = end_time - start_time
            chunk = AudioChunk(
                start_time=start_time,
                end_time=end_time,
                audio_path=tmp_path,
                duration=duration
            )
            
            # Get Gurbani prompt for better ASR
            gurbani_prompt = None
            if self.prompt_builder:
                gurbani_prompt = self.prompt_builder.get_prompt(
                    mode='sggs',
                    context='scripture'
                )
            
            # Transcribe with Gurbani-focused prompt
            asr_result = self.asr_service.transcribe_chunk(
                chunk,
                language='pa',  # Punjabi
                route=ROUTE_SCRIPTURE_QUOTE_LIKELY,
                initial_prompt=gurbani_prompt
            )
            
            transcribed_text = asr_result.text
            logger.debug(f"[{job_id}] Transcribed: {transcribed_text[:100]}...")
            
            # Detect shabad and match line
            detection_result = self.shabad_detector.detect(transcribed_text)
            
            # Prepare response
            result = {
                'session_id': session_id,
                'start_time': start_time,
                'end_time': end_time,
                'transcribed_text': transcribed_text,
                'asr_confidence': asr_result.confidence,
                'audio_mode': detection_result.mode.value,
                'mode_confidence': detection_result.mode_confidence,
                'matched_line': None,
                'next_line': None,
                'shabad_info': None,
                'similar_pramans': [],
                'dissimilar_pramans': [],
                'is_new_shabad': detection_result.is_new_shabad
            }
            
            # If we matched a shabad line
            if detection_result.matched_line:
                matched = detection_result.matched_line
                result['matched_line'] = {
                    'line_id': matched.line_id,
                    'gurmukhi': matched.gurmukhi,
                    'roman': matched.roman,
                    'line_number': matched.line_number,
                    'total_lines': matched.total_lines,
                    'ang': matched.ang,
                    'raag': matched.raag,
                    'author': matched.author,
                    'shabad_id': matched.shabad_id
                }
                result['match_confidence'] = detection_result.match_confidence
                
                # Get next line prediction
                if detection_result.shabad_context:
                    next_line = detection_result.shabad_context.next_line
                    if next_line:
                        result['next_line'] = {
                            'line_id': next_line.line_id,
                            'gurmukhi': next_line.gurmukhi,
                            'roman': next_line.roman,
                            'line_number': next_line.line_number
                        }
                    
                    # Shabad info
                    result['shabad_info'] = {
                        'shabad_id': detection_result.shabad_context.shabad_id,
                        'current_line_index': detection_result.shabad_context.current_line_index,
                        'total_lines': len(detection_result.shabad_context.lines),
                        'is_at_end': detection_result.shabad_context.is_at_end()
                    }
                
                # Find related pramans
                if self.semantic_praman_service and self.semantic_praman_service.index is not None:
                    try:
                        praman_result = self.semantic_praman_service.search_pramans(
                            matched.gurmukhi,
                            similar_count=similar_count,
                            dissimilar_count=dissimilar_count,
                            exclude_same_shabad=True,
                            current_shabad_id=matched.shabad_id
                        )
                        
                        # Convert to serializable format
                        result['similar_pramans'] = [
                            {
                                'line_id': p.line_id,
                                'gurmukhi': p.gurmukhi,
                                'roman': p.roman,
                                'source': p.source,
                                'ang': p.ang,
                                'raag': p.raag,
                                'author': p.author,
                                'similarity_score': p.similarity_score,
                                'shared_keywords': p.shared_keywords
                            }
                            for p in praman_result.similar_pramans
                        ]
                        
                        result['dissimilar_pramans'] = [
                            {
                                'line_id': p.line_id,
                                'gurmukhi': p.gurmukhi,
                                'roman': p.roman,
                                'source': p.source,
                                'ang': p.ang,
                                'raag': p.raag,
                                'author': p.author,
                                'similarity_score': p.similarity_score,
                                'shared_keywords': p.shared_keywords
                            }
                            for p in praman_result.dissimilar_pramans
                        ]
                        
                        logger.debug(
                            f"[{job_id}] Found {len(result['similar_pramans'])} similar, "
                            f"{len(result['dissimilar_pramans'])} dissimilar pramans"
                        )
                    except Exception as e:
                        logger.warning(f"[{job_id}] Praman search failed: {e}")
            
            # Emit shabad update via callback
            if self.live_callback:
                self.live_callback("shabad_update", result)
            
            # Clean up temporary file
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to delete temp file: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{job_id}] Error processing shabad audio chunk: {e}", exc_info=True)
            if self.live_callback:
                self.live_callback("error", {
                    "message": f"Shabad processing error: {str(e)}",
                    "start": start_time,
                    "end": end_time
                })
            return None
    
    def reset_shabad_context(self) -> None:
        """Reset shabad tracking context for a new session."""
        if self.shabad_detector:
            self.shabad_detector.reset_context()
            logger.debug("Shabad context reset")
    
    def get_shabad_context(self) -> Optional[Dict[str, Any]]:
        """Get current shabad context for UI state."""
        if not self.shabad_detector:
            return None
        
        context = self.shabad_detector.get_current_context()
        if not context:
            return None
        
        return {
            'shabad_id': context.shabad_id,
            'current_line_index': context.current_line_index,
            'total_lines': len(context.lines),
            'current_line': {
                'line_id': context.current_line.line_id,
                'gurmukhi': context.current_line.gurmukhi,
                'roman': context.current_line.roman
            } if context.current_line else None,
            'next_line': {
                'line_id': context.next_line.line_id,
                'gurmukhi': context.next_line.gurmukhi,
                'roman': context.next_line.roman
            } if context.next_line else None,
            'is_at_end': context.is_at_end()
        }
    
    def _process_chunk_with_fusion(
        self,
        chunk: AudioChunk,
        route: str,
        language: Optional[str],
        job_id: Optional[str] = None
    ) -> ProcessedSegment:
        """
        Process a chunk using multi-ASR ensemble with fusion.
        
        Implements hybrid execution:
        1. Run ASR-A immediately
        2. Run ASR-B/C in parallel based on route
        3. Fuse results
        4. Apply re-decode policy if needed
        
        Args:
            chunk: AudioChunk to process
            route: Route string (punjabi_speech, english_speech, etc.)
            language: Language code for ASR
        
        Returns:
            ProcessedSegment with fused results
        """
        # Step 0: Generate Gurbani prompt if enabled
        gurbani_prompt = None
        if self.prompt_builder and self._enable_gurbani_prompting:
            try:
                # Get domain mode for prompt
                domain_mode = getattr(self, '_current_domain_mode', self._domain_mode)
                gurbani_prompt = self.prompt_builder.get_prompt(
                    mode=domain_mode.value,
                    context="scripture" if route == ROUTE_SCRIPTURE_QUOTE_LIKELY else None
                )
                logger.debug(f"[{job_id}] Gurbani prompt generated ({len(gurbani_prompt)} chars)")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to generate Gurbani prompt: {e}")
        
        # Step 1: Run ASR-A immediately (primary engine)
        logger.debug(f"[{job_id}] Running ASR-A (Whisper) for chunk at {chunk.start_time:.2f}s")
        try:
            asr_a_result = self.asr_service.transcribe_chunk(
                chunk,
                language=language,
                route=route,
                initial_prompt=gurbani_prompt  # Use Gurbani prompt
            )
            logger.debug(f"[{job_id}] ASR-A completed: confidence={asr_a_result.confidence:.2f}")
            
            # Phase 6: Emit draft caption for live mode
            if self.live_callback:
                segment_id = f"seg_{chunk.start_time:.2f}_{chunk.end_time:.2f}"
                try:
                    # Quick script conversion for draft (may be incomplete)
                    draft_converted = self.script_converter.convert(
                        asr_a_result.text,
                        source_language=asr_a_result.language
                    )
                    self.live_callback("draft", {
                        "session_id": getattr(self, '_current_session_id', 'unknown'),
                        "segment_id": segment_id,
                        "start": chunk.start_time,
                        "end": chunk.end_time,
                        "text": asr_a_result.text,
                        "gurmukhi": draft_converted.gurmukhi if draft_converted else asr_a_result.text,
                        "roman": draft_converted.roman if draft_converted else None,
                        "confidence": asr_a_result.confidence
                    })
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to emit draft caption: {e}")
        except Exception as e:
            logger.error(f"[{job_id}] ASR-A failed: {e}")
            raise ASREngineError("asr_a", str(e))
        
        # Step 2: Determine which additional ASR engines to run
        engines_to_run = self._get_engines_for_route(route)
        
        # Step 3: Run additional engines in parallel (if enabled)
        additional_results = []
        if engines_to_run and self.parallel_execution:
            logger.debug(f"[{job_id}] Running additional engines in parallel: {', '.join(engines_to_run)}")
            additional_results = self._run_additional_engines_parallel(
                chunk, route, language, engines_to_run, job_id
            )
        elif engines_to_run:
            # Sequential execution
            logger.debug(f"[{job_id}] Running additional engines sequentially: {', '.join(engines_to_run)}")
            additional_results = self._run_additional_engines_sequential(
                chunk, route, language, engines_to_run, job_id
            )
        
        # Step 4: Collect all hypotheses
        all_hypotheses = [asr_a_result] + additional_results
        logger.debug(f"[{job_id}] Collected {len(all_hypotheses)} hypotheses for fusion")
        
        # Step 5: Fuse hypotheses
        try:
            fusion_result = self.fusion_service.fuse_hypotheses(all_hypotheses, chunk)
            logger.debug(f"[{job_id}] Fusion completed: confidence={fusion_result.fused_confidence:.2f}, "
                        f"agreement={fusion_result.agreement_score:.2f}, selected={fusion_result.selected_engine}")
        except Exception as e:
            logger.error(f"[{job_id}] Fusion failed: {e}")
            raise FusionError(f"Failed to fuse hypotheses: {e}")
        
        # Step 5a: Check for empty transcription and retry if needed
        retry_enabled = (
            self.current_processing_options.get('segmentRetryEnabled', True) if self.current_processing_options
            else getattr(config, 'SEGMENT_RETRY_ON_EMPTY', True)
        )
        max_retries = (
            self.current_processing_options.get('maxSegmentRetries', 2) if self.current_processing_options
            else getattr(config, 'SEGMENT_MAX_RETRIES', 2)
        )
        
        if retry_enabled and not fusion_result.fused_text.strip() and max_retries > 0:
            logger.warning(f"[{job_id}] Empty transcription detected, attempting retry (max {max_retries} attempts)...")
            for attempt in range(max_retries):
                try:
                    logger.info(f"[{job_id}] Retry attempt {attempt + 1}/{max_retries} with increased resources...")
                    # Retry with ASR-B (Indic) which is better for complex vocabulary
                    if self.asr_indic is None:
                        self.asr_indic = ASRIndic()
                    retry_result = self.asr_indic.transcribe_chunk(chunk, language, route)
                    
                    if retry_result.text.strip():
                        # Found transcription in retry
                        logger.info(f"[{job_id}] Retry successful: found transcription")
                        # Use retry result as primary
                        fusion_result.fused_text = retry_result.text
                        fusion_result.fused_confidence = retry_result.confidence
                        fusion_result.hypotheses = [retry_result]
                        break
                    else:
                        logger.warning(f"[{job_id}] Retry {attempt + 1} also produced empty transcription")
                except Exception as e:
                    logger.warning(f"[{job_id}] Retry attempt {attempt + 1} failed: {e}")
            
            # If still empty after retries, mark for review
            if not fusion_result.fused_text.strip():
                logger.error(f"[{job_id}] All retry attempts failed, segment will be marked for review")
                fusion_result.fused_text = "[Transcription failed - review audio]"
                fusion_result.fused_confidence = 0.0
        
        # Step 6: Apply re-decode policy if needed
        if self.fusion_service.should_redecode(fusion_result):
            logger.warning(f"[{job_id}] Low confidence ({fusion_result.fused_confidence:.2f}), triggering re-decode...")
            redecode_result = self._redecode_chunk(chunk, route, language, job_id)
            if redecode_result:
                fusion_result = self.fusion_service.apply_redecode(
                    fusion_result, redecode_result
                )
                logger.info(f"[{job_id}] Re-decode completed, new confidence: {fusion_result.fused_confidence:.2f}")
        
        # Step 6b: Apply N-gram LM rescoring (SGGS enhancement)
        if self.ngram_rescorer and self._enable_ngram_rescoring and fusion_result.fused_text:
            try:
                rescored = self.ngram_rescorer.rescore_hypothesis(
                    fusion_result.fused_text,
                    fusion_result.fused_confidence
                )
                
                # Update confidence if LM rescoring boosted it
                if rescored.combined_score > fusion_result.fused_confidence:
                    logger.debug(
                        f"[{job_id}] N-gram LM boosted confidence: "
                        f"{fusion_result.fused_confidence:.3f} → {rescored.combined_score:.3f} "
                        f"(perplexity: {rescored.perplexity:.1f})"
                    )
                    fusion_result.fused_confidence = rescored.combined_score
            except Exception as e:
                logger.warning(f"[{job_id}] N-gram rescoring failed: {e}")
        
        # Step 6c: Quote context detection (SGGS enhancement)
        quote_context = None
        if self.quote_context_detector:
            try:
                quote_context = self.quote_context_detector.detect(
                    fusion_result.fused_text,
                    previous_text=None  # Could pass previous segment text here
                )
                if quote_context.is_quote_likely:
                    logger.debug(
                        f"[{job_id}] Quote context detected: "
                        f"type={quote_context.context_type}, "
                        f"confidence={quote_context.quote_confidence:.2f}, "
                        f"signals={quote_context.detected_signals}"
                    )
                    # If this is a quote intro, note it for next segment
                    if quote_context.is_quote_intro:
                        logger.debug(f"[{job_id}] Quote introduction detected")
            except Exception as e:
                logger.warning(f"[{job_id}] Quote context detection failed: {e}")
        
        # Step 7: Phase 3 - Apply script conversion
        logger.debug(f"[{job_id}] Applying script conversion to fused text...")
        try:
            converted = self.script_converter.convert(
                fusion_result.fused_text,
                source_language=asr_a_result.language
            )
            logger.debug(
                f"[{job_id}] Script conversion: {converted.original_script} → Gurmukhi "
                f"(confidence: {converted.confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"[{job_id}] Script conversion failed: {e}", exc_info=True)
            # Fallback: use original text as Gurmukhi, no Roman
            converted = None
        
        # Step 7b: Phase 13 - Domain validation and correction
        domain_text = converted.gurmukhi if converted else fusion_result.fused_text
        domain_needs_review = False
        
        try:
            # Get current domain settings (set in transcribe_file)
            domain_mode = getattr(self, '_current_domain_mode', self._domain_mode)
            strict_gurmukhi = getattr(self, '_current_strict_gurmukhi', self._strict_gurmukhi)
            
            # Step 7b-1: Detect drift
            drift_diagnostic = self.drift_detector.detect(domain_text)
            logger.debug(
                f"[{job_id}] Drift detection: purity={drift_diagnostic.script_purity:.2f}, "
                f"latin={drift_diagnostic.latin_ratio:.3f}, oov={drift_diagnostic.oov_ratio:.2f}, "
                f"severity={drift_diagnostic.severity.value}"
            )
            
            # Step 7b-2: Apply script lock if strict mode or drift detected
            if strict_gurmukhi or drift_diagnostic.should_redecode:
                domain_text, script_analysis, was_repaired = self.script_lock.enforce(
                    domain_text,
                    strict=strict_gurmukhi
                )
                if was_repaired:
                    logger.info(f"[{job_id}] Script lock repaired non-Gurmukhi characters")
                    # Update converted text
                    if converted:
                        converted.gurmukhi = domain_text
            
            # Step 7b-3: Apply domain correction if enabled and needed
            if self._enable_domain_correction and drift_diagnostic.should_correct:
                corrected_text, correction_results = self.domain_corrector.correct_text(
                    domain_text,
                    enforce_script=False  # Already done above
                )
                corrections_made = sum(1 for r in correction_results if r.was_corrected)
                if corrections_made > 0:
                    logger.info(f"[{job_id}] Domain corrector made {corrections_made} corrections")
                    domain_text = corrected_text
                    if converted:
                        converted.gurmukhi = domain_text
            
            # Step 7b-4: Flag for review if drift is severe
            if drift_diagnostic.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL):
                domain_needs_review = True
                logger.warning(
                    f"[{job_id}] Segment flagged for review due to drift: {drift_diagnostic.severity.value}"
                )
        except Exception as e:
            logger.error(f"[{job_id}] Domain pipeline failed: {e}", exc_info=True)
            # Continue with original text - don't fail the whole segment
        
        # Step 7c: SGGS Alignment (Phase 14) - "snap" to canonical text if high confidence match
        sggs_alignment_result = None
        if self.sggs_aligner and self._enable_quote_alignment:
            # Only attempt alignment if quote context suggests a quote or route is scripture
            should_align = (
                route == ROUTE_SCRIPTURE_QUOTE_LIKELY or
                (quote_context and quote_context.is_quote_likely and quote_context.quote_confidence >= 0.5)
            )
            
            if should_align:
                try:
                    # Extract Ang hint from quote context if available
                    ang_hint = None
                    if quote_context:
                        ang_hint = self.quote_context_detector.extract_ang_reference(fusion_result.fused_text)
                    
                    sggs_alignment_result = self.sggs_aligner.align_to_canonical(
                        domain_text,
                        ang_hint=ang_hint
                    )
                    
                    if sggs_alignment_result.was_aligned:
                        logger.info(
                            f"[{job_id}] SGGS alignment applied: score={sggs_alignment_result.alignment_score:.2f}, "
                            f"ang={sggs_alignment_result.ang}"
                        )
                        domain_text = sggs_alignment_result.aligned_text
                        if converted:
                            converted.gurmukhi = domain_text
                    elif sggs_alignment_result.alignment_score >= 0.5:
                        logger.debug(
                            f"[{job_id}] SGGS alignment found candidate (score={sggs_alignment_result.alignment_score:.2f}) "
                            f"but below threshold"
                        )
                except Exception as e:
                    logger.warning(f"[{job_id}] SGGS alignment failed: {e}")
        
        # Step 8: Phase 4 - Quote Detection + Matching
        # Create temporary segment for quote detection
        temp_segment = ProcessedSegment(
            start=chunk.start_time,
            end=chunk.end_time,
            route=route,
            type="speech",  # Will be updated if quote found
            text=domain_text,  # Use domain-processed text
            confidence=fusion_result.fused_confidence,
            language=asr_a_result.language,
            hypotheses=fusion_result.hypotheses,
            needs_review=domain_needs_review,  # Include domain review flag
            roman=converted.roman if converted else None,
            original_script=converted.original_script if converted else None,
            script_confidence=converted.confidence if converted else None
        )
        
        # Detect quote candidates and match if route suggests scripture or quote context is likely
        should_detect_quotes = (
            route == ROUTE_SCRIPTURE_QUOTE_LIKELY or
            (quote_context and quote_context.is_quote_likely and quote_context.quote_confidence >= 0.4)
        )
        
        if should_detect_quotes:
            logger.debug(f"[{job_id}] Detecting quote candidates...")
            try:
                # If we already have a SGGS alignment result, use it for quote matching
                if sggs_alignment_result and sggs_alignment_result.matched_line:
                    # Use the alignment result directly for quote replacement
                    from core.models import QuoteMatch
                    matched_line = sggs_alignment_result.matched_line
                    quote_match = QuoteMatch(
                        source=matched_line.source,
                        line_id=matched_line.line_id,
                        canonical_text=matched_line.gurmukhi,
                        canonical_roman=matched_line.roman,
                        spoken_text=temp_segment.text,
                        confidence=sggs_alignment_result.confidence,
                        ang=matched_line.ang,
                        raag=matched_line.raag,
                        author=matched_line.author,
                        match_method="sggs_alignment"
                    )
                    logger.info(
                        f"[{job_id}] Using SGGS alignment for quote match: {matched_line.line_id} "
                        f"(confidence: {sggs_alignment_result.confidence:.2f})"
                    )
                    temp_segment = self.quote_replacer.replace_with_canonical(
                        temp_segment,
                        quote_match
                    )
                else:
                    # Use traditional quote detection flow
                    candidates = self.quote_detector.detect_candidates(
                        temp_segment,
                        hypotheses=fusion_result.hypotheses
                    )
                    
                    if candidates:
                        logger.debug(f"[{job_id}] Found {len(candidates)} quote candidate(s)")
                        
                        # Try to find a match using constrained matcher first (more accurate)
                        quote_match = None
                        if self.constrained_matcher:
                            try:
                                alignment = self.constrained_matcher.find_best_alignment(
                                    temp_segment.text
                                )
                                if alignment and alignment.is_confident_match:
                                    from core.models import QuoteMatch
                                    matched_line = alignment.matched_line
                                    quote_match = QuoteMatch(
                                        source=matched_line.source,
                                        line_id=matched_line.line_id,
                                        canonical_text=matched_line.gurmukhi,
                                        canonical_roman=matched_line.roman,
                                        spoken_text=temp_segment.text,
                                        confidence=alignment.confidence,
                                        ang=matched_line.ang,
                                        raag=matched_line.raag,
                                        author=matched_line.author,
                                        match_method="constrained_alignment"
                                    )
                                    logger.info(
                                        f"[{job_id}] Constrained matcher found: {matched_line.line_id} "
                                        f"(score: {alignment.alignment_score:.2f})"
                                    )
                            except Exception as e:
                                logger.debug(f"[{job_id}] Constrained matcher failed: {e}")
                        
                        # Fall back to traditional quote matcher
                        if not quote_match:
                            quote_match = self.quote_matcher.find_match(
                                candidates,
                                hypotheses=fusion_result.hypotheses,
                                source=None  # Search all sources
                            )
                        
                        if quote_match:
                            logger.info(
                                f"[{job_id}] Quote match found: {quote_match.line_id} "
                                f"(confidence: {quote_match.confidence:.2f})"
                            )
                            # Replace with canonical text
                            temp_segment = self.quote_replacer.replace_with_canonical(
                                temp_segment,
                                quote_match
                            )
                        else:
                            logger.debug(f"[{job_id}] No quote match found for candidates")
                    else:
                        logger.debug(f"[{job_id}] No quote candidates detected")
            except Exception as e:
                logger.error(f"[{job_id}] Quote detection/matching failed: {e}", exc_info=True)
                # Continue with original text - don't fail the whole segment
        
        # Step 9: Create final processed segment (use temp_segment, update needs_review)
        # Update needs_review based on all factors
        needs_review = (
            fusion_result.fused_confidence < (
                config.SEGMENT_CONFIDENCE_THRESHOLD 
                if hasattr(config, 'SEGMENT_CONFIDENCE_THRESHOLD') 
                else 0.7
            ) or
            fusion_result.agreement_score < 0.5 or  # Low agreement also flags review
            (converted and converted.needs_review) or  # Script conversion review flag
            temp_segment.needs_review  # Quote match review flag
        )
        
        temp_segment.needs_review = needs_review
        
        # Phase 6: Emit verified update for live mode
        if self.live_callback:
            segment_id = f"seg_{chunk.start_time:.2f}_{chunk.end_time:.2f}"
            try:
                quote_match_data = None
                if temp_segment.quote_match:
                    quote_match_data = {
                        "source": temp_segment.quote_match.source.value if hasattr(temp_segment.quote_match.source, 'value') else str(temp_segment.quote_match.source),
                        "line_id": temp_segment.quote_match.line_id,
                        "ang": temp_segment.quote_match.ang,
                        "raag": temp_segment.quote_match.raag,
                        "author": temp_segment.quote_match.author,
                        "confidence": temp_segment.quote_match.confidence
                    }
                
                self.live_callback("verified", {
                    "session_id": getattr(self, '_current_session_id', 'unknown'),
                    "segment_id": segment_id,
                    "start": chunk.start_time,
                    "end": chunk.end_time,
                    "gurmukhi": temp_segment.text,
                    "roman": temp_segment.roman or "",
                    "confidence": temp_segment.confidence,
                    "quote_match": quote_match_data,
                    "needs_review": temp_segment.needs_review
                })
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to emit verified update: {e}")
        
        return temp_segment
    
    def _get_engines_for_route(self, route: str) -> List[str]:
        """
        Determine which additional ASR engines to run based on route.
        
        Args:
            route: Route string
        
        Returns:
            List of engine names to run ('asr_b', 'asr_c')
        """
        engines = []
        
        if route == ROUTE_PUNJABI_SPEECH:
            engines.append('asr_b')  # Indic ASR for Punjabi
        elif route == ROUTE_ENGLISH_SPEECH:
            engines.append('asr_c')  # English ASR
        elif route == ROUTE_SCRIPTURE_QUOTE_LIKELY:
            engines.append('asr_b')  # Indic ASR for Gurbani
        elif route == ROUTE_MIXED:
            engines.append('asr_b')  # Indic ASR
            engines.append('asr_c')  # English ASR
        
        return engines
    
    def _run_additional_engines_parallel(
        self,
        chunk: AudioChunk,
        route: str,
        language: Optional[str],
        engines: List[str],
        job_id: Optional[str] = None
    ) -> List[ASRResult]:
        """
        Run additional ASR engines in parallel.
        
        Args:
            chunk: AudioChunk to process
            route: Route string
            language: Language code
            engines: List of engine names to run (asr_b, asr_c, indicconformer, wav2vec2, commercial)
        
        Returns:
            List of ASRResult from additional engines
        """
        results = []
        
        def run_engine(engine_name: str) -> Optional[ASRResult]:
            """Run a single ASR engine with timeout."""
            try:
                logger.debug(f"[{job_id}] Starting {engine_name}...")
                
                # Legacy engine names
                if engine_name == 'asr_b':
                    if self.asr_indic is None:
                        self.asr_indic = ASRIndic()
                    result = self.asr_indic.transcribe_chunk(chunk, language, route)
                elif engine_name == 'asr_c':
                    if self.asr_english is None:
                        self.asr_english = ASREnglish()
                    result = self.asr_english.transcribe_chunk(chunk, language, route)
                
                # New provider registry engines
                elif engine_name == 'indicconformer':
                    provider = self.get_provider('indicconformer')
                    result = provider.transcribe_chunk(chunk, language, route)
                elif engine_name == 'wav2vec2':
                    provider = self.get_provider('wav2vec2')
                    result = provider.transcribe_chunk(chunk, language, route)
                elif engine_name == 'commercial':
                    provider = self.get_provider('commercial')
                    result = provider.transcribe_chunk(chunk, language, route)
                elif engine_name == 'whisper':
                    # Use primary whisper service
                    result = self.asr_service.transcribe_chunk(chunk, language, route)
                else:
                    # Try to get from registry
                    provider = self.get_provider(engine_name)
                    result = provider.transcribe_chunk(chunk, language, route)
                
                logger.debug(f"[{job_id}] {engine_name} completed: confidence={result.confidence:.2f}")
                return result
                
            except Exception as e:
                logger.warning(f"[{job_id}] {engine_name} failed: {e}")
                return None
        
        # Determine max workers from options or use number of engines
        max_workers = len(engines)
        if self.current_processing_options:
            parallel_workers = self.current_processing_options.get('parallelWorkers')
            if parallel_workers:
                max_workers = min(parallel_workers, len(engines))
        
        # Run engines in parallel with timeout
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_engine, engine): engine 
                for engine in engines
            }
            
            for future in futures:
                try:
                    result = future.result(timeout=self.asr_timeout)
                    if result:
                        results.append(result)
                except FutureTimeoutError:
                    engine_name = futures[future]
                    logger.warning(f"[{job_id}] {engine_name} timed out after {self.asr_timeout}s")
                except Exception as e:
                    engine_name = futures[future]
                    logger.warning(f"[{job_id}] {engine_name} error: {e}")
        
        return results
    
    def _run_additional_engines_sequential(
        self,
        chunk: AudioChunk,
        route: str,
        language: Optional[str],
        engines: List[str],
        job_id: Optional[str] = None
    ) -> List[ASRResult]:
        """
        Run additional ASR engines sequentially.
        
        Args:
            chunk: AudioChunk to process
            route: Route string
            language: Language code
            engines: List of engine names to run (asr_b, asr_c, indicconformer, wav2vec2, commercial)
        
        Returns:
            List of ASRResult from additional engines
        """
        results = []
        
        for engine in engines:
            try:
                # Legacy engine names
                if engine == 'asr_b':
                    if self.asr_indic is None:
                        self.asr_indic = ASRIndic()
                    result = self.asr_indic.transcribe_chunk(chunk, language, route)
                    results.append(result)
                elif engine == 'asr_c':
                    if self.asr_english is None:
                        self.asr_english = ASREnglish()
                    result = self.asr_english.transcribe_chunk(chunk, language, route)
                    results.append(result)
                
                # New provider registry engines
                elif engine == 'indicconformer':
                    provider = self.get_provider('indicconformer')
                    result = provider.transcribe_chunk(chunk, language, route)
                    results.append(result)
                elif engine == 'wav2vec2':
                    provider = self.get_provider('wav2vec2')
                    result = provider.transcribe_chunk(chunk, language, route)
                    results.append(result)
                elif engine == 'commercial':
                    provider = self.get_provider('commercial')
                    result = provider.transcribe_chunk(chunk, language, route)
                    results.append(result)
                elif engine == 'whisper':
                    result = self.asr_service.transcribe_chunk(chunk, language, route)
                    results.append(result)
                else:
                    # Try to get from registry
                    provider = self.get_provider(engine)
                    result = provider.transcribe_chunk(chunk, language, route)
                    results.append(result)
                    
            except Exception as e:
                logger.warning(f"[{job_id}] {engine} failed: {e}")
        
        return results
    
    def _redecode_chunk(
        self,
        chunk: AudioChunk,
        route: str,
        language: Optional[str],
        job_id: Optional[str] = None
    ) -> Optional[ASRResult]:
        """
        Re-decode chunk with ASR-B (Indic) using larger beam size.
        
        Args:
            chunk: AudioChunk to re-decode
            route: Route string
            language: Language code
            job_id: Optional job identifier for logging
        
        Returns:
            ASRResult from re-decode, or None if failed
        """
        try:
            if self.asr_indic is None:
                self.asr_indic = ASRIndic()
            # Re-decode with ASR-B (Indic) - it's better for complex vocabulary
            logger.debug(f"[{job_id}] Re-decoding with ASR-B...")
            return self.asr_indic.transcribe_chunk(chunk, language, route)
        except Exception as e:
            logger.warning(f"[{job_id}] Re-decode failed: {e}")
            return None
