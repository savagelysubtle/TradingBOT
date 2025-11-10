<!-- Phase 1: TUI Critical UX Improvements -->
# Phase 1: Critical UX Improvements for Trading Bot TUI

## Overview

Focus on immediate, high-impact UX improvements that make the TUI more intuitive, responsive, and user-friendly. This phase tackles the top 3 pain points identified in the analysis.

**Duration**: 1-2 weeks
**Focus**: Loading states, error messages, and initial wizard refactor

---

## Priority 1: Better Progress & Loading States 🚨

### Problem
Users don't know what's happening during long operations (data fetching, backtesting). Text-based status updates are unclear.

### Solution: Create Visual Feedback System

#### Task 1.1: Create LoadingSpinner Widget
**File**: `src/trading_bot/interfaces/widgets/loading_spinner.py`

```python
"""Loading spinner widget with customizable messages."""

from textual.widgets import Static
from textual.reactive import reactive


class LoadingSpinner(Static):
    """Animated loading spinner with status message."""

    DEFAULT_CSS = """
    LoadingSpinner {
        height: 5;
        width: 100%;
        content-align: center middle;
        background: $boost;
        border: solid $primary;
    }
    """

    message = reactive("Loading...")
    is_active = reactive(True)

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Loading...", **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.frame_index = 0

    def on_mount(self) -> None:
        """Start animation."""
        self.set_interval(0.1, self.animate)

    def animate(self) -> None:
        """Update spinner animation."""
        if not self.is_active:
            return

        frame = self.SPINNER_FRAMES[self.frame_index]
        self.update(f"[cyan]{frame}[/cyan] {self.message}")
        self.frame_index = (self.frame_index + 1) % len(self.SPINNER_FRAMES)

    def stop(self, success_message: str | None = None) -> None:
        """Stop spinner and show result."""
        self.is_active = False
        if success_message:
            self.update(f"[green]✓[/green] {success_message}")
        else:
            self.update("")
```

**Export in**: `src/trading_bot/interfaces/widgets/__init__.py`

#### Task 1.2: Create EnhancedProgressBar Widget
**File**: `src/trading_bot/interfaces/widgets/enhanced_progress_bar.py`

```python
"""Enhanced progress bar with stages and cancellation."""

from textual import on, work
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, ProgressBar, Static


class EnhancedProgressBar(Vertical):
    """Progress bar with stage tracking and cancel button."""

    DEFAULT_CSS = """
    EnhancedProgressBar {
        height: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }

    EnhancedProgressBar .stage-label {
        text-align: center;
        margin-bottom: 1;
    }

    EnhancedProgressBar .percentage {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    progress = reactive(0.0)
    stage = reactive("")
    total_stages = reactive(1)
    current_stage = reactive(1)
    can_cancel = reactive(True)

    def __init__(self, stages: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.stages = stages or ["Processing"]
        self.total_stages = len(self.stages)
        self._cancel_callback = None

    def compose(self):
        """Compose progress widgets."""
        yield Static(
            f"Stage {self.current_stage}/{self.total_stages}: {self.stage}",
            classes="stage-label",
            id="stage-label"
        )
        yield ProgressBar(total=100.0, show_eta=False, id="progress-bar")
        yield Static("0%", classes="percentage", id="percentage-label")
        if self.can_cancel:
            yield Button("Cancel", variant="error", id="btn-cancel-progress")

    def watch_progress(self, progress: float) -> None:
        """Update progress bar."""
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=progress)

            percent = self.query_one("#percentage-label", Static)
            percent.update(f"{progress:.0f}%")
        except Exception:
            pass

    def watch_stage(self, stage: str) -> None:
        """Update stage label."""
        try:
            label = self.query_one("#stage-label", Static)
            label.update(f"Stage {self.current_stage}/{self.total_stages}: {stage}")
        except Exception:
            pass

    def set_stage(self, stage_index: int) -> None:
        """Set current stage."""
        if 0 <= stage_index < len(self.stages):
            self.current_stage = stage_index + 1
            self.stage = self.stages[stage_index]

    def set_cancel_callback(self, callback) -> None:
        """Set callback for cancel button."""
        self._cancel_callback = callback

    @on(Button.Pressed, "#btn-cancel-progress")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        if self._cancel_callback:
            self._cancel_callback()
```

**Export in**: `src/trading_bot/interfaces/widgets/__init__.py`

#### Task 1.3: Update Wizard Page to Use New Widgets
**File**: `src/trading_bot/interfaces/pages/wizard_page.py`

**Lines to update**: 496-502 (results display section)

Replace:
```python
LoadBarWidget(id="wizard-progress-bar"),
ScrollableContainer(
    Static("", id="wizard-results"),
    id="wizard-results-scroll",
),
```

With:
```python
Container(id="wizard-progress-container"),  # For spinner or progress bar
ScrollableContainer(
    Static("", id="wizard-results"),
    id="wizard-results-scroll",
),
```

**Update `handle_run_backtest()`** (lines 863-1220):

