# Phase 2: Wizard Page Refactor & Advanced Features

## Overview

Now that Phase 1 UX improvements are complete and working, Phase 2 focuses on **architectural improvements** and **advanced functionality**. The wizard page is still ~1,300 lines and needs to be broken down, plus we can add powerful new features.

**Duration**: 2-3 weeks
**Focus**: Wizard refactor, keyboard navigation, comparison features

---

## Priority 1: Wizard Page Refactor ⚡

### Problem
`wizard_page.py` is still 1,300+ lines with everything in one class. This makes it:
- Hard to maintain and test
- Difficult to add new features
- Error-prone to modify

### Solution: Step Component Architecture

#### Task 2.1: Create Step Base Classes
**File**: `src/trading_bot/interfaces/pages/wizard_steps/__init__.py`

```python
"""Wizard step components."""

from .base_step import BaseWizardStep
from .data_step import DataConfigurationStep
from .strategy_step import StrategySelectionStep
from .parameters_step import ParametersStep

__all__ = ["BaseWizardStep", "DataConfigurationStep", "StrategySelectionStep", "ParametersStep"]
```

**File**: `src/trading_bot/interfaces/pages/wizard_steps/base_step.py`

```python
"""Base class for wizard steps."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from textual.containers import Container

if TYPE_CHECKING:
    from ..wizard_page import WizardPage

class BaseWizardStep(ABC):
    """Base class for wizard steps."""

    def __init__(self, wizard: "WizardPage"):
        """Initialize step with wizard reference."""
        self.wizard = wizard

    @abstractmethod
    def compose(self, container: Container) -> None:
        """Compose step UI into container."""
        pass

    @abstractmethod
    def validate(self) -> list[ValidationResult]:
        """Validate step data."""
        pass

    @abstractmethod
    def save_data(self) -> dict:
        """Save step data to config."""
        pass

    @abstractmethod
    def load_data(self) -> None:
        """Load step data from config."""
        pass

    def on_enter(self) -> None:
        """Called when step becomes active."""
        pass

    def on_exit(self) -> None:
        """Called when step becomes inactive."""
        pass
```

#### Task 2.2: Create Data Configuration Step
**File**: `src/trading_bot/interfaces/pages/wizard_steps/data_step.py`

- Exchange selector
- Symbol input with validation
- Timeframe selector
- Candles input or date range
- Real-time validation

#### Task 2.3: Create Strategy Selection Step
**File**: `src/trading_bot/interfaces/pages/wizard_steps/strategy_step.py`

- Strategy dropdown
- Engine selector
- Basic strategy info
- Availability indicators

#### Task 2.4: Create Parameters Step
**File**: `src/trading_bot/interfaces/pages/wizard_steps/parameters_step.py`

- Dynamic parameter panels
- Strategy-specific validation
- Parameter hints and tooltips

#### Task 2.5: Refactor Main Wizard Page
**File**: `src/trading_bot/interfaces/pages/wizard_page.py`

- Reduce from 1,300+ lines to ~400 lines
- Step navigation logic
- Progress tracking
- Step validation coordination

---

## Priority 2: Keyboard Navigation System 🎯

### Problem
Users are stuck with mouse-only navigation. Power users want keyboard shortcuts.

### Solution: Vim-Inspired Navigation

#### Task 2.6: Add Global Shortcuts
**File**: `src/trading_bot/interfaces/tui.py`

```python
BINDINGS = [
    # Navigation
    ("j", "scroll_down", "Scroll Down"),
    ("k", "scroll_up", "Scroll Up"),
    ("h", "go_back", "Go Back"),
    ("l", "select_item", "Select Item"),

    # Quick Actions
    ("ctrl+n", "new_backtest", "New Backtest"),
    ("ctrl+h", "show_history", "History"),
    ("ctrl+s", "save_config", "Save Config"),
    ("ctrl+r", "run_backtest", "Run Backtest"),

    # Page-specific
    ("f", "focus_search", "Focus Search"),
    ("/", "global_search", "Global Search"),
    ("?", "show_help", "Help"),
]
```

#### Task 2.7: Add Page-Specific Shortcuts
**File**: `src/trading_bot/interfaces/pages/base_page.py`

- Base keyboard navigation
- Focus management
- Scroll helpers

#### Task 2.8: Implement Table Navigation
**File**: `src/trading_bot/interfaces/pages/history_page.py`

- j/k for row navigation
- Enter to select/view
- / for search
- Number keys for quick selection

---

## Priority 3: Backtest Comparison System 📊

