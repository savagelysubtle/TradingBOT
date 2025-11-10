<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# what other things can I do with tui sticking with a quasnt bot

Now I have enough information. Let me create a comprehensive guide for TUI features for a quant trading bot:

## Advanced TUI Features for Quantitative Trading Bots

Building on the foundational Textual TUI from the previous guide, here are comprehensive TUI features you can integrate into a quantitative trading bot:[^1][^2][^3]

### Core Performance Metrics Display

Create a metrics panel showing real-time performance statistics:[^3][^4]

```python
from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Grid

class PerformanceMetrics(Static):
    """Display key trading metrics"""
    
    trades_executed = reactive(0)
    win_rate = reactive(0.0)
    profit_factor = reactive(0.0)
    sharpe_ratio = reactive(0.0)
    max_drawdown = reactive(0.0)
    daily_pnl = reactive(0.0)
    
    def render(self) -> str:
        return f"""
╔════════════════════════════════════╗
║   TRADING BOT PERFORMANCE          ║
╠════════════════════════════════════╣
║ Trades:        {self.trades_executed:>6d}               ║
║ Win Rate:      {self.win_rate:>6.1f}%              ║
║ Profit Factor: {self.profit_factor:>6.2f}              ║
║ Sharpe Ratio:  {self.sharpe_ratio:>6.2f}              ║
║ Max Drawdown:  {self.max_drawdown:>6.2f}%             ║
║ Daily P&L:     ${self.daily_pnl:>10,.2f}         ║
╚════════════════════════════════════╝
        """
```


### Real-Time Signal Log

Display recent trading signals with timestamp, symbol, signal type, and confirmation score:[^5]

```python
from textual.widgets import DataTable
from datetime import datetime

class SignalLog(Static):
    """Track recent trading signals"""
    
    def on_mount(self) -> None:
        table = DataTable()
        self.mount(table)
        
        table.add_columns(
            "Time",
            "Symbol",
            "Signal",
            "Indicator",
            "Confidence",
            "Status"
        )
        
        # Example entries
        signals = [
            (
                datetime.now().strftime("%H:%M:%S"),
                "BTC/USD",
                "BUY",
                "RSI Oversold",
                "92%",
                "✓ EXECUTED"
            ),
            (
                datetime.now().strftime("%H:%M:%S"),
                "ETH/USD",
                "HOLD",
                "MACD Flat",
                "45%",
                "WAITING"
            ),
        ]
        
        for signal in signals:
            table.add_row(*signal)
```


### Risk Management Panel

Display active risk parameters and alerts:[^2]

```python
class RiskPanel(Static):
    """Monitor risk management parameters"""
    
    max_position_size = reactive(0.05)  # 5% of capital
    stop_loss_pct = reactive(0.02)      # 2% stop-loss
    max_drawdown_limit = reactive(0.15) # 15% max drawdown
    current_exposure = reactive(0.0)
    
    def render(self) -> str:
        exposure_color = "red" if self.current_exposure > 0.8 else "yellow" if self.current_exposure > 0.5 else "green"
        
        return f"""
╔════════════════════════════════════╗
║   RISK MANAGEMENT                  ║
╠════════════════════════════════════╣
║ Max Position:  {self.max_position_size*100:>5.1f}%          ║
║ Stop-Loss:     {self.stop_loss_pct*100:>5.1f}%          ║
║ Max Drawdown:  {self.max_drawdown_limit*100:>5.1f}%          ║
║ Current Exp:   [{exposure_color}]{self.current_exposure*100:>5.1f}%[/{exposure_color}]         ║
╚════════════════════════════════════╝
        """
```


### Open Positions Monitor

Track all active trades with entry price, current price, and P\&L:[^1]

```python
class OpenPositions(Static):
    """Display live open trades"""
    
    def on_mount(self) -> None:
        table = DataTable()
        self.mount(table)
        
        table.add_columns(
            "Symbol",
            "Entry Price",
            "Current Price",
            "Size",
            "Entry Time",
            "P&L $",
            "P&L %",
            "Stop Loss"
        )
        
        positions = [
            ("BTC", "$42,500", "$43,250", "0.5", "14:30:22", "+$375", "+0.88%", "$41,650"),
            ("ETH", "$2,320", "$2,280", "5.0", "15:15:45", "-$200", "-0.86%", "$2,273"),
        ]
        
        for pos in positions:
            table.add_row(*pos)
```


