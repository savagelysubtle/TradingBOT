"""Centralized validation with user-friendly error messages."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    field: str
    message: str
    suggestion: str = ""
    severity: str = "error"  # error, warning, info

    def to_rich_text(self) -> str:
        """Convert to rich-formatted text."""
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[self.severity]
        color = {"error": "red", "warning": "yellow", "info": "blue"}[self.severity]

        text = f"[{color}]{icon}[/{color}] [bold]{self.field}:[/bold] {self.message}"
        if self.suggestion:
            text += f"\n  💡 [dim]{self.suggestion}[/dim]"
        return text


class BacktestValidator:
    """Validates backtest configuration with helpful messages."""

    @staticmethod
    def validate_symbol(symbol: str) -> ValidationResult:
        """Validate trading symbol format."""
        if not symbol:
            return ValidationResult(
                is_valid=False,
                field="Symbol",
                message="Symbol is required",
                suggestion="Enter a trading pair like BTC/USDT or stock ticker like AAPL"
            )

        if "/" not in symbol:
            return ValidationResult(
                is_valid=False,
                field="Symbol",
                message="Invalid symbol format",
                suggestion=f"Crypto symbols need '/' separator. Try: {symbol[:3]}/{symbol[3:] or 'USDT'}"
            )

        parts = symbol.split("/")
        if len(parts) != 2 or not all(parts):
            return ValidationResult(
                is_valid=False,
                field="Symbol",
                message="Symbol must have two parts",
                suggestion="Format: BASE/QUOTE (e.g., BTC/USDT, ETH/USDT)"
            )

        return ValidationResult(
            is_valid=True,
            field="Symbol",
            message=f"Valid format: {symbol}",
            severity="info"
        )

    @staticmethod
    def validate_candle_count(limit: int, timeframe: str) -> ValidationResult:
        """Validate candle count is reasonable."""
        if limit < 50:
            return ValidationResult(
                is_valid=False,
                field="Candle Count",
                message=f"Too few candles: {limit}",
                suggestion="Use at least 50 candles for reliable signals. Recommended: 200-1000"
            )

        if limit > 50000:
            return ValidationResult(
                is_valid=False,
                field="Candle Count",
                message=f"Too many candles: {limit:,}",
                suggestion="Maximum is 50,000. For multi-year backtests, use date range instead"
            )

        # Estimate data size
        if timeframe == "1d" and limit > 3650:
            years = limit / 365
            return ValidationResult(
                is_valid=False,
                field="Candle Count",
                message=f"Requesting {years:.1f} years of daily data",
                suggestion="Consider using a shorter period or weekly timeframe",
                severity="warning"
            )

        if 50 <= limit <= 1000:
            return ValidationResult(
                is_valid=True,
                field="Candle Count",
                message=f"{limit} candles is a good range",
                severity="info"
            )

        return ValidationResult(
            is_valid=True,
            field="Candle Count",
            message=f"{limit} candles",
            severity="info"
        )

    @staticmethod
    def validate_date_range(
        start_date: str | None,
        end_date: str | None
    ) -> ValidationResult:
        """Validate date range if provided."""
        if not start_date and not end_date:
            return ValidationResult(
                is_valid=True,
                field="Date Range",
                message="Using candle count instead",
                severity="info"
            )

        if bool(start_date) != bool(end_date):
            missing = "start date" if not start_date else "end date"
            return ValidationResult(
                is_valid=False,
                field="Date Range",
                message=f"Missing {missing}",
                suggestion="Provide both start and end dates, or leave both empty"
            )

        # Validate date format
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                field="Date Range",
                message="Invalid date format",
                suggestion=f"Use YYYY-MM-DD format. Error: {e}"
            )

        # Validate logical order
        if start >= end:
            return ValidationResult(
                is_valid=False,
                field="Date Range",
                message="Start date must be before end date",
                suggestion=f"Swap dates: start={end_date}, end={start_date}"
            )

        # Check if range is too large
        days = (end - start).days
        if days > 3650:  # ~10 years
            return ValidationResult(
                is_valid=False,
                field="Date Range",
                message=f"Date range too large: {days} days ({days/365:.1f} years)",
                suggestion="Maximum recommended range is 10 years. Consider shorter periods."
            )

        return ValidationResult(
            is_valid=True,
            field="Date Range",
            message=f"{days} days of data ({start_date} to {end_date})",
            severity="info"
        )

    @staticmethod
    def validate_ma_parameters(
        short_period: int,
        long_period: int,
        data_length: int
    ) -> list[ValidationResult]:
        """Validate MA strategy parameters."""
        results = []

        if short_period >= long_period:
            results.append(ValidationResult(
                is_valid=False,
                field="MA Periods",
                message=f"Short period ({short_period}) must be less than long period ({long_period})",
                suggestion=f"Try: short={long_period//4}, long={long_period}"
            ))

        if long_period >= data_length:
            results.append(ValidationResult(
                is_valid=False,
                field="Long MA Period",
                message=f"Period ({long_period}) is too large for {data_length} candles",
                suggestion=f"Need at least {long_period + 50} candles. Increase data or reduce period to {data_length // 2}"
            ))
        elif long_period > data_length * 0.5:
            results.append(ValidationResult(
                is_valid=False,
                field="Long MA Period",
                message=f"Period ({long_period}) uses {long_period/data_length*100:.0f}% of data",
                suggestion=f"For {data_length} candles, try period ≤ {int(data_length * 0.3)}",
                severity="warning"
            ))

        if not results:
            results.append(ValidationResult(
                is_valid=True,
                field="MA Periods",
                message=f"Periods look good: {short_period}/{long_period}",
                severity="info"
            ))

        return results

    @staticmethod
    def validate_strategy_availability(strategy_name: str, available_strategies: list[str]) -> ValidationResult:
        """Validate that strategy is available."""
        if strategy_name not in available_strategies:
            return ValidationResult(
                is_valid=False,
                field="Strategy",
                message=f"Strategy '{strategy_name}' is not available",
                suggestion="Check that required dependencies are installed (TA-Lib, scikit-learn)"
            )

        return ValidationResult(
            is_valid=True,
            field="Strategy",
            message=f"Strategy '{strategy_name}' is available",
            severity="info"
        )

    @staticmethod
    def validate_exchange_availability(exchange: str, available_exchanges: list[str]) -> ValidationResult:
        """Validate that exchange is supported."""
        if exchange not in available_exchanges:
            return ValidationResult(
                is_valid=False,
                field="Exchange",
                message=f"Exchange '{exchange}' is not supported",
                suggestion=f"Try: {', '.join(available_exchanges[:3])}..."
            )

        return ValidationResult(
            is_valid=True,
            field="Exchange",
            message=f"Exchange '{exchange}' is supported",
            severity="info"
        )

    @classmethod
    def validate_all(
        cls,
        symbol: str,
        limit: int,
        timeframe: str,
        start_date: str | None = None,
        end_date: str | None = None,
        strategy_name: str = "",
        exchange: str = "",
        available_strategies: list[str] | None = None,
        available_exchanges: list[str] | None = None,
        strategy_params: dict[str, Any] | None = None,
    ) -> list[ValidationResult]:
        """Validate entire backtest configuration."""
        results = []

        # Basic validations
        results.append(cls.validate_symbol(symbol))
        results.append(cls.validate_candle_count(limit, timeframe))
        results.append(cls.validate_date_range(start_date, end_date))

        # Strategy validation
        if strategy_name:
            if available_strategies:
                results.append(cls.validate_strategy_availability(strategy_name, available_strategies))

            # Strategy-specific validation
            if strategy_name in ["ma_crossover", "talib_ma"] and strategy_params:
                short = strategy_params.get("short_window") or strategy_params.get("short_period", 50)
                long = strategy_params.get("long_window") or strategy_params.get("long_period", 200)
                results.extend(cls.validate_ma_parameters(short, long, limit))

        # Exchange validation
        if exchange and available_exchanges:
            results.append(cls.validate_exchange_availability(exchange, available_exchanges))

        logger.debug(f"Validation completed: {len(results)} checks, {sum(1 for r in results if not r.is_valid)} errors")
        return results
