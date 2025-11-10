"""Backtesting module for strategy evaluation."""

from trading_bot.backtesting.backtrader_engine import BacktraderEngine
from trading_bot.backtesting.engine import BacktestEngine

# Try to import VectorBT engine (optional dependency)
try:
    from trading_bot.backtesting.vectorbt_engine import VectorBTEngine

    __all__ = ["BacktestEngine", "BacktraderEngine", "VectorBTEngine"]
except ImportError:
    __all__ = ["BacktestEngine", "BacktraderEngine"]

