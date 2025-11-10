# TUI Improvement Suggestions

## Priority 1: High Impact, Low Effort

### 1. Add Monte Carlo Tab
Add a dedicated tab for Monte Carlo simulations with:
- Method selection (Bootstrap, Shuffle Trades, Randomize Returns)
- Number of simulations slider
- Seed input for reproducibility
- Real-time progress bar
- Results visualization

```python
def show_monte_carlo(self) -> None:
    """Show Monte Carlo simulation tab."""
    body = self.query_one("#app-body", Container)

    body.mount(
        Vertical(
            Static("[bold cyan]Monte Carlo Simulation[/bold cyan]"),
            Horizontal(
                Vertical(
                    Label("Load Configuration:"),
                    Select(
                        self._get_recent_configs(),
                        id="mc-config-select"
                    ),
                ),
                Vertical(
                    Label("Method:"),
                    Select([
                        ("Bootstrap Resampling", "bootstrap"),
                        ("Shuffle Trades", "shuffle_trades"),
                        ("Randomize Returns", "randomize_returns"),
                    ], id="mc-method"),
                ),
                Vertical(
                    Label("Simulations:"),
                    Input(value="1000", id="mc-sims"),
                ),
            ),
            Button("▶ Run Monte Carlo", id="btn-run-mc", variant="success"),
            Static("", id="mc-progress"),
            DataTable(id="mc-results", zebra_stripes=True),
            id="monte-carlo"
        )
    )
```

### 2. Add Dashboard Widgets
```python
def _create_performance_sparkline(self) -> str:
    """Create ASCII sparkline of recent backtest performance."""
    runs = self.history.get_runs(limit=10)
    returns = [r.results.get("total_return_pct", 0) for r in runs]

    # Normalize to 0-8 range for sparkline characters
    if not returns:
        return "No data"

    min_val, max_val = min(returns), max(returns)
    if max_val == min_val:
        return "▄" * len(returns)

    chars = "▁▂▃▄▅▆▇█"
    normalized = [(r - min_val) / (max_val - min_val) for r in returns]
    sparkline = "".join(chars[min(int(n * 7), 7)] for n in normalized)

    return f"{sparkline} ({returns[-1]:.1f}%)"
```

### 3. Add Real-time Data Preview
```python
@work
async def _update_live_price(self, symbol: str) -> None:
    """Update live price display."""
    while True:
        try:
            fetcher = CCXTDataFetcher(exchange_id="binance")
            ticker = fetcher.exchange.fetch_ticker(symbol)

            price = ticker['last']
            change_pct = ticker['percentage']
            arrow = "↑" if change_pct > 0 else "↓"
            color = "green" if change_pct > 0 else "red"

            price_widget = self.query_one("#live-price", Static)
            price_widget.update(
                f"[bold]{symbol}:[/bold] ${price:,.2f} "
                f"[{color}]{arrow} {change_pct:.2f}%[/{color}]"
            )

            await asyncio.sleep(5)  # Update every 5 seconds
        except Exception:
            break
```

### 4. Add Quick Actions to History Rows
```python
# In history table, add clickable actions
table.add_row(
    run.timestamp[:16],
    run.config.strategy_name,
    run.config.symbol,
    f"{return_pct:.2f}%",
    "[▶ Rerun] [📊 Charts] [💾 Export]"  # Clickable actions
)
```

## Priority 2: Medium Impact

### 5. Add Parameter Presets
```python
# In wizard, add quick parameter sets
preset_select = Select([
    ("Conservative (50/200 MA)", "conservative"),
    ("Aggressive (20/50 MA)", "aggressive"),
    ("Custom", "custom"),
], id="param-preset")

# When selected, auto-fill parameters
@on(Select.Changed, "#param-preset")
def on_preset_changed(self, event):
    if event.value == "conservative":
        self.query_one("#wizard-short").value = "50"
        self.query_one("#wizard-long").value = "200"
    elif event.value == "aggressive":
        self.query_one("#wizard-short").value = "20"
        self.query_one("#wizard-long").value = "50"
```

### 6. Add Data Quality Indicators
```python
def _check_data_quality(self, data: pd.DataFrame) -> dict:
    """Check data quality before backtesting."""
    return {
        "total_rows": len(data),
        "missing_values": data.isnull().sum().sum(),
        "date_range": f"{data.index[0]} to {data.index[-1]}",
        "gaps": self._detect_gaps(data),
        "quality_score": 100 - (missing_values / len(data) * 100)
    }

def _display_data_quality(self, quality: dict) -> None:
    """Display data quality check results."""
    table = Table(title="Data Quality Check")
    table.add_row("Total Candles", str(quality["total_rows"]))
    table.add_row("Missing Values", str(quality["missing_values"]))
    table.add_row("Date Range", quality["date_range"])
    table.add_row("Quality Score", f"{quality['quality_score']:.1f}%")
    # ... render table
```

### 7. Add Export Functionality
```python
@on(Button.Pressed, "#btn-export-pdf")
def export_pdf_report(self) -> None:
    """Export backtest results as PDF."""
    if not self.backtest_results:
        self.notify("No results to export", severity="warning")
        return

    from trading_bot.utils.export import generate_pdf_report

    pdf_file = generate_pdf_report(
        self.backtest_results,
        self.backtest_data,
        self.backtest_signals,
        output_dir=self.config.results_dir
    )

    self.notify(f"PDF exported to {pdf_file}", severity="information")
```

