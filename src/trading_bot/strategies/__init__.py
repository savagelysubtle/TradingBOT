"""Trading strategies module."""

from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.moving_average import MovingAverageCrossover
from trading_bot.strategies.stop_hunt_strategy import StopHuntStrategy
from trading_bot.strategies.strategy_registry import StrategyRegistry

# Try to import TA-Lib strategies (optional dependency)
try:
    from trading_bot.strategies.ta_lib_strategy import (
        TALibMACDStrategy,
        TALibMovingAverageCrossover,
    )
    from trading_bot.strategies.advanced_indicators import (
        BollingerBandsStrategy,
        IchimokuStrategy,
        SupertrendStrategy,
    )

    __all__ = [
        "BaseStrategy",
        "MovingAverageCrossover",
        "StopHuntStrategy",
        "StrategyRegistry",
        "TALibMovingAverageCrossover",
        "TALibMACDStrategy",
        "SupertrendStrategy",
        "BollingerBandsStrategy",
        "IchimokuStrategy",
    ]
except ImportError:
    # TA-Lib not installed, only export base strategies
    __all__ = [
        "BaseStrategy",
        "MovingAverageCrossover",
        "StopHuntStrategy",
        "StrategyRegistry",
    ]

# Try to import ML strategies (optional dependency)
try:
    from trading_bot.strategies.ml_strategy import MLRandomForestStrategy

    __all__.append("MLRandomForestStrategy")
except ImportError:
    pass

