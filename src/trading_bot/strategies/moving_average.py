"""Moving Average Crossover strategy."""

import logging

import pandas as pd

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class MovingAverageCrossover(BaseStrategy):
    """Moving Average Crossover strategy.

    Buys when short MA crosses above long MA, sells when short MA crosses below long MA.
    """

    def __init__(
        self,
        short_window: int = 50,
        long_window: int = 200,
        use_rsi: bool = True,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        """Initialize Moving Average Crossover strategy.

        Args:
            short_window: Short moving average period
            long_window: Long moving average period
            use_rsi: Whether to use RSI filter
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
        """
        super().__init__(
            name="MovingAverageCrossover",
            short_window=short_window,
            long_window=long_window,
            use_rsi=use_rsi,
            rsi_period=rsi_period,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
        )
        self.short_window = short_window
        self.long_window = long_window
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        logger.info(
            f"MovingAverageCrossover initialized: short={short_window}, long={long_window}, "
            f"RSI={use_rsi} (period={rsi_period})"
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        logger.debug(f"Generating signals for {len(data)} data points")
        df = data.copy()

        # Calculate moving averages
        df["ma_short"] = df["close"].rolling(window=self.short_window).mean()
        df["ma_long"] = df["close"].rolling(window=self.long_window).mean()

        # Calculate RSI if enabled (using pandas rolling)
        if self.use_rsi:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

        # Initialize signals
        df["signal"] = 0

        # Generate buy signals (short MA crosses above long MA)
        buy_condition = (
            (df["ma_short"] > df["ma_long"])
            & (df["ma_short"].shift(1) <= df["ma_long"].shift(1))
        )

        if self.use_rsi:
            buy_condition = buy_condition & (
                (df["rsi"] < self.rsi_overbought)
                | (df["rsi"].shift(1) < self.rsi_oversold)
            )

        buy_signals = buy_condition.sum()
        df.loc[buy_condition, "signal"] = 1
        if buy_signals > 0:
            logger.debug(f"Generated {buy_signals} BUY signals")

        # Generate sell signals (short MA crosses below long MA)
        sell_condition = (
            (df["ma_short"] < df["ma_long"])
            & (df["ma_short"].shift(1) >= df["ma_long"].shift(1))
        )
        sell_signals = sell_condition.sum()
        df.loc[sell_condition, "signal"] = -1
        if sell_signals > 0:
            logger.debug(f"Generated {sell_signals} SELL signals")

        # Also sell if RSI is overbought and we're in a position
        if self.use_rsi:
            sell_rsi_condition = (
                (df["rsi"] > self.rsi_overbought)
                & (df["ma_short"] < df["ma_long"])
            )
            rsi_sell_signals = sell_rsi_condition.sum()
            df.loc[sell_rsi_condition, "signal"] = -1
            if rsi_sell_signals > 0:
                logger.debug(f"Generated {rsi_sell_signals} RSI-based SELL signals")

        total_signals = (df["signal"] != 0).sum()
        logger.info(f"Signal generation complete: {total_signals} total signals ({buy_signals} buy, {sell_signals + rsi_sell_signals if self.use_rsi else sell_signals} sell)")
        return df

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
        logger.debug(f"Calculating position size: price=${price:.2f}, account=${account_value:.2f}, risk={risk_per_trade:.1%}")
        risk_amount = account_value * risk_per_trade
        # Assume 2% stop loss
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            logger.warning(f"Invalid risk_per_share: {risk_per_share}, returning 0")
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1  # Max 10% of account
        max_shares = max_position_value / price

        final_size = min(position_size, max_shares)
        logger.debug(f"Position size calculated: {final_size:.4f} shares (risk=${risk_amount:.2f}, max=${max_position_value:.2f})")
        return final_size

