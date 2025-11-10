# Installation Guide

## Prerequisites

- **Python 3.14** or higher (required for free-threading/multi-threading support)
- **UV** package manager
- **TA-Lib C Library** (required before installing Python TA-Lib wrapper)

## Step 1: Install Python 3.14

Python 3.14 introduces free-threading (no GIL) support, enabling true parallelism.

### Windows
```powershell
# Using winget
winget install Python.Python.3.14

# Or download from python.org
# https://www.python.org/downloads/release/python-3140/
```

### macOS
```bash
# Using Homebrew
brew install python@3.14

# Or download from python.org
```

### Linux
```bash
# Download and compile from source
# https://www.python.org/downloads/release/python-3140/
```

## Step 2: Install TA-Lib C Library

**IMPORTANT**: You must install the TA-Lib C library before installing the Python wrapper.

### Windows

1. Download TA-Lib from: https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-msvc.zip
2. Extract to `C:\ta-lib`
3. Add `C:\ta-lib\c\include` to your `INCLUDE` environment variable
4. Add `C:\ta-lib\c\lib` to your `LIB` environment variable

Or use conda:
```powershell
conda install -c conda-forge ta-lib
```

### macOS
```bash
brew install ta-lib
```

### Linux (Ubuntu/Debian)
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

## Step 3: Install Project Dependencies

```bash
# Install dependencies using UV
uv sync

# Or install manually
uv add pandas numpy ccxt backtrader TA-Lib python-dotenv pydantic pydantic-settings rich click
```

## Step 4: Verify Installation

```bash
# Check Python version (should be 3.14+)
python --version

# Verify TA-Lib installation
python -c "import talib; print('TA-Lib version:', talib.__version__)"

# Verify CCXT installation
python -c "import ccxt; print('CCXT version:', ccxt.__version__)"

# Verify Backtrader installation
python -c "import backtrader; print('Backtrader installed successfully')"
```

## Troubleshooting

### TA-Lib Installation Issues

**Windows**: If you get "Microsoft Visual C++ 14.0 is required":
- Install Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
- Or use conda: `conda install -c conda-forge ta-lib`

**macOS**: If you get "library not found":
```bash
export DYLD_LIBRARY_PATH=/usr/local/lib:$DYLD_LIBRARY_PATH
```

**Linux**: If you get "ta_lib.h: No such file or directory":
```bash
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
```

### Python 3.14 Not Found

Make sure Python 3.14 is in your PATH:
```bash
# Windows
python --version

# If not found, add Python 3.14 to PATH manually
```

### CCXT Exchange Connection Issues

Some exchanges require API keys even for public data:
```python
# Set sandbox=True for testing
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)
```

## Next Steps

After installation, see [QUICKSTART.md](QUICKSTART.md) to run your first backtest!

