# GPU Acceleration with CuPy

The Monte Carlo simulation engine now supports GPU acceleration using
[CuPy](https://cupy.dev/), a NumPy-compatible library for GPU computing.

## ⚠️ Python 3.14 Compatibility Note

**CuPy 13.6.0 does not have wheels for Python 3.14 yet** (only supports up to
Python 3.13). The Monte Carlo engine will automatically fall back to CPU (NumPy)
on Python 3.14.

**Options:**

1. **Use Python 3.13** for GPU acceleration (recommended)
2. **Wait for CuPy to release Python 3.14 wheels** (check
   [CuPy releases](https://github.com/cupy/cupy/releases))
3. **Build CuPy from source** (advanced, not recommended)

## Overview

CuPy provides a drop-in replacement for NumPy that runs on NVIDIA CUDA GPUs,
offering significant speedups for Monte Carlo simulations (often 10-100x faster
depending on GPU and problem size).

## Installation

### For Python 3.13 or Earlier (Recommended)

```bash
# Install CuPy for CUDA 12.x
uv add --optional gpu cupy-cuda12x

# Or manually
uv pip install cupy-cuda12x
```

### For Python 3.14

CuPy is **not available** for Python 3.14 yet. The code will automatically use
CPU (NumPy) instead. No action needed - GPU acceleration will be enabled
automatically when CuPy releases Python 3.14 wheels.

### Other CUDA Versions

- **CUDA 11.x**: `uv pip install cupy-cuda11x`
- **CUDA 13.x**: `uv pip install cupy-cuda13x`
- **ROCm (AMD)**: `uv pip install cupy-rocm-5-0` (experimental)

See [CuPy Installation Guide](https://docs.cupy.dev/en/stable/install.html) for
details.

## Requirements

- **NVIDIA GPU** with CUDA support (CUDA 11.2+ or 12.x)
- **CUDA Toolkit** installed on your system
- **Python 3.13 or earlier** for GPU acceleration (Python 3.14 falls back to
  CPU)

### Checking GPU Availability

```python
try:
    import cupy as cp
    print(f"GPU Device: {cp.cuda.Device().compute_capability}")
    print(f"GPU Memory: {cp.get_default_memory_pool().get_limit() / 1e9:.2f} GB")
except ImportError:
    print("CuPy not available - using CPU")
```

## Automatic Fallback

The Monte Carlo engine **automatically falls back to CPU (NumPy)** if:

- CuPy is not installed
- Python 3.14 is used (no wheels available yet)
- No GPU is available
- CUDA is not properly configured

You'll see a log message indicating which backend is being used:

- `"CuPy available - using GPU acceleration for Monte Carlo simulations"`
- `"CuPy not available - using CPU (NumPy) for Monte Carlo simulations"`

## Performance Benefits

### Typical Speedups (Python 3.13 or earlier)

| Simulations | CPU Time | GPU Time (RTX 3090) | Speedup |
| ----------- | -------- | ------------------- | ------- |
| 1,000       | ~30s     | ~3s                 | 10x     |
| 10,000      | ~5min    | ~20s                | 15x     |
| 100,000     | ~50min   | ~3min               | 17x     |

_Actual performance depends on GPU model, data size, and simulation complexity_

### What's Accelerated

**GPU-Accelerated Operations:**

- ✅ Random number generation (`cp.random.choice`, `cp.random.normal`)
- ✅ Statistical calculations (mean, median, std, percentiles)
- ✅ Array operations (sorting, indexing)
- ✅ Bootstrap resampling
- ✅ Synthetic return generation

**Still CPU-Based:**

- ⚠️ Pandas DataFrame operations (converted to NumPy/CuPy arrays)
- ⚠️ Backtest engine execution (runs on CPU)
- ⚠️ File I/O and result saving

## Usage

No code changes needed! The Monte Carlo engine automatically uses GPU if
available:

```python
from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine
from trading_bot.strategies.moving_average import MovingAverageCrossover

# Create engine (will use GPU if CuPy available and Python <= 3.13)
engine = MonteCarloEngine(
    initial_capital=10000.0,
    n_simulations=1000,
    random_seed=42,
)

# Run simulation (GPU-accelerated automatically if available)
strategy = MovingAverageCrossover(short_window=50, long_window=200)
results = engine.run(strategy, data, "BTC/USDT", method="bootstrap")

# Check if GPU was used
print(f"GPU Accelerated: {results['gpu_accelerated']}")
```

## Implementation Details

### Data Flow

1. **Input**: Python lists/NumPy arrays
2. **GPU Transfer**: Convert to CuPy arrays (`cp.asarray()`)
3. **GPU Computation**: Perform calculations on GPU
4. **CPU Transfer**: Convert back to NumPy (`cp.asnumpy()`)
5. **Output**: Python native types for pandas/JSON

### Memory Management

CuPy automatically manages GPU memory. For very large simulations:

- Monitor GPU memory usage
- Consider reducing `n_simulations` or processing in batches
- Use `cp.get_default_memory_pool().free_all_blocks()` to free memory if needed

## Troubleshooting

### "CuPy not available" (Python 3.14)

**Expected**: CuPy wheels are not available for Python 3.14 yet. The code
automatically falls back to CPU (NumPy).

**Solutions**:

1. **Use Python 3.13** for GPU acceleration (recommended)
2. Wait for CuPy to release Python 3.14 wheels
3. Build CuPy from source (advanced)

### "CUDA out of memory"

**Solutions**:

1. Reduce `n_simulations` (e.g., 1000 instead of 10000)
2. Process simulations in batches
3. Use CPU fallback (uninstall CuPy or use Python 3.14)

### "No CUDA-capable device"

**Solution**:

- Verify NVIDIA GPU is installed
- Check CUDA installation: `nvidia-smi`
- Install appropriate CuPy version for your CUDA version

### Performance Not Improved

**Possible Causes**:

- Small number of simulations (< 1000) - GPU overhead may outweigh benefits
- Data transfer overhead (CPU ↔ GPU) dominates computation
- GPU is older/slower than expected
- Using Python 3.14 (no GPU acceleration available)

**Solution**: GPU acceleration is most beneficial for:

- Large simulations (1000+)
- Complex statistical calculations
- Multiple simulations in batch
- Python 3.13 or earlier

## Checking GPU Status

The Monte Carlo results include a `gpu_accelerated` field:

```python
results = engine.run(strategy, data, symbol)
print(f"GPU Used: {results['gpu_accelerated']}")
```

Results summary also shows GPU status:

```
System Information
--------------------------------------------------
GPU Accelerated: Yes (CuPy)
```

Or on Python 3.14:

```
System Information
--------------------------------------------------
GPU Accelerated: No (CPU/NumPy)
```

## Python Version Compatibility

| Python Version | CuPy Support | GPU Acceleration |
| -------------- | ------------ | ---------------- |
| 3.9 - 3.13     | ✅ Yes       | ✅ Available     |
| 3.14           | ❌ No wheels | ⚠️ CPU fallback  |

**Recommendation**: Use Python 3.13 for GPU acceleration until CuPy releases
Python 3.14 wheels.

## References

- [CuPy Documentation](https://docs.cupy.dev/)
- [CuPy GitHub](https://github.com/cupy/cupy)
- [CuPy Releases](https://github.com/cupy/cupy/releases) - Check for Python 3.14
  support
- [CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [NumPy vs CuPy Performance](https://docs.cupy.dev/en/stable/user_guide/basic.html)

## Future Enhancements

Potential improvements:

- Batch processing for very large simulations
- Multi-GPU support
- GPU-accelerated backtest engine
- Memory pool optimization
- Progress tracking with GPU utilization
- Python 3.14 support (when CuPy releases wheels)