### Alert \& Event Log

Stream important bot events with configurable severity levels:[^6][^5]

```python
class AlertLog(Static):
    """Real-time alert system"""
    
    def on_mount(self) -> None:
        table = DataTable()
        self.mount(table)
        
        table.add_columns(
            "Timestamp",
            "Level",
            "Event",
            "Details"
        )
        
        alerts = [
            ("10:45:23", "[red]ERROR[/red]", "API Connection Lost", "Reconnecting..."),
            ("10:44:15", "[yellow]WARNING[/yellow]", "High Slippage", "BTC: 15bps (normal: 5bps)"),
            ("10:43:02", "[green]INFO[/green]", "Trade Executed", "BTC Long @ $43,250"),
            ("10:41:50", "[cyan]DEBUG[/cyan]", "Signal Generated", "ETH RSI=25 (oversold)"),
        ]
        
        for alert in alerts:
            table.add_row(*alert)
```


### Backtesting Results Viewer

Display historical backtest performance analysis:[^7][^8]

```python
class BacktestResults(Static):
    """Show backtesting metrics"""
    
    total_trades = reactive(0)
    winning_trades = reactive(0)
    losing_trades = reactive(0)
    total_return = reactive(0.0)
    sharpe_ratio = reactive(0.0)
    
    def watch_total_trades(self) -> None:
        """Calculate win rate when trades change"""
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            self.post_message(f"Win Rate: {win_rate:.1f}%")
    
    def render(self) -> str:
        if self.total_trades == 0:
            return "No backtest data available"
        
        win_rate = (self.winning_trades / self.total_trades) * 100
        return f"""
╔════════════════════════════════════╗
║   BACKTEST RESULTS                 ║
╠════════════════════════════════════╣
║ Total Trades:   {self.total_trades:>6d}              ║
║ Winning:        {self.winning_trades:>6d}              ║
║ Losing:         {self.losing_trades:>6d}              ║
║ Win Rate:       {win_rate:>6.1f}%             ║
║ Total Return:   {self.total_return:>6.2f}%             ║
║ Sharpe Ratio:   {self.sharpe_ratio:>6.2f}              ║
╚════════════════════════════════════╝
        """
```


### Strategy Parameter Adjustment Panel

Allow real-time tweaking of strategy parameters without restarting:[^9][^3]

```python
from textual.widgets import Input, Button
from textual.containers import Horizontal

class StrategyParams(Static):
    """Adjust trading parameters live"""
    
    rsi_oversold = reactive(30)
    rsi_overbought = reactive(70)
    moving_avg_period = reactive(20)
    volatility_threshold = reactive(2.0)
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("RSI Oversold:")
            yield Input(value="30", id="rsi-oversold")
            
            yield Label("Moving Avg Period:")
            yield Input(value="20", id="ma-period")
            
            with Horizontal():
                yield Button("Apply", id="apply-params", variant="primary")
                yield Button("Reset", id="reset-params")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-params":
            self.apply_parameters()
        elif event.button.id == "reset-params":
            self.reset_to_defaults()
```


### Multi-Exchange Connection Status

Show real-time connection status and data freshness for multiple exchanges:[^10]

```python
class ExchangeStatus(Static):
    """Monitor exchange connectivity"""
    
    def on_mount(self) -> None:
        table = DataTable()
        self.mount(table)
        
        table.add_columns(
            "Exchange",
            "Status",
            "Latency",
            "Last Update",
            "Pairs"
        )
        
        exchanges = [
            ("Binance", "[green]✓ CONNECTED[/green]", "45ms", "10:45:23", "1,245"),
            ("Coinbase", "[green]✓ CONNECTED[/green]", "120ms", "10:45:22", "89"),
            ("Kraken", "[yellow]⚠ SLOW[/yellow]", "850ms", "10:45:10", "156"),
        ]
        
        for ex in exchanges:
            table.add_row(*ex)
```


