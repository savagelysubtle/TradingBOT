# Trading Bot TUI Examples with Textual

## Overview

Textual is a modern Python framework for building beautiful text user interfaces (TUIs) in the terminal. It's particularly useful for building real-time trading dashboards that don't require a browser or complex web setup.

## Key Concepts

### Reactive Variables
Reactive variables automatically trigger UI updates when their values change:

```python
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.widgets import Static, Label

class PriceDisplay(Static):
    current_price = reactive(0.0)
    
    def render(self) -> str:
        return f"Current Price: ${self.current_price:.2f}"

class TradingApp(App):
    def __init__(self):
        super().__init__()
        self.price_display = PriceDisplay()
    
    def on_mount(self) -> None:
        # Update price every second
        self.set_interval(1.0, self.update_price)
    
    def update_price(self) -> None:
        # Simulate price update
        self.price_display.current_price += 0.5
```

### Workers for Async Operations
Use workers to fetch data without blocking the UI:

```python
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static
import asyncio

class TradingBot(App):
    def compose(self) -> ComposeResult:
        yield Static(id="status")
    
    @work(exclusive=True)
    async def fetch_market_data(self) -> None:
        """Fetch market data in background"""
        status = self.query_one("#status", Static)
        status.update("Fetching data...")
        
        # Simulate API call
        await asyncio.sleep(2)
        
        status.update("Data received!")
```

### DataTable for Real-Time Data
Create sortable, interactive tables:

```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable

class PortfolioApp(App):
    def compose(self) -> ComposeResult:
        table = DataTable()
        yield table
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        
        # Add columns
        table.add_columns(
            "Symbol",
            "Price",
            "Change %",
            "Position",
            "P&L"
        )
        
        # Add rows
        table.add_rows([
            ("BTC/USD", "$43,250", "+2.5%", "0.5", "+$1,125"),
            ("ETH/USD", "$2,280", "-1.2%", "5.0", "-$114"),
            ("AAPL", "$192.50", "+0.8%", "100", "+$800"),
        ])
```

## Example 1: Simple Price Ticker

```python
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Container
from textual.reactive import reactive
from textual import on
import random

class PriceTicker(Static):
    price = reactive(100.0)
    change = reactive(0.0)
    
    def render(self) -> str:
        symbol = "█" if self.change >= 0 else "▼"
        color = "green" if self.change >= 0 else "red"
        return f"[{color}]{symbol} ${self.price:.2f} ({self.change:+.2f}%)[/{color}]"

class TickerApp(App):
    TITLE = "Trading Bot - Price Ticker"
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield PriceTicker(id="btc-ticker")
            yield PriceTicker(id="eth-ticker")
        yield Footer()
    
    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_prices)
    
    def update_prices(self) -> None:
        """Simulate price updates"""
        btc = self.query_one("#btc-ticker", PriceTicker)
        eth = self.query_one("#eth-ticker", PriceTicker)
        
        btc.price += random.uniform(-100, 100)
        btc.change = random.uniform(-5, 5)
        
        eth.price += random.uniform(-50, 50)
        eth.change = random.uniform(-5, 5)

if __name__ == "__main__":
    app = TickerApp()
    app.run()
```

## Example 2: Real-Time Portfolio Table

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import VerticalScroll
from textual.reactive import reactive
import random

class PortfolioApp(App):
    TITLE = "Trading Bot - Portfolio"
    
    def compose(self) -> ComposeResult:
        yield Header()
        table = DataTable()
        yield table
        yield Static("Press Ctrl+C to quit", id="footer")
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        
        # Define columns
        table.add_columns(
            "Symbol",
            "Entry Price",
            "Current Price",
            "Position Size",
            "Unrealized P&L",
            "Win Rate"
        )
        
        # Sample trading data
        trades = [
            ("BTC", "$40,000", "$43,250", "0.5 BTC", "+$1,625", "65%"),
            ("ETH", "$2,300", "$2,280", "5.0 ETH", "-$100", "58%"),
            ("ADA", "$0.98", "$1.05", "1000 ADA", "+$70", "52%"),
            ("XRP", "$0.52", "$0.55", "5000 XRP", "+$150", "61%"),
        ]
        
        for trade in trades:
            table.add_row(*trade)
        
        # Auto-update prices
        self.set_interval(2.0, self.update_table)
    
    def update_table(self) -> None:
        """Update table with simulated price changes"""
        table = self.query_one(DataTable)
        
        # In real implementation, fetch from API
        for row_index in range(table.row_count):
            # Simulate price change
            price_change = random.uniform(-5, 5)
            # Update cells (this is simplified)

