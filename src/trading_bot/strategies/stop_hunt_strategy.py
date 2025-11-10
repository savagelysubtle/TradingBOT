"""Stop Loss Hunting Entry Strategy.

This strategy identifies typical stop-loss placement zones where retail traders
commonly place stops, and uses these levels as entry points instead of exit points.
The strategy exploits the fact that big players hunt these stops, creating
temporary volatility and often price reversals.
"""

from typing import Any

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy


class StopHuntStrategy(BaseStrategy):
    """Strategy that enters trades at typical stop-loss placement zones.

    Instead of placing stops where retail traders do, this strategy enters
    positions at those levels, expecting price reversals after stop hunts.
    """

    def __init__(
        self,
        support_lookback: int = 20,
        atr_period: int = 14,
        atr_multipliers: list[float] | None = None,
        ma_periods: list[int] | None = None,
        cluster_min_factors: int = 3,
        entry_distance_pct: float = 0.5,
        volume_spike_multiplier: float = 2.0,
        reversal_candles: int = 2,
        stop_distance_atr: float = 2.0,
        use_round_numbers: bool = True,
        round_precision: int = 0,
    ):
        """Initialize Stop Hunt Strategy.

        Args:
            support_lookback: Periods to look back for support/resistance
            atr_period: Period for ATR calculation
            atr_multipliers: ATR multipliers for stop levels (default: [1.5, 2.0, 2.5, 3.0])
            ma_periods: Moving average periods to check (default: [50, 100, 200])
            cluster_min_factors: Minimum converging factors for stop cluster
            entry_distance_pct: Percentage distance from cluster to enter (default: 0.5%)
            volume_spike_multiplier: Volume spike threshold multiplier (default: 2.0x)
            reversal_candles: Number of candles to confirm reversal (default: 2)
            stop_distance_atr: Stop loss distance in ATR multiples (default: 2.0)
            use_round_numbers: Whether to consider round numbers (default: True)
            round_precision: Decimal places for round numbers (0=whole numbers, 1=tenths, etc.)
        """
        if atr_multipliers is None:
            atr_multipliers = [1.5, 2.0, 2.5, 3.0]
        if ma_periods is None:
            ma_periods = [50, 100, 200]

        super().__init__(
            name="StopHuntStrategy",
            support_lookback=support_lookback,
            atr_period=atr_period,
            atr_multipliers=atr_multipliers,
            ma_periods=ma_periods,
            cluster_min_factors=cluster_min_factors,
            entry_distance_pct=entry_distance_pct,
            volume_spike_multiplier=volume_spike_multiplier,
            reversal_candles=reversal_candles,
            stop_distance_atr=stop_distance_atr,
            use_round_numbers=use_round_numbers,
            round_precision=round_precision,
        )
        self.support_lookback = support_lookback
        self.atr_period = atr_period
        self.atr_multipliers = atr_multipliers
        self.ma_periods = ma_periods
        self.cluster_min_factors = cluster_min_factors
        self.entry_distance_pct = entry_distance_pct
        self.volume_spike_multiplier = volume_spike_multiplier
        self.reversal_candles = reversal_candles
        self.stop_distance_atr = stop_distance_atr
        self.use_round_numbers = use_round_numbers
        self.round_precision = round_precision

    def _find_support_resistance(
        self, df: pd.DataFrame, lookback: int
    ) -> tuple[pd.Series, pd.Series]:  # type: ignore[type-arg]
        """Find support and resistance levels using pivot points.

        Args:
            df: DataFrame with OHLCV data
            lookback: Periods to look back for pivots

        Returns:
            Tuple of (support levels, resistance levels)
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Find pivot highs (resistance)
        pivot_highs = high.rolling(window=lookback * 2 + 1, center=True).max()  # type: ignore[call-overload]
        resistance = pd.Series(index=df.index, dtype=float)  # type: ignore[type-arg]
        for i in range(lookback, len(df) - lookback):
            if high.iloc[i] == pivot_highs.iloc[i]:
                resistance.iloc[i] = high.iloc[i]

        # Find pivot lows (support)
        pivot_lows = low.rolling(window=lookback * 2 + 1, center=True).min()  # type: ignore[call-overload]
        support = pd.Series(index=df.index, dtype=float)  # type: ignore[type-arg]
        for i in range(lookback, len(df) - lookback):
            if low.iloc[i] == pivot_lows.iloc[i]:
                support.iloc[i] = low.iloc[i]

        # Forward fill to carry levels forward
        support = support.ffill()  # type: ignore[assignment]
        resistance = resistance.ffill()  # type: ignore[assignment]

        return support, resistance

    def _find_round_numbers(
        self, price: float, precision: int = 0
    ) -> list[float]:
        """Find nearby round numbers.

        Args:
            price: Current price
            precision: Decimal precision (0=whole numbers, 1=tenths, etc.)

        Returns:
            List of nearby round numbers
        """
        if precision == 0:
            # Whole numbers
            base = 10 ** (len(str(int(price))) - 1)
            lower = (int(price // base) * base) - base
            current = int(price // base) * base
            upper = (int(price // base) * base) + base
            return [lower, current, upper]
        else:
            # Decimal precision
            multiplier = 10**precision
            rounded = round(price * multiplier) / multiplier
            step = 10 ** (-precision)
            return [rounded - step, rounded, rounded + step]

    def _detect_stop_clusters(
        self, df: pd.DataFrame, index: int
    ) -> tuple[list[float], list[float]]:  # type: ignore[type-arg]
        """Detect stop-loss clusters at given index.

        Args:
            df: DataFrame with OHLCV data
            index: Current index to analyze

        Returns:
            Tuple of (support clusters, resistance clusters) with scores
        """
        if index < max(self.support_lookback, max(self.ma_periods)):
            return [], []

        current_price = df["close"].iloc[index]
        high = df["high"].values.astype(np.float64)  # type: ignore[attr-defined]
        low = df["low"].values.astype(np.float64)  # type: ignore[attr-defined]
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate ATR
        atr = talib.ATR(high, low, close, timeperiod=self.atr_period)  # type: ignore[call-overload]
        current_atr = atr[index] if not np.isnan(atr[index]) else 0

        # Find support/resistance levels
        support_levels, resistance_levels = self._find_support_resistance(
            df.iloc[: index + 1], self.support_lookback
        )

        # Get recent support/resistance
        recent_support = support_levels.iloc[: index + 1].dropna().tail(5).tolist()
        recent_resistance = (
            resistance_levels.iloc[: index + 1].dropna().tail(5).tolist()
        )

        # Calculate ATR-based stop levels
        atr_support_levels = []
        atr_resistance_levels = []
        if current_atr > 0:
            for multiplier in self.atr_multipliers:
                atr_support_levels.append(current_price - (current_atr * multiplier))
                atr_resistance_levels.append(current_price + (current_atr * multiplier))

        # Calculate moving averages
        ma_levels = []
        for period in self.ma_periods:
            if index >= period:
                ma = talib.SMA(close[: index + 1], timeperiod=period)  # type: ignore[call-overload]
                if not np.isnan(ma[-1]):
                    ma_levels.append(ma[-1])

        # Find round numbers
        round_numbers = []
        if self.use_round_numbers:
            round_numbers = self._find_round_numbers(current_price, self.round_precision)

        # Cluster detection: find levels that converge
        support_clusters = []
        resistance_clusters = []

        # Combine all support factors (filter out invalid values)
        all_support_levels = [
            level
            for level in recent_support + atr_support_levels + ma_levels + round_numbers
            if level > 0 and not np.isnan(level)
        ]
        all_resistance_levels = [
            level
            for level in recent_resistance + atr_resistance_levels + ma_levels + round_numbers
            if level > 0 and not np.isnan(level)
        ]

        # Score clusters by proximity (within 1% of each other)
        cluster_threshold = current_price * 0.01

        # Find support clusters
        for level in all_support_levels:
            if level < current_price:
                # Count how many factors converge near this level
                nearby_count = sum(
                    1
                    for other_level in all_support_levels
                    if abs(level - other_level) <= cluster_threshold
                )
                if nearby_count >= self.cluster_min_factors:
                    support_clusters.append(level)

        # Find resistance clusters
        for level in all_resistance_levels:
            if level > current_price:
                nearby_count = sum(
                    1
                    for other_level in all_resistance_levels
                    if abs(level - other_level) <= cluster_threshold
                )
                if nearby_count >= self.cluster_min_factors:
                    resistance_clusters.append(level)

        # Remove duplicates and sort
        support_clusters = sorted(list(set(support_clusters)), reverse=True)
        resistance_clusters = sorted(list(set(resistance_clusters)))

        return support_clusters, resistance_clusters

    def _detect_stop_hunt(
        self, df: pd.DataFrame, index: int, cluster_level: float, is_support: bool
    ) -> bool:
        """Detect if a stop hunt occurred at the cluster level.

        Args:
            df: DataFrame with OHLCV data
            index: Current index
            cluster_level: The stop cluster level
            is_support: True if checking support (long entry), False for resistance (short)

        Returns:
            True if stop hunt detected
        """
        if index < self.reversal_candles:
            return False

        # Check for false breakout pattern
        lookback_start = max(0, index - self.reversal_candles - 2)
        recent_data = df.iloc[lookback_start : index + 1]

        # Calculate average volume
        avg_volume = recent_data["volume"].mean()

        # Check if price broke through level and reversed
        if is_support:
            # For support: price should have broken below, then reversed up
            broke_below = (recent_data["low"] < cluster_level).any()
            current_above = df["close"].iloc[index] > cluster_level
            volume_spike = df["volume"].iloc[index] > (avg_volume * self.volume_spike_multiplier)

            # Check for reversal pattern (hammer, doji, or bullish engulfing)
            reversal_pattern = False
            if index >= 1:
                prev_candle = recent_data.iloc[-2]
                curr_candle = recent_data.iloc[-1]

                # Hammer pattern: long lower wick, small body
                body = abs(curr_candle["close"] - curr_candle["open"])
                lower_wick = min(curr_candle["open"], curr_candle["close"]) - curr_candle["low"]
                if lower_wick > body * 2 and curr_candle["close"] > curr_candle["open"]:
                    reversal_pattern = True

                # Bullish engulfing
                if (
                    prev_candle["close"] < prev_candle["open"]
                    and curr_candle["close"] > curr_candle["open"]
                    and curr_candle["open"] < prev_candle["close"]
                    and curr_candle["close"] > prev_candle["open"]
                ):
                    reversal_pattern = True

            return broke_below and current_above and (volume_spike or reversal_pattern)
        else:
            # For resistance: price should have broken above, then reversed down
            broke_above = (recent_data["high"] > cluster_level).any()
            current_below = df["close"].iloc[index] < cluster_level
            volume_spike = df["volume"].iloc[index] > (avg_volume * self.volume_spike_multiplier)

            # Check for reversal pattern
            reversal_pattern = False
            if index >= 1:
                prev_candle = recent_data.iloc[-2]
                curr_candle = recent_data.iloc[-1]

                # Shooting star pattern: long upper wick, small body
                body = abs(curr_candle["close"] - curr_candle["open"])
                upper_wick = curr_candle["high"] - max(curr_candle["open"], curr_candle["close"])
                if upper_wick > body * 2 and curr_candle["close"] < curr_candle["open"]:
                    reversal_pattern = True

                # Bearish engulfing
                if (
                    prev_candle["close"] > prev_candle["open"]
                    and curr_candle["close"] < curr_candle["open"]
                    and curr_candle["open"] > prev_candle["close"]
                    and curr_candle["close"] < prev_candle["open"]
                ):
                    reversal_pattern = True

            return broke_above and current_below and (volume_spike or reversal_pattern)

    def generate_signals(self, data: pd.DataFrame, **params: Any) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals based on stop-loss cluster detection.

        Args:
            data: DataFrame with OHLCV data
            **params: Optional parameter overrides

        Returns:
            DataFrame with signals added (1=buy, -1=sell, 0=hold)
        """
        # Use provided params or fall back to instance attributes
        support_lookback = params.get("support_lookback", self.support_lookback)
        cluster_min_factors = params.get("cluster_min_factors", self.cluster_min_factors)
        entry_distance_pct = params.get("entry_distance_pct", self.entry_distance_pct)

        df = data.copy()
        df["signal"] = 0

        min_periods = max(support_lookback, max(self.ma_periods), self.atr_period)

        for i in range(min_periods, len(df)):
            # Detect stop clusters
            support_clusters, resistance_clusters = self._detect_stop_clusters(df, i)

            current_price = df["close"].iloc[i]

            # Check for long entry (support cluster)
            for support_level in support_clusters:
                # Entry when price approaches support cluster
                distance_pct = abs((current_price - support_level) / support_level) * 100
                if distance_pct <= entry_distance_pct:
                    # Check for stop hunt or pre-hunt entry
                    if self._detect_stop_hunt(df, i, support_level, is_support=True):
                        df.loc[df.index[i], "signal"] = 1
                        break

            # Check for short entry (resistance cluster)
            for resistance_level in resistance_clusters:
                distance_pct = abs((current_price - resistance_level) / resistance_level) * 100
                if distance_pct <= entry_distance_pct:
                    if self._detect_stop_hunt(df, i, resistance_level, is_support=False):
                        df.loc[df.index[i], "signal"] = -1
                        break

        return df

    def get_parameter_ranges(self) -> dict[str, list[float]]:
        """Get parameter ranges for walk-forward optimization.

        Returns:
            Dictionary with parameter ranges for optimization
        """
        return {
            "support_lookback": [10, 15, 20, 25, 30],
            "cluster_min_factors": [2, 3, 4],
            "entry_distance_pct": [0.3, 0.5, 0.7, 1.0],
            "volume_spike_multiplier": [1.5, 2.0, 2.5, 3.0],
        }

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.01,  # Lower risk for this strategy
    ) -> float:
        """Calculate position size based on risk management.

        Args:
            price: Current price
            account_value: Total account value
            risk_per_trade: Risk percentage per trade (default: 1% for this strategy)

        Returns:
            Position size (number of shares)
        """
        # Use ATR-based stop distance
        risk_amount = account_value * risk_per_trade
        stop_distance_pct = (self.stop_distance_atr * 0.02)  # Approximate ATR as 2% of price
        stop_loss_price = price * (1 - stop_distance_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1  # Max 10% of account
        max_shares = max_position_value / price

        return min(position_size, max_shares)

