"""Advanced risk management using Kelly Criterion and dynamic position sizing."""

from dataclasses import dataclass
from typing import List

import logging

logger = logging.getLogger(__name__)


@dataclass
class KellyMetrics:
    """Store historical trade metrics for Kelly Criterion calculation."""

    win_rate: float  # 0.0 to 1.0
    avg_win_pct: float  # Average win as % of risk
    avg_loss_pct: float  # Average loss as % of risk (positive value)
    total_trades: int
    reward_risk_ratio: float  # avg_win / avg_loss


def kelly_criterion(win_rate: float, reward_risk_ratio: float) -> float:
    """Calculate Kelly fraction for position sizing.

    Args:
        win_rate: Probability of winning (0.0-1.0)
        reward_risk_ratio: Average win / Average loss

    Returns:
        Kelly fraction as decimal (0.0-1.0)

    Example:
        >>> kelly_criterion(0.60, 1.5)
        0.4  # Risk 40% per trade at full Kelly
    """
    if win_rate <= 0 or reward_risk_ratio <= 0:
        return 0.0

    kelly = (win_rate * reward_risk_ratio - (1 - win_rate)) / reward_risk_ratio
    return max(0.0, kelly)


def fractional_kelly(kelly_fraction: float, fraction: float = 0.5) -> float:
    """Apply fractional Kelly for safety.

    Args:
        kelly_fraction: Full Kelly fraction
        fraction: What fraction of Kelly to use
            - 0.25 = Quarter Kelly (safest)
            - 0.50 = Half Kelly (recommended)
            - 0.75 = Three-Quarter Kelly
            - 1.00 = Full Kelly (aggressive)

    Returns:
        Adjusted Kelly fraction
    """
    return kelly_fraction * fraction


def kelly_to_position_units(
    account_balance: float,
    kelly_fraction: float,
    entry_price: float,
    stop_loss_price: float,
) -> float:
    """Convert Kelly fraction to position size (units).

    Args:
        account_balance: Total account value
        kelly_fraction: Kelly % to risk (e.g., 0.20 for 20%)
        entry_price: Trade entry price
        stop_loss_price: Stop-loss price level

    Returns:
        Position size (number of units)
    """
    risk_dollars = account_balance * kelly_fraction
    price_risk = abs(entry_price - stop_loss_price)
    return risk_dollars / price_risk if price_risk > 0 else 0.0


def calculate_metrics_from_backtest(trades: List[dict]) -> KellyMetrics:
    """Extract Kelly-ready metrics from backtest results.

    Args:
        trades: List of trade dicts with 'pnl', 'entry', 'exit', 'stop_loss' or similar

    Returns:
        KellyMetrics object with calculated metrics
    """
    if not trades:
        return KellyMetrics(0.0, 0.0, 0.0, 0, 1.0)

    # Identify winning and losing trades
    # Handle different trade formats
    wins = []
    losses = []

    for trade in trades:
        pnl = trade.get("pnl", 0.0)
        if isinstance(pnl, (int, float)):
            if pnl > 0:
                wins.append(trade)
            elif pnl < 0:
                losses.append(trade)

    total = len(trades)
    win_rate = len(wins) / total if total > 0 else 0.0

    # Calculate average win/loss
    # Try to get as percentage of risk, otherwise use absolute values
    if wins:
        win_values = [abs(t.get("pnl", 0.0)) for t in wins]
        avg_win = sum(win_values) / len(win_values) if win_values else 0.0
    else:
        avg_win = 0.0

    if losses:
        loss_values = [abs(t.get("pnl", 0.0)) for t in losses]
        avg_loss = sum(loss_values) / len(loss_values) if loss_values else 1.0
    else:
        avg_loss = 1.0  # Default to avoid division by zero

    # Calculate reward/risk ratio
    reward_risk_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

    return KellyMetrics(
        win_rate=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        total_trades=total,
        reward_risk_ratio=reward_risk_ratio,
    )


def validate_kelly_parameters(metrics: KellyMetrics, kelly_fraction: float) -> List[str]:
    """Validate Kelly calculation is safe.

    Args:
        metrics: Kelly metrics from backtest
        kelly_fraction: Fraction of Kelly being used

    Returns:
        List of warning messages (empty if all checks pass)
    """
    warnings: List[str] = []

    # Check sufficient data
    if metrics.total_trades < 20:
        warnings.append("⚠️  Less than 20 trades: Kelly unreliable")

    # Check positive edge
    kelly_full = kelly_criterion(metrics.win_rate, metrics.reward_risk_ratio)
    if kelly_full <= 0:
        warnings.append("⚠️  No positive edge detected (Kelly ≤ 0)")

    # Check for overfitting
    if metrics.win_rate > 0.75:
        warnings.append("⚠️  Suspiciously high win rate (>75%): Possible overfitting")

    # Check using fractional Kelly
    if kelly_fraction > 0.75:
        warnings.append("⚠️  Using more than 75% Kelly: High drawdown risk")

    return warnings


