# Backtesting Troubleshooting Guide

## Problem: No Trades Generated (0 trades, 0 wins, 0 losses)

If your backtest shows 0 trades, this is usually due to **insufficient data** or **MA periods that are too long** for your dataset.

### Root Cause

Moving Average strategies require:
- **Enough historical data** to calculate the indicators
- **Price movement** that creates crossovers between short and long MAs

### Common Scenarios

#### Scenario 1: MA Periods Too Long for Data

**Example:**
- Data: 365 hourly candles
- Strategy: 50/200 MA periods
- Result: Only 166 valid periods for 200-period MA, no crossovers

**Solution:**
- Use shorter MA periods (e.g., 10/30 for hourly data)
- OR increase data limit (e.g., 500-1000 candles)
- OR use daily timeframe instead of hourly

#### Scenario 2: Not Enough Price Movement

**Example:**
- Data: 365 daily candles
- Strategy: 50/200 MA periods
- Result: Price stayed in range, no crossovers occurred

**Solution:**
- Use shorter MA periods to catch smaller trends
- Try different timeframes (e.g., 4h instead of 1d)
- Select a different date range with more volatility

### Recommended MA Periods by Timeframe

| Timeframe | Short MA | Long MA | Min Candles |
|-----------|----------|---------|-------------|
| 1m, 5m    | 10-20    | 30-50   | 100+        |
| 15m       | 10-20    | 30-50   | 100+        |
| 1h        | 10-20    | 30-50   | 200+        |
| 4h        | 20-30    | 50-100  | 300+        |
| 1d        | 50       | 200     | 500+        |
| 1w        | 10-20    | 50-100  | 200+        |

### Quick Fixes

1. **For Hourly Data (1h):**
   - Change Short MA: 50 → **10**
   - Change Long MA: 200 → **30**
   - Increase Candles: 365 → **500**

2. **For Daily Data (1d):**
   - Keep Short MA: 50
   - Keep Long MA: 200
   - Increase Candles: 365 → **500-1000**

3. **For Testing:**
   - Use very short periods: Short=5, Long=15
   - Use 200+ candles
   - This will generate more signals for testing

### Validation in TUI

The TUI now includes validation that:
- Warns if MA periods are too large relative to data
- Suggests appropriate periods based on your data limit
- Blocks backtests if periods exceed available data

### Diagnostic Script

Run the diagnostic script to check your setup:

```bash
uv run --python 3.14 python diagnose_signals.py
```

This will show:
- How many candles were fetched
- How many valid MA periods are available
- Whether any crossovers were detected
- Recommendations for fixing the issue

### Understanding Results

**Good Setup:**
- ✓ At least 2x more candles than long MA period
- ✓ Short MA < Long MA
- ✓ Multiple crossovers detected
- ✓ Trades generated

**Problem Setup:**
- ✗ Long MA period >= number of candles
- ✗ Only a few valid MA periods
- ✗ No crossovers detected
- ✗ 0 trades generated

### Example: Fixing a Failed Backtest

**Original (Failed):**
- Timeframe: 1h
- Candles: 365
- Short MA: 50
- Long MA: 200
- Result: 0 trades

**Fixed:**
- Timeframe: 1h
- Candles: 500
- Short MA: 10
- Long MA: 30
- Result: Multiple trades generated

### Still Having Issues?

1. Check the diagnostic script output
2. Verify data is being fetched correctly (check `data/` folder)
3. Try a different symbol (some have more volatility)
4. Try a different timeframe
5. Check logs in `logs/trading_bot.log` for errors

