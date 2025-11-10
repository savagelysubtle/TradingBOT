# Trading Bot TUI - UX Improvement Plan

**Date:** November 10, 2025
**Status:** Analysis Complete - Ready for Implementation

---

## Executive Summary

Based on the screenshot analysis, the current TUI has a **fragmented workflow** requiring excessive tab switching and lacking state persistence. This document outlines critical UX issues and provides a prioritized improvement roadmap.

**Key Problems:**
- 5-tab workflow forces users to remember state across tabs
- No visual feedback on current configuration
- Duplicate functionality (Results in both Backtest and Results tabs)
- Strategy-specific parameters (MA windows) shown for all strategies
- No ability to save/load configurations

---

## Current Workflow Analysis

### Current User Journey (Problematic)
```
Dashboard → Data Fetch Tab → Strategies Tab → Backtest Tab → Run → Results Tab
    ↓           ↓                  ↓                ↓              ↓
  Info      Select Data       Pick Strategy    Configure     View Results
            Parameters                          & Run
```

**Problems:**
- **6 navigation steps** to complete one backtest
- **State lost** between tabs (no visual indication of selections)
- **Cognitive load** - users must remember: what data they fetched, which strategy they selected
- **Disconnected results** - shown in Backtest tab but also separate Results tab

---

## Identified UX Issues

### 🔴 CRITICAL Issues (Blocks User Goals)

#### 1. **Excessive Tab Switching**
- **Problem:** Users navigate through 5 tabs to complete basic workflow
- **Impact:** High friction, confusion about current state
- **Evidence:** Screenshots show empty states, user must remember previous selections

#### 2. **No State Visibility**
- **Problem:** No indication of what's been configured (data fetched, strategy selected)
- **Impact:** Users don't know if they're ready to run backtest
- **Evidence:** Dashboard shows static info, doesn't reflect user actions

#### 3. **Strategy-Parameter Mismatch**
- **Problem:** MA window inputs shown for ALL strategies in Backtest tab
- **Impact:** Confusing for strategies that don't use MA (Supertrend, MACD, etc.)
- **Evidence:** Screenshot 3 shows MA inputs even for non-MA strategies

#### 4. **Duplicate Results Display**
- **Problem:** Results shown in both Backtest tab AND Results tab
- **Impact:** Unclear which is "source of truth", waste of screen space
- **Evidence:** Screenshots 3 and 5 show two locations for results

### 🟡 HIGH Priority Issues (Degrades Experience)

#### 5. **No Saved Configurations**
- **Problem:** Can't save favorite setups (BTC/USDT, 1h, MA Crossover)
- **Impact:** Repetitive data entry for common backtests

#### 6. **No Backtest Comparison**
- **Problem:** Can't compare multiple runs (MA 50/200 vs 20/50)
- **Impact:** Users must take manual notes, can't optimize strategies

#### 7. **Poor Data-to-Strategy Flow**
- **Problem:** "Use for Backtest" button doesn't pre-select strategy
- **Impact:** Extra navigation required, broken expectation

#### 8. **Dashboard Doesn't Reflect State**
- **Problem:** Quick actions don't show progress or recent actions
- **Impact:** Dashboard becomes unused after initial launch

### 🟢 MEDIUM Priority Issues (Polish)

#### 9. **No Recent History**
- **Problem:** Can't see last 5 backtests or recent configurations
- **Impact:** Can't quickly re-run or reference past results

#### 10. **Limited Strategy Comparison**
- **Problem:** Can't run same data through multiple strategies at once
- **Impact:** Manual process to compare strategies

#### 11. **No Visual Progress Indicators**
- **Problem:** Long-running backtests don't show progress
- **Impact:** User uncertainty during operations

---

## Proposed Solutions

### Phase 1: Critical UX Fixes (Week 1-2)

#### ✅ Solution 1: Unified Workflow Tab
**Goal:** Reduce 5 tabs to 3-step workflow in ONE tab

**Design:**
```
┌─────────────────────────────────────────────────────────────┐
│ [WIZARD TAB: Run Backtest]                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│ │  STEP 1 ✓    │ → │  STEP 2 ✓    │ → │  STEP 3      │    │
│ │  Data Config │   │  Strategy    │   │  Run & View  │    │
│ └──────────────┘   └──────────────┘   └──────────────┘    │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Current Configuration                                   │ │
│ │ • Data: BTC/USDT @ Binance, 1m, 1000 candles  [Edit]  │ │
│ │ • Strategy: MA Crossover (50/200)             [Change]│ │
│ │ • Engine: Custom                               [Change]│ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ [▶ Run Backtest]  [💾 Save as Template]  [📊 Compare]     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
- New `show_wizard()` method creates step-by-step UI
- State tracking: `self.wizard_state` with data/strategy/engine
- Visual indicators for completed steps
- Collapsible sections for each step

**Benefits:**
- **Single tab** for entire workflow
- **State always visible** in summary box
- **Clear progression** through steps
- **Reduce navigation** from 6 steps to 3

---

#### ✅ Solution 2: Dynamic Strategy Parameters
**Goal:** Show only relevant parameters for selected strategy

**Design:**
```python
# When strategy changes, update parameter panel
def on_strategy_change(strategy_name):
    params_container.clear()

    if strategy_name == "ma_crossover":
        params_container.add(Input("Short MA", value=50))
        params_container.add(Input("Long MA", value=200))

    elif strategy_name == "supertrend":
        params_container.add(Input("Period", value=10))
        params_container.add(Input("Multiplier", value=3.0))

    elif strategy_name == "bollinger":
        params_container.add(Input("Period", value=20))
        params_container.add(Input("Std Dev", value=2.0))
