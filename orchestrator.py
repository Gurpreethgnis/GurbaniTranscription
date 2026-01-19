"""
Orchestrator for the transcription pipeline.

Coordinates VAD chunking, language identification, and ASR processing
to produce structured transcription results.

Phase 2: Supports multi-ASR ensemble with fusion.
"""
import logging
import uuid
import tempfile
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
import config
from models import (
    AudioChunk, ASRResult, ProcessedSegment, TranscriptionResult, Segment
)
from vad_service import VADService
from langid_service import LangIDService, ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH, ROUTE_SCRIPTURE_QUOTE_LIKELY, ROUTE_MIXED
from asr.asr_whisper import ASRWhisper
from asr.asr_indic import ASRIndic
from asr.asr_english_fallback import ASREnglish
from asr.asr_fusion import ASRFusion
from script_converter import ScriptConverter
from quotes.quote_candidates import QuoteCandidateDetector
from quotes.assisted_matcher import AssistedMatcher
from quotes.canonical_replacer import CanonicalReplacer
from errors import ASREngineError, VADError, FusionError

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
        live_callback: Optional[Callable] = None
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
        """
        self.vad_service = vad_service or VADService(
            aggressiveness=config.VAD_AGGRESSIVENESS if hasattr(config, 'VAD_AGGRESSIVENESS') else 2,
            min_chunk_duration=config.VAD_MIN_CHUNK_DURATION if hasattr(config, 'VAD_MIN_CHUNK_DURATION') else 1.0,
            max_chunk_duration=config.VAD_MAX_CHUNK_DURATION if hasattr(config, 'VAD_MAX_CHUNK_DURATION') else 30.0,
            overlap_seconds=config.VAD_OVERLAP_SECONDS if hasattr(config, 'VAD_OVERLAP_SECONDS') else 0.5
        )
        
        # Initialize ASR-A service first (needed for LangID)
        self.asr_service = asr_service or ASRWhisper()
        
        # Initialize ASR-B (Indic) and ASR-C (English) for Phase 2
        self.asr_indic = asr_indic
        self.asr_english = asr_english
        
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
        
        # Phase 6: Live mode callback
        self.live_callback = live_callback
    
    def transcribe_file(
        self,
        audio_path: Path,
        mode: str = "batch",
        job_id: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file using the orchestrated pipeline.
        
        Args:
            audio_path: Path to audio file
            mode: Processing mode ("batch" or "live")
            job_id: Optional job identifier for logging (auto-generated if None)
        
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
        
        # Step 1: VAD chunking
        logger.info(f"[{job_id}] Step 1: Chunking audio with VAD...")
        try:
            chunks = self.vad_service.chunk_audio(audio_path)
            logger.info(f"[{job_id}] Created {len(chunks)} audio chunks")
        except Exception as e:
            logger.error(f"[{job_id}] VAD chunking failed: {e}")
            raise VADError(f"Failed to chunk audio: {e}")
        
        # Step 2: Process each chunk
        processed_segments = []
        total_gurmukhi_text = ""
        total_roman_text = ""  # Will be populated in later phases
        
        for i, chunk in enumerate(chunks):
            logger.info(f"[{job_id}] Processing chunk {i+1}/{len(chunks)} (time: {chunk.start_time:.2f}-{chunk.end_time:.2f}s)")
            
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
        
        # Step 3: Aggregate results
        transcription = {
            "gurmukhi": total_gurmukhi_text.strip(),
            "roman": total_roman_text.strip()  # Will be populated in later phases
        }
        
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
        
        return TranscriptionResult(
            filename=filename,
            segments=processed_segments,
            transcription=transcription,
            metrics=metrics
        )
    
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
        
        # Create temporary file from audio bytes
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
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
        # Step 1: Run ASR-A immediately (primary engine)
        logger.debug(f"[{job_id}] Running ASR-A (Whisper) for chunk at {chunk.start_time:.2f}s")
        try:
            asr_a_result = self.asr_service.transcribe_chunk(
                chunk,
                language=language,
                route=route
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
        
        # Step 6: Apply re-decode policy if needed
        if self.fusion_service.should_redecode(fusion_result):
            logger.warning(f"[{job_id}] Low confidence ({fusion_result.fused_confidence:.2f}), triggering re-decode...")
            redecode_result = self._redecode_chunk(chunk, route, language, job_id)
            if redecode_result:
                fusion_result = self.fusion_service.apply_redecode(
                    fusion_result, redecode_result
                )
                logger.info(f"[{job_id}] Re-decode completed, new confidence: {fusion_result.fused_confidence:.2f}")
        
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
        
        # Step 8: Phase 4 - Quote Detection + Matching
        # Create temporary segment for quote detection
        temp_segment = ProcessedSegment(
            start=chunk.start_time,
            end=chunk.end_time,
            route=route,
            type="speech",  # Will be updated if quote found
            text=converted.gurmukhi if converted else fusion_result.fused_text,
            confidence=fusion_result.fused_confidence,
            language=asr_a_result.language,
            hypotheses=fusion_result.hypotheses,
            needs_review=False,
            roman=converted.roman if converted else None,
            original_script=converted.original_script if converted else None,
            script_confidence=converted.confidence if converted else None
        )
        
        # Detect quote candidates and match if route suggests scripture
        if route == ROUTE_SCRIPTURE_QUOTE_LIKELY:
            logger.debug(f"[{job_id}] Detecting quote candidates...")
            try:
                candidates = self.quote_detector.detect_candidates(
                    temp_segment,
                    hypotheses=fusion_result.hypotheses
                )
                
                if candidates:
                    logger.debug(f"[{job_id}] Found {len(candidates)} quote candidate(s)")
                    
                    # Try to find a match
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
            engines: List of engine names to run
        
        Returns:
            List of ASRResult from additional engines
        """
        results = []
        
        def run_engine(engine_name: str) -> Optional[ASRResult]:
            """Run a single ASR engine with timeout."""
            try:
                logger.debug(f"[{job_id}] Starting {engine_name}...")
                if engine_name == 'asr_b':
                    if self.asr_indic is None:
                        self.asr_indic = ASRIndic()
                    result = self.asr_indic.transcribe_chunk(chunk, language, route)
                    logger.debug(f"[{job_id}] {engine_name} completed: confidence={result.confidence:.2f}")
                    return result
                elif engine_name == 'asr_c':
                    if self.asr_english is None:
                        self.asr_english = ASREnglish()
                    result = self.asr_english.transcribe_chunk(chunk, language, route)
                    logger.debug(f"[{job_id}] {engine_name} completed: confidence={result.confidence:.2f}")
                    return result
            except Exception as e:
                logger.warning(f"[{job_id}] {engine_name} failed: {e}")
                return None
        
        # Run engines in parallel with timeout
        with ThreadPoolExecutor(max_workers=len(engines)) as executor:
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
            engines: List of engine names to run
        
        Returns:
            List of ASRResult from additional engines
        """
        results = []
        
        for engine in engines:
            try:
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
