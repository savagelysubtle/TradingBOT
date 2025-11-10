"""Paper trading broker implementation."""

import logging
from datetime import datetime

import pandas as pd

from trading_bot.broker.base import BaseBroker
from trading_bot.data.fetcher import DataFetcher
from trading_bot.risk.kelly_criterion import (
    KellyMetrics,
    fractional_kelly,
    kelly_criterion,
    kelly_to_position_units,
)

logger = logging.getLogger(__name__)


class PaperBroker(BaseBroker):
    """Paper trading broker (simulated trading)."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        data_fetcher: DataFetcher | None = None,
        kelly_fraction: float = 0.5,
        max_risk_pct: float = 0.05,
        kelly_metrics: KellyMetrics | None = None,
    ):
        """Initialize paper broker.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
            slippage: Slippage rate per trade
            data_fetcher: Data fetcher instance
            kelly_fraction: Fraction of Kelly to use (0.25=Quarter, 0.5=Half, 1.0=Full)
            max_risk_pct: Maximum risk % per trade (default: 0.05 = 5%)
            kelly_metrics: Kelly metrics from backtest (optional, for position sizing)
        """
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.positions: dict[str, float] = {}  # symbol -> shares
        self.orders: list[dict] = []
        self.data_fetcher = data_fetcher or DataFetcher()
        self.kelly_fraction = kelly_fraction
        self.max_risk_pct = max_risk_pct
        self.kelly_metrics = kelly_metrics

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

    def update_kelly_metrics(self, metrics: KellyMetrics) -> None:
        """Update Kelly metrics from recent trades.

        Args:
            metrics: Kelly metrics from backtest or recent trades
        """
        self.kelly_metrics = metrics
        logger.info(
            f"Updated Kelly metrics: Win Rate={metrics.win_rate:.1%}, R:R={metrics.reward_risk_ratio:.2f}"
        )

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        use_kelly: bool = True,
    ) -> float:
        """Calculate position size using Kelly Criterion or fixed risk.

        Args:
            symbol: Trading symbol
            entry_price: Entry price for the trade
            stop_loss_price: Stop-loss price level
            use_kelly: Use Kelly sizing if metrics available, else use fixed 2%

        Returns:
            Position size (number of units)
        """
        account = self.get_account()
        account_equity = account.get("equity", account.get("cash", self.initial_capital))

        if use_kelly and self.kelly_metrics and self.kelly_metrics.total_trades >= 20:
            # Use Kelly Criterion
            kelly_full = kelly_criterion(
                self.kelly_metrics.win_rate,
                self.kelly_metrics.reward_risk_ratio,
            )
            kelly_to_use = fractional_kelly(kelly_full, self.kelly_fraction)
            kelly_to_use = min(kelly_to_use, self.max_risk_pct)  # Apply cap

            position_size = kelly_to_position_units(
                account_equity,
                kelly_to_use,
                entry_price,
                stop_loss_price,
            )

            logger.debug(
                f"Kelly sizing: {kelly_to_use:.1%} risk → {position_size:.4f} units "
                f"(Full Kelly: {kelly_full:.1%})",
            )
        else:
            # Fallback to fixed 2% risk
            fixed_risk = 0.02
            position_size = kelly_to_position_units(
                account_equity,
                fixed_risk,
                entry_price,
                stop_loss_price,
            )

            if use_kelly:
                logger.debug(
                    f"Insufficient Kelly data ({self.kelly_metrics.total_trades if self.kelly_metrics else 0} trades), "
                    f"using fixed {fixed_risk:.1%} risk",
                )

        return position_size

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