Add at start of function:
```python
# Show loading spinner
progress_container = self.app.query_one("#wizard-progress-container", Container)
spinner = LoadingSpinner("Initializing backtest...")
progress_container.mount(spinner)

# Define stages
stages = [
    "Validating configuration",
    "Fetching market data",
    "Generating signals",
    "Running backtest",
    "Calculating metrics"
]
```

Replace old progress updates with:
```python
# After validation
spinner.message = stages[1]

# After fetching data
spinner.message = stages[2]

# After generating signals
spinner.message = stages[3]

# After backtest completes
spinner.stop("Backtest completed successfully!")
```

---

## Priority 2: Improved Validation & Error Messages 🎯

### Problem
Error messages are too technical. Validation is scattered. Users don't know how to fix issues.

### Solution: Centralized Validation with User-Friendly Messages

#### Task 2.1: Create Validation Service
**File**: `src/trading_bot/utils/validation.py`

```python
"""Centralized validation with user-friendly error messages."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
                suggestion="Maximum is 50,000. For multi-year data, use date range instead"
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

    @classmethod
    def validate_all(
        cls,
        symbol: str,
        limit: int,
        timeframe: str,
        start_date: str | None = None,
        end_date: str | None = None,
        strategy_name: str = "",
        strategy_params: dict[str, Any] | None = None,
    ) -> list[ValidationResult]:
        """Validate entire backtest configuration."""
        results = []

        # Basic validations
        results.append(cls.validate_symbol(symbol))
        results.append(cls.validate_candle_count(limit, timeframe))
        results.append(cls.validate_date_range(start_date, end_date))

        # Strategy-specific validation
        if strategy_name in ["ma_crossover", "talib_ma"] and strategy_params:
            short = strategy_params.get("short_window") or strategy_params.get("short_period", 50)
            long = strategy_params.get("long_window") or strategy_params.get("long_period", 200)
            results.extend(cls.validate_ma_parameters(short, long, limit))

        return results
```

#### Task 2.2: Create Validation Display Widget
**File**: `src/trading_bot/interfaces/widgets/validation_panel.py`

```python
"""Panel for displaying validation results."""

from textual.containers import Vertical
from textual.widgets import Static

from trading_bot.utils.validation import ValidationResult


class ValidationPanel(Vertical):
    """Display validation results in a formatted panel."""

    DEFAULT_CSS = """
    ValidationPanel {
        height: auto;
        max-height: 20;
        padding: 1;
        background: $surface;
        border: solid $primary;
        overflow-y: auto;
    }

    ValidationPanel.has-errors {
        border: solid $error;
    }

    ValidationPanel.has-warnings {
        border: solid $warning;
    }

    ValidationPanel.all-valid {
        border: solid $success;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results: list[ValidationResult] = []

    def compose(self):
        yield Static("", id="validation-content")

    def update_results(self, results: list[ValidationResult]) -> None:
        """Update displayed validation results."""
        self.results = results

        # Categorize results
        errors = [r for r in results if not r.is_valid and r.severity == "error"]
        warnings = [r for r in results if not r.is_valid and r.severity == "warning"]
        info = [r for r in results if r.is_valid]

        # Build display text
        lines = []

        if errors:
            lines.append("[bold red]❌ Issues Found:[/bold red]\n")
            for result in errors:
                lines.append(result.to_rich_text())
                lines.append("")

        if warnings:
            lines.append("[bold yellow]⚠️  Warnings:[/bold yellow]\n")
            for result in warnings:
                lines.append(result.to_rich_text())
                lines.append("")

        if info and not (errors or warnings):
            lines.append("[bold green]✅ All Validations Passed:[/bold green]\n")
            for result in info:
                lines.append(f"[green]✓[/green] {result.field}: {result.message}")
            lines.append("")

        # Update styling
        if errors:
            self.remove_class("has-warnings", "all-valid")
            self.add_class("has-errors")
        elif warnings:
            self.remove_class("has-errors", "all-valid")
            self.add_class("has-warnings")
        else:
            self.remove_class("has-errors", "has-warnings")
            self.add_class("all-valid")

        # Update content
        content = self.query_one("#validation-content", Static)
        content.update("\n".join(lines))

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(not r.is_valid and r.severity == "error" for r in self.results)
```

**Export both in**: `src/trading_bot/interfaces/widgets/__init__.py`

#### Task 2.3: Integrate into Wizard Page
**File**: `src/trading_bot/interfaces/pages/wizard_page.py`

Add validation panel after parameters (line ~481):
```python
# After Container(id="wizard-params-container")
ValidationPanel(id="wizard-validation-panel"),
```

Update `_validate_config()` method (lines 1325-1383) to use new validator:
```python
def _validate_config(self) -> list[str]:
    """Validate configuration and return list of errors."""
    from trading_bot.utils.validation import BacktestValidator

    results = BacktestValidator.validate_all(
        symbol=self.backtest_config.symbol,
        limit=self.backtest_config.limit,
        timeframe=self.backtest_config.timeframe,
        start_date=self.backtest_config.start_date,
        end_date=self.backtest_config.end_date,
        strategy_name=self.backtest_config.strategy_name,
        strategy_params=self.backtest_config.strategy_params,
    )

    # Update validation panel
    try:
        panel = self.app.query_one("#wizard-validation-panel", ValidationPanel)
        panel.update_results(results)
    except Exception as e:
        logger.debug(f"Could not update validation panel: {e}")

    # Return errors for backward compatibility
    return [r.message for r in results if not r.is_valid and r.severity == "error"]
```