class AdvancedRiskManager:
    """Advanced risk management with Kelly Criterion and dynamic position sizing."""

    def __init__(self, max_risk: float = 0.02, kelly_fraction: float = 0.25):
        """Initialize advanced risk manager.

        Args:
            max_risk: Maximum risk per trade as fraction of capital (0.02 = 2%)
            kelly_fraction: Fraction of Kelly Criterion to use (0.25 = 1/4 Kelly, conservative)
        """
        self.max_risk = max_risk
        self.kelly_fraction = kelly_fraction

    def calculate_kelly_position(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """Calculate Kelly Criterion position size.

        Args:
            win_rate: Win rate (0.0 to 1.0)
            avg_win: Average win amount (positive)
            avg_loss: Average loss amount (positive, will be negated)

        Returns:
            Kelly position size as fraction of capital
        """
        if avg_loss == 0 or win_rate <= 0:
            return 0.0

        # Calculate reward/risk ratio
        reward_risk_ratio = abs(avg_win / avg_loss)

        # Use the standalone kelly_criterion function
        kelly_full = kelly_criterion(win_rate, reward_risk_ratio)

        # Apply fractional Kelly and cap at max_risk
        kelly_adjusted = fractional_kelly(kelly_full, self.kelly_fraction)
        kelly_adjusted = max(0.0, min(kelly_adjusted, self.max_risk))

        return kelly_adjusted

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        strategy_stats: dict | None = None,
        risk_per_trade: float | None = None,
    ) -> float:
        """Calculate dynamic position size based on strategy performance.

        Args:
            price: Current price
            account_value: Total account value
            strategy_stats: Strategy performance statistics
            risk_per_trade: Override risk per trade (uses Kelly if None)

        Returns:
            Position size (number of shares/units)
        """
        if risk_per_trade is not None:
            # Use fixed risk per trade
            risk_fraction = risk_per_trade
        elif strategy_stats:
            # Use Kelly Criterion based on strategy stats
            win_rate = strategy_stats.get("win_rate", 0.5)
            avg_win = strategy_stats.get("avg_win", 0.02)
            avg_loss = abs(strategy_stats.get("avg_loss", 0.01))

            risk_fraction = self.calculate_kelly_position(win_rate, avg_win, avg_loss)
        else:
            # Default to max_risk
            risk_fraction = self.max_risk

        # Calculate position value
        position_value = account_value * risk_fraction

        # Calculate shares/units
        shares = position_value / price

        logger.debug(
            f"Position size: {shares:.4f} shares @ ${price:.2f} "
            f"(Risk: {risk_fraction * 100:.2f}% of ${account_value:.2f})",
        )

        return shares

    def should_trade(self, current_drawdown: float, max_drawdown: float = 0.15) -> bool:
        """Check if trading should continue based on drawdown.

        Args:
            current_drawdown: Current drawdown as fraction (0.15 = 15%)
            max_drawdown: Maximum allowed drawdown

        Returns:
            True if trading should continue
        """
        return abs(current_drawdown) < max_drawdown

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        multiplier: float = 2.0,
    ) -> float:
        """Calculate ATR-based dynamic stop loss.

        Args:
            entry_price: Entry price
            atr: Average True Range value
            multiplier: ATR multiplier (2.0 = 2x ATR)

        Returns:
            Stop loss price
        """
        stop_loss = entry_price - (atr * multiplier)
        return stop_loss

    def calculate_take_profit(
        self,
        entry_price: float,
        atr: float,
        risk_reward_ratio: float = 3.0,
        stop_loss_price: float | None = None,
    ) -> float:
        """Calculate ATR-based dynamic take profit.

        Args:
            entry_price: Entry price
            atr: Average True Range value
            risk_reward_ratio: Risk:Reward ratio (3.0 = 3:1)
            stop_loss_price: Stop loss price (if None, uses ATR-based)

        Returns:
            Take profit price
        """
        if stop_loss_price is None:
            stop_loss_price = self.calculate_stop_loss(entry_price, atr)

        risk = entry_price - stop_loss_price
        reward = risk * risk_reward_ratio
        take_profit = entry_price + reward

        return take_profit

    def calculate_max_position_value(
        self,
        account_value: float,
        max_position_pct: float = 0.1,
    ) -> float:
        """Calculate maximum position value.

        Args:
            account_value: Total account value
            max_position_pct: Maximum position as percentage (0.1 = 10%)

        Returns:
            Maximum position value
        """
        return account_value * max_position_pct

    def calculate_kelly_from_metrics(self, metrics: KellyMetrics) -> float:
        """Calculate Kelly position size from KellyMetrics.

        Args:
            metrics: Kelly metrics from backtest

        Returns:
            Kelly position size as fraction of capital
        """
        return self.calculate_kelly_position(
            metrics.win_rate,
            metrics.avg_win_pct,
            metrics.avg_loss_pct,
        )
