"""Diagnostic script to check why strategies aren't generating trades.

Run this to diagnose why your backtests show 0 trades.

Usage:
    uv run --python 3.14 python examples/diagnose_signals.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.strategies.moving_average import MovingAverageCrossover

def main():
    """Run diagnostics on signal generation."""
    print("=" * 60)
    print("Signal Generation Diagnostic")
    print("=" * 60)

    # Fetch data
    print("\n1. Fetching data...")
    fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=False, use_cache=False)
    data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=365)

    print(f"   ✓ Fetched {len(data)} candles")
    print(f"   Date range: {data.index[0]} to {data.index[-1]}")
    print(f"   Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

    # Create strategy
    print("\n2. Creating strategy...")
    strategy = MovingAverageCrossover(short_window=50, long_window=200, use_rsi=False)
    print(f"   Strategy: {strategy.name}")
    print(f"   Short MA: {strategy.short_window} periods")
    print(f"   Long MA: {strategy.long_window} periods")

    # Generate signals
    print("\n3. Generating signals...")
    signals_df = strategy.generate_signals(data)

    # Check for signals
    buy_signals = signals_df[signals_df["signal"] == 1]
    sell_signals = signals_df[signals_df["signal"] == -1]

    print(f"   Total candles: {len(signals_df)}")
    print(f"   Buy signals: {len(buy_signals)}")
    print(f"   Sell signals: {len(sell_signals)}")

    # Check MA calculation
    print("\n4. Checking moving averages...")
    ma_short_valid = signals_df["ma_short"].notna().sum()
    ma_long_valid = signals_df["ma_long"].notna().sum()
    print(f"   Short MA valid values: {ma_short_valid} / {len(signals_df)}")
    print(f"   Long MA valid values: {ma_long_valid} / {len(signals_df)}")

    if ma_short_valid < strategy.short_window:
        print(f"   ⚠ WARNING: Need {strategy.short_window} candles for short MA, only have {ma_short_valid}")

    if ma_long_valid < strategy.long_window:
        print(f"   ⚠ WARNING: Need {strategy.long_window} candles for long MA, only have {ma_long_valid}")

    # Show first few signals
    if len(buy_signals) > 0:
        print("\n5. First few buy signals:")
        for idx, row in buy_signals.head(5).iterrows():
            print(f"   {idx}: Price=${row['close']:.2f}, Short MA=${row['ma_short']:.2f}, Long MA=${row['ma_long']:.2f}")

    if len(sell_signals) > 0:
        print("\n6. First few sell signals:")
        for idx, row in sell_signals.head(5).iterrows():
            print(f"   {idx}: Price=${row['close']:.2f}, Short MA=${row['ma_short']:.2f}, Long MA=${row['ma_long']:.2f}")

    # Check crossover conditions
    print("\n7. Checking crossover logic...")
    # Check if short MA ever crosses above long MA
    crossovers_above = (
        (signals_df["ma_short"] > signals_df["ma_long"]) &
        (signals_df["ma_short"].shift(1) <= signals_df["ma_long"].shift(1))
    ).sum()

    crossovers_below = (
        (signals_df["ma_short"] < signals_df["ma_long"]) &
        (signals_df["ma_short"].shift(1) >= signals_df["ma_long"].shift(1))
    ).sum()

    print(f"   Crossovers (short above long): {crossovers_above}")
    print(f"   Crossovers (short below long): {crossovers_below}")

    # Show MA relationship over time
    print("\n8. MA relationship summary:")
    short_above_long = (signals_df["ma_short"] > signals_df["ma_long"]).sum()
    short_below_long = (signals_df["ma_short"] < signals_df["ma_long"]).sum()
    print(f"   Periods where short MA > long MA: {short_above_long}")
    print(f"   Periods where short MA < long MA: {short_below_long}")

    # Recommendations
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)

    if len(data) < strategy.long_window:
        print(f"❌ PROBLEM: Not enough data! Need at least {strategy.long_window} candles")
        print(f"   Current: {len(data)} candles")
        print(f"   Solution: Increase limit to at least {strategy.long_window + 50}")
    elif len(buy_signals) == 0 and len(sell_signals) == 0:
        print("❌ PROBLEM: No signals generated!")
        if crossovers_above == 0 and crossovers_below == 0:
            print("   Reason: No MA crossovers detected")
            print("   Possible causes:")
            print("   - Not enough price movement for crossovers")
            print("   - MA periods too long for the data timeframe")
            print("   - Try shorter MA periods (e.g., 10/30 instead of 50/200)")
        else:
            print(f"   Found {crossovers_above} crossovers but no signals generated")
            print("   This suggests a bug in signal generation logic")
    elif len(buy_signals) > 0 or len(sell_signals) > 0:
        print(f"✓ Signals are being generated ({len(buy_signals)} buys, {len(sell_signals)} sells)")
        print("   If backtest shows 0 trades, check backtesting engine logic")

    print("\n" + "=" * 60)
    print("\nRECOMMENDATIONS:")
    print("=" * 60)
    print(f"For {len(data)} candles with {strategy.short_window}/{strategy.long_window} MA:")
    print(f"  • Short MA: {max(10, int(len(data) * 0.05))} - {max(20, int(len(data) * 0.1))}")
    print(f"  • Long MA: {max(30, int(len(data) * 0.15))} - {max(50, int(len(data) * 0.3))}")
    print(f"  • Or increase candles to: {strategy.long_window + 100}+")

if __name__ == "__main__":
    main()

