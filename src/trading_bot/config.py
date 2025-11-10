"""Configuration management for the trading bot."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class TradingConfig(BaseSettings):
    """Trading bot configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Broker settings
    broker_api_key: str | None = Field(default=None, alias="BROKER_API_KEY")
    broker_secret_key: str | None = Field(default=None, alias="BROKER_SECRET_KEY")
    broker_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        alias="BROKER_BASE_URL",
    )

    # Trading settings
    initial_capital: float = Field(default=10000.0, alias="INITIAL_CAPITAL")
    max_position_size: float = Field(default=0.1, alias="MAX_POSITION_SIZE")
    risk_per_trade: float = Field(default=0.02, alias="RISK_PER_TRADE")

    # Exchange settings (CCXT)
    exchange_id: str = Field(default="binance", alias="EXCHANGE_ID")
    exchange_api_key: str | None = Field(default=None, alias="EXCHANGE_API_KEY")
    exchange_secret: str | None = Field(default=None, alias="EXCHANGE_SECRET")
    exchange_sandbox: bool = Field(default=True, alias="EXCHANGE_SANDBOX")

    # Data settings
    data_provider: str = Field(default="ccxt", alias="DATA_PROVIDER")
    cache_data: bool = Field(default=True, alias="CACHE_DATA")
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")

    # Backtesting engine (vectorbt, backtrader, or custom)
    # Note: vectorbt requires optional dependency, falls back to custom if not available
    backtest_engine: str = Field(default="custom", alias="BACKTEST_ENGINE")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("logs/trading_bot.log"), alias="LOG_FILE")

    # Results
    results_dir: Path = Field(default=Path("results"), alias="RESULTS_DIR")

    def __init__(self, **kwargs):
        """Initialize configuration and create directories."""
        super().__init__(**kwargs)
        logger.debug(f"Initializing TradingConfig: exchange={self.exchange_id}, data_provider={self.data_provider}, backtest_engine={self.backtest_engine}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Configuration initialized: data_dir={self.data_dir}, results_dir={self.results_dir}, log_file={self.log_file}")


def load_config() -> TradingConfig:
    """Load trading configuration from environment."""
    logger.info("Loading configuration from environment")
    config = TradingConfig()
    logger.info(f"Configuration loaded successfully: exchange={config.exchange_id}, initial_capital=${config.initial_capital:,.2f}")
    return config