```

**Implementation:**
- `@on(Select.Changed, "#select-strategy")` handler
- `_render_strategy_params(strategy_name)` method
- Parameter validation per strategy type

**Benefits:**
- **No confusion** - only see relevant inputs
- **Type-appropriate validation** - integers for periods, floats for multipliers
- **Cleaner UI** - less visual clutter

---

#### ✅ Solution 3: Persistent State Sidebar
**Goal:** Always show current configuration state

**Design:**
```
┌──────────────────┐
│ Current Setup    │
├──────────────────┤
│ 📊 Data          │
│  BTC/USDT        │
│  Binance (1m)    │
│  1000 candles    │
│  [Change]        │
├──────────────────┤
│ 🎯 Strategy      │
│  MA Crossover    │
│  50/200 periods  │
│  [Change]        │
├──────────────────┤
│ ⚙️ Engine        │
│  Custom          │
│  [Change]        │
├──────────────────┤
│ [▶ Run Now]      │
│ [💾 Save Setup]  │
└──────────────────┘
```

**Implementation:**
- New `StatusSidebar` widget class
- Auto-updates when `self.current_*` properties change
- Always visible on right side
- Quick-edit buttons for each section

**Benefits:**
- **Always visible** - no need to remember state
- **One-click changes** - modify without full navigation
- **Status at a glance** - ready to run or missing config?

---

### Phase 2: Enhanced Functionality (Week 3-4)

#### ✅ Solution 4: Configuration Templates
**Goal:** Save and load common backtest setups

**Features:**
- Save current config as named template
- Template library with built-in examples
- One-click load of saved templates
- Export/import templates as JSON

**UI Location:** New "Templates" section in wizard or sidebar

---

#### ✅ Solution 5: Backtest History & Comparison
**Goal:** Track all backtests and compare results

**Features:**
- History table: Date, Strategy, Symbol, Return %, Actions
- Select 2-5 runs for side-by-side comparison
- Visual comparison charts (matplotlib)
- Export comparison to CSV/PDF

**UI Location:** New "History" tab (replaces empty "Results" tab)

---

#### ✅ Solution 6: Enhanced Dashboard
**Goal:** Make dashboard a useful command center

**Design:**
```
┌─────────────────────────────────────────────────────────┐
│ Trading Bot Dashboard                                    │
├─────────────────────────────────────────────────────────┤
│ Recent Backtests           │  Quick Actions              │
│ • MA 50/200  +12.3%  [▶]  │  [▶ Run Last Config]       │
│ • Supertrend +8.1%   [▶]  │  [🔍 Browse Templates]     │
│ • MACD      +15.4%   [▶]  │  [📊 Compare All]          │
│                            │                             │
│ Favorite Templates         │  System Status             │
│ • BTC Scalp  [Load]        │  ✓ CCXT Connected          │
│ • ETH Swing  [Load]        │  ✓ Strategies: 8 Ready     │
│ • Alt Trend  [Load]        │  ✓ TA-Lib Available       │
└─────────────────────────────────────────────────────────┘
```

---

### Phase 3: Advanced Features (Week 5-6)

#### ✅ Solution 7: Multi-Strategy Runner
**Goal:** Run same data through multiple strategies

**Features:**
- Checkbox selection of strategies to run
- Batch execution with progress tracking
- Automatic comparison table generation
- Strategy ranking by metrics

---

#### ✅ Solution 8: Real-time Preview
**Goal:** Show data/signal preview before full backtest

**Features:**
- Mini chart showing data and signals
- Strategy signal preview (buy/sell markers)
- Quick validation before full run
- Embedded matplotlib charts

---

#### ✅ Solution 9: Parameter Optimization
**Goal:** Find optimal strategy parameters

**Features:**
- Parameter range definition (MA: 20-100, step 10)
- Grid search or random search
- Heatmap visualization of parameter performance
- Auto-save best configurations

---

## Implementation Priority Matrix

```
         Impact →
       Low    Med    High
    ┌──────┬──────┬──────┐
High│  8   │ 2,3  │  1   │ ← Urgency
    ├──────┼──────┼──────┤    ↓
Med │  9   │ 4,5  │  6   │
    ├──────┼──────┼──────┤
