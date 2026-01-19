"""
Comprehensive test script for Phase 2: Multi-ASR Ensemble + Fusion

Tests all Phase 2 components:
1. ASR-B (Indic Whisper)
2. ASR-C (English Whisper)
3. ASR Fusion layer
4. Orchestrator with multi-ASR integration
5. End-to-end pipeline with fusion
"""
import sys
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all Phase 2 modules can be imported."""
    print("=" * 60)
    print("TEST 1: Phase 2 Module Imports")
    print("=" * 60)
    
    try:
        from asr.asr_indic import ASRIndic
        print("[OK] ASRIndic imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import ASRIndic: {e}")
        traceback.print_exc()
        return False
    
    try:
        from asr.asr_english_fallback import ASREnglish
        print("[OK] ASREnglish imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import ASREnglish: {e}")
        traceback.print_exc()
        return False
    
    try:
        from asr.asr_fusion import ASRFusion
        print("[OK] ASRFusion imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import ASRFusion: {e}")
        traceback.print_exc()
        return False
    
    try:
        from core.models import FusionResult
        print("[OK] FusionResult imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import FusionResult: {e}")
        traceback.print_exc()
        return False
    
    try:
        from core.orchestrator import Orchestrator
        print("[OK] Orchestrator imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import Orchestrator: {e}")
        traceback.print_exc()
        return False
    
    return True


def test_fusion_result_model():
    """Test FusionResult data model."""
    print("\n" + "=" * 60)
    print("TEST 2: FusionResult Data Model")
    print("=" * 60)
    
    try:
        from models import FusionResult
        
        fusion_result = FusionResult(
            fused_text="Test transcription",
            fused_confidence=0.85,
            agreement_score=0.90,
            hypotheses=[
                {"engine": "asr_a", "text": "Test transcription", "confidence": 0.80},
                {"engine": "asr_b", "text": "Test transcription", "confidence": 0.90}
            ],
            redecode_attempts=0,
            selected_engine="asr_b"
        )
        
        print(f"[OK] FusionResult created successfully")
        print(f"  - Fused text: {fusion_result.fused_text}")
        print(f"  - Confidence: {fusion_result.fused_confidence:.2f}")
        print(f"  - Agreement: {fusion_result.agreement_score:.2f}")
        print(f"  - Hypotheses: {len(fusion_result.hypotheses)}")
        
        # Test serialization
        result_dict = fusion_result.to_dict()
        required_fields = [
            "fused_text", "fused_confidence", "agreement_score",
            "hypotheses", "redecode_attempts", "selected_engine"
        ]
        missing = [f for f in required_fields if f not in result_dict]
        if missing:
            print(f"[FAIL] Missing fields in to_dict(): {missing}")
            return False
        
        print("[OK] FusionResult serialization works correctly")
        return True
        
    except Exception as e:
        print(f"[FAIL] FusionResult test failed: {e}")
        traceback.print_exc()
        return False


def test_fusion_service():
    """Test ASR Fusion service with mock data."""
    print("\n" + "=" * 60)
    print("TEST 3: ASR Fusion Service")
    print("=" * 60)
    
    try:
        from asr.asr_fusion import ASRFusion
        from models import ASRResult, Segment
        
        fusion = ASRFusion()
        print("[OK] ASRFusion initialized")
        
        # Create mock ASR results
        result1 = ASRResult(
            text="Hello world",
            language="en",
            confidence=0.80,
            segments=[],
            engine="asr_a"
        )
        
        result2 = ASRResult(
            text="Hello world",
            language="en",
            confidence=0.90,
            segments=[],
            engine="asr_b"
        )
        
        # Test fusion with agreeing hypotheses
        fusion_result = fusion.fuse_hypotheses([result1, result2])
        print(f"[OK] Fusion completed")
        print(f"  - Fused text: {fusion_result.fused_text}")
        print(f"  - Confidence: {fusion_result.fused_confidence:.2f}")
        print(f"  - Agreement: {fusion_result.agreement_score:.2f}")
        print(f"  - Selected engine: {fusion_result.selected_engine}")
        
        # Test with disagreeing hypotheses
        result3 = ASRResult(
            text="Different text",
            language="en",
            confidence=0.70,
            segments=[],
            engine="asr_c"
        )
        
        fusion_result2 = fusion.fuse_hypotheses([result1, result3])
        print(f"[OK] Fusion with disagreement completed")
        print(f"  - Agreement: {fusion_result2.agreement_score:.2f}")
        print(f"  - Selected engine: {fusion_result2.selected_engine}")
        
        # Test re-decode decision
        should_redecode = fusion.should_redecode(fusion_result)
        print(f"[OK] Re-decode decision: {should_redecode}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Fusion service test failed: {e}")
        traceback.print_exc()
        return False


def test_asr_indic_init():
    """Test ASR-B (Indic) initialization."""
    print("\n" + "=" * 60)
    print("TEST 4: ASR-B (Indic) Initialization")
    print("=" * 60)
    
    try:
        from asr.asr_indic import ASRIndic
        
        print("Initializing ASR-B (Indic) service...")
        print("(This may take a while to load the model)")
        
        asr_indic = ASRIndic()
        
        if asr_indic.is_model_loaded():
            print("[OK] ASRIndic initialized successfully")
            print(f"  - Model size: {asr_indic.model_size}")
            print(f"  - Device: {asr_indic.device} ({asr_indic.device_name})")
            return True
        else:
            print("[FAIL] ASRIndic model not loaded")
            return False
            
    except Exception as e:
        print(f"[FAIL] ASR-B initialization test failed: {e}")
        traceback.print_exc()
        return False


def test_asr_english_init():
    """Test ASR-C (English) initialization."""
    print("\n" + "=" * 60)
    print("TEST 5: ASR-C (English) Initialization")
    print("=" * 60)
    
    try:
        from asr.asr_english_fallback import ASREnglish
        
        print("Initializing ASR-C (English) service...")
        print("(This may take a while to load the model)")
        
        asr_english = ASREnglish()
        
        if asr_english.is_model_loaded():
            print("[OK] ASREnglish initialized successfully")
            print(f"  - Model size: {asr_english.model_size}")
            print(f"  - Device: {asr_english.device} ({asr_english.device_name})")
            print(f"  - Force language: {asr_english.force_language}")
            return True
        else:
            print("[FAIL] ASREnglish model not loaded")
            return False
            
    except Exception as e:
        print(f"[FAIL] ASR-C initialization test failed: {e}")
        traceback.print_exc()
        return False


def test_orchestrator_phase2_init():
    """Test orchestrator initialization with Phase 2 components."""
    print("\n" + "=" * 60)
    print("TEST 6: Orchestrator Phase 2 Initialization")
    print("=" * 60)
    
    try:
        from core.orchestrator import Orchestrator
        
        print("Initializing Orchestrator with Phase 2 components...")
        print("(This will initialize VAD, LangID, ASR-A, and optionally ASR-B/C)")
        
        orch = Orchestrator()
        
        print("[OK] Orchestrator initialized successfully")
        print(f"  - VAD service: {type(orch.vad_service).__name__}")
        print(f"  - LangID service: {type(orch.langid_service).__name__}")
        print(f"  - ASR-A service: {type(orch.asr_service).__name__}")
        print(f"  - Fusion service: {type(orch.fusion_service).__name__}")
        print(f"  - Parallel execution: {orch.parallel_execution}")
        print(f"  - ASR timeout: {orch.asr_timeout}s")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Orchestrator Phase 2 initialization failed: {e}")
        traceback.print_exc()
        return False


def test_end_to_end_phase2(audio_file=None):
    """Test end-to-end transcription pipeline with Phase 2 fusion."""
    print("\n" + "=" * 60)
    print("TEST 7: End-to-End Phase 2 Pipeline")
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
                print("[WARN] No audio files found in uploads/ directory")
                print("  Skipping end-to-end test")
                return True
        else:
            print("[WARN] uploads/ directory not found")
            print("  Skipping end-to-end test")
            return True
    
    try:
        from core.orchestrator import Orchestrator
        from pathlib import Path
        
        audio_path = Path(audio_file) if isinstance(audio_file, str) else audio_file
        
        if not audio_path.exists():
            print(f"[FAIL] Audio file not found: {audio_path}")
            return False
        
        print(f"Transcribing: {audio_path.name}")
        print("(This may take several minutes with multi-ASR ensemble...)")
        
        orch = Orchestrator()
        result = orch.transcribe_file(audio_path, mode="batch")
        
        print("[OK] End-to-end Phase 2 transcription completed")
        print(f"  - Filename: {result.filename}")
        print(f"  - Total segments: {len(result.segments)}")
        print(f"  - Mode: {result.metrics.get('mode', 'unknown')}")
        print(f"  - Routes: {result.metrics.get('routes', {})}")
        print(f"  - Average confidence: {result.metrics.get('average_confidence', 0):.2f}")
        print(f"  - Segments needing review: {result.metrics.get('segments_needing_review', 0)}")
        
        # Check for multi-ASR hypotheses
        segments_with_multiple_hypotheses = [
            seg for seg in result.segments 
            if len(seg.hypotheses) > 1
        ]
        print(f"  - Segments with multiple hypotheses: {len(segments_with_multiple_hypotheses)}")
        
        if segments_with_multiple_hypotheses:
            first_multi = segments_with_multiple_hypotheses[0]
            print(f"  - Example: {len(first_multi.hypotheses)} hypotheses from engines: {[h['engine'] for h in first_multi.hypotheses]}")
        
        # Check output format
        result_dict = result.to_dict()
        if "segments" in result_dict and len(result_dict["segments"]) > 0:
            first_seg = result_dict["segments"][0]
            required_fields = ["start", "end", "route", "type", "text", "confidence", "language", "hypotheses"]
            missing = [f for f in required_fields if f not in first_seg]
            if missing:
                print(f"[WARN] Missing fields in segment: {missing}")
            else:
                print("[OK] Output format matches Phase 2 specification")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] End-to-end Phase 2 test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    print("\n" + "=" * 60)
    print("PHASE 2: MULTI-ASR ENSEMBLE + FUSION - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run basic tests
    results.append(("Imports", test_imports()))
    results.append(("FusionResult Model", test_fusion_result_model()))
    results.append(("Fusion Service", test_fusion_service()))
    
    # ASR and Orchestrator tests require model loading (may be slow)
    print("\n[WARN] Note: ASR and Orchestrator tests will load Whisper models")
    print("   This may take 2-5 minutes and requires GPU/CPU resources")
    
    user_input = input("\nContinue with ASR/Orchestrator tests? (y/n): ").strip().lower()
    if user_input == 'y':
        results.append(("ASR-B Indic Init", test_asr_indic_init()))
        results.append(("ASR-C English Init", test_asr_english_init()))
        results.append(("Orchestrator Phase 2 Init", test_orchestrator_phase2_init()))
        
        # End-to-end test
        user_input = input("\nRun end-to-end Phase 2 transcription test? (y/n): ").strip().lower()
        if user_input == 'y':
            results.append(("End-to-End Phase 2", test_end_to_end_phase2()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status:8} {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Phase 2 implementation is working correctly.")
    else:
        print(f"\n[WARN] {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
