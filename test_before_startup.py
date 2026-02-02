"""
Pre-startup Transcription Test

Run this before app.py to verify transcription pipeline is working correctly.
Uses a quick synthetic test to validate the pipeline.

Usage:
    python test_before_startup.py && python app.py
"""
import sys
import tempfile
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_test_audio(duration_seconds: float = 2.0, sample_rate: int = 16000) -> Path:
    """Create a simple test audio file with a tone."""
    import soundfile as sf
    
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    # Create a simple 440Hz tone (A note)
    audio = 0.3 * np.sin(2 * np.pi * 440 * t)
    
    # Add a slight fade in/out
    fade_samples = int(sample_rate * 0.1)
    audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = Path(f.name)
    
    sf.write(str(output_path), audio, sample_rate)
    return output_path


def test_pipeline_components():
    """Test each pipeline component individually."""
    print("=" * 60)
    print("PRE-STARTUP TRANSCRIPTION PIPELINE TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: Core imports
    print("\n[1/5] Testing core imports...")
    try:
        from core.orchestrator import Orchestrator
        from core.models import TranscriptionResult, ProcessedSegment
        from services.vad_service import VADService
        print("  [OK] Core imports OK")
        results.append(("Core imports", True, None))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Core imports", False, str(e)))
    
    # Test 2: ASR imports
    print("\n[2/5] Testing ASR providers...")
    try:
        from asr.asr_whisper import ASRWhisper
        asr = ASRWhisper()
        print("  [OK] Whisper ASR initialized")
        results.append(("ASR providers", True, None))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("ASR providers", False, str(e)))
    
    # Test 3: VAD service
    print("\n[3/5] Testing VAD service...")
    try:
        from services.vad_service import VADService
        vad = VADService()
        print("  [OK] VAD service initialized")
        results.append(("VAD service", True, None))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("VAD service", False, str(e)))
    
    # Test 4: Create and process test audio
    print("\n[4/5] Testing audio processing...")
    test_audio = None
    try:
        import soundfile as sf
        test_audio = create_test_audio(duration_seconds=1.0)
        
        # Get audio info
        info = sf.info(str(test_audio))
        print(f"  [OK] Test audio created: {info.duration:.1f}s, {info.samplerate}Hz")
        results.append(("Audio processing", True, None))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Audio processing", False, str(e)))
    
    # Test 5: Check for ffmpeg
    print("\n[5/6] Testing ffmpeg installation...")
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("  [OK] ffmpeg is installed")
        results.append(("ffmpeg", True, None))
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  [FAIL] ffmpeg is not installed or not in PATH")
        results.append(("ffmpeg", False, "ffmpeg not found"))

    # Test 6: Full orchestrator (quick test)
    print("\n[6/6] Testing full orchestrator pipeline...")
    try:
        if test_audio and test_audio.exists():
            orch = Orchestrator()
            result = orch.transcribe_file(
                test_audio,
                mode="batch",
                processing_options={"denoiseEnabled": False}
            )
            
            print("  [OK] Pipeline completed")
            print(f"    Segments: {len(result.segments)}")
            print(f"    Metrics: {result.metrics.get('total_chunks', 0)} chunks processed")
            
            if result.transcription.get('gurmukhi'):
                print(f"    Output: {result.transcription['gurmukhi'][:50]}...")
            
            results.append(("Full pipeline", True, None))
        else:
            print("  [SKIP] No test audio available")
            results.append(("Full pipeline", None, "Skipped"))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Full pipeline", False, str(e)))
    finally:
        # Cleanup
        if test_audio and test_audio.exists():
            try:
                test_audio.unlink()
            except:
                pass
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status, _ in results if status is True)
    failed = sum(1 for _, status, _ in results if status is False)
    skipped = sum(1 for _, status, _ in results if status is None)
    
    for name, status, error in results:
        if status is True:
            print(f"  [OK] {name}")
        elif status is False:
            print(f"  [FAIL] {name}: {error}")
        else:
            print(f"  [SKIP] {name}: {error}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
    
    if failed > 0:
        print("\n[!] Some tests failed. The app may not work correctly.")
        return False
    else:
        print("\n[SUCCESS] All tests passed. Safe to start the app.")
        return True


def test_accuracy_metrics():
    """Quick test of accuracy metric calculations."""
    print("\n" + "-" * 40)
    print("ACCURACY METRIC VALIDATION")
    print("-" * 40)
    
    from tests.test_transcription_accuracy import calculate_wer, calculate_cer
    
    # Test cases with known expected values
    test_cases = [
        # (reference, hypothesis, expected_wer, expected_cer)
        ("hello world", "hello world", 0.0, 0.0),
        ("hello world", "hello there", 0.5, None),  # 1 word wrong out of 2
        ("abc", "abd", None, 1/3),  # 1 char wrong out of 3
    ]
    
    print("\nWER/CER calculation tests:")
    all_pass = True
    
    for ref, hyp, exp_wer, exp_cer in test_cases:
        actual_wer = calculate_wer(ref, hyp)
        actual_cer = calculate_cer(ref, hyp)
        
        wer_ok = exp_wer is None or abs(actual_wer - exp_wer) < 0.01
        cer_ok = exp_cer is None or abs(actual_cer - exp_cer) < 0.01
        
        status = "[OK]" if (wer_ok and cer_ok) else "[FAIL]"
        print(f"  {status} '{ref}' vs '{hyp}' -> WER={actual_wer:.2f}, CER={actual_cer:.2f}")
        
        if not (wer_ok and cer_ok):
            all_pass = False
    
    if all_pass:
        print("\n[OK] Accuracy metrics working correctly")
    else:
        print("\n[FAIL] Accuracy metric issues detected")
    
    return all_pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-startup transcription test")
    parser.add_argument("--quick", action="store_true", help="Quick test (skip full pipeline)")
    parser.add_argument("--metrics", action="store_true", help="Also test accuracy metrics")
    args = parser.parse_args()
    
    success = test_pipeline_components()
    
    if args.metrics:
        test_accuracy_metrics()
    
    if success:
        print("\nTip: Run 'python app.py' to start the server")
    
    sys.exit(0 if success else 1)
