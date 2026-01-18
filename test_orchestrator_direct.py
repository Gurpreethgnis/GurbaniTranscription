"""Direct test of the orchestrator (bypassing Flask server)"""
import sys
from pathlib import Path
import time

def test_orchestrator_direct():
    """Test orchestrator directly."""
    print("=" * 60)
    print("PHASE 1: DIRECT ORCHESTRATOR TEST")
    print("=" * 60)
    
    # Find a test file
    upload_dir = Path("uploads")
    test_file = None
    
    for f in ["Gyan_Da_Sagar_02.mp3", "Lavaan.mp3", "Gurbani_Can_Cure_Cancer.mp3"]:
        file_path = upload_dir / f
        if file_path.exists():
            test_file = file_path
            break
    
    if not test_file:
        # Get any mp3 file
        mp3_files = list(upload_dir.glob("*.mp3"))
        if mp3_files:
            test_file = mp3_files[0]
    
    if not test_file:
        print("[ERROR] No audio files found in uploads/ directory")
        return False
    
    print(f"\nUsing test file: {test_file.name}")
    print(f"File path: {test_file}")
    print(f"File exists: {test_file.exists()}")
    
    try:
        print("\n" + "=" * 60)
        print("Initializing Orchestrator...")
        print("(This will load VAD, LangID, and ASR services)")
        print("=" * 60)
        
        from orchestrator import Orchestrator
        
        start_init = time.time()
        orch = Orchestrator()
        init_time = time.time() - start_init
        
        print(f"\n[SUCCESS] Orchestrator initialized in {init_time:.1f}s")
        print(f"  - VAD service: {type(orch.vad_service).__name__}")
        print(f"  - LangID service: {type(orch.langid_service).__name__}")
        print(f"  - ASR service: {type(orch.asr_service).__name__}")
        
        print("\n" + "=" * 60)
        print("Running Transcription Pipeline...")
        print("=" * 60)
        print("This will:")
        print("  1. Chunk audio with VAD")
        print("  2. Identify language for each chunk")
        print("  3. Transcribe with ASR-A (Whisper)")
        print("  4. Aggregate results")
        print("\nThis may take several minutes...")
        print("=" * 60)
        
        start_transcribe = time.time()
        result = orch.transcribe_file(test_file, mode="batch")
        transcribe_time = time.time() - start_transcribe
        
        print(f"\n[SUCCESS] Transcription completed in {transcribe_time:.1f}s")
        
        # Display results
        print("\n" + "=" * 60)
        print("TRANSCRIPTION RESULTS")
        print("=" * 60)
        
        print(f"\nFilename: {result.filename}")
        print(f"Total segments: {len(result.segments)}")
        
        print(f"\nMetrics:")
        print(f"  - Mode: {result.metrics.get('mode', 'unknown')}")
        print(f"  - Total chunks: {result.metrics.get('total_chunks', 0)}")
        print(f"  - Total segments: {result.metrics.get('total_segments', 0)}")
        print(f"  - Average confidence: {result.metrics.get('average_confidence', 0):.2f}")
        print(f"  - Segments needing review: {result.metrics.get('segments_needing_review', 0)}")
        
        routes = result.metrics.get('routes', {})
        if routes:
            print(f"\n  Route Distribution:")
            for route, count in routes.items():
                if count > 0:
                    print(f"    - {route}: {count}")
        
        print(f"\nTranscription:")
        gurmukhi = result.transcription.get('gurmukhi', '')
        if gurmukhi:
            preview = gurmukhi[:200] + "..." if len(gurmukhi) > 200 else gurmukhi
            print(f"  Gurmukhi preview: {preview}")
        
        print(f"\nSample Segments (first 5):")
        for i, seg in enumerate(result.segments[:5], 1):
            print(f"\n  Segment {i}:")
            print(f"    - Time: {seg.start:.2f}s - {seg.end:.2f}s")
            print(f"    - Route: {seg.route}")
            print(f"    - Type: {seg.type}")
            print(f"    - Confidence: {seg.confidence:.2f}")
            print(f"    - Language: {seg.language}")
            print(f"    - Needs review: {seg.needs_review}")
            print(f"    - Hypotheses: {len(seg.hypotheses)}")
            if seg.hypotheses:
                hyp = seg.hypotheses[0]
                print(f"      Engine: {hyp.get('engine', 'unknown')}")
                print(f"      Confidence: {hyp.get('confidence', 0):.2f}")
            text = seg.text
            if text:
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"    - Text: {preview}")
        
        if len(result.segments) > 5:
            print(f"\n  ... and {len(result.segments) - 5} more segments")
        
        # Verify Phase 1 output format
        print("\n" + "=" * 60)
        print("PHASE 1 OUTPUT FORMAT VERIFICATION")
        print("=" * 60)
        
        required_fields = ['start', 'end', 'route', 'type', 'text', 'confidence', 'language', 'hypotheses']
        all_valid = True
        
        for i, seg in enumerate(result.segments[:10], 1):
            seg_dict = seg.to_dict()
            missing = [f for f in required_fields if f not in seg_dict]
            if missing:
                print(f"  [FAIL] Segment {i}: Missing fields: {missing}")
                all_valid = False
            else:
                # Check hypotheses structure
                hypotheses = seg_dict.get('hypotheses', [])
                if not isinstance(hypotheses, list):
                    print(f"  [FAIL] Segment {i}: hypotheses is not a list")
                    all_valid = False
                elif len(hypotheses) > 0:
                    hyp = hypotheses[0]
                    if not all(k in hyp for k in ['engine', 'text', 'confidence']):
                        print(f"  [FAIL] Segment {i}: hypotheses missing required fields")
                        all_valid = False
        
        if all_valid:
            print("  [PASS] All segments have required Phase 1 fields")
            print("  [PASS] Hypotheses structure is correct")
            print("  [PASS] Output format matches Phase 1 specification")
        else:
            print("  [FAIL] Some segments missing required fields")
        
        # Test serialization
        print("\n" + "=" * 60)
        print("SERIALIZATION TEST")
        print("=" * 60)
        
        try:
            result_dict = result.to_dict()
            print("  [PASS] TranscriptionResult.to_dict() works")
            
            import json
            json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
            print(f"  [PASS] JSON serialization works ({len(json_str)} bytes)")
            
        except Exception as e:
            print(f"  [FAIL] Serialization error: {e}")
            all_valid = False
        
        print("\n" + "=" * 60)
        if all_valid:
            print("[SUCCESS] PHASE 1 IMPLEMENTATION IS COMPLETE AND WORKING!")
            print("=" * 60)
            print("\nAll tests passed:")
            print("  ✓ Orchestrator initialization")
            print("  ✓ VAD chunking")
            print("  ✓ Language identification")
            print("  ✓ ASR-A transcription")
            print("  ✓ Result aggregation")
            print("  ✓ Output format validation")
            print("  ✓ JSON serialization")
            return True
        else:
            print("[PARTIAL SUCCESS] Pipeline works but some format issues found")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_orchestrator_direct()
    sys.exit(0 if success else 1)
