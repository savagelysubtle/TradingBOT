"""Dynamic strategy registry for managing available trading strategies."""

import logging
from typing import TYPE_CHECKING

from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.moving_average import MovingAverageCrossover

if TYPE_CHECKING:
    pass  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """Dynamic strategy registry that discovers and manages available strategies."""

    def __init__(self):
        """Initialize strategy registry."""
        self._strategies: dict[str, dict] = {}
        self._load_strategies()

    def _load_strategies(self) -> None:
        """Dynamically load all available strategies."""
        # Base strategies (always available)
        self._register_strategy(
            name="ma_crossover",
            display_name="Simple MA Crossover",
            strategy_class=MovingAverageCrossover,
            available=True,
            category="basic",
        )

        # Stop Hunt Strategy
        try:
            from trading_bot.strategies.stop_hunt_strategy import StopHuntStrategy

            self._register_strategy(
                name="stop_hunt",
                display_name="Stop Hunt Entry",
                strategy_class=StopHuntStrategy,
                available=True,
                category="advanced",
            )
        except ImportError:
            logger.debug("StopHuntStrategy not available")
            # Register as unavailable so it still shows in the list
            self._register_strategy(
                name="stop_hunt",
                display_name="Stop Hunt Entry",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="advanced",
            )

        # TA-Lib MA Crossover
        try:
            from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover

            self._register_strategy(
                name="talib_ma",
                display_name="TA-Lib MA Crossover",
                strategy_class=TALibMovingAverageCrossover,
                available=True,
                category="talib",
            )
        except ImportError:
            logger.debug("TA-Lib MA strategy not available")
            self._register_strategy(
                name="talib_ma",
                display_name="TA-Lib MA Crossover",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="talib",
            )

        # TA-Lib MACD
        try:
            from trading_bot.strategies.ta_lib_strategy import TALibMACDStrategy

            self._register_strategy(
                name="talib_macd",
                display_name="TA-Lib MACD",
                strategy_class=TALibMACDStrategy,
                available=True,
                category="talib",
            )
        except ImportError:
            logger.debug("TA-Lib MACD strategy not available")
            self._register_strategy(
                name="talib_macd",
                display_name="TA-Lib MACD",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="talib",
            )

        # Supertrend
        try:
            from trading_bot.strategies.advanced_indicators import SupertrendStrategy

            self._register_strategy(
                name="supertrend",
                display_name="Supertrend",
                strategy_class=SupertrendStrategy,
                available=True,
                category="advanced",
            )
        except ImportError:
            logger.debug("Supertrend strategy not available")
            self._register_strategy(
                name="supertrend",
                display_name="Supertrend",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="advanced",
            )

        # Bollinger Bands
        try:
            from trading_bot.strategies.advanced_indicators import BollingerBandsStrategy

            self._register_strategy(
                name="bollinger",
                display_name="Bollinger Bands",
                strategy_class=BollingerBandsStrategy,
                available=True,
                category="advanced",
            )
        except ImportError:
            logger.debug("Bollinger Bands strategy not available")
            self._register_strategy(
                name="bollinger",
                display_name="Bollinger Bands",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="advanced",
            )

        # Ichimoku Cloud
        try:
            from trading_bot.strategies.advanced_indicators import IchimokuStrategy

            self._register_strategy(
                name="ichimoku",
                display_name="Ichimoku Cloud",
                strategy_class=IchimokuStrategy,
                available=True,
                category="advanced",
            )
        except ImportError:
            logger.debug("Ichimoku strategy not available")
            self._register_strategy(
                name="ichimoku",
                display_name="Ichimoku Cloud",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="advanced",
            )

        # ML Random Forest
        try:
            from trading_bot.strategies.ml_strategy import MLRandomForestStrategy

            self._register_strategy(
                name="ml_randomforest",
                display_name="ML Random Forest",
                strategy_class=MLRandomForestStrategy,
                available=True,
                category="ml",
            )
        except ImportError:
            logger.debug("ML Random Forest strategy not available")
            self._register_strategy(
                name="ml_randomforest",
                display_name="ML Random Forest",
                strategy_class=None,  # type: ignore[arg-type]
                available=False,
                category="ml",
            )

    def _register_strategy(
        self,
        name: str,
        display_name: str,
        strategy_class: type[BaseStrategy] | None,
        available: bool,
        category: str,
    ) -> None:
        """Register a strategy in the registry.

        Args:
            name: Internal strategy name (e.g., "ma_crossover")
            display_name: Display name for UI (e.g., "Simple MA Crossover")
            strategy_class: Strategy class (None if unavailable)
            available: Whether strategy is available
            category: Strategy category (basic, talib, advanced, ml)
        """
        self._strategies[name] = {
            "display_name": display_name,
            "class": strategy_class,
            "available": available,
            "category": category,
        }

    def get_strategies_list(self) -> list[tuple[str, str]]:
        """Get list of strategies for dropdown.

        Returns:
            List of tuples (display_name, internal_name)
        """
        strategies = []
        for name, info in sorted(self._strategies.items()):
            display = info["display_name"]
            if not info["available"]:
                # Add requirement indicator
                if info["category"] == "talib":
                    display += " (req TA-Lib)"
                elif info["category"] == "ml":
                    display += " (req scikit-learn)"
                elif info["category"] == "advanced":
                    display += " (req TA-Lib)"
            strategies.append((display, name))
        return strategies

    def get_strategy_class(self, name: str) -> type[BaseStrategy] | None:
        """Get strategy class by name.

        Args:
            name: Internal strategy name

        Returns:
            Strategy class or None if not found
        """
        strategy_info = self._strategies.get(name)
        if strategy_info and strategy_info["available"]:
            return strategy_info["class"]
        return None

    def is_available(self, name: str) -> bool:
        """Check if strategy is available.

        Args:
            name: Internal strategy name

        Returns:
            True if strategy is available
        """
        strategy_info = self._strategies.get(name)
        return strategy_info is not None and strategy_info["available"]

    def get_display_name(self, name: str) -> str:
        """Get display name for strategy.

        Args:
            name: Internal strategy name

        Returns:
            Display name or name if not found
        """
        strategy_info = self._strategies.get(name)
        return strategy_info["display_name"] if strategy_info else name


# Global strategy registry instance
_strategy_registry = StrategyRegistry()
