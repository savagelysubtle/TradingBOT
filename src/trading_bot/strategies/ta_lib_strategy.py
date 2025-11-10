"""TA-Lib based trading strategies."""

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy


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

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using TA-Lib.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = data.copy()

        # Convert to numpy arrays for TA-Lib
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate moving averages using TA-Lib
        # Note: talib doesn't have complete type stubs
        df["ma_short"] = talib.MA(close, timeperiod=self.short_period, matype=self.ma_type)  # type: ignore[call-overload]
        df["ma_long"] = talib.MA(close, timeperiod=self.long_period, matype=self.ma_type)  # type: ignore[call-overload]

        # Calculate RSI if enabled
        if self.use_rsi:
            df["rsi"] = talib.RSI(close, timeperiod=self.rsi_period)  # type: ignore[call-overload]

        # Initialize signals
        df["signal"] = 0

        # Generate buy signals (short MA crosses above long MA)
        df.loc[
            (df["ma_short"] > df["ma_long"])
            & (df["ma_short"].shift(1) <= df["ma_long"].shift(1))
            & (
                ~self.use_rsi
                | (df["rsi"] < self.rsi_overbought)
                | (df["rsi"].shift(1) < self.rsi_oversold)
            ),
            "signal",
        ] = 1

        # Generate sell signals (short MA crosses below long MA)
        df.loc[
            (df["ma_short"] < df["ma_long"]) & (df["ma_short"].shift(1) >= df["ma_long"].shift(1)),
            "signal",
        ] = -1

        # Also sell if RSI is overbought
        if self.use_rsi:
            df.loc[
                (df["rsi"] > self.rsi_overbought) & (df["ma_short"] < df["ma_long"]),
                "signal",
            ] = -1

        return df

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size based on risk management."""
        risk_amount = account_value * risk_per_trade
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        return min(position_size, max_shares)


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

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate MACD trading signals."""
        df = data.copy()
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate MACD using TA-Lib
        # Note: talib doesn't have complete type stubs
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
        df.loc[
            (df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1)),
            "signal",
        ] = 1

        # Sell when MACD crosses below signal line
        df.loc[
            (df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1)),
            "signal",
        ] = -1

        return df

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size."""
        risk_amount = account_value * risk_per_trade
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        return min(position_size, max_shares)