Low │  11  │ 10   │  7   │
    └──────┴──────┴──────┘

Legend:
1. Unified Workflow Tab (HIGH/HIGH) ⭐ START HERE
2. Dynamic Strategy Parameters (HIGH/HIGH) ⭐ START HERE
3. Persistent State Sidebar (HIGH/HIGH) ⭐ START HERE
4. Configuration Templates (MED/MED)
5. Backtest History (MED/MED)
6. Enhanced Dashboard (MED/HIGH)
7. Multi-Strategy Runner (LOW/HIGH)
8. Real-time Preview (HIGH/LOW)
9. Parameter Optimization (MED/LOW)
10. Visual Progress (LOW/MED)
11. History browsing (LOW/LOW)
```

---

## Recommended Implementation Order

### Sprint 1 (Week 1-2): Core UX Fixes ⭐ PRIORITY
1. **Persistent State Sidebar** (2 days)
   - Create StatusSidebar widget
   - Wire up to state changes
   - Add quick-edit buttons

2. **Dynamic Strategy Parameters** (2 days)
   - Create parameter rendering system
   - Add strategy-specific param configs
   - Implement validation

3. **Unified Workflow Tab** (4 days)
   - Design wizard layout
   - Implement step tracking
   - Add configuration summary
   - Wire up existing logic

4. **Remove Results Tab** (1 day)
   - Consolidate into Backtest tab
   - Update navigation

### Sprint 2 (Week 3-4): Enhanced Features
5. **Configuration Templates** (3 days)
6. **Backtest History** (3 days)
7. **Enhanced Dashboard** (2 days)

### Sprint 3 (Week 5-6): Advanced Features
8. **Multi-Strategy Runner** (4 days)
9. **Parameter Optimization** (4 days)

---

## Success Metrics

**Target Improvements:**
- Reduce workflow steps: 6 → 3 (50% reduction)
- Reduce tab switches: 4 → 0 for basic backtest
- User can complete backtest in: <30 seconds (vs current ~2 minutes)
- Configuration errors: Reduce by 80% (via validation & visibility)

**User Satisfaction:**
- "I always know what's configured" ✅
- "I can quickly re-run with changes" ✅
- "I can compare strategies easily" ✅

---

## Technical Considerations

### State Management
```python
@dataclass
class BacktestConfiguration:
    """Persistent configuration state."""
    # Data
    exchange: str
    symbol: str
    timeframe: str
    limit: int

    # Strategy
    strategy_name: str
    strategy_params: dict

    # Engine
    engine: str

    # Metadata
    created_at: datetime
    name: str = ""

    def to_dict(self) -> dict: ...
    def from_dict(cls, data: dict) -> 'BacktestConfiguration': ...
    def save(self, path: Path) -> None: ...
    def load(cls, path: Path) -> 'BacktestConfiguration': ...
```

### History Storage
```python
# Store in ~/.trading_bot/backtest_history.json
{
    "runs": [
        {
            "id": "uuid",
            "timestamp": "2025-11-10T12:00:00",
            "config": {...},
            "results": {...}
        }
    ],
    "templates": [
        {
            "name": "BTC Scalp",
            "config": {...}
        }
    ]
}
```

### Widget Architecture
```python
class WizardTab(Container):
    """Main workflow tab with steps."""
    def __init__(self):
        self.state = BacktestConfiguration()
        self.sidebar = StatusSidebar(self.state)
        self.step1 = DataConfigPanel(self.state)
        self.step2 = StrategyPanel(self.state)
        self.step3 = ResultsPanel(self.state)
```

---

## Risk Assessment

**Risks:**
1. **Breaking existing workflows** - Mitigation: Keep old tabs during transition, add feature flag
2. **State synchronization bugs** - Mitigation: Single source of truth (BacktestConfiguration)
3. **Increased complexity** - Mitigation: Modular widget design, clear separation of concerns
4. **Performance with history** - Mitigation: Paginate history, lazy load old runs

---

## Next Steps

### Immediate Actions (This Week):
1. ✅ **Review this plan** with team/users
2. ✅ **Create `BacktestConfiguration` class** in `src/trading_bot/config.py`
3. ✅ **Prototype StatusSidebar** widget
4. ✅ **Design wizard tab layout** (mockup in Textual)

### Week 1-2 Goals:
- Implement Sprint 1 items (Core UX Fixes)
- User testing with new workflow
- Gather feedback, iterate

### Week 3+:
- Implement Sprint 2 & 3 based on feedback
- Document new features
- Update README with screenshots

---

## Appendix: User Testing Script

When testing, ask users to:
1. **Configure a backtest** from scratch (track time, errors)
2. **Modify and re-run** with different parameters
3. **Compare two strategies** on same data
4. **Save a template** and reload it later

**Questions:**
- Was the workflow clear?
- Did you know what was configured at each step?
- Could you complete tasks without help?
- What would you change?

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Author:** AI Assistant (Analyzing Screenshots)