if __name__ == "__main__":
    app = PortfolioApp()
    app.run()
```

## Example 3: Trading Bot with Status Display

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual import work
import asyncio

class StatusBox(Static):
    status = reactive("IDLE")
    
    def render(self) -> str:
        colors = {
            "IDLE": "yellow",
            "RUNNING": "green",
            "ERROR": "red",
            "WAITING": "blue"
        }
        color = colors.get(self.status, "white")
        return f"[{color}]Status: {self.status}[/{color}]"

class TradingBotApp(App):
    TITLE = "Automated Trading Bot"
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield StatusBox(id="status")
            yield Static("Trades: 0 | Win Rate: 0% | P&L: $0", id="stats")
            with Horizontal():
                yield Button("Start Bot", id="start-btn", variant="primary")
                yield Button("Stop Bot", id="stop-btn")
        yield Footer()
    
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
            for i in range(10):
                await asyncio.sleep(1)
                # Fetch market data and execute trades
                pass
        except Exception as e:
            status_box.status = "ERROR"
        finally:
            status_box.status = "IDLE"
    
    def stop_trading(self) -> None:
        status_box = self.query_one("#status", StatusBox)
        status_box.status = "IDLE"

if __name__ == "__main__":
    app = TradingBotApp()
    app.run()
```

## Production Example: FTUI (Freqtrade TUI)

FTUI is a production-grade Textual TUI for monitoring Freqtrade bots:

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

**Usage:**
```bash
ftui -y config.yaml
```

Features:
- Monitor multiple bots in one interface
- View open/closed trades
- Real-time profit tracking
- Performance analytics
- Customizable colors

## Best Practices for Trading TUIs

### 1. Use Workers for API Calls
```python
@work(exclusive=True)
async def fetch_prices(self):
    """Fetch prices without blocking UI"""
    async with AsyncClient() as client:
        response = await client.get("https://api.example.com/prices")
        self.update_ui(response.json())
```

### 2. Use Reactive Variables for Auto-Update
```python
class TradeInfo(Static):
    profit = reactive(0.0)
    
    def watch_profit(self, old_value: float, new_value: float):
        # Automatically called when profit changes
        self.styles.color = "green" if new_value > 0 else "red"
```

### 3. Implement Efficient Table Updates
```python
# Instead of recreating table:
table.update_cell("Symbol", row_key, value)

# Use DataTable for large datasets
table.zebra_stripes = True  # Better readability
table.cursor_type = "row"   # Row selection
```

### 4. Add Keyboard Shortcuts
```python
BINDINGS = [
    ("s", "start_bot", "Start"),
    ("t", "stop_bot", "Stop"),
    ("r", "refresh", "Refresh"),
    ("q", "quit", "Quit"),
]

def action_start_bot(self) -> None:
    self.start_trading()
```

### 5. Handle Real-Time Data Updates
```python
def on_mount(self) -> None:
    # Update every 500ms for price ticker
    self.set_interval(0.5, self.update_prices)
    
    # Update every 5s for portfolio
    self.set_interval(5.0, self.update_portfolio)
```

## Dependencies

```bash
pip install textual rich yfinance aiohttp
```

## Running Your First TUI

Save one of the examples above and run:

```bash
python trading_bot.py
```

Press `Ctrl+C` or `Q` to exit.

## Resources

- **Textual Documentation**: https://textual.textualize.io/
- **DataTable Guide**: https://textual.textualize.io/widgets/data_table/
- **Workers Guide**: https://textual.textualize.io/guide/workers/
- **FTUI Repository**: https://github.com/freqtrade/ftui
- **TenBagger (Portfolio Tracker)**: https://github.com/AramKoorn/TenBagger

## Next Steps

1. Start with Example 1 (Price Ticker) to understand basics
2. Expand to Example 2 (Portfolio Table) for real data
3. Add trading logic from Example 3
4. Integrate with your broker's API
5. Deploy as background service or Docker container