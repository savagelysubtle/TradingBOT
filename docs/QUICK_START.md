# Quick Start Guide

## Launch the TUI

After installing the package, you can launch the TUI in several ways:

### Method 1: Using the `tui` command (After venv activation)

```bash
# Activate virtual environment
.venv\Scripts\activate

# Launch TUI
tui
```

### Method 2: Using uv run

```bash
# Launch TUI with uv (specify Python 3.14)
uv run --python .venv\Scripts\python.exe tui
```

### Method 3: Using Python module

```bash
# Activate venv first
.venv\Scripts\activate

# Then run
python -m trading_bot.cli tui
```

### Method 4: Direct script execution

```bash
# Activate venv first
.venv\Scripts\activate

# Run the script directly
python examples/run_tui.py
```

## Install Package in Editable Mode

To use the `tui` command, install the package in editable mode:

```bash
uv pip install --python .venv\Scripts\python.exe -e .
```

This creates the `tui` command in your virtual environment's Scripts folder.

## Quick Commands Reference

| Command                       | Description                    |
| ----------------------------- | ------------------------------ |
| `tui`                         | Launch the Text User Interface |
| `trading-bot backtest`        | Run a backtest via CLI         |
| `trading-bot list-strategies` | List available strategies      |

## Troubleshooting

### "tui: command not found"

Make sure you:

1. Installed the package in editable mode:
   `uv pip install --python .venv\Scripts\python.exe -e .`
2. Activated the virtual environment: `.venv\Scripts\activate`

### "Python 3.13 detected"

Always specify Python 3.14:

```bash
uv run --python .venv\Scripts\python.exe tui
```
