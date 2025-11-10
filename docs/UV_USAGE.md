# Using UV with Python 3.14

Since your project requires Python 3.14, you need to tell `uv` which Python to use.

## Launching the TUI with UV

### Method 1: Specify Python 3.14 explicitly (Recommended)

```bash
# Use the Python from your venv
uv run --python .venv\Scripts\python.exe -m trading_bot.cli tui
```

### Method 2: Activate venv first, then use uv

```bash
# Activate the virtual environment
.venv\Scripts\activate

# Now uv will use the venv Python
uv run -m trading_bot.cli tui
```

### Method 3: Use Python directly (after venv activation)

```bash
# Activate venv
.venv\Scripts\activate

# Use Python directly
python -m trading_bot.cli tui
```

## Other Commands with UV

### Backtest

```bash
# With explicit Python
uv run --python .venv\Scripts\python.exe -m trading_bot.cli backtest --symbol BTC/USDT --exchange binance --strategy talib_ma

# Or after venv activation
uv run -m trading_bot.cli backtest --symbol BTC/USDT --exchange binance --strategy talib_ma
```

### Run Examples

```bash
# With explicit Python
uv run --python .venv\Scripts\python.exe examples/quick_start_live.py

# Or after venv activation
uv run examples/quick_start_live.py
```

## Why This Happens

`uv run` by default looks for Python in your system PATH, which might be Python 3.13. Since your project requires Python 3.14, you need to:

1. **Specify the Python explicitly**: `--python .venv\Scripts\python.exe`
2. **Or activate the venv first**: This adds the venv Python to PATH

## Quick Reference

| Command | With UV (Python 3.14) |
|---------|----------------------|
| Launch TUI | `uv run --python .venv\Scripts\python.exe -m trading_bot.cli tui` |
| Run Backtest | `uv run --python .venv\Scripts\python.exe -m trading_bot.cli backtest ...` |
| Run Example | `uv run --python .venv\Scripts\python.exe examples/quick_start_live.py` |

## Pro Tip: Create Aliases

You can create a batch file or PowerShell alias:

**Windows PowerShell** (add to your profile):
```powershell
function uv-tui { uv run --python .venv\Scripts\python.exe -m trading_bot.cli tui }
function uv-backtest { uv run --python .venv\Scripts\python.exe -m trading_bot.cli backtest $args }
```

Then use:
```powershell
uv-tui
uv-backtest --symbol BTC/USDT --exchange binance --strategy talib_ma
```

