"""Base strategy class for trading strategies."""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


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

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals (1 for buy, -1 for sell, 0 for hold)
        """
        pass

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
            return False
        return data["signal"].iloc[index] == 1

    def should_sell(self, data: pd.DataFrame, index: int) -> bool:  # type: ignore[arg-type]
        """Check if should sell at given index.

        Args:
            data: DataFrame with signals
            index: Index to check

        Returns:
            True if should sell
        """
        if "signal" not in data.columns or index >= len(data):
            return False
        return data["signal"].iloc[index] == -1

    def get_params(self) -> dict[str, Any]:
        """Get strategy parameters."""
        return {"name": self.name, **self.params}
