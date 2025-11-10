"""Advanced risk management using Kelly Criterion and dynamic position sizing."""

import logging

logger = logging.getLogger(__name__)


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

        # Kelly formula: f = (p * b - q) / b
        # where p = win rate, q = loss rate, b = avg_win/avg_loss
        b = abs(avg_win / avg_loss)
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b

        # Use fractional Kelly for safety (1/4 Kelly is conservative)
        fractional_kelly = max(0.0, min(kelly * self.kelly_fraction, self.max_risk))

        return fractional_kelly

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