### 8. Add Search/Filter to History
```python
@on(Input.Changed, "#history-search")
def filter_history(self, event: Input.Changed) -> None:
    """Filter history table by search term."""
    search = event.value.lower()
    table = self.query_one("#history-table", DataTable)
    table.clear()

    runs = self.history.get_runs(limit=50)
    for run in runs:
        # Filter by strategy name, symbol, or date
        if (search in run.config.strategy_name.lower() or
            search in run.config.symbol.lower() or
            search in run.timestamp):
            table.add_row(...)  # Add matching rows
```

## Priority 3: Nice to Have

### 9. Add Theme Customization
```python
@on(Select.Changed, "#theme-select")
def change_theme(self, event: Select.Changed) -> None:
    """Change TUI color theme."""
    themes = {
        "default": "dark",
        "light": "light",
        "dracula": "dracula",
        "monokai": "monokai",
    }

    theme = themes.get(event.value, "dark")
    # Apply theme (requires custom CSS)
```

### 10. Add Keyboard Navigation
```python
def on_key(self, event: events.Key) -> None:
    """Handle keyboard shortcuts."""
    if event.key == "ctrl+n":
        self._switch_to_tab("Wizard")
    elif event.key == "ctrl+h":
        self._switch_to_tab("History")
    elif event.key == "ctrl+s":
        self.on_save_template()
    elif event.key == "f5":
        self.on_refresh()
```

### 11. Add Multi-symbol Comparison
```python
# Compare same strategy on different symbols
symbols_to_compare = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Run backtest on all and show comparison table
┌─────────┬────────┬─────────┬──────────┐
│ Symbol  │ Return │ Sharpe  │ Max DD   │
├─────────┼────────┼─────────┼──────────┤
│ BTC     │ 15.2%  │ 1.2     │ -18%     │
│ ETH     │ 12.8%  │ 1.5     │ -12%     │
│ SOL     │ 8.3%   │ 0.9     │ -25%     │
└─────────┴────────┴─────────┴──────────┘
```

### 12. Add Strategy Backtester Queue
```python
# Queue multiple backtests to run sequentially
queue = [
    ("BTC/USDT", "talib_ma", {"short": 50, "long": 200}),
    ("BTC/USDT", "talib_macd", {}),
    ("ETH/USDT", "supertrend", {"period": 10}),
]

# Show progress: "Running 2/3 backtests..."
```

### 13. Add Notification Sound/Toast
```python
def notify_with_sound(self, message: str, severity: str = "information"):
    """Notify with optional sound."""
    self.notify(message, severity=severity)

    # Play sound (Windows)
    if severity == "information":
        import winsound
        winsound.MessageBeep()
    elif severity == "error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
```

### 14. Add Auto-save Feature
```python
# Auto-save configuration every N seconds
@work
async def auto_save_config(self) -> None:
    """Auto-save configuration periodically."""
    while True:
        await asyncio.sleep(60)  # Every minute
        if self.backtest_config.has_changes:
            self.history.save_template(self.backtest_config)
            self.notify("Auto-saved", severity="information", timeout=1)
```

### 15. Add Heatmap View
```python
# Show parameter optimization heatmap
# X-axis: short_period (10-100)
# Y-axis: long_period (50-300)
# Color: total_return

def create_heatmap_widget(self, results: list) -> Widget:
    """Create ASCII heatmap of parameter optimization."""
    # Use block characters to show performance
    # █ = high return, ░ = low return
    ...
```

## Implementation Priority Order

### Week 1
1. Add Monte Carlo tab (biggest feature request)
2. Add dashboard sparklines
3. Add live price preview

### Week 2
4. Add export functionality (PDF, CSV)
5. Add search/filter to history
6. Add quick action buttons to history rows

### Week 3
7. Add data quality indicators
8. Add parameter presets
9. Add keyboard shortcuts

### Week 4
10. Add theme customization
11. Add multi-symbol comparison
12. Polish and bug fixes

## CSS Improvements

Add custom styling:
```css
/* In tui.css */

/* Highlight positive returns */
.positive-return {
    background: $success;
    color: $text;
}

/* Highlight negative returns */
.negative-return {
    background: $error;
    color: $text;
}

/* Status indicators */
.status-ready {
    color: $success;
}

.status-warning {
    color: $warning;
}

.status-error {
    color: $error;
}

/* Sparkline container */
.sparkline {
    height: 3;
    border: solid $primary;
}

/* Monte Carlo results */
.mc-good {
    background: $success 20%;
}

.mc-medium {
    background: $warning 20%;
}

.mc-poor {
    background: $error 20%;
}
```

## Code Quality Improvements

1. **Add type hints throughout**
2. **Add docstrings to all methods**
3. **Extract magic numbers to constants**
4. **Add error boundaries for async operations**
5. **Add loading states for all async operations**
6. **Add confirmation dialogs for destructive actions**

## Testing Improvements

Create test file: `tests/test_tui.py`
```python
from textual.pilot import Pilot
from trading_bot.interfaces.tui import TradingBotTUI

async def test_dashboard_loads():
    """Test dashboard tab loads correctly."""
    app = TradingBotTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_tab == "Dashboard"

async def test_wizard_workflow():
    """Test complete wizard workflow."""
    app = TradingBotTUI()
    async with app.run_test() as pilot:
        await pilot.click("#tabs", "Wizard")
        await pilot.click("#wizard-run")
        await pilot.pause()
        # Assert results displayed
```
