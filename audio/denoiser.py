"""
Audio Denoising Service.

Provides configurable audio denoising for both batch and live transcription modes.
Supports multiple backends: noisereduce (default), facebook-denoiser, DeepFilterNet.

Phase 7: Audio Denoising Module
"""
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from core.errors import AudioDenoiseError, AudioDecodeError

logger = logging.getLogger(__name__)

# Try to import audio processing libraries
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available. Install with: pip install soundfile")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available. Install with: pip install pydub")


class AudioDenoiser:
    """
    Audio denoising service with configurable backend and strength.
    
    Supports:
    - Batch mode: denoise_file() for full audio files
    - Live mode: denoise_chunk() for streaming audio chunks
    - Multiple backends: noisereduce (default), facebook, deepfilter
    - Configurable strength: light, medium, aggressive
    """
    
    def __init__(
        self,
        backend: str = "noisereduce",
        strength: str = "medium",
        sample_rate: int = 16000
    ):
        """
        Initialize audio denoiser.
        
        Args:
            backend: Denoising backend ("noisereduce", "facebook", "deepfilter")
            strength: Denoising strength ("light", "medium", "aggressive")
            sample_rate: Target sample rate (default: 16000 Hz for ASR)
        
        Raises:
            AudioDenoiseError: If backend is not available
        """
        self.backend = backend.lower()
        self.strength = strength.lower()
        self.sample_rate = sample_rate
        
        # Validate strength
        valid_strengths = ["light", "medium", "aggressive"]
        if self.strength not in valid_strengths:
            logger.warning(f"Invalid strength '{strength}', using 'medium'")
            self.strength = "medium"
        
        # Initialize backend
        self._backend_impl = None
        self._init_backend()
        
        logger.info(
            f"AudioDenoiser initialized: backend={self.backend}, "
            f"strength={self.strength}, sample_rate={self.sample_rate}"
        )
    
    def _init_backend(self) -> None:
        """Initialize the selected denoising backend."""
        if self.backend == "noisereduce":
            self._init_noisereduce()
        elif self.backend == "facebook":
            self._init_facebook_denoiser()
        elif self.backend == "deepfilter":
            self._init_deepfilter()
        else:
            raise AudioDenoiseError(
                self.backend,
                f"Unknown backend. Supported: noisereduce, facebook, deepfilter"
            )
    
    def _init_noisereduce(self) -> None:
        """Initialize noisereduce backend."""
        try:
            import noisereduce as nr
            self._backend_impl = nr
            logger.debug("noisereduce backend initialized")
        except ImportError:
            raise AudioDenoiseError(
                "noisereduce",
                "Package not installed. Install with: pip install noisereduce"
            )
    
    def _init_facebook_denoiser(self) -> None:
        """Initialize Facebook denoiser backend."""
        try:
            from denoiser import pretrained
            from denoiser.dsp import convert_audio
            self._facebook_pretrained = pretrained
            self._facebook_convert = convert_audio
            logger.debug("Facebook denoiser backend initialized")
        except ImportError:
            raise AudioDenoiseError(
                "facebook",
                "Package not installed. Install with: pip install denoiser"
            )
    
    def _init_deepfilter(self) -> None:
        """Initialize DeepFilterNet backend."""
        try:
            import deepfilternet as df
            self._backend_impl = df
            logger.debug("DeepFilterNet backend initialized")
        except ImportError:
            raise AudioDenoiseError(
                "deepfilter",
                "Package not installed. Install with: pip install deepfilternet"
            )
    
    def denoise_file(
        self,
        audio_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Denoise an audio file (batch mode).
        
        Args:
            audio_path: Path to input audio file
            output_path: Optional output path (auto-generated if None)
        
        Returns:
            Path to denoised audio file
        
        Raises:
            AudioDecodeError: If audio file cannot be read
            AudioDenoiseError: If denoising fails
        """
        if not audio_path.exists():
            raise AudioDecodeError(str(audio_path), "File not found")
        
        logger.info(f"Denoising audio file: {audio_path.name} (backend: {self.backend})")
        
        try:
            # Load audio
            if not SOUNDFILE_AVAILABLE:
                raise AudioDecodeError(
                    str(audio_path),
                    "soundfile not available. Install with: pip install soundfile"
                )
            
            audio_data, sr = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Resample if needed
            if sr != self.sample_rate:
                audio_data = self._resample_audio(audio_data, sr, self.sample_rate)
                sr = self.sample_rate
            
            # Denoise
            denoised_audio = self._denoise_audio(audio_data, sr)
            
            # Generate output path if not provided
            if output_path is None:
                output_path = audio_path.parent / f"{audio_path.stem}_denoised.wav"
            
            # Save denoised audio
            sf.write(str(output_path), denoised_audio, self.sample_rate)
            
            logger.info(f"Denoised audio saved to: {output_path.name}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to denoise audio file: {e}", exc_info=True)
            raise AudioDenoiseError(self.backend, str(e))
    
    def denoise_chunk(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000
    ) -> bytes:
        """
        Denoise an audio chunk (live mode).
        
        Args:
            audio_bytes: Raw audio data (WAV format expected)
            sample_rate: Sample rate of input audio
        
        Returns:
            Denoised audio bytes (WAV format)
        
        Raises:
            AudioDenoiseError: If denoising fails
        """
        logger.debug(f"Denoising audio chunk: {len(audio_bytes)} bytes (backend: {self.backend})")
        
        try:
            # Convert bytes to numpy array
            # Assume 16-bit PCM WAV format
            # Ensure even number of bytes for int16 alignment
            if len(audio_bytes) % 2 != 0:
                audio_bytes = audio_bytes[:-1]
            
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0  # Normalize to [-1, 1]
            
            # Resample if needed
            if sample_rate != self.sample_rate:
                audio_array = self._resample_audio(audio_array, sample_rate, self.sample_rate)
                sample_rate = self.sample_rate
            
            # Denoise
            denoised_audio = self._denoise_audio(audio_array, sample_rate)
            
            # Convert back to bytes (16-bit PCM)
            denoised_audio = np.clip(denoised_audio, -1.0, 1.0)
            denoised_bytes = (denoised_audio * 32768.0).astype(np.int16).tobytes()
            
            logger.debug(f"Denoised chunk: {len(denoised_bytes)} bytes")
            return denoised_bytes
            
        except Exception as e:
            logger.error(f"Failed to denoise audio chunk: {e}", exc_info=True)
            raise AudioDenoiseError(self.backend, str(e))
    
    def _denoise_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply denoising to audio data using configured backend.
        
        Args:
            audio_data: Audio data as numpy array (normalized to [-1, 1])
            sample_rate: Sample rate of audio
        
        Returns:
            Denoised audio data
        """
        if self.backend == "noisereduce":
            return self._denoise_noisereduce(audio_data, sample_rate)
        elif self.backend == "facebook":
            return self._denoise_facebook(audio_data, sample_rate)
        elif self.backend == "deepfilter":
            return self._denoise_deepfilter(audio_data, sample_rate)
        else:
            raise AudioDenoiseError(self.backend, "Backend not initialized")
    
    def _denoise_noisereduce(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Denoise using noisereduce backend."""
        # Map strength to noisereduce parameters
        strength_map = {
            "light": {"stationary": True, "prop_decrease": 0.3},
            "medium": {"stationary": True, "prop_decrease": 0.6},
            "aggressive": {"stationary": False, "prop_decrease": 0.9}
        }
        
        params = strength_map.get(self.strength, strength_map["medium"])
        
        denoised = self._backend_impl.reduce_noise(
            y=audio_data,
            sr=sample_rate,
            **params
        )
        
        return denoised
    
    def _denoise_facebook(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Denoise using Facebook denoiser backend."""
        # Load model (cached after first load)
        if not hasattr(self, '_facebook_model'):
            logger.debug("Loading Facebook denoiser model...")
            self._facebook_model = self._facebook_pretrained.dns64()
            self._facebook_model.eval()
        
        # Convert audio format
        import torch
        audio_tensor = torch.from_numpy(audio_data).float().unsqueeze(0)
        audio_tensor = self._facebook_convert(audio_tensor, sample_rate, self._facebook_model.sample_rate)
        
        # Denoise
        with torch.no_grad():
            denoised_tensor = self._facebook_model(audio_tensor[None])[0]
            denoised_tensor = self._facebook_convert(denoised_tensor, self._facebook_model.sample_rate, sample_rate)
        
        denoised = denoised_tensor.squeeze(0).cpu().numpy()
        return denoised
    
    def _denoise_deepfilter(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Denoise using DeepFilterNet backend."""
        # DeepFilterNet expects specific format
        # This is a simplified implementation
        logger.warning("DeepFilterNet backend requires additional setup. Using noisereduce fallback.")
        # For now, fallback to noisereduce if DeepFilterNet not fully configured
        if self.backend == "deepfilter":
            # Try to use noisereduce as fallback
            try:
                import noisereduce as nr
                return nr.reduce_noise(y=audio_data, sr=sample_rate, stationary=True, prop_decrease=0.6)
            except ImportError:
                raise AudioDenoiseError("deepfilter", "DeepFilterNet not fully configured, and noisereduce fallback unavailable")
        
        return audio_data
    
    def _resample_audio(
        self,
        audio_data: np.ndarray,
        original_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            audio_data: Audio data
            original_sr: Original sample rate
            target_sr: Target sample rate
        
        Returns:
            Resampled audio data
        """
        if original_sr == target_sr:
            return audio_data
        
        try:
            from scipy import signal
            num_samples = int(len(audio_data) * target_sr / original_sr)
            resampled = signal.resample(audio_data, num_samples)
            return resampled
        except ImportError:
            logger.warning("scipy not available for resampling. Using simple decimation/interpolation.")
            # Simple decimation/interpolation (less accurate)
            ratio = target_sr / original_sr
            if ratio < 1:
                # Decimate
                step = int(1 / ratio)
                return audio_data[::step]
            else:
                # Interpolate using numpy (linear interpolation)
                original_indices = np.arange(len(audio_data))
                target_length = int(len(audio_data) * ratio)
                target_indices = np.linspace(0, len(audio_data) - 1, target_length)
                resampled = np.interp(target_indices, original_indices, audio_data)
                return resampled
    
    def estimate_noise_level(self, audio_path: Path) -> float:
        """
        Estimate noise level in audio file (0.0-1.0).
        
        Simple heuristic: ratio of low-energy frames to total frames.
        Higher value = more noise.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Noise level estimate (0.0 = clean, 1.0 = very noisy)
        
        Raises:
            AudioDecodeError: If audio file cannot be read
        """
        if not audio_path.exists():
            raise AudioDecodeError(str(audio_path), "File not found")
        
        try:
            if not SOUNDFILE_AVAILABLE:
                raise AudioDecodeError(
                    str(audio_path),
                    "soundfile not available. Install with: pip install soundfile"
                )
            
            audio_data, sr = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Calculate frame energy (simple RMS)
            frame_size = int(sr * 0.025)  # 25ms frames
            num_frames = len(audio_data) // frame_size
            
            if num_frames == 0:
                return 0.5  # Unknown
            
            energies = []
            for i in range(num_frames):
                frame = audio_data[i * frame_size:(i + 1) * frame_size]
                energy = np.sqrt(np.mean(frame ** 2))
                energies.append(energy)
            
            # Estimate noise: ratio of low-energy frames
            threshold = np.percentile(energies, 25)  # Bottom 25% likely noise
            low_energy_frames = sum(1 for e in energies if e < threshold)
            noise_ratio = low_energy_frames / num_frames
            
            logger.debug(f"Estimated noise level for {audio_path.name}: {noise_ratio:.2f}")
            return float(noise_ratio)
            
        except Exception as e:
            logger.error(f"Failed to estimate noise level: {e}", exc_info=True)
            return 0.5  # Default to medium noise if estimation fails
