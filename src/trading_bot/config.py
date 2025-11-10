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
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> TradingConfig:
    """Load trading configuration from environment."""
    return TradingConfig()


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
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = self.created_at

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BacktestConfiguration:
        """Create from dictionary."""
        return cls(**data)

    def save(self, path: Path) -> None:
        """Save configuration to JSON file."""
        self.last_modified = datetime.now().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> BacktestConfiguration:
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

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

    def add_run(self, run: BacktestRun) -> None:
        """Add a backtest run to history."""
        history = self._load_history()
        history["runs"].insert(0, run.to_dict())  # Most recent first
        # Keep last 100 runs
        history["runs"] = history["runs"][:100]
        self._save_history(history)

    def get_runs(self, limit: int = 20) -> list[BacktestRun]:
        """Get recent backtest runs."""
        history = self._load_history()
        return [BacktestRun.from_dict(r) for r in history["runs"][:limit]]

    def save_template(self, config: BacktestConfiguration) -> None:
        """Save a configuration as a template."""
        if not config.name:
            config.name = config.get_display_name()
        template_file = self.templates_dir / f"{config.name}.json"
        config.save(template_file)

    def get_templates(self) -> list[BacktestConfiguration]:
        """Get all saved templates."""
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            try:
                templates.append(BacktestConfiguration.load(template_file))
            except Exception:
                continue
        return sorted(templates, key=lambda t: t.last_modified, reverse=True)

    def delete_template(self, name: str) -> bool:
        """Delete a template by name."""
        template_file = self.templates_dir / f"{name}.json"
        if template_file.exists():
            template_file.unlink()
            return True
        return False

    def _load_history(self) -> dict:
        """Load history from file."""
        if not self.history_file.exists():
            return {"runs": [], "version": "1.0"}
        try:
            with open(self.history_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # If file is corrupted, try to backup and start fresh
            logger.warning(f"History file is corrupted: {e}. Creating backup and starting fresh.")
            backup_file = self.history_file.with_suffix(".json.bak")
            try:
                if self.history_file.exists():
                    import shutil
                    shutil.copy2(self.history_file, backup_file)
                    logger.info(f"Corrupted history backed up to {backup_file}")
            except Exception:
                pass
            # Return empty history
            return {"runs": [], "version": "1.0"}

    def _save_history(self, history: dict) -> None:
        """Save history to file."""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)
