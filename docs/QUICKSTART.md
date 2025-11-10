# Quick Start Guide

Get started with the Trading Bot in 5 minutes!

## Step 1: Install Dependencies

```bash
uv sync
```

## Step 2: Run Your First Backtest

Test the Moving Average Crossover strategy on Apple stock:

```bash
uv run python -m trading_bot.cli backtest --symbol AAPL --period 1y
```

This will:
- Download historical data for AAPL
- Run the MA Crossover strategy (50/200 day moving averages)
- Generate performance metrics
- Save results to `results/` directory

## Step 3: Try Different Parameters

Experiment with different moving average windows:

```bash
# Fast MA crossover (20/50 days)
uv run python -m trading_bot.cli backtest --symbol TSLA --short-window 20 --long-window 50 --period 2y

# Slow MA crossover (100/200 days)
uv run python -m trading_bot.cli backtest --symbol MSFT --short-window 100 --long-window 200 --period 1y
```

## Step 4: Paper Trading

Test your strategy with simulated trading:

```bash
uv run python -m trading_bot.cli paper --symbol AAPL
```

## Step 5: View Results

Check the `results/` directory for:
- `summary.txt` - Performance summary
- `trades.csv` - All executed trades
- `portfolio_history.csv` - Portfolio value over time

## Next Steps

1. **Create Custom Strategies**: Extend `BaseStrategy` class to implement your own trading logic
2. **Add More Indicators**: Use the `ta` library to add technical indicators
3. **Connect Live Broker**: Implement a broker interface for live trading (Alpaca, Interactive Brokers, etc.)
4. **Optimize Parameters**: Use backtesting to find optimal strategy parameters

## Example Python Script

You can also use the bot programmatically:

```python
from trading_bot.bot import TradingBot
from trading_bot.strategies.moving_average import MovingAverageCrossover

# Initialize bot
bot = TradingBot()

# Create strategy
strategy = MovingAverageCrossover(short_window=50, long_window=200)

# Run backtest
results = bot.backtest(strategy, symbol="AAPL", period="1y")

print(f"Total Return: {results['total_return_pct']:.2f}%")
print(f"Win Rate: {results['win_rate_pct']:.2f}%")
```

## Common Issues

**Problem**: `ModuleNotFoundError: No module named 'trading_bot'`
**Solution**: Make sure you're running from the project root and using `uv run`

**Problem**: Data download fails
**Solution**: Check your internet connection and try again. Data is cached after first download.

**Problem**: No trades executed
**Solution**: Adjust strategy parameters or try a different time period

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review example scripts in the `examples/` directory
- Check logs in the `logs/` directory for debugging

Happy Trading! 🚀

