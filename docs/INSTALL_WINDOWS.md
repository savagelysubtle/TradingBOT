# Windows Installation Guide for Python 3.14

## Quick Install (Recommended)

Since `coincurve` (a dependency of `ccxt`) has build issues on Windows with Python 3.14, follow these steps:

### Step 1: Create Virtual Environment with Python 3.14

```powershell
uv venv --python 3.14
.venv\Scripts\activate
```

### Step 2: Install Dependencies (Skip coincurve)

```powershell
# Install core dependencies
uv pip install --python .venv\Scripts\python.exe pandas numpy backtrader python-dotenv pydantic pydantic-settings rich click

# Install ccxt without coincurve (coincurve is optional)
uv pip install --python .venv\Scripts\python.exe ccxt --no-deps
uv pip install --python .venv\Scripts\python.exe requests aiohttp certifi
```

### Step 3: Install TA-Lib (Optional but Recommended)

**Option A: Using Conda (Easiest)**

```powershell
# If you have conda installed
conda install -c conda-forge ta-lib
```

**Option B: Manual Installation**

1. Download TA-Lib from: https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-msvc.zip
2. Extract to `C:\ta-lib`
3. Add to environment variables:
   - `INCLUDE`: Add `C:\ta-lib\c\include`
   - `LIB`: Add `C:\ta-lib\c\lib`
4. Install Python wrapper:
   ```powershell
   uv pip install --python .venv\Scripts\python.exe TA-Lib
   ```

### Step 4: Verify Installation

```powershell
.venv\Scripts\python.exe -c "import ccxt, backtrader, pandas, numpy; print('✓ Core libraries installed')"
.venv\Scripts\python.exe -c "import talib; print('✓ TA-Lib installed')"  # Optional
```

## Alternative: Use uv sync with Python 3.14

If you want to use `uv sync`, you need to specify the Python interpreter:

```powershell
# Activate venv first
.venv\Scripts\activate

# Use the venv Python explicitly
uv sync --python .venv\Scripts\python.exe
```

However, this may fail due to `coincurve` build issues. If it does, use the manual installation method above.

## Troubleshooting

### Issue: "coincurve build failed"

**Solution**: `coincurve` is optional for `ccxt`. Install `ccxt` without dependencies and manually install what's needed:

```powershell
uv pip install --python .venv\Scripts\python.exe ccxt --no-deps
uv pip install --python .venv\Scripts\python.exe requests aiohttp certifi
```

### Issue: "TA-Lib not found"

**Solution**: TA-Lib requires the C library first. See Step 3 above.

### Issue: "Python 3.13 detected instead of 3.14"

**Solution**: Always specify the Python interpreter:

```powershell
uv pip install --python .venv\Scripts\python.exe <package>
```

Or activate the venv first:

```powershell
.venv\Scripts\activate
python --version  # Should show 3.14.0
```

## What Works Without coincurve

`ccxt` works perfectly fine without `coincurve`. The `coincurve` dependency is only needed for:
- ECDSA signature verification (optional)
- Some advanced cryptographic features

For basic trading and data fetching, `ccxt` works without it.

## Verify Everything Works

```powershell
.venv\Scripts\python.exe examples\quick_start_live.py
```

This should fetch live data and run a backtest!