### Heatmap for Pair Performance

Visualize which trading pairs are performing best in a grid:[^11]

```python
class PairHeatmap(Static):
    """Visual representation of pair performance"""
    
    def render(self) -> str:
        # Color intensity based on performance
        return """
╔═══════════════════════════════════╗
║   PAIR PERFORMANCE HEATMAP        ║
╠═══════════════════════════════════╣
║ BTC:  [green]████████[/green] +2.1%             ║
║ ETH:  [red]██[/red]      -1.2%             ║
║ ADA:  [yellow]█████[/yellow]   +0.8%             ║
║ XRP:  [green]███████[/green] +1.5%             ║
║ DOT:  [red]███[/red]     -0.3%             ║
╚═══════════════════════════════════╝
        """
```


### Live Order Book Monitor

Display current bid/ask spreads and depth:[^10]

```python
class OrderBook(Static):
    """Real-time order book visualization"""
    
    def on_mount(self) -> None:
        table = DataTable()
        self.mount(table)
        
        table.add_columns(
            "Asks (Sell)",
            "Size",
            "Bid/Ask",
            "Size",
            "Bids (Buy)"
        )
        
        bids_asks = [
            ("$43,300", "2.5", "---", "---", "$43,100 - 1.8"),
            ("$43,250", "5.2", "[yellow]SPREAD[/yellow]", "[yellow]$150[/yellow]", "$42,950 - 3.1"),
            ("$43,200", "3.8", "---", "---", "$42,850 - 2.4"),
        ]
        
        for bid_ask in bids_asks:
            table.add_row(*bid_ask)
```


### Trade History with Filters

Query past trades by date, symbol, or result:[^6]

```python
class TradeHistory(Static):
    """Search and filter past trades"""
    
    def compose(self) -> ComposeResult:
        yield Label("Filter trades (symbol, date range, P&L):")
        with Horizontal():
            yield Input(placeholder="Symbol", id="filter-symbol")
            yield Input(placeholder="From date", id="filter-from")
            yield Button("Search", id="search-trades")
        
        table = DataTable()
        yield table
        
        table.add_columns(
            "Date",
            "Time",
            "Symbol",
            "Side",
            "Entry",
            "Exit",
            "Size",
            "P&L",
            "Exit Reason"
        )
        
        trades = [
            ("2025-11-10", "14:30:45", "BTC", "LONG", "$42,500", "$43,250", "0.5", "+$375", "TP"),
            ("2025-11-10", "15:15:22", "ETH", "LONG", "$2,320", "$2,280", "5.0", "-$200", "SL"),
        ]
        
        for trade in trades:
            table.add_row(*trade)
```


### System Health Monitor

Track CPU, memory, network usage, and data freshness:[^11][^6]

```python
class SystemHealth(Static):
    """Monitor bot system resources"""
    
    cpu_percent = reactive(25.0)
    memory_percent = reactive(45.0)
    network_mbps = reactive(2.1)
    data_latency_ms = reactive(45)
    
    def render(self) -> str:
        cpu_bar = "█" * int(self.cpu_percent / 5) + "░" * (20 - int(self.cpu_percent / 5))
        mem_bar = "█" * int(self.memory_percent / 5) + "░" * (20 - int(self.memory_percent / 5))
        
        return f"""
╔════════════════════════════════════╗
║   SYSTEM HEALTH                    ║
╠════════════════════════════════════╣
║ CPU:     {cpu_bar} {self.cpu_percent:>5.1f}%  ║
║ Memory:  {mem_bar} {self.memory_percent:>5.1f}%  ║
║ Network: {self.network_mbps:>5.1f} Mbps              ║
║ Latency: {self.data_latency_ms:>5.0f} ms               ║
╚════════════════════════════════════╝
        """
```


### Notification/Telegram Integration Indicator

Show which alerts are being sent to external channels:[^12][^5]

