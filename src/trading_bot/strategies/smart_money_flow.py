"""Smart Money Flow Strategy - Institutional-grade trading using order flow analysis."""

import logging
import warnings

import numpy as np
import pandas as pd
import talib  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)


class SmartMoneyFlowStrategy(BaseStrategy):
    """Advanced institutional trading strategy using Smart Money Concepts.

    This strategy identifies high-probability trade setups by analyzing:
    - Order Blocks: Institutional accumulation/distribution zones
    - Fair Value Gaps: Price imbalances that need to be filled
    - Liquidity Sweeps: Stop loss hunting before directional moves
    - Market Structure: Higher highs/higher lows shifts
    - Volume Confirmation: Ensuring moves have institutional participation
    """

    def __init__(
        self,
        order_block_lookback: int = 50,
        fvg_lookback: int = 20,
        volume_ma_period: int = 20,
        atr_period: int = 14,
        min_volume_ratio: float = 1.2,
        risk_per_trade: float = 0.01,
        reward_risk_ratio: float = 2.0,
        max_positions: int = 3,
        simplified_mode: bool = True,  # New parameter for easier testing
        daily_mode: bool = False,  # New parameter for daily timeframe adaptation
    ):
        """Initialize Smart Money Flow Strategy.

        Args:
            order_block_lookback: Periods to look back for order block identification
            fvg_lookback: Periods to look back for fair value gap detection
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation (risk management)
            min_volume_ratio: Minimum volume ratio above average for valid signals
            risk_per_trade: Risk percentage per trade (0.01 = 1%)
            reward_risk_ratio: Minimum reward-to-risk ratio for entries
            max_positions: Maximum concurrent positions allowed
        """
        super().__init__(
            name="SmartMoneyFlowStrategy",
            order_block_lookback=order_block_lookback,
            fvg_lookback=fvg_lookback,
            volume_ma_period=volume_ma_period,
            atr_period=atr_period,
            min_volume_ratio=min_volume_ratio,
            risk_per_trade=risk_per_trade,
            reward_risk_ratio=reward_risk_ratio,
            max_positions=max_positions,
            simplified_mode=simplified_mode,
            daily_mode=daily_mode,
        )

        self.order_block_lookback = order_block_lookback
        self.fvg_lookback = fvg_lookback
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.min_volume_ratio = min_volume_ratio
        self.risk_per_trade = risk_per_trade
        self.reward_risk_ratio = reward_risk_ratio
        self.max_positions = max_positions
        self.simplified_mode = simplified_mode
        self.daily_mode = daily_mode

        # Risk management attributes
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.recent_trades = []  # Track recent trade outcomes
        self.max_recent_trades = 10
        self.dynamic_position_sizing = True

    def identify_order_blocks(self, df: pd.DataFrame) -> pd.Series:
        """Identify order blocks (institutional accumulation/distribution zones)."""
        order_blocks = pd.Series(False, index=df.index)

        # Need minimum data for analysis
        if len(df) < self.order_block_lookback + 10:
            return order_blocks

        for i in range(self.order_block_lookback, len(df)):
            current_idx = df.index[i]

            # Must have sufficient volume (at least 2x average for institutional interest)
            if df.loc[current_idx, 'volume_ratio'] < max(self.min_volume_ratio * 2, 2.5):
                continue

            # Calculate candle metrics
            body_size = abs(df.loc[current_idx, 'close'] - df.loc[current_idx, 'open'])
            total_range = df.loc[current_idx, 'high'] - df.loc[current_idx, 'low']
            upper_wick = df.loc[current_idx, 'high'] - max(df.loc[current_idx, 'open'], df.loc[current_idx, 'close'])
            lower_wick = min(df.loc[current_idx, 'open'], df.loc[current_idx, 'close']) - df.loc[current_idx, 'low']

            if total_range == 0:
                continue

            body_ratio = body_size / total_range

            # Check for institutional order block characteristics
            is_bullish_ob = False
            is_bearish_ob = False

            # Bullish Order Block: Strong bullish candle with rejection of lower levels
            if (df.loc[current_idx, 'close'] > df.loc[current_idx, 'open'] and  # Bullish candle
                body_ratio > 0.6 and  # Strong body
                lower_wick < upper_wick * 0.3 and  # Small lower wick (rejection of lower levels)
                upper_wick < body_size * 0.5):  # Controlled upper wick

                # Additional confirmation: check if this breaks recent resistance
                recent_highs = df.loc[df.index[max(0, i-10):i], 'high'].max()
                if df.loc[current_idx, 'close'] > recent_highs * 0.998:  # Breaks recent resistance
                    is_bullish_ob = True

            # Bearish Order Block: Strong bearish candle with rejection of higher levels
            elif (df.loc[current_idx, 'close'] < df.loc[current_idx, 'open'] and  # Bearish candle
                  body_ratio > 0.6 and  # Strong body
                  upper_wick < lower_wick * 0.3 and  # Small upper wick (rejection of higher levels)
                  lower_wick < body_size * 0.5):  # Controlled lower wick

                # Additional confirmation: check if this breaks recent support
                recent_lows = df.loc[df.index[max(0, i-10):i], 'low'].min()
                if df.loc[current_idx, 'close'] < recent_lows * 1.002:  # Breaks recent support
                    is_bearish_ob = True

            # Mark order block if conditions met
            if is_bullish_ob or is_bearish_ob:
                order_blocks.loc[current_idx] = True

        return order_blocks

    def identify_fair_value_gaps(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """Identify fair value gaps (price imbalances that need to be filled)."""
        bullish_fvg = pd.Series(False, index=df.index)
        bearish_fvg = pd.Series(False, index=df.index)

        # Need sufficient data for analysis
        if len(df) < self.fvg_lookback + 5:
            return bullish_fvg, bearish_fvg

        for i in range(3, len(df)):
            current_idx = df.index[i]

            # Calculate average true range for context
            lookback_data = df.loc[df.index[max(0, i-self.fvg_lookback):i]]
            avg_atr = lookback_data['atr'].mean() if 'atr' in df.columns else lookback_data['high'].std()

            # Bullish FVG: Gap between previous candle's high and current candle's low
            # This represents an area where price should return to fill the gap
            prev_candle_high = df.loc[df.index[i-1], 'high']
            current_candle_low = df.loc[current_idx, 'low']

            if current_candle_low > prev_candle_high:
                gap_size = current_candle_low - prev_candle_high

                # Gap must be significant relative to ATR (at least 0.75 ATR)
                if avg_atr > 0 and gap_size > avg_atr * 0.75:
                    # Additional validation: ensure this is a true imbalance
                    # Check that the previous candle didn't fully fill any prior gap
                    prev_prev_high = df.loc[df.index[i-2], 'high'] if i >= 2 else prev_candle_high
                    if current_candle_low > prev_prev_high:
                        # Check volume confirmation during gap formation
                        gap_volume = (df.loc[df.index[i-1], 'volume'] + df.loc[current_idx, 'volume']) / 2
                        avg_volume = df.loc[df.index[max(0, i-10):i], 'volume'].mean()

                        if gap_volume > avg_volume * 1.2:  # Above average volume during gap
                            bullish_fvg.loc[current_idx] = True

            # Bearish FVG: Gap between previous candle's low and current candle's high
            prev_candle_low = df.loc[df.index[i-1], 'low']
            current_candle_high = df.loc[current_idx, 'high']

            if current_candle_high < prev_candle_low:
                gap_size = prev_candle_low - current_candle_high

                # Gap must be significant relative to ATR (at least 0.75 ATR)
                if avg_atr > 0 and gap_size > avg_atr * 0.75:
                    # Additional validation: ensure this is a true imbalance
                    prev_prev_low = df.loc[df.index[i-2], 'low'] if i >= 2 else prev_candle_low
                    if current_candle_high < prev_prev_low:
                        # Check volume confirmation during gap formation
                        gap_volume = (df.loc[df.index[i-1], 'volume'] + df.loc[current_idx, 'volume']) / 2
                        avg_volume = df.loc[df.index[max(0, i-10):i], 'volume'].mean()

                        if gap_volume > avg_volume * 1.2:  # Above average volume during gap
                            bearish_fvg.loc[current_idx] = True

        return bullish_fvg, bearish_fvg

    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """Detect liquidity sweeps (stop loss hunting) with proper wick analysis."""
        bullish_sweeps = pd.Series(False, index=df.index)
        bearish_sweeps = pd.Series(False, index=df.index)

        # Need at least 10 candles for proper analysis
        if len(df) < 10:
            return bullish_sweeps, bearish_sweeps

        for i in range(5, len(df)):  # Start after warmup period
            current_idx = df.index[i]

            # Calculate wick metrics
            current_high = df.loc[current_idx, 'high']
            current_low = df.loc[current_idx, 'low']
            current_open = df.loc[current_idx, 'open']
            current_close = df.loc[current_idx, 'close']

            body_size = abs(current_close - current_open)
            total_range = current_high - current_low

            if total_range == 0:
                continue

            upper_wick = current_high - max(current_open, current_close)
            lower_wick = min(current_open, current_close) - current_low

            upper_wick_ratio = upper_wick / total_range
            lower_wick_ratio = lower_wick / total_range

            # Look back 5-10 candles for liquidity levels
            lookback_period = min(10, i)
            recent_highs = df.loc[df.index[i-lookback_period:i], 'high'].max()
            recent_lows = df.loc[df.index[i-lookback_period:i], 'low'].min()

            # Bullish Sweep: Breaks below recent support then rejects lower levels
            if (current_low < recent_lows * 1.001 and  # Breaks recent low (liquidity level)
                lower_wick_ratio > 0.6 and  # Significant lower wick rejection
                current_close > current_open and  # Closes higher (rejection)
                upper_wick_ratio < 0.3 and  # Small upper wick
                df.loc[current_idx, 'volume_ratio'] > max(self.min_volume_ratio, 1.8) and  # Volume confirmation
                lower_wick > body_size * 1.5):  # Wick should be at least 1.5x body size
                bullish_sweeps.loc[current_idx] = True

            # Bearish Sweep: Breaks above recent resistance then rejects higher levels
            if (current_high > recent_highs * 0.999 and  # Breaks recent high (liquidity level)
                upper_wick_ratio > 0.6 and  # Significant upper wick rejection
                current_close < current_open and  # Closes lower (rejection)
                lower_wick_ratio < 0.3 and  # Small lower wick
                df.loc[current_idx, 'volume_ratio'] > max(self.min_volume_ratio, 1.8) and  # Volume confirmation
                upper_wick > body_size * 1.5):  # Wick should be at least 1.5x body size
                bearish_sweeps.loc[current_idx] = True

        return bullish_sweeps, bearish_sweeps

    def calculate_signal_quality(self, df: pd.DataFrame, idx: int, signal_type: str) -> float:
        """Calculate signal quality score based on confluence factors."""
        score = 0.0

        # Base score from market structure alignment
        structure = df.loc[idx, 'market_structure']
        if ((signal_type == 'bullish' and structure == 'bullish') or
            (signal_type == 'bearish' and structure == 'bearish')):
            score += 0.3
        elif structure == 'neutral':
            score += 0.1  # Neutral is better than counter-trend

        # Volume confirmation strength
        volume_ratio = df.loc[idx, 'volume_ratio']
        if volume_ratio >= 3.0:
            score += 0.25
        elif volume_ratio >= 2.0:
            score += 0.15
        elif volume_ratio >= 1.5:
            score += 0.1

        # Count institutional signal confluence
        institutional_signals = 0
        if df.loc[idx, 'order_block']:
            institutional_signals += 1
        if (signal_type == 'bullish' and df.loc[idx, 'bullish_fvg']) or \
           (signal_type == 'bearish' and df.loc[idx, 'bearish_fvg']):
            institutional_signals += 1
        if (signal_type == 'bullish' and df.loc[idx, 'bullish_sweep']) or \
           (signal_type == 'bearish' and df.loc[idx, 'bearish_sweep']):
            institutional_signals += 1

        # Score based on confluence
        if institutional_signals >= 2:
            score += 0.3  # Strong confluence
        elif institutional_signals == 1:
            score += 0.15  # Moderate confluence
        else:
            score += 0.05  # Weak/no confluence

        # Trend alignment with EMA
        if 'ema_trend' in df.columns and not pd.isna(df.loc[idx, 'ema_trend']):
            current_price = df.loc[idx, 'close']
            ema_price = df.loc[idx, 'ema_trend']
            trend_alignment = abs(current_price - ema_price) / ema_price

            if ((signal_type == 'bullish' and current_price > ema_price) or
                (signal_type == 'bearish' and current_price < ema_price)):
                if trend_alignment > 0.005:  # Strong trend alignment
                    score += 0.1
                else:  # Moderate trend alignment
                    score += 0.05

        # ATR-based volatility filter (prefer calmer markets for better entries)
        if 'atr' in df.columns and not pd.isna(df.loc[idx, 'atr']):
            avg_atr = df.loc[df.index[max(0, df.index.get_loc(idx)-20):df.index.get_loc(idx)+1], 'atr'].mean()
            current_atr = df.loc[idx, 'atr']

            if avg_atr > 0:
                atr_ratio = current_atr / avg_atr
                if atr_ratio < 1.2:  # Less volatile = better conditions
                    score += 0.05
                elif atr_ratio > 2.0:  # Very volatile = worse conditions
                    score -= 0.05

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))

    def update_risk_metrics(self, trade_result: bool) -> None:
        """Update risk management metrics after each trade.

        Args:
            trade_result: True for profitable trade, False for loss
        """
        # Track recent trades
        self.recent_trades.append(trade_result)
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades.pop(0)

        # Update consecutive losses
        if not trade_result:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def should_restrict_trading(self) -> tuple[bool, float]:
        """Check if trading should be restricted based on risk metrics.

        Returns:
            tuple: (should_restrict, position_size_multiplier)
        """
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return True, 0.0  # Complete restriction

        # Check recent performance
        if len(self.recent_trades) >= 5:
            recent_win_rate = sum(self.recent_trades) / len(self.recent_trades)

            if recent_win_rate < 0.3:  # Less than 30% win rate recently
                return True, 0.5  # Reduce position size by half
            elif recent_win_rate < 0.4:  # Less than 40% win rate
                return False, 0.75  # Reduce position size by 25%

        return False, 1.0  # Normal trading

    def get_dynamic_position_size(self, base_position_size: float, signal_quality: float) -> float:
        """Calculate dynamic position size based on risk metrics and signal quality.

        Args:
            base_position_size: Base position size from risk calculation
            signal_quality: Signal quality score (0-1)

        Returns:
            Adjusted position size
        """
        if not self.dynamic_position_sizing:
            return base_position_size

        # Check risk restrictions
        restrict_trading, size_multiplier = self.should_restrict_trading()

        if restrict_trading and size_multiplier == 0.0:
            return 0.0  # No trading allowed

        # Base adjustment from risk metrics
        adjusted_size = base_position_size * size_multiplier

        # Quality-based adjustment (better signals = larger positions)
        quality_multiplier = 0.5 + (signal_quality * 0.5)  # 0.5 to 1.0 range
        adjusted_size *= quality_multiplier

        # Consecutive loss protection
        if self.consecutive_losses > 0:
            loss_multiplier = max(0.3, 1.0 - (self.consecutive_losses * 0.2))
            adjusted_size *= loss_multiplier

        return adjusted_size

    def analyze_market_structure(self, df: pd.DataFrame) -> pd.Series:
        """Analyze market structure using trend-following approach."""
        structure = pd.Series("neutral", index=df.index)

        # Need at least 20 candles for analysis
        if len(df) < 20:
            return structure

        # Calculate EMA trend for fallback (same as used in signal generation)
        ema_trend = talib.EMA(df['close'].values, timeperiod=20)
        df_copy = df.copy()
        df_copy['ema_trend'] = ema_trend

        # Use simplified trend-following market structure
        # This is more practical than strict swing point analysis

        # Calculate short-term trend (5-period SMA)
        short_trend = talib.SMA(df['close'].values, timeperiod=5)
        # Calculate medium-term trend (20-period SMA)
        medium_trend = talib.SMA(df['close'].values, timeperiod=20)

        for i in range(len(df)):
            if pd.isna(short_trend[i]) or pd.isna(medium_trend[i]):
                structure.iloc[i] = "neutral"
                continue

            # Bullish structure: short-term trend above medium-term trend
            if short_trend[i] > medium_trend[i] * 1.001:  # 0.1% above for stability
                structure.iloc[i] = "bullish"
            # Bearish structure: short-term trend below medium-term trend
            elif short_trend[i] < medium_trend[i] * 0.999:  # 0.1% below for stability
                structure.iloc[i] = "bearish"
            else:
                # Neutral - use EMA for finer bias
                if not pd.isna(ema_trend[i]):
                    current_price = df.iloc[i]['close']
                    ema_price = ema_trend[i]
                    if current_price > ema_price * 1.002:  # 0.2% above EMA
                        structure.iloc[i] = "bullish"
                    elif current_price < ema_price * 0.998:  # 0.2% below EMA
                        structure.iloc[i] = "bearish"
                    else:
                        structure.iloc[i] = "neutral"
                else:
                    structure.iloc[i] = "neutral"

        return structure

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate trading signals using Smart Money Flow analysis."""
        df = data.copy()

        # Check minimum data requirements
        min_periods = max(self.order_block_lookback, self.fvg_lookback, self.volume_ma_period, self.atr_period)
        if len(df) < min_periods:
            logger.warning(
                f"Insufficient data for Smart Money Flow: need {min_periods} periods, got {len(df)}"
            )
            df["signal"] = 0
            return df

        # Calculate volume metrics
        volume_ma = talib.SMA(df["volume"].values, timeperiod=self.volume_ma_period)  # type: ignore[call-overload]
        df["volume_ma"] = volume_ma
        df["volume_ratio"] = df["volume"] / df["volume_ma"]

        # Calculate ATR for risk management
        atr = talib.ATR(df["high"].values, df["low"].values, df["close"].values, timeperiod=self.atr_period)  # type: ignore[call-overload]
        df["atr"] = atr

        # Identify Smart Money concepts
        order_blocks = self.identify_order_blocks(df)
        df["order_block"] = order_blocks

        bullish_fvg, bearish_fvg = self.identify_fair_value_gaps(df)
        df["bullish_fvg"] = bullish_fvg
        df["bearish_fvg"] = bearish_fvg

        bullish_sweeps, bearish_sweeps = self.detect_liquidity_sweeps(df)
        df["bullish_sweep"] = bullish_sweeps
        df["bearish_sweep"] = bearish_sweeps

        market_structure = self.analyze_market_structure(df)
        df["market_structure"] = market_structure

        # Add EMA trend to dataframe (calculated in analyze_market_structure)
        df['ema_trend'] = talib.EMA(df['close'].values, timeperiod=20)

        # Debug: Count signals
        order_blocks_count = df['order_block'].sum()
        bullish_fvg_count = df['bullish_fvg'].sum()
        bearish_fvg_count = df['bearish_fvg'].sum()
        bullish_sweep_count = df['bullish_sweep'].sum()
        bearish_sweep_count = df['bearish_sweep'].sum()
        bullish_structure_count = (df['market_structure'] == 'bullish').sum()
        bearish_structure_count = (df['market_structure'] == 'bearish').sum()

        logger.info(f"Smart Money Flow signal counts: OrderBlocks={order_blocks_count}, "
                   f"BullishFVG={bullish_fvg_count}, BearishFVG={bearish_fvg_count}, "
                   f"BullishSweeps={bullish_sweep_count}, BearishSweeps={bearish_sweep_count}, "
                   f"BullishStructure={bullish_structure_count}, BearishStructure={bearish_structure_count}")

        # Initialize signals
        df["signal"] = 0
        df["entry_price"] = np.nan
        df["stop_loss"] = np.nan
        df["take_profit"] = np.nan
        df["confidence"] = 0.0

        # Generate buy signals
        bullish_signals = 0
        bearish_signals = 0

        if self.daily_mode:
            # Daily mode: Use simple trend-following with moving averages
            bullish_signals, bearish_signals = self._generate_daily_signals(df)
        else:
            # Intraday mode: Use full Smart Money Flow logic
            bullish_signals, bearish_signals = self._generate_intraday_signals(df)
        logger.info(f"  Signals Generated: {bullish_signals} bullish, {bearish_signals} bearish")

        # Log summary
        signals_generated = df["signal"].abs().sum()
        logger.info(
            f"Smart Money Flow generated {signals_generated} signals from {len(df)} candles. "
            f"Average confidence: {df['confidence'].mean():.3f}"
        )

        return df

    def get_parameter_schema(self) -> dict:  # type: ignore[return]
        """Get parameter schema for this strategy."""
        return {
            "order_block_lookback": {
                "type": "integer",
                "default": 50,
                "minimum": 10,
                "maximum": 100,
                "description": "Periods to look back for order block identification",
            },
            "fvg_lookback": {
                "type": "integer",
                "default": 20,
                "minimum": 5,
                "maximum": 50,
                "description": "Periods to look back for fair value gap detection",
            },
            "volume_ma_period": {
                "type": "integer",
                "default": 20,
                "minimum": 5,
                "maximum": 50,
                "description": "Period for volume moving average calculation",
            },
            "atr_period": {
                "type": "integer",
                "default": 14,
                "minimum": 5,
                "maximum": 50,
                "description": "Period for ATR calculation (risk management)",
            },
            "min_volume_ratio": {
                "type": "number",
                "default": 1.2,
                "minimum": 1.0,
                "maximum": 3.0,
                "description": "Minimum volume ratio above average for valid signals",
            },
            "risk_per_trade": {
                "type": "number",
                "default": 0.01,
                "minimum": 0.005,
                "maximum": 0.05,
                "description": "Risk percentage per trade (0.01 = 1%)",
            },
            "reward_risk_ratio": {
                "type": "number",
                "default": 2.0,
                "minimum": 1.5,
                "maximum": 5.0,
                "description": "Minimum reward-to-risk ratio for entries",
            },
            "max_positions": {
                "type": "integer",
                "default": 3,
                "minimum": 1,
                "maximum": 10,
                "description": "Maximum concurrent positions allowed",
            },
            "simplified_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use simplified signal conditions for easier testing (market structure + volume + one institutional signal vs all institutional signals required)",
            },
            "daily_mode": {
                "type": "boolean",
                "default": False,
                "description": "Use daily timeframe mode with trend-following MA strategy instead of intraday Smart Money Flow",
            },
        }

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.01,
    ) -> float:
        """Calculate position size based on risk management."""
        risk_amount = account_value * risk_per_trade

        # Use ATR-based stop distance if available, otherwise default
        if hasattr(self, 'current_atr') and self.current_atr > 0:
            stop_distance = self.current_atr * 1.5
        else:
            stop_distance = price * 0.02  # Default 2% stop

        risk_per_share = abs(price - (price - stop_distance))

        if risk_per_share <= 0:
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        return min(position_size, max_shares)

    def _generate_daily_signals(self, df: pd.DataFrame) -> tuple[int, int]:
        """Generate signals for daily timeframe using trend-following approach."""
        logger.info("Using daily mode signal generation")

        # Add moving averages for trend identification
        df['sma_20'] = talib.SMA(df['close'].values, timeperiod=20)
        df['sma_50'] = talib.SMA(df['close'].values, timeperiod=50)

        bullish_signals = 0
        bearish_signals = 0

        for i in range(50, len(df)):  # Start after MA warmup
            if pd.isna(df.iloc[i]['sma_20']) or pd.isna(df.iloc[i]['sma_50']) or pd.isna(df.iloc[i]['atr']):
                continue

            current_idx = df.index[i]
            prev_idx = df.index[i-1]

            # Bullish signal: Price above both MAs, MA20 > MA50, volume above average
            bullish_condition = (
                df.loc[current_idx, 'close'] > df.loc[current_idx, 'sma_20'] and
                df.loc[current_idx, 'sma_20'] > df.loc[current_idx, 'sma_50'] and
                df.loc[current_idx, 'volume_ratio'] > 1.0 and
                df.loc[prev_idx, 'close'] <= df.loc[prev_idx, 'sma_20']  # Break above MA
            )

            if bullish_condition:
                entry_price = df.loc[current_idx, 'close']
                stop_distance = df.loc[current_idx, 'atr'] * 2.0  # Wider stops for daily
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + (stop_distance * self.reward_risk_ratio)

                df.loc[current_idx, "signal"] = 1
                df.loc[current_idx, "entry_price"] = entry_price
                df.loc[current_idx, "stop_loss"] = stop_loss
                df.loc[current_idx, "take_profit"] = take_profit
                df.loc[current_idx, "confidence"] = 0.7

                bullish_signals += 1
                logger.debug(f"Daily bullish signal at {current_idx}: Entry={entry_price:.4f}")

            # Bearish signal: Price below both MAs, MA20 < MA50, volume above average
            bearish_condition = (
                df.loc[current_idx, 'close'] < df.loc[current_idx, 'sma_20'] and
                df.loc[current_idx, 'sma_20'] < df.loc[current_idx, 'sma_50'] and
                df.loc[current_idx, 'volume_ratio'] > 1.0 and
                df.loc[prev_idx, 'close'] >= df.loc[prev_idx, 'sma_20']  # Break below MA
            )

            if bearish_condition:
                entry_price = df.loc[current_idx, 'close']
                stop_distance = df.loc[current_idx, 'atr'] * 2.0
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - (stop_distance * self.reward_risk_ratio)

                df.loc[current_idx, "signal"] = -1
                df.loc[current_idx, "entry_price"] = entry_price
                df.loc[current_idx, "stop_loss"] = stop_loss
                df.loc[current_idx, "take_profit"] = take_profit
                df.loc[current_idx, "confidence"] = 0.7

                bearish_signals += 1
                logger.debug(f"Daily bearish signal at {current_idx}: Entry={entry_price:.4f}")

        return bullish_signals, bearish_signals

    def _generate_intraday_signals(self, df: pd.DataFrame) -> tuple[int, int]:
        """Generate signals for intraday timeframe using Smart Money Flow logic."""
        logger.info("Using improved intraday Smart Money Flow signal generation")

        # EMA trend already added in generate_signals method

        bullish_signals = 0
        bearish_signals = 0
        last_signal_idx = None
        min_bars_between_signals = 4  # Minimum 4 bars (1 hour) between signals

        for i in range(20, len(df)):  # Start after EMA warmup
            if pd.isna(df.iloc[i]["atr"]) or pd.isna(df.iloc[i]["ema_trend"]):
                continue

            current_idx = df.index[i]

            # Check minimum time between signals to avoid whipsaws
            skip_signal = False
            if last_signal_idx is not None:
                bars_since_last_signal = i - df.index.get_loc(last_signal_idx)
                if bars_since_last_signal < min_bars_between_signals:
                    skip_signal = True

            # Risk management check - skip if trading is restricted
            restrict_trading, _ = self.should_restrict_trading()
            if restrict_trading:
                logger.debug(f"Trading restricted at {current_idx} due to risk management")
                continue

            if skip_signal:
                continue

            # Enhanced Bullish Setup with trend confirmation and tighter filters
        # Calculate signal quality first
        bullish_quality = self.calculate_signal_quality(df, current_idx, 'bullish')

        # Minimum quality threshold - only high-quality signals
        min_quality_threshold = 0.4 if self.simplified_mode else 0.6

        if bullish_quality < min_quality_threshold:
            bullish_condition = False
        else:
            if self.simplified_mode:
                # Simplified: Market structure + volume + trend + institutional confluence
                bullish_condition = (
                    (df.loc[current_idx, "market_structure"] == "bullish" or
                     df.loc[current_idx, "market_structure"] == "neutral") and  # Allow neutral in trending markets
                    df.loc[current_idx, "volume_ratio"] > max(self.min_volume_ratio, 2.0) and  # Higher volume threshold
                    df.loc[current_idx, "close"] > df.loc[current_idx, "ema_trend"] and  # Trend confirmation
                    bullish_quality >= min_quality_threshold  # Quality filter
                )
            else:
                # Full institutional: Strong confluence required
                institutional_count = sum([
                    df.loc[current_idx, "order_block"],
                    df.loc[current_idx, "bullish_fvg"],
                    df.loc[current_idx, "bullish_sweep"]
                ])
                bullish_condition = (
                    institutional_count >= 2 and  # At least 2 institutional signals
                    df.loc[current_idx, "market_structure"] == "bullish" and
                    df.loc[current_idx, "volume_ratio"] > max(self.min_volume_ratio, 2.5) and  # Very high volume
                    df.loc[current_idx, "close"] > df.loc[current_idx, "ema_trend"] and
                    bullish_quality >= min_quality_threshold
                )

            if bullish_condition:
                entry_price = df.loc[current_idx, "close"]
                # Dynamic stop distance based on ATR and quality
                base_stop = df.loc[current_idx, "atr"] * 1.2  # Slightly wider stops for better entries
                quality_multiplier = 1.0 - (bullish_quality - 0.5) * 0.5  # Better quality = tighter stops
                stop_distance = min(base_stop * quality_multiplier, entry_price * 0.04)  # Max 4% stop
                stop_loss = entry_price - stop_distance

                # Dynamic take profit based on quality and market conditions
                if bullish_quality > 0.8:
                    rr_ratio = 3.0  # High quality = higher target
                elif bullish_quality > 0.7:
                    rr_ratio = 2.5
                else:
                    rr_ratio = 2.0

                take_profit = entry_price + (stop_distance * rr_ratio)

                df.loc[current_idx, "signal"] = 1
                df.loc[current_idx, "entry_price"] = entry_price
                df.loc[current_idx, "stop_loss"] = stop_loss
                df.loc[current_idx, "take_profit"] = take_profit
                df.loc[current_idx, "confidence"] = bullish_quality

                bullish_signals += 1
                last_signal_idx = current_idx
                logger.info(f"BULLISH SIGNAL: {current_idx} Entry={entry_price:.4f}, SL={stop_loss:.4f}, TP={take_profit:.4f}, Quality={bullish_quality:.3f}")
                logger.info(f"  Market Structure: {df.loc[current_idx, 'market_structure']}, Volume Ratio: {df.loc[current_idx, 'volume_ratio']:.2f}, EMA Trend: {df.loc[current_idx, 'ema_trend']:.4f}")

            # Enhanced Bearish Setup with trend confirmation and tighter filters
            bearish_quality = self.calculate_signal_quality(df, current_idx, 'bearish')

            if bearish_quality < min_quality_threshold:
                bearish_condition = False
            else:
                if self.simplified_mode:
                    # Simplified: Market structure + volume + trend + institutional confluence
                    bearish_condition = (
                        (df.loc[current_idx, "market_structure"] == "bearish" or
                         df.loc[current_idx, "market_structure"] == "neutral") and  # Allow neutral in trending markets
                        df.loc[current_idx, "volume_ratio"] > max(self.min_volume_ratio, 2.0) and  # Higher volume threshold
                        df.loc[current_idx, "close"] < df.loc[current_idx, "ema_trend"] and  # Trend confirmation
                        bearish_quality >= min_quality_threshold  # Quality filter
                    )
                else:
                    # Full institutional: Strong confluence required
                    institutional_count = sum([
                        df.loc[current_idx, "order_block"],
                        df.loc[current_idx, "bearish_fvg"],
                        df.loc[current_idx, "bearish_sweep"]
                    ])
                    bearish_condition = (
                        institutional_count >= 2 and  # At least 2 institutional signals
                        df.loc[current_idx, "market_structure"] == "bearish" and
                        df.loc[current_idx, "volume_ratio"] > max(self.min_volume_ratio, 2.5) and  # Very high volume
                        df.loc[current_idx, "close"] < df.loc[current_idx, "ema_trend"] and
                        bearish_quality >= min_quality_threshold
                    )

            if bearish_condition:
                entry_price = df.loc[current_idx, "close"]
                # Dynamic stop distance based on ATR and quality
                base_stop = df.loc[current_idx, "atr"] * 1.2  # Slightly wider stops for better entries
                quality_multiplier = 1.0 - (bearish_quality - 0.5) * 0.5  # Better quality = tighter stops
                stop_distance = min(base_stop * quality_multiplier, entry_price * 0.04)  # Max 4% stop
                stop_loss = entry_price + stop_distance

                # Dynamic take profit based on quality and market conditions
                if bearish_quality > 0.8:
                    rr_ratio = 3.0  # High quality = higher target
                elif bearish_quality > 0.7:
                    rr_ratio = 2.5
                else:
                    rr_ratio = 2.0

                take_profit = entry_price - (stop_distance * rr_ratio)

                df.loc[current_idx, "signal"] = -1
                df.loc[current_idx, "entry_price"] = entry_price
                df.loc[current_idx, "stop_loss"] = stop_loss
                df.loc[current_idx, "take_profit"] = take_profit
                df.loc[current_idx, "confidence"] = bearish_quality

                bearish_signals += 1
                last_signal_idx = current_idx
                logger.info(f"BEARISH SIGNAL: {current_idx} Entry={entry_price:.4f}, SL={stop_loss:.4f}, TP={take_profit:.4f}, Quality={bearish_quality:.3f}")
                logger.info(f"  Market Structure: {df.loc[current_idx, 'market_structure']}, Volume Ratio: {df.loc[current_idx, 'volume_ratio']:.2f}, EMA Trend: {df.loc[current_idx, 'ema_trend']:.4f}")

        logger.info(f"Generated {bullish_signals} bullish and {bearish_signals} bearish signals with improved filters")
        return bullish_signals, bearish_signals
