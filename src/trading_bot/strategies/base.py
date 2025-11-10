"""Base strategy class for trading strategies."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, name: str, **kwargs):
        """Initialize strategy.

        Args:
            name: Strategy name
            **kwargs: Strategy-specific parameters
        """
        self.name = name
        self.params = kwargs
        self.positions: dict[str, float] = {}
        self.signals: pd.DataFrame = pd.DataFrame()  # type: ignore[assignment]
        logger.debug(f"Initialized strategy '{name}' with parameters: {kwargs}")

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, **params: Any) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV data
            **params: Optional parameter overrides for optimization

        Returns:
            DataFrame with signals (1 for buy, -1 for sell, 0 for hold)
        """
        pass

    def get_parameter_ranges(self) -> dict[str, list[float]]:
        """Get parameter ranges for optimization.

        Returns:
            Dictionary mapping parameter names to lists of values to test
            Default implementation returns empty dict (no optimization)

        Example:
            >>> return {
            ...     'short_period': [10, 20, 30, 40, 50],
            ...     'long_period': [50, 100, 150, 200]
            ... }
        """
        ranges = {}
        logger.debug(f"Strategy '{self.name}' parameter ranges: {ranges}")
        return ranges

    @abstractmethod
    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size based on risk management.

        Args:
            price: Current price
            account_value: Total account value
            risk_per_trade: Risk percentage per trade

        Returns:
            Position size (number of shares)
        """
        pass

    def should_buy(self, data: pd.DataFrame, index: int) -> bool:  # type: ignore[arg-type]
        """Check if should buy at given index.

        Args:
            data: DataFrame with signals
            index: Index to check

        Returns:
            True if should buy
        """
        if "signal" not in data.columns or index >= len(data):
            logger.debug(f"should_buy: Invalid data or index (index={index}, len={len(data)})")
            return False
        result = data["signal"].iloc[index] == 1
        if result:
            logger.debug(f"should_buy: BUY signal detected at index {index}")
        return result

    def should_sell(self, data: pd.DataFrame, index: int) -> bool:  # type: ignore[arg-type]
        """Check if should sell at given index.

        Args:
            data: DataFrame with signals
            index: Index to check

        Returns:
            True if should sell
        """
        if "signal" not in data.columns or index >= len(data):
            logger.debug(f"should_sell: Invalid data or index (index={index}, len={len(data)})")
            return False
        result = data["signal"].iloc[index] == -1
        if result:
            logger.debug(f"should_sell: SELL signal detected at index {index}")
        return result

    def get_params(self) -> dict[str, Any]:
        """Get strategy parameters."""
        params = {"name": self.name, **self.params}
        logger.debug(f"Strategy '{self.name}' parameters: {params}")
        return params
