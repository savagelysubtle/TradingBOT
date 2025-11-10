<!-- 8f1f50fa-f054-49bb-9dd3-95c34081cc0a 04acd623-22a3-4ad0-90ae-16dae35ff901 -->
# Phase 1: Database Persistence + Event-Driven Architecture

## Overview

Upgrade TradingBOT with TimescaleDB for time-series persistence and Redis Streams for event-driven architecture. This matches production patterns from Hummingbot and institutional trading systems while maintaining backward compatibility with CSV caching.

## Prerequisites Setup (Manual Steps)

### 1. Install PostgreSQL with TimescaleDB (Windows Native)

```powershell
# Install PostgreSQL 16 via winget
winget install PostgreSQL.PostgreSQL.16

# Install TimescaleDB extension
# Download from: https://docs.timescale.com/self-hosted/latest/install/installation-windows/
# Follow installer to add TimescaleDB to PostgreSQL
```

### 2. Install Redis (Windows Native)

```powershell
# Install Redis via winget (Memurai - Redis-compatible for Windows)
winget install Memurai.Memurai-Developer
```

### 3. Configure Database

```sql
-- Connect to PostgreSQL via psql or pgAdmin
CREATE DATABASE trading_bot;
\c trading_bot
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 4. Add Dependencies

```bash
# Add to project
uv add psycopg[binary] sqlalchemy timescaledb redis[hiredis] pydantic
```

## Implementation Tasks

### Task 1: Database Infrastructure

**Create `src/trading_bot/database/__init__.py`**

```python
"""Database persistence layer with TimescaleDB support."""

from trading_bot.database.models import Base, MarketData, Trade, Signal, RiskEvent
from trading_bot.database.timescale_client import TimescaleClient

__all__ = ["Base", "MarketData", "Trade", "Signal", "RiskEvent", "TimescaleClient"]
```

**Create `src/trading_bot/database/models.py`**

- Define SQLAlchemy models for: `MarketData`, `Trade`, `Signal`, `RiskEvent`
- Include proper indexes on `(symbol, time)` columns
- Add metadata fields for tracking data sources

**Create `src/trading_bot/database/timescale_client.py`**

- Implement `TimescaleClient` class with connection management
- Methods: `init_hypertables()`, `insert_ohlcv()`, `insert_trade()`, `insert_signal()`
- Create continuous aggregates for 1h, 4h, 1d candles
- Query methods: `query_candles()`, `query_trades()`, `get_latest_signal()`
- Connection pooling and error handling

**Create `src/trading_bot/database/migrations.py`**

- Schema initialization script
- Hypertable creation with proper chunk intervals
- Continuous aggregate definitions
- Index creation for performance

### Task 2: Message Broker Infrastructure

**Create `src/trading_bot/messaging/__init__.py`**

```python
"""Event-driven messaging infrastructure with Redis Streams."""

from trading_bot.messaging.broker import MessageBroker
from trading_bot.messaging.events import (
    MarketDataEvent,
    SignalEvent,
    FillEvent,
    RiskEvent,
    EventType,
)
from trading_bot.messaging.subscribers import BaseSubscriber

