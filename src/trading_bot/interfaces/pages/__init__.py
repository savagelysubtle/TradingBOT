"""TUI page modules for the Trading Bot."""

from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.pages.dashboard_page import DashboardPage
from trading_bot.interfaces.pages.history_page import HistoryPage
from trading_bot.interfaces.pages.monte_carlo_page import MonteCarloPage
from trading_bot.interfaces.pages.paper_trading_page import PaperTradingPage
from trading_bot.interfaces.pages.strategies_page import StrategiesPage
from trading_bot.interfaces.pages.wfo_page import WFOPage
from trading_bot.interfaces.pages.wizard_logic import WizardLogic
from trading_bot.interfaces.pages.wizard_page import WizardPage
from trading_bot.interfaces.pages.wizard_widgets import (
    WizardActionWidget,
    WizardDataConfigWidget,
    WizardProgressWidget,
    WizardResultsWidget,
    WizardStrategyConfigWidget,
)

__all__ = [
    "BasePage",
    "DashboardPage",
    "HistoryPage",
    "MonteCarloPage",
    "PaperTradingPage",
    "StrategiesPage",
    "WFOPage",
    "WizardActionWidget",
    "WizardDataConfigWidget",
    "WizardLogic",
    "WizardPage",
    "WizardProgressWidget",
    "WizardResultsWidget",
    "WizardStrategyConfigWidget",
]
