# TradingBOT Enhancement Quick Reference

**Quick lookup guide for Kelly Criterion and Walk-Forward Optimization implementation**

---

## 🎯 Priority Order

1. **Kelly Criterion** (4-6 hours) → +30-50% returns
2. **Walk-Forward Optimization** (8-13 hours) → 90%+ overfitting reduction

---

## Kelly Criterion Quick Start

### Copy-Paste Code Location
`docs/research/kelly-python.md` Section 1

### Key Functions
```python
kelly_criterion(win_rate, reward_risk_ratio) → float
fractional_kelly(kelly_fraction, fraction=0.5) → float
kelly_to_position_units(account_balance, kelly_fraction, entry_price, stop_loss_price) → float
```

### Recommended Settings
- **New Strategy:** Quarter Kelly (0.25)
- **Established:** Half Kelly (0.5) ⭐ RECOMMENDED
- **High Confidence:** Three-Quarter Kelly (0.75)
- **Max Risk Cap:** 5% per trade

### Integration Points
1. `src/trading_bot/risk/kelly_criterion.py` - Enhance existing
2. `src/trading_bot/backtesting/analyzer.py` - Calculate from trades
3. `src/trading_bot/broker/ccxt_broker.py` - Use for position sizing
4. `src/trading_bot/interfaces/cli.py` - Add `--kelly-fraction` option

### CLI Usage
```bash
uv run --python 3.14 trading-bot backtest \
    --symbol BTC/USDT \
    --strategy talib_ma \
    --kelly-fraction 0.5 \
    --max-risk 0.05
```

### Expected Results
- **Fixed 2%:** +28% return, Sharpe 0.82
- **Half Kelly:** +42% return, Sharpe 1.34
- **Advantage:** +14% return, +63% Sharpe improvement

---

## Walk-Forward Optimization Quick Start

### Copy-Paste Code Location
`docs/research/wfo-python.md` Section 1 (minimal), Section 3 (complete)

### Key Functions
```python
split_walk_forward(data, in_sample_pct=0.70, out_of_sample_pct=0.30, num_periods=5) → List[Tuple]
calculate_wfe(in_sample_return, out_of_sample_return) → float
```

### WFE Interpretation
- **WFE > 60%:** ✓ Strategy not overfitted
- **WFE 50-60%:** △ Borderline, acceptable
- **WFE < 50%:** ✗ Likely overfitted
- **WFE < 0%:** ✗ No edge, negative OOS returns

### Window Sizes (Standard)
- **In-Sample:** 70% of data (minimum 30+ trades)
- **Out-of-Sample:** 30% of data
- **Periods:** 5-10 minimum

### Integration Points
1. `src/trading_bot/backtesting/walk_forward_minimal.py` - NEW file
2. `src/trading_bot/backtesting/parameter_optimizer.py` - NEW file
3. `src/trading_bot/backtesting/walk_forward_backtest.py` - NEW file
4. `src/trading_bot/strategies/base.py` - Add parameterization support
5. `src/trading_bot/interfaces/cli.py` - Add `wfo` command

### CLI Usage
```bash
uv run --python 3.14 trading-bot wfo \
    --symbol BTC/USDT \
    --strategy talib_ma \
    --periods 5 \
    --metric sharpe_ratio
```

### Expected Results
- **Good Strategy:** WFE 60-80%, stable parameters
- **Overfitted Strategy:** WFE < 50%, parameters change wildly
- **90%+ reduction** in bad strategies entering live trading

---

## Implementation Timeline

### Week 1: Kelly Criterion
- Day 1-2: Enhance Kelly module, integrate with backtest analyzer
- Day 3-4: Add CLI/TUI support, integrate with broker
- Day 5: Testing & validation

### Week 2-3: Walk-Forward Optimization
- Week 2: Create WFO functions, optimizer, enhance strategies
- Week 3: Build WFO backtester, add CLI/TUI, testing

### Week 4: Integration & Polish
- Combine Kelly + WFO workflow
- Documentation
- Error handling

**Total:** 12-19 hours development + 1-2 weeks validation

---

## Code Files to Create/Modify

### New Files
- `src/trading_bot/backtesting/walk_forward_minimal.py`
- `src/trading_bot/backtesting/parameter_optimizer.py`
- `src/trading_bot/backtesting/walk_forward_backtest.py`
- `src/trading_bot/backtesting/wfo_report.py`
- `src/trading_bot/risk/adaptive_kelly.py` (optional)

### Files to Modify
- `src/trading_bot/risk/kelly_criterion.py` (enhance)
- `src/trading_bot/backtesting/analyzer.py` (add Kelly calculation)
- `src/trading_bot/backtesting/engine.py` (add WFO method)
- `src/trading_bot/strategies/base.py` (add parameterization)
- `src/trading_bot/broker/ccxt_broker.py` (use Kelly sizing)
- `src/trading_bot/interfaces/cli.py` (add commands)
- `src/trading_bot/interfaces/tui.py` (add panels)

---

## Testing Checklist

### Kelly Criterion
- [ ] Calculate Kelly from backtest trades
- [ ] Fractional Kelly works (0.25, 0.5, 0.75)
- [ ] Position sizing uses Kelly when metrics available
- [ ] Falls back to fixed 2% if insufficient trades
- [ ] Safety warnings appear for edge cases
- [ ] CLI shows Kelly analysis
- [ ] TUI displays Kelly panel

### Walk-Forward Optimization
- [ ] Data splits correctly into periods
- [ ] Optimizer finds best parameters
- [ ] WFE calculated correctly
- [ ] Overfitted strategies identified (WFE < 50%)
- [ ] Good strategies identified (WFE > 60%)
- [ ] CLI command works end-to-end
- [ ] TUI displays WFO results
- [ ] Results saved to JSON

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Kelly is negative | Strategy has no edge, don't use Kelly |
| Position size too large | Reduce `max_risk_pct` or use Quarter Kelly |
| WFE very low (< 30%) | Strategy overfitted, reduce parameters |
| WFO too slow | Reduce parameter ranges or use random search |
| Insufficient data | Need 2+ years for WFO, 20+ trades for Kelly |

---

## Key Formulas

### Kelly Criterion
```
f* = (W × b - (1 - W)) / b

Where:
- f* = Optimal capital fraction to risk
- W = Win rate (0.0-1.0)
- b = Reward/risk ratio (avg win / avg loss)
```

### Walk Forward Efficiency
```
WFE = Out-of-Sample Return / In-Sample Return

Interpretation:
- WFE > 60% = Good strategy
- WFE < 50% = Overfitted
```

---

## Reference Documents

- **Full Plan:** `docs/@docs/IMPLEMENTATION_PLAN.md`
- **Kelly Theory:** `docs/research/kelly-guide.md`
- **Kelly Code:** `docs/research/kelly-python.md`
- **WFO Theory:** `docs/research/wfo-guide.md`
- **WFO Code:** `docs/research/wfo-python.md`
- **Bot Review:** `docs/research/bot-review-guide.md`

---

## Next Steps

1. **Start with Kelly** (fastest impact, 4-6 hours)
2. **Then WFO** (most important, 8-13 hours)
3. **Combine both** for production-ready validation

**Ready?** See `docs/@docs/IMPLEMENTATION_PLAN.md` for detailed steps.