---

## Priority 3: Extract Strategy Registry ⚙️

### Problem
`wizard_page.py` is 1,665 lines. StrategyRegistry class is 300+ lines and should be separate.

### Solution: Move to Dedicated File

#### Task 3.1: Create Strategy Registry Module
**File**: `src/trading_bot/strategies/strategy_registry.py`

Move `StrategyRegistry` class from `wizard_page.py` (lines 50-301) to this new file.

Add imports:
```python
"""Dynamic strategy registry for managing available trading strategies."""

import logging
from typing import TYPE_CHECKING

from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.moving_average import MovingAverageCrossover

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Rest of StrategyRegistry class here...
```

#### Task 3.2: Update Wizard Page
**File**: `src/trading_bot/interfaces/pages/wizard_page.py`

Replace lines 50-301 with:
```python
from trading_bot.strategies.strategy_registry import StrategyRegistry
```

Replace line 301 with:
```python
# Initialize global registry (imported from strategies module)
_strategy_registry = StrategyRegistry()
```

#### Task 3.3: Update Strategies Package
**File**: `src/trading_bot/strategies/__init__.py`

Add registry to exports:
```python
from trading_bot.strategies.strategy_registry import StrategyRegistry

__all__ = [
    # ... existing exports
    "StrategyRegistry",
]
```

---

## Testing Checklist

### Manual Testing
- [ ] LoadingSpinner displays and animates correctly
- [ ] EnhancedProgressBar updates stages properly
- [ ] Cancel button works during backtest
- [ ] Validation panel shows errors with suggestions
- [ ] Validation panel updates in real-time as fields change
- [ ] Error messages are clear and actionable
- [ ] Strategy registry still works after extraction

### Integration Testing
- [ ] Wizard page still functions with new widgets
- [ ] Backtest runs complete successfully
- [ ] Error handling doesn't break UI
- [ ] All validation scenarios covered

### Performance Testing
- [ ] Spinner animation is smooth (doesn't lag)
- [ ] Progress updates don't block UI
- [ ] Validation is fast (< 100ms)

---

## Documentation Updates

### Task 4.1: Update TUI Architecture Doc
**File**: `.cursor/rules/tui-architecture.mdc`

Add new section:
```markdown
## Loading States and Progress

### LoadingSpinner
Use for indeterminate operations:
- Initial data fetching
- Connection testing
- Quick operations (< 5 seconds)

### EnhancedProgressBar
Use for multi-stage operations:
- Backtesting (5+ stages)
- Data processing pipelines
- Long-running calculations

### Best Practices
- Always show visual feedback for operations > 1 second
- Provide cancel buttons for operations > 5 seconds
- Update progress at meaningful milestones, not on every iteration
```

### Task 4.2: Update Widget Documentation
Add JSDoc-style comments to each new widget with usage examples.

---

## Success Criteria

✅ Users can see what's happening during long operations
✅ Error messages are actionable with clear suggestions
✅ Validation happens in real-time with inline feedback
✅ Cancel button works for long operations
✅ Wizard page is ~300 lines shorter (strategy registry extracted)
✅ No breaking changes to existing functionality
✅ All tests pass

---

## Timeline

### Week 1: Core Improvements
- **Day 1-2**: Create LoadingSpinner and EnhancedProgressBar widgets
- **Day 3**: Integrate into wizard page
- **Day 4-5**: Create validation system with user-friendly messages
- **Day 6**: Extract strategy registry to separate file
- **Day 7**: Testing and bug fixes

### Week 2: Polish and Documentation
- **Day 8-9**: Refine error messages based on testing
- **Day 10**: Add validation panel to all input fields
- **Day 11-12**: Documentation and examples
- **Day 13-14**: Final testing and release

---

## Next Steps (Phase 2 Preview)

After Phase 1 is complete and stable, we'll tackle:
1. Wizard page refactor (split into step components)
2. Keyboard navigation system
3. Comparison view for backtests

---

## To-dos

- [ ] Create LoadingSpinner widget with animation
- [ ] Create EnhancedProgressBar with stages and cancel button
- [ ] Update wizard page to use new progress widgets
- [ ] Create BacktestValidator with user-friendly error messages
- [ ] Create ValidationPanel widget for displaying validation results
- [ ] Integrate validation panel into wizard page with real-time updates
- [ ] Extract StrategyRegistry to src/trading_bot/strategies/strategy_registry.py
- [ ] Update wizard_page.py to import StrategyRegistry instead of defining it
- [ ] Update strategies/__init__.py to export StrategyRegistry
- [ ] Test all new widgets in wizard page
- [ ] Test validation messages are clear and actionable
- [ ] Test cancel button functionality during backtest
- [ ] Update .cursor/rules/tui-architecture.mdc with new patterns
- [ ] Add usage examples to widget docstrings

