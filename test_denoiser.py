"""
Tests for audio denoising module.

Phase 7: Audio Denoising Module Tests
"""
import pytest
import tempfile
import numpy as np
from pathlib import Path
import soundfile as sf
from audio.denoiser import AudioDenoiser
from errors import AudioDenoiseError, AudioDecodeError


def create_test_audio_file(
    output_path: Path,
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    add_noise: bool = False
) -> None:
    """Create a test audio file."""
    num_samples = int(duration_seconds * sample_rate)
    
    # Generate a simple sine wave (440 Hz)
    t = np.linspace(0, duration_seconds, num_samples)
    signal = np.sin(2 * np.pi * 440 * t)
    
    # Add noise if requested
    if add_noise:
        noise = np.random.normal(0, 0.1, num_samples)
        signal = signal + noise
    
    # Normalize to [-1, 1]
    signal = signal / np.max(np.abs(signal))
    
    # Save as WAV
    sf.write(str(output_path), signal, sample_rate)


class TestAudioDenoiser:
    """Test suite for AudioDenoiser class."""
    
    def test_init_default(self):
        """Test default initialization."""
        denoiser = AudioDenoiser()
        assert denoiser.backend == "noisereduce"
        assert denoiser.strength == "medium"
        assert denoiser.sample_rate == 16000
    
    def test_init_custom(self):
        """Test custom initialization."""
        denoiser = AudioDenoiser(
            backend="noisereduce",
            strength="light",
            sample_rate=22050
        )
        assert denoiser.backend == "noisereduce"
        assert denoiser.strength == "light"
        assert denoiser.sample_rate == 22050
    
    def test_init_invalid_strength(self):
        """Test initialization with invalid strength."""
        denoiser = AudioDenoiser(strength="invalid")
        # Should default to "medium"
        assert denoiser.strength == "medium"
    
    def test_init_invalid_backend(self):
        """Test initialization with invalid backend."""
        with pytest.raises(AudioDenoiseError):
            AudioDenoiser(backend="nonexistent")
    
    def test_denoise_file_clean_audio(self):
        """Test denoising a clean audio file."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            input_path = Path(tmp.name)
        
        try:
            # Create clean test audio
            create_test_audio_file(input_path, add_noise=False)
            
            denoiser = AudioDenoiser(backend="noisereduce", strength="light")
            output_path = denoiser.denoise_file(input_path)
            
            # Check output file exists
            assert output_path.exists()
            
            # Check output is readable
            data, sr = sf.read(str(output_path))
            assert len(data) > 0
            assert sr == 16000
            
        finally:
            # Cleanup
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_denoise_file_noisy_audio(self):
        """Test denoising a noisy audio file."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            input_path = Path(tmp.name)
        
        try:
            # Create noisy test audio
            create_test_audio_file(input_path, add_noise=True)
            
            denoiser = AudioDenoiser(backend="noisereduce", strength="medium")
            output_path = denoiser.denoise_file(input_path)
            
            # Check output file exists
            assert output_path.exists()
            
            # Check output is readable
            data, sr = sf.read(str(output_path))
            assert len(data) > 0
            
        finally:
            # Cleanup
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_denoise_file_custom_output_path(self):
        """Test denoising with custom output path."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            input_path = Path(tmp.name)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            create_test_audio_file(input_path)
            
            denoiser = AudioDenoiser()
            result_path = denoiser.denoise_file(input_path, output_path)
            
            assert result_path == output_path
            assert output_path.exists()
            
        finally:
            # Cleanup
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_denoise_file_nonexistent(self):
        """Test denoising a nonexistent file."""
        denoiser = AudioDenoiser()
        nonexistent = Path("/nonexistent/file.wav")
        
        with pytest.raises(AudioDecodeError):
            denoiser.denoise_file(nonexistent)
    
    def test_denoise_chunk(self):
        """Test denoising an audio chunk (live mode)."""
        # Create test audio data (16-bit PCM)
        sample_rate = 16000
        duration = 0.5  # 500ms
        num_samples = int(sample_rate * duration)
        
        # Generate sine wave
        t = np.linspace(0, duration, num_samples)
        signal = np.sin(2 * np.pi * 440 * t)
        
        # Add noise
        noise = np.random.normal(0, 0.1, num_samples)
        signal = signal + noise
        
        # Normalize and convert to 16-bit PCM bytes
        signal = np.clip(signal, -1.0, 1.0)
        audio_bytes = (signal * 32768.0).astype(np.int16).tobytes()
        
        denoiser = AudioDenoiser(backend="noisereduce", strength="light")
        denoised_bytes = denoiser.denoise_chunk(audio_bytes, sample_rate)
        
        # Check output is bytes
        assert isinstance(denoised_bytes, bytes)
        assert len(denoised_bytes) > 0
    
    def test_estimate_noise_level(self):
        """Test noise level estimation."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio_path = Path(tmp.name)
        
        try:
            # Create noisy audio
            create_test_audio_file(audio_path, add_noise=True)
            
            denoiser = AudioDenoiser()
            noise_level = denoiser.estimate_noise_level(audio_path)
            
            # Noise level should be between 0 and 1
            assert 0.0 <= noise_level <= 1.0
            
        finally:
            if audio_path.exists():
                audio_path.unlink()
    
    def test_estimate_noise_level_nonexistent(self):
        """Test noise estimation on nonexistent file."""
        denoiser = AudioDenoiser()
        nonexistent = Path("/nonexistent/file.wav")
        
        with pytest.raises(AudioDecodeError):
            denoiser.estimate_noise_level(nonexistent)
    
    def test_different_strengths(self):
        """Test different denoising strengths."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            input_path = Path(tmp.name)
        
        try:
            create_test_audio_file(input_path, add_noise=True)
            
            for strength in ["light", "medium", "aggressive"]:
                denoiser = AudioDenoiser(strength=strength)
                output_path = denoiser.denoise_file(input_path)
                
                assert output_path.exists()
                
                # Cleanup output
                if output_path.exists():
                    output_path.unlink()
                
        finally:
            if input_path.exists():
                input_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
