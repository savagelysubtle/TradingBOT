"""Multi-indicator strategy combining multiple technical indicators with confirmation scoring."""

import logging

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.advanced_indicators import SupertrendStrategy
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class MultiIndicatorStrategy(BaseStrategy):
    """Advanced strategy combining multiple indicators with dynamic weighting and confirmation scoring."""

    def __init__(
        self,
        supertrend_period: int = 10,
        supertrend_multiplier: float = 3.0,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_ma_period: int = 20,
        confirmation_threshold: float = 0.7,
    ):
        """Initialize Multi-Indicator strategy.

        Args:
            supertrend_period: Supertrend ATR period
            supertrend_multiplier: Supertrend multiplier
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation
            volume_ma_period: Volume moving average period
            confirmation_threshold: Minimum confirmation score (0-1) for signal
        """
        super().__init__(
            name="MultiIndicatorStrategy",
            supertrend_period=supertrend_period,
            supertrend_multiplier=supertrend_multiplier,
            rsi_period=rsi_period,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            bb_period=bb_period,
            bb_std=bb_std,
            volume_ma_period=volume_ma_period,
            confirmation_threshold=confirmation_threshold,
        )
        self.supertrend_period = supertrend_period
        self.supertrend_multiplier = supertrend_multiplier
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_ma_period = volume_ma_period
        self.confirmation_threshold = confirmation_threshold

        # Create Supertrend helper
        self.supertrend_helper = SupertrendStrategy(
            period=supertrend_period,
            multiplier=supertrend_multiplier
        )

    def calculate_confirmation_score(
        self,
        df: pd.DataFrame,
        signal_type: str
    ) -> pd.Series:  # type: ignore[return]
        """Calculate confirmation score for signals (0-1 scale)."""
        scores = pd.Series(0.0, index=df.index)

        for i in range(len(df)):
            score = 0.0
            total_weight = 0.0

            # Supertrend (40% weight) - Trend direction
            if signal_type == "buy" and df["supertrend_trend"].iloc[i] == 1:
                score += 0.4
            elif signal_type == "sell" and df["supertrend_trend"].iloc[i] == -1:
                score += 0.4
            total_weight += 0.4

            # RSI (25% weight) - Momentum confirmation
            rsi = df["rsi"].iloc[i]
            if signal_type == "buy" and rsi <= self.rsi_oversold:
                # Stronger signal when more oversold
                score += 0.25 * (1 - rsi / self.rsi_oversold)
            elif signal_type == "sell" and rsi >= self.rsi_overbought:
                # Stronger signal when more overbought
                score += 0.25 * (rsi / 100.0)
            total_weight += 0.25

            # MACD (20% weight) - Trend momentum
            if signal_type == "buy" and df["macd_hist"].iloc[i] > 0:
                score += 0.2
            elif signal_type == "sell" and df["macd_hist"].iloc[i] < 0:
                score += 0.2
            total_weight += 0.2

            # Volume (10% weight) - Confirmation strength
            if df["volume_ratio"].iloc[i] > 1.0:  # Above average volume
                score += 0.1
            total_weight += 0.1

            # Bollinger Bands (5% weight) - Mean reversion signals
            bb_pos = df["bb_position"].iloc[i]
            if signal_type == "buy" and bb_pos < 0.2:  # Near lower band
                score += 0.05
            elif signal_type == "sell" and bb_pos > 0.8:  # Near upper band
                score += 0.05
            total_weight += 0.05

            scores.iloc[i] = score / total_weight if total_weight > 0 else 0.0

        return scores

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate signals using multiple indicators with confirmation scoring."""
        df = data.copy()

        # Convert to numpy arrays for TA-Lib
        high = df["high"].values.astype(np.float64)  # type: ignore[attr-defined]
        low = df["low"].values.astype(np.float64)  # type: ignore[attr-defined]
        close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]
        volume = df["volume"].values.astype(np.float64)  # type: ignore[attr-defined]

        # Calculate all indicators
        # Supertrend - Primary trend indicator
        supertrend, trend = self.supertrend_helper.calculate_supertrend(high, low, close)
        df["supertrend"] = supertrend
        df["supertrend_trend"] = trend

        # RSI - Momentum oscillator
        df["rsi"] = talib.RSI(close, timeperiod=self.rsi_period)  # type: ignore[call-overload]

        # MACD - Trend-following momentum
        macd, macd_signal, macd_hist = talib.MACD(  # type: ignore[call-overload]
            close,
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal
        )
        df["macd"] = macd
        df["macd_signal"] = macd_signal
        df["macd_hist"] = macd_hist

        # Bollinger Bands - Volatility-based levels
        upper, middle, lower = talib.BBANDS(  # type: ignore[call-overload]
            close,
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std,
            matype=0
        )
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["bb_position"] = (close - lower) / (upper - lower)  # Position within bands (0-1)

        # Volume analysis - Liquidity confirmation
        df["volume_ma"] = talib.SMA(volume, timeperiod=self.volume_ma_period)  # type: ignore[call-overload]
        df["volume_ratio"] = volume / df["volume_ma"]

        # Calculate confirmation scores for each signal type
        buy_scores = self.calculate_confirmation_score(df, "buy")
        sell_scores = self.calculate_confirmation_score(df, "sell")

        # Generate signals based on confirmation threshold
        df["signal"] = 0
        df["confirmation_score"] = 0.0

        # Buy signals - Require trend alignment + oversold + confirmation
        buy_mask = (
            (df["supertrend_trend"] == 1) &  # Uptrend confirmed
            (df["rsi"] <= self.rsi_oversold) &  # Oversold condition
            (buy_scores >= self.confirmation_threshold)  # Sufficient confirmation
        )
        df.loc[buy_mask, "signal"] = 1
        df.loc[buy_mask, "confirmation_score"] = buy_scores[buy_mask]

        # Sell signals - Require trend alignment + overbought + confirmation
        sell_mask = (
            (df["supertrend_trend"] == -1) &  # Downtrend confirmed
            (df["rsi"] >= self.rsi_overbought) &  # Overbought condition
            (sell_scores >= self.confirmation_threshold)  # Sufficient confirmation
        )
        df.loc[sell_mask, "signal"] = -1
        df.loc[sell_mask, "confirmation_score"] = sell_scores[sell_mask]

        logger.debug(
            f"Generated {df['signal'].abs().sum()} signals with confirmation threshold {self.confirmation_threshold}. "
            f"Avg confirmation score: {df['confirmation_score'].mean():.3f}"
        )

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

    def get_parameter_schema(self) -> dict:  # type: ignore[return]
        """Get parameter schema for this strategy."""
        return {
            "supertrend_period": {
                "type": "integer",
                "default": 10,
                "minimum": 3,
                "maximum": 50,
                "description": "Supertrend ATR period",
            },
            "supertrend_multiplier": {
                "type": "number",
                "default": 3.0,
                "minimum": 1.0,
                "maximum": 5.0,
                "description": "Supertrend ATR multiplier",
            },
            "rsi_period": {
                "type": "integer",
                "default": 14,
                "minimum": 2,
                "maximum": 50,
                "description": "RSI calculation period",
            },
            "rsi_overbought": {
                "type": "number",
                "default": 70.0,
                "minimum": 50.0,
                "maximum": 90.0,
                "description": "RSI overbought threshold",
            },
            "rsi_oversold": {
                "type": "number",
                "default": 30.0,
                "minimum": 10.0,
                "maximum": 50.0,
                "description": "RSI oversold threshold",
            },
            "macd_fast": {
                "type": "integer",
                "default": 12,
                "minimum": 5,
                "maximum": 50,
                "description": "MACD fast period",
            },
            "macd_slow": {
                "type": "integer",
                "default": 26,
                "minimum": 10,
                "maximum": 100,
                "description": "MACD slow period",
            },
            "macd_signal": {
                "type": "integer",
                "default": 9,
                "minimum": 5,
                "maximum": 50,
                "description": "MACD signal period",
            },
            "bb_period": {
                "type": "integer",
                "default": 20,
                "minimum": 5,
                "maximum": 50,
                "description": "Bollinger Bands period",
            },
            "bb_std": {
                "type": "number",
                "default": 2.0,
                "minimum": 1.0,
                "maximum": 3.0,
                "description": "Bollinger Bands standard deviation",
            },
            "volume_ma_period": {
                "type": "integer",
                "default": 20,
                "minimum": 5,
                "maximum": 50,
                "description": "Volume moving average period",
            },
            "confirmation_threshold": {
                "type": "number",
                "default": 0.7,
                "minimum": 0.1,
                "maximum": 1.0,
                "description": "Minimum confirmation score for signals",
            },
        }

    def get_parameter_ranges(self) -> dict[str, list[float]]:
        """Get parameter ranges for walk-forward optimization."""
        return {
            "supertrend_period": [7, 10, 14, 20],
            "supertrend_multiplier": [2.0, 2.5, 3.0, 3.5],
            "rsi_period": [10, 14, 21],
            "rsi_overbought": [65.0, 70.0, 75.0],
            "rsi_oversold": [25.0, 30.0, 35.0],
            "confirmation_threshold": [0.5, 0.6, 0.7, 0.8],
        }
