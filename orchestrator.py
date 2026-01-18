"""
Orchestrator for the transcription pipeline.

Coordinates VAD chunking, language identification, and ASR processing
to produce structured transcription results.
"""
from pathlib import Path
from typing import Optional, Dict, Any
from models import (
    AudioChunk, ASRResult, ProcessedSegment, TranscriptionResult, Segment
)
from vad_service import VADService
from langid_service import LangIDService, ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH
from asr.asr_whisper import ASRWhisper
import config


class Orchestrator:
    """
    Main orchestrator for the transcription pipeline.
    
    Coordinates:
    1. VAD chunking
    2. Language/domain identification
    3. ASR processing with forced language
    4. Result aggregation
    """
    
    def __init__(
        self,
        vad_service: Optional[VADService] = None,
        langid_service: Optional[LangIDService] = None,
        asr_service: Optional[ASRWhisper] = None
    ):
        """
        Initialize orchestrator with services.
        
        Args:
            vad_service: VAD service instance (created if None)
            langid_service: LangID service instance (created if None)
            asr_service: ASR-A service instance (created if None)
        """
        self.vad_service = vad_service or VADService(
            aggressiveness=config.VAD_AGGRESSIVENESS if hasattr(config, 'VAD_AGGRESSIVENESS') else 2,
            min_chunk_duration=config.VAD_MIN_CHUNK_DURATION if hasattr(config, 'VAD_MIN_CHUNK_DURATION') else 1.0,
            max_chunk_duration=config.VAD_MAX_CHUNK_DURATION if hasattr(config, 'VAD_MAX_CHUNK_DURATION') else 30.0,
            overlap_seconds=config.VAD_OVERLAP_SECONDS if hasattr(config, 'VAD_OVERLAP_SECONDS') else 0.5
        )
        
        # Initialize ASR service first (needed for LangID)
        self.asr_service = asr_service or ASRWhisper()
        
        # Create LangID service with ASR-A for quick detection
        if langid_service is None:
            self.langid_service = LangIDService(
                quick_asr_service=self.asr_service,
                punjabi_threshold=config.LANGID_PUNJABI_THRESHOLD if hasattr(config, 'LANGID_PUNJABI_THRESHOLD') else 0.6,
                english_threshold=config.LANGID_ENGLISH_THRESHOLD if hasattr(config, 'LANGID_ENGLISH_THRESHOLD') else 0.6
            )
        else:
            self.langid_service = langid_service
    
    def transcribe_file(
        self,
        audio_path: Path,
        mode: str = "batch"
    ) -> TranscriptionResult:
        """
        Transcribe an audio file using the orchestrated pipeline.
        
        Args:
            audio_path: Path to audio file
            mode: Processing mode ("batch" or "live")
        
        Returns:
            TranscriptionResult with structured segments and metadata
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        filename = audio_path.name
        
        # Step 1: VAD chunking
        print(f"Step 1: Chunking audio with VAD...")
        chunks = self.vad_service.chunk_audio(audio_path)
        print(f"Created {len(chunks)} audio chunks")
        
        # Step 2: Process each chunk
        processed_segments = []
        total_gurmukhi_text = ""
        total_roman_text = ""  # Will be populated in later phases
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} (time: {chunk.start_time:.2f}-{chunk.end_time:.2f}s)")
            
            # Step 2a: Language/domain identification
            route = self.langid_service.identify_segment(chunk)
            print(f"  Route: {route}")
            
            # Step 2b: Get language code for ASR
            language = self.langid_service.get_language_code(route)
            
            # Step 2c: Transcribe with ASR-A
            try:
                asr_result = self.asr_service.transcribe_chunk(
                    chunk,
                    language=language,
                    route=route
                )
                
                # Step 2d: Create processed segment
                # Determine segment type
                segment_type = "scripture_quote" if route == "scripture_quote_likely" else "speech"
                
                # Get text (for now, just use ASR text - later phases will handle Gurmukhi conversion)
                segment_text = asr_result.text
                
                # Check if needs review (low confidence)
                needs_review = asr_result.confidence < (
                    config.SEGMENT_CONFIDENCE_THRESHOLD if hasattr(config, 'SEGMENT_CONFIDENCE_THRESHOLD') else 0.7
                )
                
                processed_segment = ProcessedSegment(
                    start=chunk.start_time,
                    end=chunk.end_time,
                    route=route,
                    type=segment_type,
                    text=segment_text,
                    confidence=asr_result.confidence,
                    language=asr_result.language,
                    hypotheses=[{
                        "engine": asr_result.engine,
                        "text": asr_result.text,
                        "confidence": asr_result.confidence
                    }],
                    needs_review=needs_review
                )
                
                processed_segments.append(processed_segment)
                total_gurmukhi_text += segment_text + " "
                
            except Exception as e:
                print(f"  Error processing chunk {i+1}: {e}")
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
        metrics = {
            "mode": mode,
            "total_chunks": len(chunks),
            "total_segments": len(processed_segments),
            "segments_needing_review": sum(1 for seg in processed_segments if seg.needs_review),
            "average_confidence": (
                sum(seg.confidence for seg in processed_segments) / len(processed_segments)
                if processed_segments else 0.0
            ),
            "routes": {
                route: sum(1 for seg in processed_segments if seg.route == route)
                for route in [ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH, "scripture_quote_likely", "mixed"]
            }
        }
        
        return TranscriptionResult(
            filename=filename,
            segments=processed_segments,
            transcription=transcription,
            metrics=metrics
        )
