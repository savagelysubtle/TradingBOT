# TUI Refactoring Plan

## Current Structure
- **File**: `src/trading_bot/interfaces/tui.py` (2260 lines)
- **Problem**: Too large, hard to navigate and maintain

## Proposed Structure

```
src/trading_bot/interfaces/
├── tui.py                    # Main app (< 500 lines)
├── tui.css                   # Styles
├── tui_widgets.py           # Shared widgets
└── pages/                    # Page modules
    ├── __init__.py
    ├── base_page.py          # Abstract base class
    ├── dashboard_page.py     # Dashboard (~150 lines)
    ├── wizard_page.py        # Wizard (~400 lines)
    ├── monte_carlo_page.py   # Monte Carlo (~200 lines)
    ├── history_page.py       # History (~150 lines)
    └── strategies_page.py    # Strategies (~100 lines)
```

## Refactoring Steps

### Phase 1: Setup ✓
- [x] Create `pages/` directory
- [x] Create `base_page.py` abstract class
- [x] Create `__init__.py` with exports

### Phase 2: Extract Pages (To Do)
1. **dashboard_page.py**
   - `show_dashboard()` method
   - `_create_performance_sparkline()` helper
   - `_start_live_price_ticker()` helper

2. **wizard_page.py**
   - `show_wizard()` method
   - `_update_parameters_panel()` helper
   - `_mount_params_panel()` helper
   - `_sync_config_from_inputs()` helper
   - `_update_wizard_progress()` helper
   - `_get_available_strategies()` helper
   - Wizard event handlers

3. **monte_carlo_page.py**
   - `show_monte_carlo()` method
   - `_display_monte_carlo_results()` helper
   - Monte Carlo event handlers

4. **history_page.py**
   - `show_history()` method
   - `_populate_history_table()` helper
   - History event handlers

5. **strategies_page.py**
   - `show_strategies()` method
   - `_populate_strategies_table()` helper

### Phase 3: Update Main TUI
- Keep only app initialization
- Keep tab switching logic
- Delegate to page modules
- Keep shared utilities

## Benefits
- **Maintainability**: Each page is self-contained
- **Readability**: Easier to find and understand code
- **Scalability**: Easy to add new pages
- **Testing**: Pages can be tested independently

## Next Steps
Run this command to see current line distribution:
```bash
# Count lines in show_ methods
findstr /N "def show_" src\trading_bot\interfaces\tui.py
```

Then extract pages one by one, testing after each extraction.

