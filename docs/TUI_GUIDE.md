# Trading Bot TUI Guide

## Overview

The Trading Bot now includes a beautiful Text User Interface (TUI) built with `textual` for an interactive, terminal-based experience.

## Launching the TUI

### Method 1: Using UV (Recommended)

```bash
# Launch TUI with uv (specify Python 3.14 from venv)
uv run --python .venv\Scripts\python.exe -m trading_bot.cli tui

# Or activate venv first, then use uv
.venv\Scripts\activate
uv run -m trading_bot.cli tui
```

### Method 2: Using Python (if venv is activated)

```bash
# Activate virtual environment first
.venv\Scripts\activate

# Then launch TUI
python -m trading_bot.cli tui
```

### Method 3: Direct Python Script

```bash
# With uv
uv run examples/run_tui.py

# Or with Python (if venv activated)
python examples/run_tui.py
```

## TUI Features

### Dashboard Tab
- Quick actions for common tasks
- System status indicators
- Python 3.14 free-threading status
- Exchange connection status

### Data Fetch Tab
- **Exchange Selection**: Choose from Binance, Coinbase, Kraken
- **Symbol Input**: Enter trading pairs (e.g., BTC/USDT)
- **Timeframe Selection**: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- **Limit Setting**: Number of candles to fetch
- **Live Data Preview**: View fetched data in a table
- **Real-time Logging**: See fetch progress and results

### Backtest Tab
- **Strategy Selection**: Choose from available strategies
  - TA-Lib Moving Average
  - TA-Lib MACD
  - Simple MA Crossover
- **Configuration**: Set MA periods, symbol, exchange, timeframe
- **Engine Selection**: Backtrader or Custom engine
- **Results Display**: View backtest results in real-time
- **Detailed Logging**: Monitor backtest progress

### Strategies Tab
- View all available strategies
- See strategy descriptions and indicators
- Check strategy status

### Results Tab
- View detailed backtest results
- Performance metrics
- Trade statistics

## Keyboard Shortcuts

- `Q` - Quit the application
- `D` - Toggle dark mode
- `R` - Refresh current view
- `Tab` - Navigate between tabs
- `Enter` - Activate buttons/inputs
- Arrow keys - Navigate tables and lists

## Usage Example

1. **Launch TUI**:
   ```bash
   python -m trading_bot.cli tui
   ```

2. **Fetch Live Data**:
   - Go to "Data Fetch" tab
   - Select exchange: Binance
   - Enter symbol: BTC/USDT
   - Select timeframe: 1d
   - Set limit: 365
   - Click "Fetch Data"
   - View results in the data table

3. **Run Backtest**:
   - Go to "Backtest" tab
   - Select strategy: TA-Lib Moving Average
   - Enter symbol: BTC/USDT
   - Set Short MA: 50
   - Set Long MA: 200
   - Select engine: Backtrader
   - Click "Run Backtest"
   - View results in the results panel

## Tips

- **Dark Mode**: Press `D` to toggle between light and dark themes
- **Multiple Tabs**: Use `Tab` key to switch between different tabs
- **Data Tables**: Use arrow keys to navigate through data
- **Logs**: Check the log panels at the bottom for detailed information

## Troubleshooting

### TUI Not Starting

If you get an import error:
```bash
uv pip install --python .venv\Scripts\python.exe textual
```

### Data Not Fetching

- Check your internet connection
- Verify exchange name is correct
- Ensure symbol format is correct (e.g., BTC/USDT not BTCUSDT)
- Check the log panel for error messages

### Backtest Failing

- Ensure TA-Lib is installed if using TA-Lib strategies
- Check symbol format
- Verify exchange supports the symbol
- Review log panel for detailed errors

## Screenshots

The TUI features:
- Clean, modern interface
- Color-coded status indicators
- Interactive tables and forms
- Real-time logging
- Responsive layout

## Advanced Usage

### Custom Styling

You can customize the TUI appearance by modifying `src/trading_bot/tui.css` (if you enable CSS_PATH).

### Extending the TUI

The TUI is built with `textual` and can be extended:
- Add new tabs
- Create custom widgets
- Add more features

See [Textual Documentation](https://textual.textualize.io/) for more information.

## Next Steps

1. **Explore the Dashboard**: Get familiar with the interface
2. **Fetch Some Data**: Try fetching data for different symbols
3. **Run Backtests**: Test different strategies and parameters
4. **Analyze Results**: Review backtest results in the Results tab

Enjoy your interactive trading bot experience! 🚀

