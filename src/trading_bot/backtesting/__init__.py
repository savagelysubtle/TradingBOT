"""Backtesting module for strategy evaluation."""

from trading_bot.backtesting.engine import BacktestEngine

# Try to import Backtrader engine (optional dependency)
try:
    from trading_bot.backtesting.backtrader_engine import BacktraderEngine

    BACKTRADER_AVAILABLE = True
except ImportError:
    BacktraderEngine = None  # type: ignore[assignment, misc]
    BACKTRADER_AVAILABLE = False

# Try to import VectorBT engine (optional dependency)
try:
    from trading_bot.backtesting.vectorbt_engine import VectorBTEngine

    VECTORBT_AVAILABLE = True
except ImportError:
    VectorBTEngine = None  # type: ignore[assignment, misc]
    VECTORBT_AVAILABLE = False

# Build __all__ based on what's available
__all__ = ["BacktestEngine"]
if BACKTRADER_AVAILABLE:
    __all__.append("BacktraderEngine")
if VECTORBT_AVAILABLE:
    __all__.append("VectorBTEngine")
