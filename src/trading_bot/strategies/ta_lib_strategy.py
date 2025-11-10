"""TA-Lib based trading strategies."""

import logging
from typing import Any

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class TALibMovingAverageCrossover(BaseStrategy):
    """Moving Average Crossover strategy using TA-Lib."""

    def __init__(
        self,
        short_period: int = 50,
        long_period: int = 200,
        ma_type: int = talib.MA_Type.SMA,  # type: ignore[attr-defined]
        use_rsi: bool = True,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        """Initialize TA-Lib Moving Average Crossover strategy.

        Args:
            short_period: Short moving average period
            long_period: Long moving average period
            ma_type: Moving average type (SMA, EMA, WMA, etc.)
            use_rsi: Whether to use RSI filter
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
        """
        super().__init__(
            name="TALibMovingAverageCrossover",
            short_period=short_period,
            long_period=long_period,
            ma_type=ma_type,
            use_rsi=use_rsi,
            rsi_period=rsi_period,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
        )
        self.short_period = short_period
        self.long_period = long_period
        self.ma_type = ma_type
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        logger.info(
            f"TALibMovingAverageCrossover initialized: short={short_period}, long={long_period}, "
            f"MA_type={ma_type}, RSI={use_rsi} (period={rsi_period})"
        )

    def get_parameter_ranges(self) -> dict[str, list[float]]:
        """Get parameter ranges for walk-forward optimization.

        Returns:
            Dictionary with parameter ranges for optimization
        """
        return {
            "short_period": [10, 20, 30, 40, 50],
            "long_period": [50, 100, 150, 200],
        }

    def generate_signals(self, data: pd.DataFrame, **params: Any) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using TA-Lib.

        Args:
            data: DataFrame with OHLCV data
            **params: Optional parameter overrides (short_period, long_period, etc.)

        Returns:
            DataFrame with signals added
        """
        # Use provided params or fall back to instance attributes
        short_period = params.get("short_period", self.short_period)
        long_period = params.get("long_period", self.long_period)
        ma_type = params.get("ma_type", self.ma_type)
        use_rsi = params.get("use_rsi", self.use_rsi)
        rsi_period = params.get("rsi_period", self.rsi_period)
        rsi_overbought = params.get("rsi_overbought", self.rsi_overbought)
        rsi_oversold = params.get("rsi_oversold", self.rsi_oversold)
        logger.debug(
            f"Generating signals with params: short={short_period}, long={long_period}, "
            f"RSI={use_rsi} for {len(data)} data points"
        )
        df = data.copy()

        # Convert to numpy arrays for TA-Lib
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate moving averages using TA-Lib
        # Note: talib doesn't have complete type stubs
        df["ma_short"] = talib.MA(close, timeperiod=int(short_period), matype=ma_type)  # type: ignore[call-overload]
        df["ma_long"] = talib.MA(close, timeperiod=int(long_period), matype=ma_type)  # type: ignore[call-overload]

        # Calculate RSI if enabled
        if use_rsi:
            df["rsi"] = talib.RSI(close, timeperiod=int(rsi_period))  # type: ignore[call-overload]

        # Initialize signals
        df["signal"] = 0

        # Generate buy signals (short MA crosses above long MA)
        buy_condition = (
            (df["ma_short"] > df["ma_long"])
            & (df["ma_short"].shift(1) <= df["ma_long"].shift(1))
            & (~use_rsi | (df["rsi"] < rsi_overbought) | (df["rsi"].shift(1) < rsi_oversold))
        )
        buy_signals = buy_condition.sum()
        df.loc[buy_condition, "signal"] = 1
        if buy_signals > 0:
            logger.debug(f"Generated {buy_signals} BUY signals")

        # Generate sell signals (short MA crosses below long MA)
        sell_condition = (df["ma_short"] < df["ma_long"]) & (
            df["ma_short"].shift(1) >= df["ma_long"].shift(1)
        )
        sell_signals = sell_condition.sum()
        df.loc[sell_condition, "signal"] = -1
        if sell_signals > 0:
            logger.debug(f"Generated {sell_signals} SELL signals")

        # Also sell if RSI is overbought
        rsi_sell_signals = 0
        if use_rsi:
            rsi_sell_condition = (df["rsi"] > rsi_overbought) & (df["ma_short"] < df["ma_long"])
            rsi_sell_signals = rsi_sell_condition.sum()
            df.loc[rsi_sell_condition, "signal"] = -1
            if rsi_sell_signals > 0:
                logger.debug(f"Generated {rsi_sell_signals} RSI-based SELL signals")

        total_signals = (df["signal"] != 0).sum()
        logger.info(
            f"TALib signal generation complete: {total_signals} total signals "
            f"({buy_signals} buy, {sell_signals + rsi_sell_signals} sell)"
        )
        return df

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size based on risk management."""
        logger.debug(
            f"Calculating position size: price=${price:.2f}, account=${account_value:.2f}, risk={risk_per_trade:.1%}"
        )
        risk_amount = account_value * risk_per_trade
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            logger.warning(f"Invalid risk_per_share: {risk_per_share}, returning 0")
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        final_size = min(position_size, max_shares)
        logger.debug(
            f"Position size calculated: {final_size:.4f} shares (risk=${risk_amount:.2f}, max=${max_position_value:.2f})"
        )
        return final_size


class TALibMACDStrategy(BaseStrategy):
    """MACD strategy using TA-Lib."""

    def __init__(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
    ):
        """Initialize MACD strategy.

        Args:
            fastperiod: Fast EMA period
            slowperiod: Slow EMA period
            signalperiod: Signal line EMA period
        """
        super().__init__(
            name="TALibMACDStrategy",
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod,
        )
        self.fastperiod = fastperiod
        self.slowperiod = slowperiod
        self.signalperiod = signalperiod
        logger.info(
            f"TALibMACDStrategy initialized: fast={fastperiod}, slow={slowperiod}, signal={signalperiod}"
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate MACD trading signals."""
        logger.debug(f"Generating MACD signals for {len(data)} data points")
        df = data.copy()
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate MACD using TA-Lib
        # Note: talib doesn't have complete type stubs
        logger.debug(
            f"Calculating MACD: fast={self.fastperiod}, slow={self.slowperiod}, signal={self.signalperiod}"
        )
        macd, signal, hist = talib.MACD(  # type: ignore[call-overload]
            close,
            fastperiod=self.fastperiod,
            slowperiod=self.slowperiod,
            signalperiod=self.signalperiod,
        )

        df["macd"] = macd
        df["macd_signal"] = signal
        df["macd_hist"] = hist

        # Initialize signals
        df["signal"] = 0

        # Buy when MACD crosses above signal line
        buy_condition = (df["macd"] > df["macd_signal"]) & (
            df["macd"].shift(1) <= df["macd_signal"].shift(1)
        )
        buy_signals = buy_condition.sum()
        df.loc[buy_condition, "signal"] = 1
        if buy_signals > 0:
            logger.debug(f"Generated {buy_signals} BUY signals (MACD crossover)")

        # Sell when MACD crosses below signal line
        sell_condition = (df["macd"] < df["macd_signal"]) & (
            df["macd"].shift(1) >= df["macd_signal"].shift(1)
        )
        sell_signals = sell_condition.sum()
        df.loc[sell_condition, "signal"] = -1
        if sell_signals > 0:
            logger.debug(f"Generated {sell_signals} SELL signals (MACD crossover)")

        total_signals = (df["signal"] != 0).sum()
        logger.info(
            f"MACD signal generation complete: {total_signals} total signals ({buy_signals} buy, {sell_signals} sell)"
        )
        return df

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size."""
        logger.debug(
            f"Calculating position size: price=${price:.2f}, account=${account_value:.2f}, risk={risk_per_trade:.1%}"
        )
        risk_amount = account_value * risk_per_trade
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            logger.warning(f"Invalid risk_per_share: {risk_per_share}, returning 0")
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        final_size = min(position_size, max_shares)
        logger.debug(
            f"Position size calculated: {final_size:.4f} shares (risk=${risk_amount:.2f}, max=${max_position_value:.2f})"
        )
        return final_size
