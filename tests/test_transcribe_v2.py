"""Quick test for /transcribe-v2 endpoint"""
import requests
import json
import sys

def test_transcribe_v2(filename):
    """Test the /transcribe-v2 endpoint."""
    url = "http://localhost:5000/transcribe-v2"
    payload = {"filename": filename}
    
    print(f"Testing /transcribe-v2 with file: {filename}")
    print("=" * 60)
    
    try:
        # Send request with long timeout (transcription can take time)
        response = requests.post(url, json=payload, timeout=600)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n[SUCCESS] Transcription completed!")
            print(f"  - Status: {data.get('status', 'unknown')}")
            
            if 'result' in data:
                result = data['result']
                print(f"  - Filename: {result.get('filename', 'unknown')}")
                print(f"  - Total segments: {len(result.get('segments', []))}")
                
                if 'metrics' in result:
                    metrics = result['metrics']
                    print(f"  - Mode: {metrics.get('mode', 'unknown')}")
                    print(f"  - Total chunks: {metrics.get('total_chunks', 0)}")
                    print(f"  - Average confidence: {metrics.get('average_confidence', 0):.2f}")
                    print(f"  - Routes: {metrics.get('routes', {})}")
                
                # Show first segment as example
                segments = result.get('segments', [])
                if segments:
                    first = segments[0]
                    print(f"\n  First segment example:")
                    print(f"    - Start: {first.get('start', 0):.2f}s")
                    print(f"    - End: {first.get('end', 0):.2f}s")
                    print(f"    - Route: {first.get('route', 'unknown')}")
                    print(f"    - Type: {first.get('type', 'unknown')}")
                    print(f"    - Confidence: {first.get('confidence', 0):.2f}")
                    print(f"    - Text preview: {first.get('text', '')[:50]}...")
            
            print(f"\n  - Processing time: {data.get('processing_time', 0):.2f}s")
            print(f"  - Text file: {data.get('text_file', 'N/A')}")
            print(f"  - JSON file: {data.get('json_file', 'N/A')}")
            
            return True
        else:
            print(f"\n[ERROR] Request failed")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n[ERROR] Request timed out (transcription taking too long)")
        print("  This is normal for large files. Check server logs for progress.")
        return False
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Cannot connect to server")
        print("  Make sure the server is running: python app.py")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with a file that exists
    test_file = "Gyan_Da_Sagar_02.mp3"  # This file exists based on directory listing
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    print("\n" + "=" * 60)
    print("PHASE 1: /transcribe-v2 ENDPOINT TEST")
    print("=" * 60 + "\n")
    
    success = test_transcribe_v2(test_file)
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Phase 1 endpoint is working correctly!")
    else:
        print("[FAILED] Endpoint test failed. Check errors above.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
