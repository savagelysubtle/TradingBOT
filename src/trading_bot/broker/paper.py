"""Paper trading broker implementation."""

import logging
from datetime import datetime

import pandas as pd

from trading_bot.broker.base import BaseBroker
from trading_bot.data.fetcher import DataFetcher

logger = logging.getLogger(__name__)


class PaperBroker(BaseBroker):
    """Paper trading broker (simulated trading)."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        data_fetcher: DataFetcher | None = None,
    ):
        """Initialize paper broker.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
            slippage: Slippage rate per trade
            data_fetcher: Data fetcher instance
        """
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.positions: dict[str, float] = {}  # symbol -> shares
        self.orders: list[dict] = []
        self.data_fetcher = data_fetcher or DataFetcher()

    def get_account(self) -> dict:
        """Get account information."""
        total_value = self.cash
        for symbol, shares in self.positions.items():
            if shares > 0:
                try:
                    price = self.data_fetcher.get_latest_price(symbol)
                    total_value += shares * price
                except Exception as e:
                    logger.warning(f"Could not get price for {symbol}: {e}")

        return {
            "cash": self.cash,
            "equity": total_value,
            "buying_power": self.cash,
            "initial_capital": self.initial_capital,
        }

    def get_positions(self) -> list[dict]:
        """Get current positions."""
        positions = []
        for symbol, shares in self.positions.items():
            if shares != 0:
                try:
                    price = self.data_fetcher.get_latest_price(symbol)
                    positions.append(
                        {
                            "symbol": symbol,
                            "quantity": shares,
                            "avg_price": price,  # Simplified
                            "market_value": shares * price,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Could not get price for {symbol}: {e}")
        return positions

    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        price: float | None = None,
    ) -> dict:
        """Place an order."""
        if order_type == "limit" and price is None:
            raise ValueError("Limit orders require a price")

        # Get current price
        current_price = price or self.data_fetcher.get_latest_price(symbol)

        # Apply slippage
        if side.lower() == "buy":
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)

        # Calculate costs
        if side.lower() == "buy":
            cost = quantity * execution_price * (1 + self.commission)
            if cost > self.cash:
                raise ValueError(f"Insufficient funds. Need ${cost:.2f}, have ${self.cash:.2f}")

            self.cash -= cost
            self.positions[symbol] = self.positions.get(symbol, 0) + quantity
            logger.info(
                f"BOUGHT {quantity:.2f} {symbol} @ ${execution_price:.2f} "
                f"(Cost: ${cost:.2f}, Cash: ${self.cash:.2f})",
            )

        else:  # sell
            current_shares = self.positions.get(symbol, 0)
            if quantity > current_shares:
                raise ValueError(
                    f"Insufficient shares. Trying to sell {quantity}, have {current_shares}",
                )

            proceeds = quantity * execution_price * (1 - self.commission)
            self.cash += proceeds
            self.positions[symbol] = current_shares - quantity
            if self.positions[symbol] == 0:
                del self.positions[symbol]

            logger.info(
                f"SOLD {quantity:.2f} {symbol} @ ${execution_price:.2f} "
                f"(Proceeds: ${proceeds:.2f}, Cash: ${self.cash:.2f})",
            )

        order = {
            "id": f"order_{len(self.orders)}",
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "price": execution_price,
            "status": "filled",
            "timestamp": datetime.now().isoformat(),
        }

        self.orders.append(order)
        return order

    def get_market_data(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:  # type: ignore[return]
        """Get market data."""
        return self.data_fetcher.fetch_ohlcv(
            symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an order (not implemented for paper trading)."""
        logger.warning("Order cancellation not implemented for paper trading")
        return {"status": "cancelled", "order_id": order_id}
