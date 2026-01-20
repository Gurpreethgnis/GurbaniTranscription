"""
Device detection utilities for Katha Transcription System.

Provides shared GPU/CPU device detection used by all ASR engines.
"""
import os
import config


def detect_device():
    """
    Detect available device (CUDA GPU or CPU).
    
    Returns:
        tuple: (device_type, device_name) where device_type is 'cuda' or 'cpu'
    
    Raises:
        RuntimeError: If GPU is required but not available/compatible
    """
    require_gpu = getattr(config, "REQUIRE_GPU", False)
    
    # Check for environment variable to force CPU mode
    force_cpu = os.getenv("FORCE_CPU", "false").lower() == "true"
    if force_cpu:
        if require_gpu:
            raise RuntimeError("FORCE_CPU is set but REQUIRE_GPU=true. Refusing CPU fallback.")
        print("FORCE_CPU environment variable set, using CPU mode")
        return "cpu", "CPU (forced)"
    
    try:
        import torch
        
        if not torch.cuda.is_available():
            if require_gpu:
                raise RuntimeError("CUDA is not available but REQUIRE_GPU=true.")
            print("CUDA is not available, using CPU")
            return "cpu", "CPU"
        
        device_name = torch.cuda.get_device_name(0)
        device_props = torch.cuda.get_device_properties(0)
        compute_cap = f"sm_{device_props.major}{device_props.minor}"
        
        # Get supported architectures
        arch_list = torch.cuda.get_arch_list()
        print(f"GPU detected: {device_name} (Compute: {compute_cap})")
        print(f"PyTorch CUDA version: {torch.version.cuda}")
        print(f"Supported architectures: {arch_list}")
        
        # Check if compute capability is supported
        if compute_cap not in arch_list:
            print(f"WARNING: {compute_cap} not in supported architectures!")
            print("This may cause 'no kernel image available' errors.")
            print("Attempting GPU operations anyway...")
        
        # Test GPU compatibility with actual operations
        try:
            # Test tensor creation and computation
            test_tensor = torch.randn(10, 10, device="cuda")
            result = torch.matmul(test_tensor, test_tensor)
            result_mean = result.mean().item()
            del test_tensor, result
            torch.cuda.empty_cache()
            
            print(f"✓ GPU compatibility test passed (test result: {result_mean:.4f})")
            return "cuda", device_name
            
        except RuntimeError as e:
            error_msg = str(e).lower()
            if "no kernel image" in error_msg or "cuda error" in error_msg:
                if require_gpu:
                    raise RuntimeError(
                        "GPU compatibility test failed and REQUIRE_GPU=true. "
                        "Install a compatible PyTorch/CUDA build for this GPU."
                    )
                print(f"[ERROR] GPU compatibility test failed: {e}")
                print("Falling back to CPU mode.")
                print("To fix: Use PyTorch nightly with CUDA 12.8+ for RTX 50 series support")
                return "cpu", "CPU (CUDA incompatible)"
            else:
                # Re-raise if it's a different error
                raise
        
    except ImportError:
        if require_gpu:
            raise RuntimeError("PyTorch is not installed but REQUIRE_GPU=true.")
        print("PyTorch not available, using CPU")
        return "cpu", "CPU"
    except Exception as e:
        print(f"Warning: Error detecting device, using CPU: {e}")
        return "cpu", "CPU"

