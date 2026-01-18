"""
Quick health check for the Flask server and Phase 1 components.

This script tests if the server can start and basic endpoints work
without requiring full model loading.
"""
import sys
import os
import requests
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def test_server_running(base_url="http://localhost:5000"):
    """Test if the server is running."""
    print("=" * 60)
    print("SERVER HEALTH CHECK")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Server is running")
            print(f"  - Status: {data.get('status', 'unknown')}")
            print(f"  - Whisper loaded: {data.get('whisper_loaded', False)}")
            print(f"  - Model size: {data.get('model_size', 'unknown')}")
            return True
        else:
            print(f"[FAIL] Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to server. Is it running?")
        print("  Start the server with: python app.py")
        return False
    except requests.exceptions.Timeout:
        print("[FAIL] Server request timed out")
        return False
    except Exception as e:
        print(f"[FAIL] Error checking server: {e}")
        return False


def test_imports():
    """Test that all modules can be imported without errors."""
    print("\n" + "=" * 60)
    print("MODULE IMPORT CHECK")
    print("=" * 60)
    
    modules = [
        ("models", ["AudioChunk", "Segment", "ASRResult", "ProcessedSegment", "TranscriptionResult"]),
        ("vad_service", ["VADService"]),
        ("langid_service", ["LangIDService"]),
        ("asr.asr_whisper", ["ASRWhisper"]),
        ("orchestrator", ["Orchestrator"]),
    ]
    
    all_ok = True
    for module_name, classes in modules:
        try:
            module = __import__(module_name, fromlist=classes)
            for class_name in classes:
                if hasattr(module, class_name):
                    print(f"[OK] {module_name}.{class_name}")
                else:
                    print(f"[FAIL] {module_name}.{class_name} not found")
                    all_ok = False
        except ImportError as e:
            print(f"[FAIL] Failed to import {module_name}: {e}")
            all_ok = False
        except Exception as e:
            print(f"[FAIL] Error importing {module_name}: {e}")
            all_ok = False
    
    return all_ok


def test_dependencies():
    """Check if required dependencies are installed."""
    print("\n" + "=" * 60)
    print("DEPENDENCY CHECK")
    print("=" * 60)
    
    dependencies = {
        "webrtcvad": "VAD service",
        "pydub": "Audio chunking",
        "soundfile": "Audio file handling",
        "faster_whisper": "ASR engine",
        "flask": "Web server",
        "numpy": "Numerical operations"
    }
    
    all_ok = True
    for dep, purpose in dependencies.items():
        try:
            __import__(dep.replace("-", "_"))
            print(f"[OK] {dep:20} ({purpose})")
        except ImportError:
            print(f"[MISSING] {dep:20} ({purpose}) - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def test_config():
    """Check configuration values."""
    print("\n" + "=" * 60)
    print("CONFIGURATION CHECK")
    print("=" * 60)
    
    try:
        import config
        
        configs = [
            ("VAD_AGGRESSIVENESS", config.VAD_AGGRESSIVENESS),
            ("VAD_MIN_CHUNK_DURATION", config.VAD_MIN_CHUNK_DURATION),
            ("VAD_MAX_CHUNK_DURATION", config.VAD_MAX_CHUNK_DURATION),
            ("VAD_OVERLAP_SECONDS", config.VAD_OVERLAP_SECONDS),
            ("LANGID_PUNJABI_THRESHOLD", config.LANGID_PUNJABI_THRESHOLD),
            ("LANGID_ENGLISH_THRESHOLD", config.LANGID_ENGLISH_THRESHOLD),
            ("SEGMENT_CONFIDENCE_THRESHOLD", config.SEGMENT_CONFIDENCE_THRESHOLD),
        ]
        
        for name, value in configs:
            print(f"[OK] {name:30} = {value}")
        
        return True
    except Exception as e:
        print(f"✗ Config check failed: {e}")
        return False


def test_file_structure():
    """Check if required directories exist."""
    print("\n" + "=" * 60)
    print("FILE STRUCTURE CHECK")
    print("=" * 60)
    
    required_dirs = [
        "uploads",
        "outputs/transcriptions",
        "outputs/json",
        "logs",
        "asr"
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"[OK] {dir_path}/")
        else:
            print(f"[MISSING] {dir_path}/ - MISSING")
            all_ok = False
    
    # Check for required files
    required_files = [
        "app.py",
        "orchestrator.py",
        "vad_service.py",
        "langid_service.py",
        "models.py",
        "config.py",
        "asr/__init__.py",
        "asr/asr_whisper.py"
    ]
    
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"[OK] {file_path}")
        else:
            print(f"[MISSING] {file_path} - MISSING")
            all_ok = False
    
    return all_ok


def main():
    """Run all health checks."""
    print("\n" + "=" * 60)
    print("PHASE 1 HEALTH CHECK")
    print("=" * 60)
    
    results = []
    
    results.append(("Dependencies", test_dependencies()))
    results.append(("File Structure", test_file_structure()))
    results.append(("Configuration", test_config()))
    results.append(("Module Imports", test_imports()))
    results.append(("Server Status", test_server_running()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status:8} {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n[SUCCESS] All health checks passed!")
        print("\nNext steps:")
        print("  1. Run full test suite: python test_phase1.py")
        print("  2. Test transcription: curl -X POST http://localhost:5000/transcribe-v2 \\")
        print("     -H 'Content-Type: application/json' -d '{\"filename\": \"Lavaan.mp3\"}'")
    else:
        print(f"\n[WARNING] {total - passed} check(s) failed. Please fix issues before testing.")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