```python
class NotificationStatus(Static):
    """Track notification delivery"""
    
    telegram_enabled = reactive(True)
    email_enabled = reactive(False)
    webhook_enabled = reactive(True)
    last_alert_sent = reactive("None")
    
    def render(self) -> str:
        tg = "[green]✓[/green]" if self.telegram_enabled else "[red]✗[/red]"
        em = "[green]✓[/green]" if self.email_enabled else "[red]✗[/red]"
        wh = "[green]✓[/green]" if self.webhook_enabled else "[red]✗[/red]"
        
        return f"""
╔════════════════════════════════════╗
║   NOTIFICATION CHANNELS            ║
╠════════════════════════════════════╣
║ Telegram:  {tg}                      ║
║ Email:     {em}                      ║
║ Webhook:   {wh}                      ║
║ Last Sent: {self.last_alert_sent}   ║
╚════════════════════════════════════╝
        """
```


### Implementation Tips

**1. Update Strategy with Workers** – Fetch all metrics asynchronously to avoid UI freezing:[^1]

```python
@work(exclusive=True)
async def fetch_all_metrics(self):
    """Update all dashboard metrics without blocking"""
    metrics = await self.get_metrics_from_api()
    self.query_one(PerformanceMetrics).trades_executed = metrics['trades']
    self.query_one(PerformanceMetrics).win_rate = metrics['win_rate']
```

**2. Color Code by Status** – Use red/yellow/green to indicate conditions:[^11][^1]

```python
def watch_current_exposure(self, old: float, new: float):
    """Auto-color based on exposure level"""
    if new > 0.8:
        self.styles.color = "red"  # Over-exposed
    elif new > 0.5:
        self.styles.color = "yellow"  # Moderate
    else:
        self.styles.color = "green"  # Safe
```

**3. Keyboard Navigation** – Add shortcuts for quick access:

```python
BINDINGS = [
    ("p", "toggle_positions", "Positions"),
    ("a", "toggle_alerts", "Alerts"),
    ("b", "toggle_backtest", "Backtest"),
    ("r", "refresh_all", "Refresh"),
]
```

These TUI components transform a basic trading bot into a comprehensive monitoring and control center that provides real-time visibility into all aspects of your quantitative trading strategy without requiring a web browser or heavy resource consumption.
<span style="display:none">[^13][^14][^15][^16][^17][^18][^19][^20]</span>

<div align="center">⁂</div>

[^1]: https://www.biz4group.com/blog/build-ai-quantitative-trading-bot

[^2]: https://ideausher.com/blog/building-a-trading-bot/

[^3]: https://www.antiersolutions.com/blogs/the-complete-guide-to-building-crypto-ai-quantitative-trading-bots/

[^4]: https://www.gunbot.com/blog/compare-trading-bot-performance/

[^5]: https://blog.pickmytrade.io/standard-bots-stock-monitoring/

[^6]: https://optionalpha.com/help/bot-logs

[^7]: https://library.tradingtechnologies.com/tt-backtesting/rb-displaying-backtest-results.html

[^8]: https://www.quantconnect.com/forum/discussion/7322/visualizing-the-results-of-back-tests/

[^9]: https://www.luxalgo.com/blog/building-your-first-trading-bot-step-by-step-guide/

[^10]: https://3commas.io/blog/ai-trading-bots-real-time-market-data

[^11]: https://www.smiletotalk.com/blog/crypto-trading-bots-dashboards-ai-automation-ux-reviews-2025

[^12]: https://www.gunbot.com/blog/gunbot-monitor-for-power-users/

[^13]: https://blog.sourcetable.com/quant/

[^14]: https://digitaloneagency.com.au/build-a-high-performance-algo-trading-bot-with-digital-one-agency/

[^15]: https://www.luxalgo.com/blog/quantitative-trading-data-driven-strategies/

[^16]: https://obside.com/trading-algorithmic-trading/automated-trading-bots/

[^17]: https://www.wallstreetzen.com/blog/best-quantitative-analysis-trading-tools/

[^18]: https://www.quantconnect.com

[^19]: https://cornix.io/features/tracking-performance/

[^20]: https://github.com/freqtrade/frequi/issues/247

