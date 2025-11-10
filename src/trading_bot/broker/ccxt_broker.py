"""CCXT-based broker for cryptocurrency trading."""

import logging
from datetime import datetime

import ccxt
import pandas as pd

from trading_bot.broker.base import BaseBroker
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

logger = logging.getLogger(__name__)


class CCXTBroker(BaseBroker):
    """CCXT-based broker for cryptocurrency exchanges."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ):
        """Initialize CCXT broker.

        Args:
            exchange_id: Exchange ID (e.g., 'binance', 'coinbase', 'kraken')
            api_key: API key for authenticated requests
            secret: API secret for authenticated requests
            sandbox: Use sandbox/testnet if available
        """
        self.exchange_id = exchange_id
        self.sandbox = sandbox

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
