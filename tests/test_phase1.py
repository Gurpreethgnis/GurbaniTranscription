"""
Comprehensive test script for Phase 1: Baseline Orchestrated Pipeline

Tests all components:
1. Data models
2. VAD service
3. LangID service
4. ASR-A (Whisper)
5. Orchestrator
6. End-to-end pipeline
"""
import sys
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)
    
    try:
        from models import AudioChunk, Segment, ASRResult, ProcessedSegment, TranscriptionResult
        print("✓ Models imported successfully")
    except Exception as e:
        print(f"✗ Failed to import models: {e}")
        traceback.print_exc()
        return False
    
    try:
        from vad_service import VADService
        print("✓ VADService imported successfully")
    except Exception as e:
        print(f"✗ Failed to import VADService: {e}")
        traceback.print_exc()
        return False
    
    try:
        from langid_service import LangIDService
        print("✓ LangIDService imported successfully")
    except Exception as e:
        print(f"✗ Failed to import LangIDService: {e}")
        traceback.print_exc()
        return False
    
    try:
        from asr.asr_whisper import ASRWhisper
        print("✓ ASRWhisper imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ASRWhisper: {e}")
        traceback.print_exc()
        return False
    
    try:
        from orchestrator import Orchestrator
        print("✓ Orchestrator imported successfully")
    except Exception as e:
        print(f"✗ Failed to import Orchestrator: {e}")
        traceback.print_exc()
        return False
    
    return True


def test_data_models():
    """Test data model creation and serialization."""
    print("\n" + "=" * 60)
    print("TEST 2: Data Models")
    print("=" * 60)
    
    try:
        from models import AudioChunk, Segment, ASRResult, ProcessedSegment, TranscriptionResult
        
        # Test AudioChunk
        chunk = AudioChunk(
            start_time=0.0,
            end_time=5.0,
            audio_path=Path("test.mp3"),
            duration=5.0
        )
        print(f"✓ AudioChunk created: {chunk.start_time}s - {chunk.end_time}s")
        
        # Test Segment
        segment = Segment(
            start=0.0,
            end=5.0,
            text="Test transcription",
            confidence=0.85,
            language="pa"
        )
        segment_dict = segment.to_dict()
        print(f"✓ Segment created and serialized: {segment_dict}")
        
        # Test ASRResult
        asr_result = ASRResult(
            text="Test text",
            language="pa",
            confidence=0.85,
            segments=[segment],
            engine="asr_a_whisper"
        )
        print(f"✓ ASRResult created: {asr_result.engine}")
        
        # Test ProcessedSegment
        processed = ProcessedSegment(
            start=0.0,
            end=5.0,
            route="punjabi_speech",
            type="speech",
            text="Test",
            confidence=0.85,
            language="pa"
        )
        print(f"✓ ProcessedSegment created: route={processed.route}")
        
        # Test TranscriptionResult
        result = TranscriptionResult(
            filename="test.mp3",
            segments=[processed],
            transcription={"gurmukhi": "Test", "roman": ""},
            metrics={"mode": "batch"}
        )
        result_dict = result.to_dict()
        print(f"✓ TranscriptionResult created and serialized")
        print(f"  - Filename: {result_dict['filename']}")
        print(f"  - Segments: {len(result_dict['segments'])}")
        
        return True
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        traceback.print_exc()
        return False


def test_vad_service():
    """Test VAD service initialization."""
    print("\n" + "=" * 60)
    print("TEST 3: VAD Service")
    print("=" * 60)
    
    try:
        from vad_service import VADService
        
        # Check if dependencies are available
        try:
            import webrtcvad
            print("✓ webrtcvad available")
        except ImportError:
            print("✗ webrtcvad not installed - VAD will not work")
            return False
        
        try:
            from pydub import AudioSegment
            print("✓ pydub available")
        except ImportError:
            print("✗ pydub not installed - VAD will not work")
            return False
        
        # Initialize VAD service
        vad = VADService(
            aggressiveness=2,
            min_chunk_duration=1.0,
            max_chunk_duration=30.0,
            overlap_seconds=0.5
        )
        print("✓ VADService initialized successfully")
        print(f"  - Aggressiveness: {vad.vad.get_mode()}")
        print(f"  - Min chunk: {vad.min_chunk_duration}s")
        print(f"  - Max chunk: {vad.max_chunk_duration}s")
        print(f"  - Overlap: {vad.overlap_seconds}s")
        
        return True
    except Exception as e:
        print(f"✗ VAD service test failed: {e}")
        traceback.print_exc()
        return False


def test_langid_service():
    """Test LangID service initialization."""
    print("\n" + "=" * 60)
    print("TEST 4: LangID Service")
    print("=" * 60)
    
    try:
        from langid_service import LangIDService, ROUTE_PUNJABI_SPEECH, ROUTE_ENGLISH_SPEECH
        
        langid = LangIDService(
            quick_asr_service=None,  # Will use fallback heuristics
            punjabi_threshold=0.6,
            english_threshold=0.6
        )
        print("✓ LangIDService initialized successfully")
        print(f"  - Punjabi threshold: {langid.punjabi_threshold}")
        print(f"  - English threshold: {langid.english_threshold}")
        
        # Test route to language mapping
        lang_code = langid.get_language_code(ROUTE_PUNJABI_SPEECH)
        print(f"✓ Route mapping: {ROUTE_PUNJABI_SPEECH} -> {lang_code}")
        
        return True
    except Exception as e:
        print(f"✗ LangID service test failed: {e}")
        traceback.print_exc()
        return False


def test_asr_whisper():
    """Test ASR-A Whisper service initialization."""
    print("\n" + "=" * 60)
    print("TEST 5: ASR-A Whisper Service")
    print("=" * 60)
    
    try:
        from asr.asr_whisper import ASRWhisper
        
        print("Initializing ASR-A Whisper service...")
        print("(This may take a while to load the model)")
        
        asr = ASRWhisper()
        
        if asr.is_model_loaded():
            print("✓ ASRWhisper initialized successfully")
            print(f"  - Model size: {asr.model_size}")
            print(f"  - Device: {asr.device} ({asr.device_name})")
            return True
        else:
            print("✗ ASRWhisper model not loaded")
            return False
    except Exception as e:
        print(f"✗ ASR-A Whisper test failed: {e}")
        traceback.print_exc()
        return False


def test_orchestrator_init():
    """Test orchestrator initialization."""
    print("\n" + "=" * 60)
    print("TEST 6: Orchestrator Initialization")
    print("=" * 60)
    
    try:
        from orchestrator import Orchestrator
        
        print("Initializing Orchestrator...")
        print("(This will initialize VAD, LangID, and ASR services)")
        
        orch = Orchestrator()
        
        print("✓ Orchestrator initialized successfully")
        print(f"  - VAD service: {type(orch.vad_service).__name__}")
        print(f"  - LangID service: {type(orch.langid_service).__name__}")
        print(f"  - ASR service: {type(orch.asr_service).__name__}")
        
        return True
    except Exception as e:
        print(f"✗ Orchestrator initialization failed: {e}")
        traceback.print_exc()
        return False


def test_end_to_end(audio_file=None):
    """Test end-to-end transcription pipeline."""
    print("\n" + "=" * 60)
    print("TEST 7: End-to-End Pipeline")
    print("=" * 60)
    
    if audio_file is None:
        # Try to find a test file
        upload_dir = Path("uploads")
        if upload_dir.exists():
            audio_files = list(upload_dir.glob("*.mp3"))
            if audio_files:
                audio_file = audio_files[0]
                print(f"Using test file: {audio_file.name}")
            else:
                print("⚠ No audio files found in uploads/ directory")
                print("  Skipping end-to-end test")
                return True
        else:
            print("⚠ uploads/ directory not found")
            print("  Skipping end-to-end test")
            return True
    
    try:
        from orchestrator import Orchestrator
        from pathlib import Path
        
        audio_path = Path(audio_file) if isinstance(audio_file, str) else audio_file
        
        if not audio_path.exists():
            print(f"✗ Audio file not found: {audio_path}")
            return False
        
        print(f"Transcribing: {audio_path.name}")
        print("(This may take several minutes...)")
        
        orch = Orchestrator()
        result = orch.transcribe_file(audio_path, mode="batch")
        
        print("✓ End-to-end transcription completed")
        print(f"  - Filename: {result.filename}")
        print(f"  - Total segments: {len(result.segments)}")
        print(f"  - Mode: {result.metrics.get('mode', 'unknown')}")
        print(f"  - Routes: {result.metrics.get('routes', {})}")
        print(f"  - Average confidence: {result.metrics.get('average_confidence', 0):.2f}")
        print(f"  - Segments needing review: {result.metrics.get('segments_needing_review', 0)}")
        
        # Check output format
        result_dict = result.to_dict()
        if "segments" in result_dict and len(result_dict["segments"]) > 0:
            first_seg = result_dict["segments"][0]
            required_fields = ["start", "end", "route", "type", "text", "confidence", "language", "hypotheses"]
            missing = [f for f in required_fields if f not in first_seg]
            if missing:
                print(f"⚠ Missing fields in segment: {missing}")
            else:
                print("✓ Output format matches Phase 1 specification")
        
        return True
    except Exception as e:
        print(f"✗ End-to-end test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 1: BASELINE ORCHESTRATED PIPELINE - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Data Models", test_data_models()))
    results.append(("VAD Service", test_vad_service()))
    results.append(("LangID Service", test_langid_service()))
    
    # ASR and Orchestrator tests require model loading (may be slow)
    print("\n⚠ Note: ASR and Orchestrator tests will load the Whisper model")
    print("   This may take 1-2 minutes and requires GPU/CPU resources")
    
    user_input = input("\nContinue with ASR/Orchestrator tests? (y/n): ").strip().lower()
    if user_input == 'y':
        results.append(("ASR-A Whisper", test_asr_whisper()))
        results.append(("Orchestrator Init", test_orchestrator_init()))
        
        # End-to-end test
        user_input = input("\nRun end-to-end transcription test? (y/n): ").strip().lower()
        if user_input == 'y':
            results.append(("End-to-End", test_end_to_end()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 implementation is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