### Problem
Users can't compare multiple backtests side-by-side. Hard to choose best strategy.

### Solution: Multi-Backtest Comparison

#### Task 2.9: Create Comparison Modal
**File**: `src/trading_bot/interfaces/widgets/backtest_comparison_modal.py`

```python
class BacktestComparisonModal(ModalScreen):
    """Modal for comparing multiple backtests."""

    def __init__(self, backtest_ids: list[str]):
        super().__init__()
        self.backtest_ids = backtest_ids

    def compose(self):
        # Side-by-side metrics table
        # Performance charts
        # Parameter diff highlighting
        # Winner indicators
        pass
```

#### Task 2.10: Add Comparison Actions
**File**: `src/trading_bot/interfaces/pages/history_page.py`

- Multi-select checkboxes
- "Compare Selected" button
- Quick compare (last 3 runs)

#### Task 2.11: Create Comparison Service
**File**: `src/trading_bot/utils/backtest_comparison.py`

```python
class BacktestComparator:
    """Compare multiple backtests."""

    def compare_runs(self, run_ids: list[str]) -> ComparisonResult:
        """Compare multiple backtest runs."""
        # Load runs
        # Calculate metrics comparison
        # Identify best performers
        # Generate insights
        pass

    def generate_report(self, comparison: ComparisonResult) -> str:
        """Generate human-readable comparison report."""
        pass
```

---

## Priority 4: Smart Template System 💡

### Problem
Templates are basic. Users don't know which template to use for their strategy.

### Solution: Intelligent Template Recommendations

#### Task 2.12: Enhance Template System
**File**: `src/trading_bot/config.py`

```python
class TemplateManager:
    """Enhanced template management with recommendations."""

    def get_recommendations(self, symbol: str, timeframe: str) -> list[Template]:
        """Get recommended templates for symbol/timeframe."""
        # BTC/USDT + 1d → Conservative MA template
        # ALT + 4h → Trend following template
        # Stocks + 1d → Mean reversion template
        pass

    def create_from_backtest(self, run_id: str, name: str) -> Template:
        """Create template from successful backtest."""
        pass
```

#### Task 2.13: Add Template Categories
**File**: `src/trading_bot/interfaces/pages/dashboard_page.py`

- Trending Strategies
- Conservative (Low Risk)
- Aggressive (High Risk)
- Market Condition Based

---

## Implementation Order

1. **Wizard Refactor** (Week 1)
   - Create step components
   - Test step navigation
   - Verify no functionality loss

2. **Keyboard Navigation** (Week 2)
   - Global shortcuts
   - Page-specific shortcuts
   - Table navigation

3. **Comparison System** (Week 3)
   - Comparison modal
   - Multi-select in history
   - Comparison service

4. **Template System** (Week 3-4)
   - Enhanced templates
   - Recommendations
   - Categories

---

## Success Criteria

✅ Wizard page < 500 lines total
✅ Full keyboard navigation (vim-style)
✅ Compare any number of backtests
✅ Smart template recommendations
✅ No breaking changes to existing functionality

---

## Technical Benefits

- **Maintainability**: Wizard split into logical components
- **Testability**: Each step can be tested independently
- **Extensibility**: Easy to add new wizard steps
- **User Experience**: Power users can navigate entirely with keyboard
- **Decision Making**: Data-driven strategy selection with comparisons

---

## User Impact

**Before Phase 2:**
- 1,300-line monolithic wizard
- Mouse-only navigation
- Can't compare strategies
- Basic templates

**After Phase 2:**
- Modular, maintainable wizard
- Full keyboard shortcuts
- Side-by-side comparisons
- Smart recommendations

---

## Next Steps (Phase 3 Preview)

After Phase 2, we can tackle:
1. Live trading integration
2. Advanced analytics dashboard
3. Strategy optimization workflows
4. Plugin system for custom strategies

---

## To-dos

- [ ] Create wizard_steps/ directory with base classes
- [ ] Implement DataConfigurationStep, StrategySelectionStep, ParametersStep
- [ ] Refactor main wizard_page.py to use step components (~400 lines)
- [ ] Add global keyboard shortcuts to TUI
- [ ] Implement page-specific keyboard navigation
- [ ] Create BacktestComparisonModal with side-by-side views
- [ ] Add multi-select and comparison actions to history page
- [ ] Create BacktestComparator service with insights
- [ ] Enhance TemplateManager with recommendations
- [ ] Add template categories and smart suggestions
- [ ] Test all new features work together
- [ ] Update documentation and examples
