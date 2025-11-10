<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Trading Bot TUI Examples with Textual

Textual is a powerful modern Python framework for building interactive terminal user interfaces (TUIs). It's excellent for real-time trading dashboards because it doesn't require a browser and provides responsive, professional-looking UIs in the terminal.[^1][^2]

## Core Concepts for Trading TUIs

### Reactive Variables for Auto-Updating Displays

**Reactive attributes** automatically trigger UI updates when their values change, making them perfect for displaying live trading data:[^2]

```python
from textual.reactive import reactive
from textual.widgets import Static

class PriceDisplay(Static):
    current_price = reactive(0.0)
    
    def render(self) -> str:
        return f"Current Price: ${self.current_price:.2f}"
    
    def watch_current_price(self, old_value: float, new_value: float):
        # Called automatically when current_price changes
        self.styles.color = "green" if new_value > old_value else "red"
```

When you update `self.current_price`, the display automatically re-renders. This eliminates the need for manual refresh calls.[^2]

### Workers for Non-Blocking API Calls

The `@work` decorator runs async functions in the background without freezing the UI. This is critical for trading bots that need to fetch market data continuously:[^3]

```python
from textual import work
import asyncio

class TradingBot(App):
    @work(exclusive=True)
    async def fetch_market_data(self):
        """Fetch data in background without blocking UI"""
        status = self.query_one("#status", Static)
        status.update("Fetching data...")
        
        # Simulate API call
        await asyncio.sleep(2)
        
        status.update("Data received!")
```

The `exclusive=True` parameter ensures only one worker runs at a time, preventing race conditions when handling concurrent requests.[^1]

### DataTable for Real-Time Data

Textual's DataTable widget efficiently displays and updates large datasets:[^4]

```python
from textual.widgets import DataTable

class PortfolioApp(App):
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        
        # Add columns
        table.add_columns(
            "Symbol",
            "Entry Price",
            "Current Price",
            "Position Size",
            "Unrealized P&L"
        )
        
        # Add data rows
        table.add_rows([
            ("BTC", "$40,000", "$43,250", "0.5", "+$1,625"),
            ("ETH", "$2,300", "$2,280", "5.0", "-$100"),
        ])
        
        # Optional: enable visual enhancements
        table.zebra_stripes = True
        table.cursor_type = "row"
```


## Complete Trading Bot Example

This comprehensive example demonstrates a complete trading bot TUI with status tracking, real-time updates, and control buttons:

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, DataTable
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual import work
import asyncio
import random

class StatusBox(Static):
    status = reactive("IDLE")
    
    def render(self) -> str:
        colors = {"IDLE": "yellow", "RUNNING": "green", "ERROR": "red"}
        color = colors.get(self.status, "white")
        return f"[{color}]Status: {self.status}[/{color}]"

class TradingBotApp(App):
    TITLE = "Automated Trading Bot"
    BINDINGS = [
        ("s", "start_bot", "Start"),
        ("t", "stop_bot", "Stop"),
        ("r", "refresh", "Refresh"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield StatusBox(id="status")
            yield Static("Trades: 0 | Win Rate: 0%", id="stats")
            table = DataTable()
            yield table
            with Horizontal():
                yield Button("Start Bot", id="start-btn", variant="primary")
                yield Button("Stop Bot", id="stop-btn")
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Symbol", "Price", "Change", "Position", "P&L")
        
        # Initialize with sample data
        table.add_rows([
            ("BTC", "$43,250", "+2.5%", "0.5", "+$1,125"),
            ("ETH", "$2,280", "-1.2%", "5.0", "-$114"),
        ])
        
        # Update prices every 2 seconds
        self.set_interval(2.0, self.update_prices)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.start_trading()
        elif event.button.id == "stop-btn":
            self.stop_trading()
    
    @work(exclusive=True)
    async def start_trading(self) -> None:
        status_box = self.query_one("#status", StatusBox)
        status_box.status = "RUNNING"
        
        try:
            # Simulate trading loop
            for i in range(20):
                await asyncio.sleep(1)
                # Fetch market data and execute trades
        except Exception as e:
            status_box.status = "ERROR"
        finally:
            status_box.status = "IDLE"
    
    def stop_trading(self) -> None:
        self.query_one("#status", StatusBox).status = "IDLE"
    
    def update_prices(self) -> None:
        """Simulate live price updates"""
        # In production, fetch from API
        pass

if __name__ == "__main__":
    app = TradingBotApp()
    app.run()
```


## Production-Grade Example: FTUI (Freqtrade TUI)

FTUI is a battle-tested Textual TUI for monitoring Freqtrade algorithmic trading bots in production. It demonstrates professional architecture and real-world patterns:[^5][^6]

**Installation:**

```bash
pip install ftui
```

**Configuration (config.yaml):**

```yaml
servers:
    - name: "bot1"
      username: "your_username"
      password: "your_password"
      ip: 127.0.0.1
      port: 8080
    - name: "bot2"
      username: "your_username"
      password: "your_password"
      ip: 127.0.0.1
      port: 8081

colours:
    pair_col: "purple"
    bot_col: "yellow"
    profit_chart_col: "orange"
    winrate_col: "cyan"
```

**Running FTUI:**

```bash
ftui -y config.yaml
```

FTUI provides:[^6]

- Multi-bot monitoring across multiple servers
- Real-time open/closed trade displays
- Performance analytics and profit tracking
- Customizable color schemes
- Lightweight terminal interface without browser dependency


## Real-Time Portfolio Tracker Example

TenBagger is another production example demonstrating a full-featured portfolio tracking TUI:[^7]

```bash
# Install
git clone https://github.com/AramKoorn/TenBagger
cd TenBagger
pip install .

# Configure your portfolio
vi ~/.tenbagger/portfolio.yaml

# Run with real-time updates
tenbagger --portfolio my_portfolio
```

TenBagger shows how to:

- Fetch real-time market data (using yfinance)
- Display portfolio metrics
- Handle live price updates
- Build responsive layouts


## Key Patterns for Production Trading TUIs

**1. Update Strategies by Interval:**

```python
def on_mount(self) -> None:
    # Fast updates for price ticker (500ms)
    self.set_interval(0.5, self.update_prices)
    
    # Slower updates for portfolio (5s)
    self.set_interval(5.0, self.update_portfolio)
```

**2. Handle Blocking Operations in Threads:**

```python
@work(thread=True)  # For non-async APIs
def sync_api_call(self):
    worker = get_current_worker()
    if not worker.is_cancelled:
        self.call_from_thread(self.update_ui, data)
```

**3. Keyboard Shortcuts for Controls:**

```python
BINDINGS = [
    ("s", "start_bot", "Start"),
    ("t", "stop_bot", "Stop"),
    ("ctrl+r", "refresh", "Refresh"),
]

def action_start_bot(self) -> None:
    self.start_trading()
```

**4. Responsive Layouts:**

```python
class TradingApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #header {
        height: 3;
        dock: top;
    }
    
    #table {
        height: 1fr;  # Fill remaining space
    }
    
    #footer {
        height: 1;
        dock: bottom;
    }
    """
```


## Getting Started

**Installation:**

```bash
pip install textual rich yfinance aiohttp
```

**Run an Example:**

```bash
# Save any of the code examples above to trading_bot.py
python trading_bot.py
```

Press `Ctrl+C` or `Q` to exit.

## Resources

- **Textual Documentation**: Modern framework guide with extensive examples[^1]
- **Textual DataTable Widget**: Building interactive tables for data display[^4]
- **Textual Workers Guide**: Managing concurrent operations safely[^2]
- **FTUI Repository**: Production Freqtrade TUI with full source code[^6]
- **TenBagger**: Portfolio tracker demonstrating real-world patterns[^7]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://realpython.com/python-textual/

[^2]: https://textual.textualize.io/guide/reactivity/

[^3]: https://stackoverflow.com/questions/76350180/how-to-update-a-textual-tui-within-a-function-call

[^4]: https://textual.textualize.io/widgets/data_table/

[^5]: https://www.youtube.com/watch?v=DXkumQlENKk

[^6]: https://github.com/freqtrade/ftui

[^7]: https://www.reddit.com/r/Python/comments/qouywd/i_created_a_cli_financial_tool_using_a_text_user/

[^8]: https://www.youtube.com/watch?v=WcfKaZL4vpA

[^9]: https://www.youtube.com/watch?v=_87QHZXOOKA

[^10]: https://www.buildalpha.com/python-tips-for-automated-trading/

[^11]: https://www.youtube.com/watch?v=ttlGF-G-_ks

[^12]: https://www.reddit.com/r/Daytrading/comments/1ghidl3/coded_my_trading_strategy_into_a_bot_and_these/

[^13]: https://dev.to/devasservice/introduction-to-textual-building-modern-text-user-interfaces-in-python-6c2

[^14]: https://github.com/matan-h/written-in-textual

[^15]: https://www.pyquantnews.com/free-python-resources/building-interactive-trading-dashboards-with-python

[^16]: https://www.youtube.com/watch?v=EoU0PXFosjI

[^17]: https://eodhd.com/financial-academy/building-stocks-apps-examples/build-a-financial-trading-dashboard-with-python-django

[^18]: https://www.freqtrade.io/en/stable/freq-ui/

[^19]: https://www.youtube.com/watch?v=19-rFVgJVkg

[^20]: https://www.youtube.com/watch?v=t0m1I_vVsIA

[^21]: https://www.youtube.com/watch?v=x-LS2KiFZ5s

[^22]: https://pypi.org/project/textual-fastdatatable/

[^23]: https://wire.insiderfinance.io/build-a-real-time-stock-price-tracker-with-python-a-step-by-step-tutorial-e3ab38352ec5

[^24]: https://www.geeksforgeeks.org/python/build-a-gui-application-to-get-live-stock-price-using-python/

[^25]: https://github.com/Textualize/textual/discussions/1883

[^26]: https://www.youtube.com/watch?v=GSHFzqqPq5U

[^27]: https://textual.textualize.io/blog/2022/11/24/spinners-and-progress-bars-in-textual/