__all__ = [
    "MessageBroker",
    "MarketDataEvent",
    "SignalEvent",
    "FillEvent",
    "RiskEvent",
    "EventType",
    "BaseSubscriber",
]
```

**Create `src/trading_bot/messaging/events.py`**

- Define Pydantic event schemas:
  - `MarketDataEvent`: OHLCV tick updates
  - `SignalEvent`: Strategy buy/sell/hold signals
  - `FillEvent`: Order execution confirmations
  - `RiskEvent`: Risk threshold violations, regime changes
- Include `EventType` enum
- Add serialization methods (`to_dict()`, `from_dict()`)

**Create `src/trading_bot/messaging/broker.py`**

- Implement `MessageBroker` class wrapping Redis Streams
- Methods: `publish()`, `subscribe()`, `create_consumer_group()`
- Stream naming convention: `market_data:{symbol}`, `signals:{symbol}`, `fills:{symbol}`, `risk:*`
- Automatic reconnection logic
- Message acknowledgment support

**Create `src/trading_bot/messaging/subscribers.py`**

- `BaseSubscriber` abstract class for consuming events
- `AnalyticsSubscriber`: Writes events to TimescaleDB
- `LoggingSubscriber`: Writes events to logs
- Background thread/asyncio support for continuous consumption

### Task 3: Configuration Updates

**Update `src/trading_bot/config.py`**

- Add `TradingConfig` fields:
  ```python
  # Database settings
  database_url: str = Field(
      default="postgresql://postgres:password@localhost:5432/trading_bot",
      alias="DATABASE_URL",
  )
  database_enabled: bool = Field(default=True, alias="DATABASE_ENABLED")
  
  # Message broker settings
  redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
  messaging_enabled: bool = Field(default=True, alias="MESSAGING_ENABLED")
  ```


**Create `.env.example`**

- Document new environment variables
- Provide secure defaults and examples

### Task 4: Data Fetcher Integration

**Update `src/trading_bot/data/ccxt_fetcher.py`**

- Add optional `db_client` parameter to `__init__`
- In `fetch_ohlcv()`, after fetching data:
  ```python
  # Persist to TimescaleDB if enabled
  if self.db_client and self.config.database_enabled:
      try:
          self.db_client.insert_ohlcv(data, symbol, self.exchange_id)
          logger.debug(f"Persisted {len(data)} candles to TimescaleDB")
      except Exception as e:
          logger.warning(f"DB persistence failed, continuing: {e}")
  
  # Always save CSV cache (fallback)
  if self.use_cache:
      self._save_to_cache(cache_key, data)
  ```

- Add method to query DB first, fall back to CSV cache, then fetch from API

**Update `src/trading_bot/data/websocket_fetcher.py`**

- Add optional `message_broker` parameter
- In `on_message()` callback, publish `MarketDataEvent` to broker
- Keep existing callback mechanism for backward compatibility

### Task 5: Strategy Integration

**Update `src/trading_bot/strategies/base.py`**

- Add optional `message_broker` parameter to `BaseStrategy.__init__`
- In `generate_signals()`, after generating signal:
  ```python
  if self.message_broker and hasattr(self, 'messaging_enabled'):
      for idx, signal in signals.iterrows():
          if signal['signal'] != 0:
              event = SignalEvent(
                  timestamp=signal.name,
                  symbol=symbol,
                  strategy=self.name,
                  signal=int(signal['signal']),
                  price=float(signal['close']),
              )
              self.message_broker.publish(f"signals:{symbol}", event)
  ```


### Task 6: Bot Core Refactor

**Update `src/trading_bot/bot.py`**

- Add database and messaging initialization in `__init__`:
  ```python
  # Initialize database client
  if self.config.database_enabled:
      from trading_bot.database.timescale_client import TimescaleClient
      self.db_client = TimescaleClient(self.config.database_url)
      self.db_client.init_hypertables()
      logger.info("TimescaleDB client initialized")
  else:
      self.db_client = None
  
  # Initialize message broker
  if self.config.messaging_enabled:
      from trading_bot.messaging.broker import MessageBroker
      from trading_bot.messaging.subscribers import AnalyticsSubscriber
      self.message_broker = MessageBroker(self.config.redis_url)
      
      # Start analytics subscriber (writes events to DB)
      self.analytics_subscriber = AnalyticsSubscriber(
          broker=self.message_broker,
          db_client=self.db_client,
      )
      self.analytics_subscriber.start()
      logger.info("Message broker initialized")
  else:
      self.message_broker = None
  ```

- Pass `db_client` to data fetchers
- Pass `message_broker` to strategies

**Update `src/trading_bot/bot.py` - `run_live()` method**

- Publish `FillEvent` after order execution:
  ```python
  if self.message_broker:
      fill_event = FillEvent(
          timestamp=datetime.now(),
          symbol=symbol,
          side=side,
          quantity=quantity,
          price=current_price,
          commission=commission,
      )
      self.message_broker.publish(f"fills:{symbol}", fill_event)
  ```

- Store trades in database via `db_client.insert_trade()`

### Task 7: Orchestrator Update

**Update `src/trading_bot/orchestrator.py`**

- Pass `db_client` and `message_broker` to strategies in `run_strategy_async()`
- Add method to query backtest results from database instead of filesystem
- Maintain filesystem results as fallback

### Task 8: TUI Integration

**Update `src/trading_bot/interfaces/pages/wizard_page.py`**

- Add toggle for database persistence (default: enabled)
- Add toggle for event streaming (default: enabled)
- Show connection status indicators for TimescaleDB and Redis

**Create new TUI page: `src/trading_bot/interfaces/pages/analytics_page.py`**

- Query live metrics from TimescaleDB
- Display: Portfolio value over time, recent trades, signal history
- Auto-refresh every 5 seconds using Redis event stream

### Task 9: Testing and Validation

**Create `tests/test_database.py`**

- Test TimescaleDB connection
- Test hypertable insertion and querying
- Test continuous aggregate updates

**Create `tests/test_messaging.py`**

- Test Redis connection
- Test event publishing and subscription
- Test subscriber acknowledgment

**Create integration test script: `examples/test_phase1_integration.py`**

- Fetch live market data
- Verify data persisted to TimescaleDB
- Verify events published to Redis
- Verify CSV fallback still works
- Generate test report

### Task 10: Documentation

**Update `README.md`**

- Add Phase 1 features to feature list
- Update architecture diagram
- Add installation instructions for TimescaleDB and Redis

**Create `docs/DATABASE_GUIDE.md`**

- TimescaleDB setup instructions (Windows-specific)
- Schema explanation (hypertables, continuous aggregates)
- Query examples for common analytics
- Backup and restore procedures

**Create `docs/MESSAGING_GUIDE.md`**

- Redis Streams architecture overview
- Event types and schemas
- Creating custom subscribers
- Message retention policies

## Success Criteria

1. TimescaleDB stores OHLCV data with automatic hourly/daily aggregation
2. Redis broker publishes market data, signals, fills, and risk events
3. AnalyticsSubscriber writes events to database in real-time
4. CSV caching still works as fallback when DB disabled
5. TUI shows database connection status and live analytics
6. All existing backtests run without modification
7. Integration test passes with sample BTC/USDT data

## Rollback Plan

If issues arise:

1. Set `DATABASE_ENABLED=false` and `MESSAGING_ENABLED=false` in `.env`
2. Bot reverts to pure CSV caching and direct function calls
3. No breaking changes to existing functionality

## Estimated Timeline

- Database infrastructure: 2 days
- Message broker infrastructure: 2 days
- Integration into existing code: 3 days
- Testing and validation: 2 days
- Documentation: 1 day

**Total: ~10 days (2 weeks with buffer)**

### To-dos

- [ ] Install PostgreSQL 16 with TimescaleDB extension and Redis (Memurai) natively on Windows, create trading_bot database
- [ ] Add psycopg, sqlalchemy, timescaledb, redis, and hiredis to project via uv
- [ ] Create src/trading_bot/database/ with models.py (SQLAlchemy models), timescale_client.py (hypertables + queries), and migrations.py
- [ ] Create src/trading_bot/messaging/ with events.py (Pydantic schemas), broker.py (Redis Streams wrapper), and subscribers.py
- [ ] Add DATABASE_URL, DATABASE_ENABLED, REDIS_URL, MESSAGING_ENABLED to TradingConfig in config.py and create .env.example
- [ ] Update ccxt_fetcher.py and websocket_fetcher.py to persist data to TimescaleDB and publish MarketDataEvent to Redis while keeping CSV fallback
- [ ] Update strategies/base.py to publish SignalEvent to message broker when signals are generated
- [ ] Update bot.py to initialize TimescaleClient and MessageBroker, start AnalyticsSubscriber, publish FillEvent on trades, and pass clients to strategies
- [ ] Update orchestrator.py to pass db_client and message_broker to strategies during parallel backtests
- [ ] Update wizard_page.py with DB/messaging toggles, create analytics_page.py for live metrics from TimescaleDB
- [ ] Create tests/test_database.py, tests/test_messaging.py, and examples/test_phase1_integration.py
- [ ] Update README.md, create docs/DATABASE_GUIDE.md and docs/MESSAGING_GUIDE.md with Windows-specific setup