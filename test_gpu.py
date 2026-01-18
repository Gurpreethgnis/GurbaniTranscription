"""
GPU test script to verify CUDA compatibility and GPU availability.
Run this before starting the main application to ensure GPU is working.
"""
import sys
import os

def test_gpu():
    """Test GPU availability and compatibility."""
    print("=" * 60)
    print("GPU Compatibility Test")
    print("=" * 60)
    
    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")
        print(f"✓ CUDA version (PyTorch): {torch.version.cuda}")
        
        # Check CUDA availability
        cuda_available = torch.cuda.is_available()
        print(f"✓ CUDA available: {cuda_available}")
        
        if not cuda_available:
            print("\n[ERROR] CUDA is not available. Check:")
            print("  - NVIDIA drivers installed")
            print("  - Docker GPU access configured")
            print("  - NVIDIA Container Toolkit installed")
            return False
        
        # Get GPU information
        device_count = torch.cuda.device_count()
        print(f"✓ Number of GPUs: {device_count}")
        
        if device_count == 0:
            print("\n[ERROR] No GPU devices found")
            return False
        
        # Check each GPU
        for i in range(device_count):
            print(f"\n--- GPU {i} ---")
            device_name = torch.cuda.get_device_name(i)
            props = torch.cuda.get_device_properties(i)
            print(f"  Name: {device_name}")
            print(f"  Compute Capability: {props.major}.{props.minor} (sm_{props.major}{props.minor})")
            print(f"  Total Memory: {props.total_memory / 1024**3:.2f} GB")
            
            # Check if sm_120 is supported
            arch_list = torch.cuda.get_arch_list()
            print(f"  Supported architectures: {arch_list}")
            
            if f"sm_{props.major}{props.minor}" not in arch_list:
                print(f"  [WARNING] sm_{props.major}{props.minor} not in supported architectures!")
                print(f"     This may cause 'no kernel image available' errors")
                print(f"     You may need PyTorch nightly with CUDA 12.8+")
        
        # Test basic GPU operations
        print("\n--- Testing GPU Operations ---")
        try:
            # Test tensor creation
            x = torch.randn(100, 100, device="cuda")
            print("  ✓ Tensor creation on GPU: SUCCESS")
            
            # Test computation
            y = torch.matmul(x, x)
            result = y.mean().item()
            print(f"  ✓ GPU computation: SUCCESS (result: {result:.4f})")
            
            # Test memory operations
            torch.cuda.empty_cache()
            print("  ✓ GPU memory operations: SUCCESS")
            
            # Clean up
            del x, y
            torch.cuda.empty_cache()
            
        except RuntimeError as e:
            print(f"  [ERROR] GPU operation failed: {e}")
            if "no kernel image" in str(e).lower():
                print("\n  This error indicates PyTorch doesn't support your GPU's compute capability.")
                print("  Solution: Use PyTorch nightly with CUDA 12.8+ for RTX 50 series support")
            return False
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All GPU tests passed! GPU is ready to use.")
        print("=" * 60)
        return True
        
    except ImportError:
        print("[ERROR] PyTorch is not installed")
        return False
    except Exception as e:
        print(f"[ERROR] Error during GPU test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_gpu()
    sys.exit(0 if success else 1)
