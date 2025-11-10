"""Base broker interface."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseBroker(ABC):
    """Base class for broker interfaces."""

    @abstractmethod
    def get_account(self) -> dict:
        """Get account information.

        Returns:
            Dictionary with account details (cash, equity, etc.)
        """
        pass

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """Get current positions.

        Returns:
            List of position dictionaries
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        price: float | None = None,
    ) -> dict:
        """Place an order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares (positive for buy, negative for sell)
            side: 'buy' or 'sell'
            order_type: Order type ('market', 'limit', etc.)
            price: Limit price (required for limit orders)

        Returns:
            Order confirmation dictionary
        """
        pass

    @abstractmethod
    def get_market_data(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:  # type: ignore[return]
        """Get market data.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation confirmation
        """
        pass

