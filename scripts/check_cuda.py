"""Check CUDA driver and runtime compatibility."""
import sys

print("=" * 60)
print("CUDA Compatibility Check")
print("=" * 60)

# Check Python version
print(f"\nPython Version: {sys.version}")
print(f"Python Executable: {sys.executable}")

# Try to import CuPy
print("\n" + "-" * 60)
print("CuPy Installation Check")
print("-" * 60)
try:
    import cupy as cp
    print(f"✓ CuPy installed: {cp.__version__}")

    # Check CUDA availability (may fail with driver error)
    try:
        cuda_available = cp.cuda.is_available()
        print(f"\nCUDA Availability: {cuda_available}")
    except Exception as e:
        print(f"\n✗ CUDA Availability Check Failed: {e}")
        print("  This indicates a driver/runtime mismatch")
        cuda_available = False

    if cuda_available:
        # Get CUDA runtime version
        try:
            runtime_version = cp.cuda.runtime.runtimeGetVersion()
            runtime_major = runtime_version // 1000
            runtime_minor = (runtime_version % 1000) // 10
            print(f"✓ CUDA Runtime Version: {runtime_major}.{runtime_minor}")
        except Exception as e:
            print(f"✗ Could not get CUDA runtime version: {e}")

        # Get CUDA driver version
        try:
            driver_version = cp.cuda.runtime.driverGetVersion()
            driver_major = driver_version // 1000
            driver_minor = (driver_version % 1000) // 10
            print(f"✓ CUDA Driver Version: {driver_major}.{driver_minor}")

            # Check compatibility
            print("\n" + "-" * 60)
            print("Compatibility Check")
            print("-" * 60)
            if driver_version < runtime_version:
                print(f"✗ ERROR: Driver version ({driver_major}.{driver_minor}) is older than runtime ({runtime_major}.{runtime_minor})")
                print(f"  You need to update your NVIDIA driver to support CUDA {runtime_major}.{runtime_minor}")
            else:
                print(f"✓ Driver version ({driver_major}.{driver_minor}) is compatible with runtime ({runtime_major}.{runtime_minor})")
        except Exception as e:
            print(f"✗ Could not get CUDA driver version: {e}")

        # Get device info
        try:
            device = cp.cuda.Device()
            print(f"\n✓ GPU Device: {device.id}")
            print(f"✓ Compute Capability: {device.compute_capability}")
            mempool = cp.get_default_memory_pool()
            try:
                mem_limit = mempool.get_limit() / 1e9  # GB
                print(f"✓ GPU Memory Limit: {mem_limit:.2f} GB")
            except:
                print("✓ GPU Memory Limit: Not set")
        except Exception as e:
            print(f"✗ Could not get device info: {e}")
    else:
        print("✗ CUDA is not available")
        print("  This could mean:")
        print("  - No NVIDIA GPU detected")
        print("  - CUDA driver not installed")
        print("  - Driver/runtime mismatch")

except ImportError:
    print("✗ CuPy not installed")
    print("  Install with: uv sync --extra gpu --python 3.13.4 --prerelease=allow")

# Check NVIDIA driver via nvidia-smi
print("\n" + "-" * 60)
print("NVIDIA Driver Check (nvidia-smi)")
print("-" * 60)
import subprocess
import os

# Try multiple possible paths for nvidia-smi
nvidia_smi_paths = [
    "nvidia-smi",
    "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
    "C:\\Windows\\System32\\nvidia-smi.exe",
]

nvidia_smi_found = False
for path in nvidia_smi_paths:
    try:
        result = subprocess.run(
            [path, "--query-gpu=driver_version,cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        driver_ver = parts[0].strip()
                        cuda_ver = parts[1].strip()
                        print(f"✓ GPU {i}: Driver {driver_ver}, Supports CUDA {cuda_ver}")
            nvidia_smi_found = True
            break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        continue
    except Exception:
        continue

if not nvidia_smi_found:
    print("✗ nvidia-smi not found or failed to run")
    print("  This may mean:")
    print("  - NVIDIA driver is not installed")
    print("  - nvidia-smi is not in PATH")
    print("  - Driver installation is incomplete")

print("\n" + "=" * 60)
print("Recommendations")
print("=" * 60)
print("""
1. CUDA Driver vs Runtime:
   - Driver version must be >= Runtime version
   - cupy-cuda13x requires CUDA 13.x runtime
   - Your driver must support CUDA 13.x

2. If driver is too old:
   - Download latest NVIDIA driver from: https://www.nvidia.com/Download/index.aspx
   - Install and restart your computer

3. If you have CUDA 12.x driver:
   - Use cupy-cuda12x instead: uv sync --extra gpu --python 3.13.4
   - Update pyproject.toml to use cupy-cuda12x

4. Check compatibility:
   - CUDA 13.x runtime requires driver >= 550.54.15
   - CUDA 12.x runtime requires driver >= 525.60.13
""")

