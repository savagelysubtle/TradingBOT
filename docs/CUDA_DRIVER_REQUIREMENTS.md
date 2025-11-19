# CUDA Driver Requirements

## Current Setup

**Your Current Driver:** 576.52
**CUDA Version Supported:** 12.9
**Status:** ✅ Working with `cupy-cuda12x`

## Driver Requirements by CUDA Version

### CUDA 12.x (Current - Recommended)
- **Minimum Driver:** 525.60.13 or newer
- **Your Driver:** 576.52 ✅ **Compatible**
- **CuPy Package:** `cupy-cuda12x`
- **Status:** ✅ **You can use this now** (already configured)

### CUDA 13.x (Future - Optional)
- **Minimum Driver:** 580.00 or newer (R580 branch)
- **Your Driver:** 576.52 ❌ **Not compatible**
- **CuPy Package:** `cupy-cuda13x`
- **Status:** ⚠️ **Requires driver upgrade**

## Recommendation

**You don't need to upgrade your driver!**

Your current driver (576.52) works perfectly with CUDA 12.9, which is:
- ✅ Fully supported
- ✅ Stable and mature
- ✅ Compatible with all CuPy features
- ✅ Already configured in your project

## If You Want CUDA 13.x Support

If you specifically need CUDA 13.x features, you would need to:

1. **Upgrade to driver 580+**
   - Download from: https://www.nvidia.com/Download/index.aspx
   - Select your GPU (RTX 3090) and Windows
   - Install driver 580.00 or newer
   - Restart your computer

2. **Update pyproject.toml**
   ```toml
   gpu = [
       "cupy-cuda13x>=13.6.0; python_version<='3.13'",
   ]
   ```

3. **Reinstall CuPy**
   ```bash
   uv sync --extra gpu --python 3.13.4 --prerelease=allow
   ```

## Driver Compatibility Chart

| CUDA Version | Minimum Driver | Your Driver (576.52) |
|--------------|----------------|---------------------|
| CUDA 11.x    | 450.80.02      | ✅ Compatible        |
| CUDA 12.0    | 525.60.13      | ✅ Compatible        |
| CUDA 12.1    | 525.60.13      | ✅ Compatible        |
| CUDA 12.2    | 525.60.13      | ✅ Compatible        |
| CUDA 12.3    | 525.60.13      | ✅ Compatible        |
| CUDA 12.4    | 525.60.13      | ✅ Compatible        |
| CUDA 12.5    | 525.60.13      | ✅ Compatible        |
| CUDA 12.6    | 525.60.13      | ✅ Compatible        |
| CUDA 12.7    | 525.60.13      | ✅ Compatible        |
| CUDA 12.8    | 525.60.13      | ✅ Compatible        |
| CUDA 12.9    | 525.60.13      | ✅ Compatible        |
| CUDA 13.0    | 580.00         | ❌ **Not compatible** |
| CUDA 13.1    | 580.00         | ❌ **Not compatible** |
| CUDA 13.2    | 580.00         | ❌ **Not compatible** |

## Summary

- **Current Status:** ✅ Your driver (576.52) is perfect for CUDA 12.9
- **No Action Needed:** Your setup is working correctly
- **If Upgrading:** You would need driver 580+ for CUDA 13.x (not necessary)

## References

- NVIDIA CUDA Compatibility: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/
- Driver Downloads: https://www.nvidia.com/Download/index.aspx
- CuPy Installation: https://docs.cupy.dev/en/stable/install.html