@dataclass
class BacktestConfiguration:
    """Persistent backtest configuration state.

    This tracks all configuration needed for a backtest run,
    allowing users to save/load templates and maintain state
    across UI interactions.
    """

    # Data configuration
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1d"
    limit: int = 365
    start_date: str | None = None  # YYYY-MM-DD format
    end_date: str | None = None  # YYYY-MM-DD format

    # Strategy configuration
    strategy_name: str = "ma_crossover"
    strategy_params: dict[str, float | int | str | bool] = None

    # Engine configuration
    engine: str = "custom"

    # Metadata
    name: str = ""
    created_at: str = ""
    last_modified: str = ""

    def __post_init__(self):
        """Initialize defaults."""
        if self.strategy_params is None:
            self.strategy_params = {"short_window": 50, "long_window": 200}
            logger.debug("BacktestConfiguration: Using default strategy parameters")
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = self.created_at
        logger.debug(f"BacktestConfiguration initialized: {self.get_display_name()}")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BacktestConfiguration:
        """Create from dictionary."""
        return cls(**data)

    def save(self, path: Path) -> None:
        """Save configuration to JSON file."""
        logger.debug(f"Saving BacktestConfiguration to {path}")
        self.last_modified = datetime.now().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"BacktestConfiguration saved to {path}")

    @classmethod
    def load(cls, path: Path) -> BacktestConfiguration:
        """Load configuration from JSON file."""
        logger.debug(f"Loading BacktestConfiguration from {path}")
        try:
            with open(path) as f:
                data = json.load(f)
            config = cls.from_dict(data)
            logger.info(f"BacktestConfiguration loaded from {path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load BacktestConfiguration from {path}: {e}")
            raise

    def update(self, **kwargs) -> None:
        """Update configuration fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_modified = datetime.now().isoformat()

    def get_display_name(self) -> str:
        """Get human-readable display name."""
        if self.name:
            return self.name
        return f"{self.strategy_name}_{self.symbol.replace('/', '')}_{self.timeframe}"

    def is_complete(self) -> bool:
        """Check if configuration is complete enough to run."""
        return bool(self.exchange and self.symbol and self.strategy_name)


@dataclass
class BacktestRun:
    """Record of a completed backtest run."""

    id: str
    timestamp: str
    config: BacktestConfiguration
    results: dict

    def __post_init__(self):
        """Ensure config is BacktestConfiguration."""
        if isinstance(self.config, dict):
            self.config = BacktestConfiguration.from_dict(self.config)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        # Convert Timestamp objects to strings for JSON serialization
        serializable_results = self._make_json_serializable(self.results)
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "config": self.config.to_dict(),
            "results": serializable_results,
        }

    def _make_json_serializable(self, obj):
        """Recursively convert Timestamp and other non-serializable objects to strings."""
        import pandas as pd
        import numpy as np

        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()  # Convert numpy scalar to Python native type
        elif isinstance(obj, np.ndarray):
            return obj.tolist()  # Convert numpy array to list
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            # Try to convert to string for other types
            try:
                return str(obj)
            except Exception:
                return obj

    @classmethod
    def from_dict(cls, data: dict) -> BacktestRun:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            config=BacktestConfiguration.from_dict(data["config"]),
            results=data["results"],
        )


class BacktestHistory:
    """Manager for backtest history and templates."""

    def __init__(self, storage_dir: Path | None = None):
        """Initialize history manager."""
        if storage_dir is None:
            storage_dir = Path.home() / ".trading_bot"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "backtest_history.json"
        self.templates_dir = self.storage_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BacktestHistory initialized: storage_dir={self.storage_dir}")

    def add_run(self, run: BacktestRun) -> None:
        """Add a backtest run to history."""
        logger.debug(f"Adding backtest run to history: {run.id} - {run.config.get_display_name()}")
        history = self._load_history()
        history["runs"].insert(0, run.to_dict())  # Most recent first
        # Keep last 100 runs
        history["runs"] = history["runs"][:100]
        self._save_history(history)
        logger.info(f"Backtest run added to history: {run.id} (total runs: {len(history['runs'])})")

    def get_runs(self, limit: int = 20) -> list[BacktestRun]:
        """Get recent backtest runs."""
        logger.debug(f"Retrieving {limit} recent backtest runs")
        history = self._load_history()
        runs = [BacktestRun.from_dict(r) for r in history["runs"][:limit]]
        logger.info(f"Retrieved {len(runs)} backtest runs")
        return runs

    def save_template(self, config: BacktestConfiguration) -> None:
        """Save a configuration as a template."""
        if not config.name:
            config.name = config.get_display_name()
        template_file = self.templates_dir / f"{config.name}.json"
        logger.debug(f"Saving template: {config.name} to {template_file}")
        config.save(template_file)
        logger.info(f"Template saved: {config.name}")

    def get_templates(self) -> list[BacktestConfiguration]:
        """Get all saved templates."""
        logger.debug("Retrieving all saved templates")
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            try:
                templates.append(BacktestConfiguration.load(template_file))
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
                continue
        sorted_templates = sorted(templates, key=lambda t: t.last_modified, reverse=True)
        logger.info(f"Retrieved {len(sorted_templates)} templates")
        return sorted_templates

    def delete_template(self, name: str) -> bool:
        """Delete a template by name."""
        template_file = self.templates_dir / f"{name}.json"
        logger.debug(f"Deleting template: {name}")
        if template_file.exists():
            template_file.unlink()
            logger.info(f"Template deleted: {name}")
            return True
        logger.warning(f"Template not found: {name}")
        return False

    def _load_history(self) -> dict:
        """Load history from file."""
        logger.debug(f"Loading history from {self.history_file}")
        if not self.history_file.exists():
            logger.debug("History file does not exist, returning empty history")
            return {"runs": [], "version": "1.0"}
        try:
            with open(self.history_file, encoding="utf-8") as f:
                history = json.load(f)
                logger.debug(f"History loaded: {len(history.get('runs', []))} runs")
                return history
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # If file is corrupted, try to backup and start fresh
            logger.warning(f"History file is corrupted: {e}. Creating backup and starting fresh.")
            backup_file = self.history_file.with_suffix(".json.bak")
            try:
                if self.history_file.exists():
                    import shutil
                    shutil.copy2(self.history_file, backup_file)
                    logger.info(f"Corrupted history backed up to {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted history file: {backup_error}")
            # Return empty history
            return {"runs": [], "version": "1.0"}

    def _save_history(self, history: dict) -> None:
        """Save history to file."""
        logger.debug(f"Saving history to {self.history_file}: {len(history.get('runs', []))} runs")
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
            logger.debug("History saved successfully")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            raise
