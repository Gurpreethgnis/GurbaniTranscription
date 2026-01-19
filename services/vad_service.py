"""
Voice Activity Detection (VAD) service for audio chunking.

This service uses WebRTC VAD to detect speech segments and chunk audio
into sentence-like segments with overlap buffers for better accuracy.
"""
import os
from pathlib import Path
from typing import List, Optional
import numpy as np
from core.models import AudioChunk

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("Warning: webrtcvad not available. Install with: pip install webrtcvad")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: pydub not available. Install with: pip install pydub")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class VADService:
    """Service for voice activity detection and audio chunking."""
    
    def __init__(
        self,
        aggressiveness: int = 2,
        frame_duration_ms: int = 30,
        min_chunk_duration: float = 1.0,
        max_chunk_duration: float = 30.0,
        overlap_seconds: float = 0.5
    ):
        """
        Initialize VAD service.
        
        Args:
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            frame_duration_ms: Frame duration in milliseconds (10, 20, or 30)
            min_chunk_duration: Minimum chunk duration in seconds
            max_chunk_duration: Maximum chunk duration in seconds
            overlap_seconds: Overlap between chunks in seconds
        """
        if not WEBRTCVAD_AVAILABLE:
            raise ImportError(
                "webrtcvad is required. Install with: pip install webrtcvad"
            )
        if not PYDUB_AVAILABLE:
            raise ImportError(
                "pydub is required for audio chunking. Install with: pip install pydub"
            )
        
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_duration_ms = frame_duration_ms
        self.min_chunk_duration = min_chunk_duration
        self.max_chunk_duration = max_chunk_duration
        self.overlap_seconds = overlap_seconds
        
        # Validate frame duration
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"frame_duration_ms must be 10, 20, or 30, got {frame_duration_ms}")
    
    def chunk_audio(
        self,
        audio_path: Path,
        min_chunk_duration: Optional[float] = None,
        max_chunk_duration: Optional[float] = None,
        overlap_seconds: Optional[float] = None
    ) -> List[AudioChunk]:
        """
        Chunk audio into speech segments with overlap.
        
        Args:
            audio_path: Path to audio file
            min_chunk_duration: Override minimum chunk duration
            max_chunk_duration: Override maximum chunk duration
            overlap_seconds: Override overlap duration
        
        Returns:
            List of AudioChunk objects with timing information
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        min_dur = min_chunk_duration or self.min_chunk_duration
        max_dur = max_chunk_duration or self.max_chunk_duration
        overlap = overlap_seconds or self.overlap_seconds
        
        # Load audio file
        try:
            audio = AudioSegment.from_file(str(audio_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load audio file: {e}")
        
        # Convert to required format for VAD (16kHz, 16-bit, mono)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        
        # Get audio data as bytes
        raw_audio = audio.raw_data
        sample_rate = audio.frame_rate
        frame_size = int(sample_rate * self.frame_duration_ms / 1000)
        
        # Detect speech frames
        speech_frames = []
        num_frames = len(raw_audio) // (frame_size * 2)  # 2 bytes per sample
        
        for i in range(num_frames):
            frame_start = i * frame_size * 2
            frame_end = frame_start + frame_size * 2
            frame = raw_audio[frame_start:frame_end]
            
            if len(frame) == frame_size * 2:
                is_speech = self.vad.is_speech(frame, sample_rate)
                speech_frames.append((i * self.frame_duration_ms / 1000.0, is_speech))
        
        # Group speech frames into chunks
        chunks = []
        current_chunk_start = None
        current_chunk_end = None
        
        for timestamp, is_speech in speech_frames:
            if is_speech:
                if current_chunk_start is None:
                    current_chunk_start = timestamp
                current_chunk_end = timestamp + (self.frame_duration_ms / 1000.0)
            else:
                # End of speech segment
                if current_chunk_start is not None and current_chunk_end is not None:
                    duration = current_chunk_end - current_chunk_start
                    if duration >= min_dur:
                        # Split long chunks
                        if duration > max_dur:
                            # Split into multiple chunks
                            num_splits = int(np.ceil(duration / max_dur))
                            split_duration = duration / num_splits
                            for j in range(num_splits):
                                chunk_start = current_chunk_start + j * split_duration
                                chunk_end = min(chunk_start + split_duration, current_chunk_end)
                                chunks.append(AudioChunk(
                                    start_time=chunk_start,
                                    end_time=chunk_end,
                                    audio_path=audio_path,
                                    duration=chunk_end - chunk_start
                                ))
                        else:
                            chunks.append(AudioChunk(
                                start_time=current_chunk_start,
                                end_time=current_chunk_end,
                                audio_path=audio_path,
                                duration=duration
                            ))
                    current_chunk_start = None
                    current_chunk_end = None
        
        # Handle case where audio ends with speech
        if current_chunk_start is not None and current_chunk_end is not None:
            duration = current_chunk_end - current_chunk_start
            if duration >= min_dur:
                if duration > max_dur:
                    num_splits = int(np.ceil(duration / max_dur))
                    split_duration = duration / num_splits
                    for j in range(num_splits):
                        chunk_start = current_chunk_start + j * split_duration
                        chunk_end = min(chunk_start + split_duration, current_chunk_end)
                        chunks.append(AudioChunk(
                            start_time=chunk_start,
                            end_time=chunk_end,
                            audio_path=audio_path,
                            duration=chunk_end - chunk_start
                        ))
                else:
                    chunks.append(AudioChunk(
                        start_time=current_chunk_start,
                        end_time=current_chunk_end,
                        audio_path=audio_path,
                        duration=duration
                    ))
        
        # Apply overlap between chunks
        if overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                # Extend start time with overlap (except first chunk)
                start_time = chunk.start_time
                if i > 0:
                    start_time = max(0, start_time - overlap)
                
                # Extend end time with overlap (except last chunk)
                end_time = chunk.end_time
                if i < len(chunks) - 1:
                    # Don't extend beyond next chunk's start
                    next_start = chunks[i + 1].start_time
                    end_time = min(chunk.end_time + overlap, next_start)
                
                overlapped_chunks.append(AudioChunk(
                    start_time=start_time,
                    end_time=end_time,
                    audio_path=chunk.audio_path,
                    duration=end_time - start_time
                ))
            chunks = overlapped_chunks
        
        # Filter out very short chunks
        chunks = [chunk for chunk in chunks if chunk.duration >= min_dur]
        
        return chunks
    
    def extract_chunk_audio(
        self,
        chunk: AudioChunk,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Extract audio chunk to a separate file.
        
        Args:
            chunk: AudioChunk to extract
            output_path: Optional output path (auto-generated if not provided)
        
        Returns:
            Path to extracted audio file
        """
        if not PYDUB_AVAILABLE:
            raise ImportError("pydub is required for audio extraction")
        
        # Load original audio
        audio = AudioSegment.from_file(str(chunk.audio_path))
        
        # Extract chunk (convert to milliseconds)
        start_ms = int(chunk.start_time * 1000)
        end_ms = int(chunk.end_time * 1000)
        chunk_audio = audio[start_ms:end_ms]
        
        # Generate output path if not provided
        if output_path is None:
            base_name = chunk.audio_path.stem
            output_path = chunk.audio_path.parent / f"{base_name}_chunk_{int(chunk.start_time)}.wav"
        
        # Export chunk
        chunk_audio.export(str(output_path), format="wav")
        
        return output_path
