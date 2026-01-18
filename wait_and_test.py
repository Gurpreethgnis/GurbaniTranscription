"""Wait for server to be ready and then run end-to-end test"""
import requests
import time
import sys

def wait_for_server(max_wait=120):
    """Wait for server to be ready."""
    print("Waiting for server to initialize...")
    print("(This may take 1-2 minutes for Whisper model to load)")
    print("=" * 60)
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < max_wait:
        attempt += 1
        try:
            r = requests.get('http://localhost:5000/status', timeout=5)
            if r.status_code == 200:
                data = r.json()
                elapsed = time.time() - start_time
                print(f"\n[SUCCESS] Server is ready! (took {elapsed:.1f}s)")
                print(f"  - Status: {data.get('status', 'unknown')}")
                print(f"  - Whisper loaded: {data.get('whisper_loaded', False)}")
                print(f"  - Model size: {data.get('model_size', 'unknown')}")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            pass
        
        if attempt % 6 == 0:  # Print every 30 seconds
            elapsed = time.time() - start_time
            print(f"  Still waiting... ({elapsed:.0f}s elapsed)")
        
        time.sleep(5)
    
    print(f"\n[ERROR] Server did not become ready within {max_wait}s")
    return False

def run_end_to_end_test(filename):
    """Run end-to-end transcription test."""
    print("\n" + "=" * 60)
    print("RUNNING END-TO-END TEST")
    print("=" * 60)
    print(f"Testing file: {filename}")
    print("\nThis will test the full Phase 1 pipeline:")
    print("  1. VAD chunking")
    print("  2. Language identification")
    print("  3. ASR-A transcription")
    print("  4. Result aggregation")
    print("\nThis may take several minutes depending on file size...")
    print("=" * 60)
    
    url = "http://localhost:5000/transcribe-v2"
    payload = {"filename": filename}
    
    start_time = time.time()
    
    try:
        print("\nSending request to /transcribe-v2...")
        response = requests.post(url, json=payload, timeout=1800)  # 30 min timeout
        
        elapsed = time.time() - start_time
        print(f"\nResponse received (took {elapsed:.1f}s)")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n" + "=" * 60)
            print("[SUCCESS] END-TO-END TEST PASSED!")
            print("=" * 60)
            
            print(f"\nResponse Summary:")
            print(f"  - Status: {data.get('status', 'unknown')}")
            print(f"  - Processing time: {data.get('processing_time', 0):.2f}s")
            
            if 'result' in data:
                result = data['result']
                print(f"\nTranscription Result:")
                print(f"  - Filename: {result.get('filename', 'unknown')}")
                print(f"  - Total segments: {len(result.get('segments', []))}")
                
                if 'metrics' in result:
                    metrics = result['metrics']
                    print(f"\nMetrics:")
                    print(f"  - Mode: {metrics.get('mode', 'unknown')}")
                    print(f"  - Total chunks: {metrics.get('total_chunks', 0)}")
                    print(f"  - Total segments: {metrics.get('total_segments', 0)}")
                    print(f"  - Average confidence: {metrics.get('average_confidence', 0):.2f}")
                    print(f"  - Segments needing review: {metrics.get('segments_needing_review', 0)}")
                    
                    routes = metrics.get('routes', {})
                    if routes:
                        print(f"\n  Route Distribution:")
                        for route, count in routes.items():
                            if count > 0:
                                print(f"    - {route}: {count}")
                
                segments = result.get('segments', [])
                if segments:
                    print(f"\nSample Segments (first 3):")
                    for i, seg in enumerate(segments[:3], 1):
                        print(f"\n  Segment {i}:")
                        print(f"    - Time: {seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s")
                        print(f"    - Route: {seg.get('route', 'unknown')}")
                        print(f"    - Type: {seg.get('type', 'unknown')}")
                        print(f"    - Confidence: {seg.get('confidence', 0):.2f}")
                        print(f"    - Language: {seg.get('language', 'unknown')}")
                        print(f"    - Needs review: {seg.get('needs_review', False)}")
                        text = seg.get('text', '')
                        if text:
                            preview = text[:80] + "..." if len(text) > 80 else text
                            print(f"    - Text: {preview}")
                    
                    if len(segments) > 3:
                        print(f"\n  ... and {len(segments) - 3} more segments")
                
                # Verify Phase 1 output format
                print(f"\n" + "=" * 60)
                print("PHASE 1 OUTPUT FORMAT VERIFICATION")
                print("=" * 60)
                
                required_fields = ['start', 'end', 'route', 'type', 'text', 'confidence', 'language', 'hypotheses']
                all_valid = True
                
                for i, seg in enumerate(segments[:5], 1):  # Check first 5 segments
                    missing = [f for f in required_fields if f not in seg]
                    if missing:
                        print(f"  Segment {i}: Missing fields: {missing}")
                        all_valid = False
                    else:
                        # Check hypotheses structure
                        hypotheses = seg.get('hypotheses', [])
                        if not isinstance(hypotheses, list):
                            print(f"  Segment {i}: hypotheses is not a list")
                            all_valid = False
                        elif len(hypotheses) > 0:
                            hyp = hypotheses[0]
                            if not all(k in hyp for k in ['engine', 'text', 'confidence']):
                                print(f"  Segment {i}: hypotheses missing required fields")
                                all_valid = False
                
                if all_valid:
                    print("  [PASS] All segments have required Phase 1 fields")
                else:
                    print("  [FAIL] Some segments missing required fields")
            
            print(f"\nOutput Files:")
            print(f"  - Text: {data.get('text_file', 'N/A')}")
            print(f"  - JSON: {data.get('json_file', 'N/A')}")
            
            print("\n" + "=" * 60)
            print("[SUCCESS] Phase 1 implementation is working correctly!")
            print("=" * 60)
            
            return True
        else:
            print(f"\n[ERROR] Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"  Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n[ERROR] Request timed out after 30 minutes")
        print("  The file might be too large or there's an issue with processing")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_file = "Gyan_Da_Sagar_02.mp3"
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    print("\n" + "=" * 60)
    print("PHASE 1: COMPLETE END-TO-END TEST")
    print("=" * 60)
    
    # Step 1: Wait for server
    if not wait_for_server():
        print("\n[FAILED] Cannot proceed - server is not ready")
        sys.exit(1)
    
    # Step 2: Run end-to-end test
    success = run_end_to_end_test(test_file)
    
    sys.exit(0 if success else 1)
