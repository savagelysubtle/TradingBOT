"""User interfaces for the trading bot (CLI and TUI)."""

from trading_bot.interfaces.cli import cli
from trading_bot.interfaces.tui import TradingBotTUI, main as tui_main

__all__ = ["cli", "TradingBotTUI", "tui_main"]
