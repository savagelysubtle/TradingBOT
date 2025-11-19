"""Advanced technical analysis strategies using TA-Lib."""

import logging

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class SupertrendStrategy(BaseStrategy):
    """Supertrend indicator strategy - identifies trend direction and strength."""

    def __init__(
        self,
        period: int = 10,
        multiplier: float = 3.0,
        use_atr: bool = True,
    ):
        """Initialize Supertrend strategy.

        Args:
            period: ATR period for Supertrend calculation
            multiplier: ATR multiplier (typically 2.0-3.0)
            use_atr: Whether to use ATR for dynamic stop loss
        """
        super().__init__(
            name="SupertrendStrategy",
            period=period,
            multiplier=multiplier,
            use_atr=use_atr,
        )
        self.period = period
        self.multiplier = multiplier
        self.use_atr = use_atr

    def calculate_supertrend(
        self,
        high: np.ndarray,  # type: ignore[type-arg]
        low: np.ndarray,  # type: ignore[type-arg]
        close: np.ndarray,  # type: ignore[type-arg]
    ) -> tuple[np.ndarray, np.ndarray]:  # type: ignore[return]
        """Calculate Supertrend indicator.

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Tuple of (supertrend values, trend direction: 1=uptrend, -1=downtrend)
        """
        # Calculate ATR
        atr = talib.ATR(high, low, close, timeperiod=self.period)  # type: ignore[call-overload]

        # Calculate basic bands
        hl_avg = (high + low) / 2
        upper_band = hl_avg + (self.multiplier * atr)
        lower_band = hl_avg - (self.multiplier * atr)

        # Initialize arrays
        supertrend = np.zeros_like(close)  # type: ignore[attr-defined]
        trend = np.zeros_like(close)  # type: ignore[attr-defined]

        # Calculate Supertrend
        for i in range(1, len(close)):
            if close[i] > upper_band[i - 1]:
                trend[i] = 1
                supertrend[i] = lower_band[i]
            elif close[i] < lower_band[i - 1]:
                trend[i] = -1
                supertrend[i] = upper_band[i]
            else:
                trend[i] = trend[i - 1]
                if trend[i] == 1:
                    supertrend[i] = max(lower_band[i], supertrend[i - 1])
                else:
                    supertrend[i] = min(upper_band[i], supertrend[i - 1])

        return supertrend, trend

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using Supertrend.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = data.copy()

        # Convert to numpy arrays
        high = df["high"].values.astype(np.float64)  # type: ignore[attr-defined]
        low = df["low"].values.astype(np.float64)  # type: ignore[attr-defined]
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate Supertrend
        supertrend, trend = self.calculate_supertrend(high, low, close)

        df["supertrend"] = supertrend
        df["trend"] = trend

        # Calculate ATR for stop loss
        if self.use_atr:
            df["atr"] = talib.ATR(high, low, close, timeperiod=self.period)  # type: ignore[call-overload]

        # Initialize signals
        df["signal"] = 0

        # Generate buy signal: trend changes from -1 to 1 (downtrend to uptrend)
        df.loc[
            (df["trend"] == 1) & (df["trend"].shift(1) == -1),
            "signal",
        ] = 1

        # Generate sell signal: trend changes from 1 to -1 (uptrend to downtrend)
        df.loc[
            (df["trend"] == -1) & (df["trend"].shift(1) == 1),
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


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands mean reversion strategy."""

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        use_rsi: bool = True,
        rsi_period: int = 14,
    ):
        """Initialize Bollinger Bands strategy.

        Args:
            period: Moving average period
            std_dev: Standard deviation multiplier
            use_rsi: Whether to use RSI filter
            rsi_period: RSI period
        """
        super().__init__(
            name="BollingerBandsStrategy",
            period=period,
            std_dev=std_dev,
            use_rsi=use_rsi,
            rsi_period=rsi_period,
        )
        self.period = period
        self.std_dev = std_dev
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using Bollinger Bands.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = data.copy()

        # Check if we have enough data for Bollinger Bands calculation
        if len(df) < self.period:
            logger.warning(
                f"Insufficient data for Bollinger Bands: need {self.period} periods, got {len(df)}"
            )
            # Initialize with NaN values
            df["bb_upper"] = np.nan
            df["bb_middle"] = np.nan
            df["bb_lower"] = np.nan
            df["bb_width"] = np.nan
            df["bb_percent"] = np.nan
            df["signal"] = 0
            return df

        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate Bollinger Bands
        # Note: talib doesn't have complete type stubs
        upper, middle, lower = talib.BBANDS(  # type: ignore[call-overload]
            close,
            timeperiod=self.period,
            nbdevup=self.std_dev,
            nbdevdn=self.std_dev,
            matype=0,  # type: ignore[arg-type]
        )

        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower

        # Calculate bandwidth with division by zero protection
        bandwidth = np.zeros_like(upper)  # type: ignore[arg-defined]
        mask = middle != 0
        bandwidth[mask] = (upper[mask] - lower[mask]) / middle[mask]
        df["bb_width"] = bandwidth

        # Calculate %B with division by zero protection
        percent_b = np.zeros_like(close)  # type: ignore[arg-defined]
        band_range = upper - lower
        mask = band_range != 0
        percent_b[mask] = (close[mask] - lower[mask]) / band_range[mask]
        df["bb_percent"] = percent_b

        # Calculate RSI if enabled
        if self.use_rsi:
            df["rsi"] = talib.RSI(close, timeperiod=self.rsi_period)  # type: ignore[call-overload]

        # Initialize signals
        df["signal"] = 0

        # Buy signal: price touches lower band and RSI oversold
        buy_condition = df["close"] <= df["bb_lower"]
        if self.use_rsi:
            buy_condition = buy_condition & (df["rsi"] < 30)

        df.loc[buy_condition, "signal"] = 1

        # Sell signal: price touches upper band and RSI overbought
        sell_condition = df["close"] >= df["bb_upper"]
        if self.use_rsi:
            sell_condition = sell_condition & (df["rsi"] > 70)

        df.loc[sell_condition, "signal"] = -1

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


class IchimokuStrategy(BaseStrategy):
    """Ichimoku Cloud strategy - comprehensive trend analysis."""

    def __init__(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
    ):
        """Initialize Ichimoku strategy.

        Args:
            tenkan_period: Tenkan-sen period
            kijun_period: Kijun-sen period
            senkou_b_period: Senkou Span B period
        """
        super().__init__(
            name="IchimokuStrategy",
            tenkan_period=tenkan_period,
            kijun_period=kijun_period,
            senkou_b_period=senkou_b_period,
        )
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period

    def calculate_ichimoku(
        self,
        high: np.ndarray,  # type: ignore[type-arg]
        low: np.ndarray,  # type: ignore[type-arg]
        close: np.ndarray,  # type: ignore[type-arg]
    ) -> dict[str, np.ndarray]:  # type: ignore[return]
        """Calculate Ichimoku Cloud components.

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Dictionary with Ichimoku components
        """
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan_high = pd.Series(high).rolling(self.tenkan_period).max().values  # type: ignore[call-overload]
        tenkan_low = pd.Series(low).rolling(self.tenkan_period).min().values  # type: ignore[call-overload]
        tenkan_sen = (tenkan_high + tenkan_low) / 2  # type: ignore[operator]

        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        kijun_high = pd.Series(high).rolling(self.kijun_period).max().values  # type: ignore[call-overload]
        kijun_low = pd.Series(low).rolling(self.kijun_period).min().values  # type: ignore[call-overload]
        kijun_sen = (kijun_high + kijun_low) / 2  # type: ignore[operator]

        # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted 26 periods
        senkou_span_a = (tenkan_sen + kijun_sen) / 2  # type: ignore[operator]

        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods
        senkou_b_high = pd.Series(high).rolling(self.senkou_b_period).max().values  # type: ignore[call-overload]
        senkou_b_low = pd.Series(low).rolling(self.senkou_b_period).min().values  # type: ignore[call-overload]
        senkou_span_b = (senkou_b_high + senkou_b_low) / 2  # type: ignore[operator]

        # Chikou Span (Lagging Span): Close price shifted 26 periods back
        chikou_span = close

        return {
            "tenkan_sen": tenkan_sen,
            "kijun_sen": kijun_sen,
            "senkou_span_a": senkou_span_a,
            "senkou_span_b": senkou_span_b,
            "chikou_span": chikou_span,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using Ichimoku Cloud.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = data.copy()

        # Convert to numpy arrays
        high = df["high"].values.astype(np.float64)  # type: ignore[attr-defined]
        low = df["low"].values.astype(np.float64)  # type: ignore[attr-defined]
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate Ichimoku components
        ichimoku = self.calculate_ichimoku(high, low, close)

        df["tenkan_sen"] = ichimoku["tenkan_sen"]
        df["kijun_sen"] = ichimoku["kijun_sen"]
        df["senkou_span_a"] = ichimoku["senkou_span_a"]
        df["senkou_span_b"] = ichimoku["senkou_span_b"]
        df["chikou_span"] = ichimoku["chikou_span"]

        # Cloud boundaries
        df["cloud_top"] = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
        df["cloud_bottom"] = df[["senkou_span_a", "senkou_span_b"]].min(axis=1)

        # Initialize signals
        df["signal"] = 0

        # Buy signal: Price above cloud, Tenkan above Kijun, Chikou above price 26 periods ago
        buy_condition = (
            (df["close"] > df["cloud_top"])
            & (df["tenkan_sen"] > df["kijun_sen"])
            & (df["close"] > df["tenkan_sen"])
        )

        df.loc[buy_condition, "signal"] = 1

        # Sell signal: Price below cloud, Tenkan below Kijun, Chikou below price 26 periods ago
        sell_condition = (
            (df["close"] < df["cloud_bottom"])
            & (df["tenkan_sen"] < df["kijun_sen"])
            & (df["close"] < df["tenkan_sen"])
        )

        df.loc[sell_condition, "signal"] = -1

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



class RSIDivergenceStrategy(BaseStrategy):
    """RSI Divergence strategy - identifies potential reversals using RSI divergences."""

    def __init__(
        self,
        rsi_period: int = 14,
        overbought_level: int = 70,
        oversold_level: int = 30,
        divergence_lookback: int = 20,
        min_divergence_strength: float = 0.5,
    ):
        """Initialize RSI Divergence strategy.

        Args:
            rsi_period: RSI calculation period
            overbought_level: RSI level considered overbought
            oversold_level: RSI level considered oversold
            divergence_lookback: Number of periods to look back for divergence
            min_divergence_strength: Minimum strength of divergence to trigger signal
        """
        super().__init__(
            name="RSIDivergenceStrategy",
            rsi_period=rsi_period,
            overbought_level=overbought_level,
            oversold_level=oversold_level,
            divergence_lookback=divergence_lookback,
            min_divergence_strength=min_divergence_strength,
        )
        self.rsi_period = rsi_period
        self.overbought_level = overbought_level
        self.oversold_level = oversold_level
        self.divergence_lookback = divergence_lookback
        self.min_divergence_strength = min_divergence_strength

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using RSI divergence analysis.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = data.copy()
        logger.info(f"RSI Divergence: received data with {len(df)} rows, columns: {list(df.columns)}")

        # Check if we have enough data
        min_periods = self.rsi_period + self.divergence_lookback
        logger.info(f"RSI Divergence: checking data sufficiency - need {min_periods} periods, got {len(df)}")
        if len(df) < min_periods:
            logger.warning(
                f"Insufficient data for RSI Divergence: need {min_periods} periods, got {len(df)}"
            )
            df["signal"] = 0
            return df

        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate RSI
        rsi = talib.RSI(close, timeperiod=self.rsi_period)  # type: ignore[call-overload]
        df["rsi"] = rsi

        # Initialize signals
        df["signal"] = 0

        # Find bullish divergences (price makes lower low, RSI makes higher low)
        for i in range(self.divergence_lookback, len(df)):
            if pd.isna(rsi[i]) or pd.isna(close[i]):
                continue

            # Look for bearish divergence (price higher high, RSI lower high)
            if rsi[i] > self.overbought_level:
                # Check for bearish divergence in the last divergence_lookback periods
                price_high_idx = df["high"].iloc[i - self.divergence_lookback:i].idxmax()
                rsi_high_idx = df["rsi"].iloc[i - self.divergence_lookback:i].idxmax()

                if price_high_idx != rsi_high_idx:
                    # Check divergence strength
                    price_range = df["high"].iloc[i - self.divergence_lookback:i].max() - df["high"].iloc[i - self.divergence_lookback:i].min()
                    rsi_range = df["rsi"].iloc[i - self.divergence_lookback:i].max() - df["rsi"].iloc[i - self.divergence_lookback:i].min()

                    if rsi_range > 0 and price_range > 0:
                        divergence_ratio = rsi_range / price_range
                        if divergence_ratio > self.min_divergence_strength:
                            df.loc[df.index[i], "signal"] = -1  # Sell signal
                            break

            # Look for bullish divergence (price lower low, RSI higher low)
            elif rsi[i] < self.oversold_level:
                # Check for bullish divergence in the last divergence_lookback periods
                price_low_idx = df["low"].iloc[i - self.divergence_lookback:i].idxmin()
                rsi_low_idx = df["rsi"].iloc[i - self.divergence_lookback:i].idxmin()

                if price_low_idx != rsi_low_idx:
                    # Check divergence strength
                    price_range = df["high"].iloc[i - self.divergence_lookback:i].max() - df["low"].iloc[i - self.divergence_lookback:i].min()
                    rsi_range = df["rsi"].iloc[i - self.divergence_lookback:i].max() - df["rsi"].iloc[i - self.divergence_lookback:i].min()

                    if rsi_range > 0 and price_range > 0:
                        divergence_ratio = rsi_range / price_range
                        if divergence_ratio > self.min_divergence_strength:
                            df.loc[df.index[i], "signal"] = 1  # Buy signal
                            break

        return df

    def get_parameter_schema(self) -> dict:  # type: ignore[return]
        """Get parameter schema for this strategy."""
        return {
            "rsi_period": {
                "type": "integer",
                "default": 14,
                "minimum": 2,
                "maximum": 50,
                "description": "RSI calculation period",
            },
            "overbought_level": {
                "type": "integer",
                "default": 70,
                "minimum": 50,
                "maximum": 90,
                "description": "RSI level considered overbought",
            },
            "oversold_level": {
                "type": "integer",
                "default": 30,
                "minimum": 10,
                "maximum": 50,
                "description": "RSI level considered oversold",
            },
            "divergence_lookback": {
                "type": "integer",
                "default": 20,
                "minimum": 5,
                "maximum": 50,
                "description": "Periods to look back for divergence detection",
            },
            "min_divergence_strength": {
                "type": "number",
                "default": 0.5,
                "minimum": 0.1,
                "maximum": 2.0,
                "description": "Minimum strength of divergence to trigger signal",
            },
        }

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
