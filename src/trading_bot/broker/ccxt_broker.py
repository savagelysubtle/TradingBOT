"""CCXT-based broker for cryptocurrency trading."""

import logging
from datetime import datetime

import ccxt
import pandas as pd

from trading_bot.broker.base import BaseBroker
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.risk.kelly_criterion import (
    KellyMetrics,
    fractional_kelly,
    kelly_criterion,
    kelly_to_position_units,
)

logger = logging.getLogger(__name__)


class CCXTBroker(BaseBroker):
    """CCXT-based broker for cryptocurrency exchanges."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
        kelly_fraction: float = 0.5,
        max_risk_pct: float = 0.05,
        kelly_metrics: KellyMetrics | None = None,
    ):
        """Initialize CCXT broker.

        Args:
            exchange_id: Exchange ID (e.g., 'binance', 'coinbase', 'kraken')
            api_key: API key for authenticated requests
            secret: API secret for authenticated requests
            sandbox: Use sandbox/testnet if available
            kelly_fraction: Fraction of Kelly to use (0.25=Quarter, 0.5=Half, 1.0=Full)
            max_risk_pct: Maximum risk % per trade (default: 0.05 = 5%)
            kelly_metrics: Kelly metrics from backtest (optional, for position sizing)
        """
        self.exchange_id = exchange_id
        self.sandbox = sandbox
        self.kelly_fraction = kelly_fraction
        self.max_risk_pct = max_risk_pct
        self.kelly_metrics = kelly_metrics

        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange_config = {
            "apiKey": api_key or "",
            "secret": secret or "",
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }

        if sandbox:
            exchange_config["sandbox"] = True

        self.exchange = exchange_class(exchange_config)
        self.data_fetcher = CCXTDataFetcher(
            exchange_id=exchange_id,
            api_key=api_key,
            secret=secret,
            sandbox=sandbox,
        )

        logger.info(f"Initialized {exchange_id} broker (sandbox={sandbox})")

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
        account_equity = account.get("equity", account.get("cash", 10000.0))

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

    def get_account(self) -> dict:
        """Get account information."""
        try:
            balance = self.exchange.fetch_balance()
            return {
                "cash": balance.get("USDT", {}).get("free", 0.0)
                or balance.get("USD", {}).get("free", 0.0),
                "equity": balance.get("total", {}).get("total", 0.0),
                "buying_power": balance.get("USDT", {}).get("free", 0.0)
                or balance.get("USD", {}).get("free", 0.0),
            }
        except Exception as e:
            logger.error(f"Error fetching account: {e}")
            return {"cash": 0.0, "equity": 0.0, "buying_power": 0.0}

    def get_positions(self) -> list[dict]:
        """Get current positions."""
        try:
            balance = self.exchange.fetch_balance()
            positions = []

            for currency, amounts in balance.items():
                if currency in ["info", "free", "used", "total"]:
                    continue

                if isinstance(amounts, dict) and amounts.get("total", 0) > 0:
                    positions.append(
                        {
                            "symbol": currency,
                            "quantity": amounts.get("total", 0),
                            "avg_price": 0.0,  # CCXT doesn't provide this directly
                            "market_value": amounts.get("total", 0),
                        },
                    )

            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        price: float | None = None,
    ) -> dict:
        """Place an order."""
        try:
            if side.lower() == "buy":
                order = self.exchange.create_market_buy_order(symbol, quantity)
            else:
                order = self.exchange.create_market_sell_order(symbol, quantity)

            logger.info(
                f"Placed {side.upper()} order: {quantity} {symbol} @ {order.get('price', 'market')}",
            )

            return {
                "id": order.get("id", ""),
                "symbol": symbol,
                "quantity": quantity,
                "side": side,
                "order_type": order_type,
                "price": order.get("price", price),
                "status": order.get("status", "filled"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

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
            timeframe=interval,
            start_date=start_date,
            end_date=end_date,
        )

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an order."""
        try:
            self.exchange.cancel_order(order_id)
            logger.info(f"Cancelled order {order_id}")
            return {"status": "cancelled", "order_id": order_id}
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise
