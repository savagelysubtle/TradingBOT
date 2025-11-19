"""Backtesting endpoints."""

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from trading_bot.api.bot_instance import get_bot
from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.strategy_registry import _strategy_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class BacktestRequest(BaseModel):
    """Backtest request model."""

    strategy_name: str
    symbol: str
    timeframe: str = "1d"
    limit: int = 365
    start_date: str | None = None
    end_date: str | None = None
    engine: str = "custom"
    strategy_params: dict[str, Any] | None = None


class BacktestResponse(BaseModel):
    """Backtest response model."""

    status: str
    results: dict[str, Any]
    strategy: str
    symbol: str
    execution_time_seconds: float
    request_id: str
    timestamp: int


@router.post("/backtest/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run a backtest."""
    backtest_start_time = time.time()
    logger.info("=" * 60)
    logger.info("BACKTEST ENDPOINT CALLED")
    logger.info("=" * 60)
    logger.info(f"Request parameters:")
    logger.info(f"  - strategy: {request.strategy_name}")
    logger.info(f"  - symbol: {request.symbol}")
    logger.info(f"  - engine: {request.engine}")
    logger.info(f"  - timeframe: {request.timeframe}")
    logger.info(f"  - limit: {request.limit}")
    logger.info(f"  - start_date: {request.start_date}")
    logger.info(f"  - end_date: {request.end_date}")
    logger.info(f"  - strategy_params: {request.strategy_params}")

    try:
        logger.info("Step 1: Getting bot instance...")
        bot = get_bot()
        logger.info(f"Step 1: ✅ Bot instance retrieved: {type(bot)}")
    except RuntimeError as e:
        logger.error("=" * 60)
        logger.error("ERROR: Bot instance not initialized")
        logger.error(f"Error details: {e}")
        logger.error("=" * 60)
        raise HTTPException(
            status_code=503,
            detail="Bot instance not initialized. Please wait for server to fully start.",
        ) from e

    try:
        # Validate request
        logger.info("Step 2: Validating request parameters...")
        if not request.strategy_name:
            logger.warning("Backtest request missing strategy_name")
            raise HTTPException(status_code=400, detail="strategy_name is required")
        if not request.symbol:
            logger.warning("Backtest request missing symbol")
            raise HTTPException(status_code=400, detail="symbol is required")
        logger.info("Step 2: ✅ Request parameters validated")

        # Get strategy class
        logger.info("Step 3: Getting strategy class from registry...")
        logger.debug(f"Strategy name: {request.strategy_name}")
        strategy_class = _strategy_registry.get_strategy_class(request.strategy_name)
        if strategy_class is None:
            logger.error("=" * 60)
            logger.error(f"ERROR: Strategy '{request.strategy_name}' not found or not available")
            logger.error("Available strategies may not be loaded")
            logger.error("=" * 60)
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{request.strategy_name}' not found or not available",
            )
        logger.info(f"Step 3: ✅ Strategy class retrieved: {strategy_class}")

        # Create strategy instance using the same logic as wizard_logic
        logger.info("Step 4: Creating strategy instance...")
        params = request.strategy_params or {}
        logger.debug(f"Strategy parameters: {params}")
        try:
            strategy = _create_strategy_instance(request.strategy_name, strategy_class, params)
            logger.info(f"Step 4: ✅ Strategy '{request.strategy_name}' instance created successfully")
            logger.debug(f"Strategy type: {type(strategy)}")
        except ValueError as e:
            logger.exception("=" * 60)
            logger.exception("ERROR: Invalid strategy parameters")
            logger.exception(f"Exception type: {type(e).__name__}")
            logger.exception(f"Exception message: {str(e)}")
            logger.exception("=" * 60)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy parameters: {e!s}",
            ) from e
        except Exception as e:
            logger.exception("=" * 60)
            logger.exception("ERROR: Failed to create strategy instance")
            logger.exception(f"Exception type: {type(e).__name__}")
            logger.exception(f"Exception message: {str(e)}")
            logger.exception("=" * 60)
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create strategy: {e!s}",
            ) from e

        # Determine engine
        use_backtrader = None
        if request.engine == "backtrader":
            use_backtrader = True
        elif request.engine == "vectorbt":
            use_backtrader = False

        # Run backtest
        logger.info(
            f"Starting backtest execution: strategy={request.strategy_name}, "
            f"symbol={request.symbol}, engine={request.engine}, limit={request.limit}"
        )
        execution_start = time.time()
        try:
            results = bot.backtest(
                strategy=strategy,
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe,
                limit=request.limit,
                use_backtrader=use_backtrader,
            )
            execution_time = time.time() - execution_start
            logger.info(
                f"Backtest execution completed in {execution_time:.2f}s for {request.symbol} | "
                f"Results keys: {list(results.keys())}"
            )
        except ValueError as e:
            logger.error(f"Invalid backtest parameters: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backtest parameters: {e!s}",
            ) from e
        except Exception as e:
            logger.exception(f"Backtest execution failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Backtest execution failed: {e!s}",
            ) from e

        # Convert results to JSON-serializable format
        logger.debug("Serializing backtest results")
        serializable_results = {}
        for key, value in results.items():
            try:
                if hasattr(value, "tolist"):
                    serializable_results[key] = value.tolist()
                elif hasattr(value, "item"):
                    serializable_results[key] = value.item()
                else:
                    serializable_results[key] = value
            except Exception as e:
                logger.warning(f"Failed to serialize result key '{key}': {e}")
                serializable_results[key] = str(value)

        total_time = time.time() - backtest_start_time
        logger.info(
            f"Backtest request completed successfully: "
            f"strategy={request.strategy_name}, symbol={request.symbol} | "
            f"Total time: {total_time:.2f}s | "
            f"Results: {len(serializable_results)} metrics"
        )

        return {
            "status": "success",
            "results": serializable_results,
            "strategy": request.strategy_name,
            "symbol": request.symbol,
            "execution_time_seconds": round(total_time, 2),
            "request_id": str(uuid.uuid4()),  # Unique identifier for this request
            "timestamp": int(time.time()),  # Unix timestamp
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in backtest endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e!s}",
        ) from e


def _create_strategy_instance(
    strategy_name: str, strategy_class: type[BaseStrategy], params: dict[str, Any]
) -> BaseStrategy:
    """Create strategy instance from parameters.

    Uses the same logic as wizard_logic.py to ensure consistency.
    """
    logger.debug(f"_create_strategy_instance called: strategy={strategy_name}, params={params}")
    try:
        if strategy_name == "ma_crossover":
            return strategy_class(  # type: ignore[call-arg]
                short_window=int(params.get("short_window", 50)),
                long_window=int(params.get("long_window", 200)),
                use_rsi=bool(params.get("use_rsi", False)),
                rsi_period=int(params.get("rsi_period", 14)),
                rsi_overbought=float(params.get("rsi_overbought", 70.0)),
                rsi_oversold=float(params.get("rsi_oversold", 30.0)),
            )
        elif strategy_name == "talib_ma":
            return strategy_class(  # type: ignore[call-arg]
                short_period=int(params.get("short_period", 50)),
                long_period=int(params.get("long_period", 200)),
                use_rsi=bool(params.get("use_rsi", True)),
                rsi_period=int(params.get("rsi_period", 14)),
                rsi_overbought=float(params.get("rsi_overbought", 70.0)),
                rsi_oversold=float(params.get("rsi_oversold", 30.0)),
            )
        elif strategy_name == "talib_macd":
            return strategy_class()  # type: ignore[call-arg]
        elif strategy_name == "supertrend":
            return strategy_class(  # type: ignore[call-arg]
                period=int(params.get("period", 10)),
                multiplier=float(params.get("multiplier", 3.0)),
                use_atr=bool(params.get("use_atr", True)),
            )
        elif strategy_name == "bollinger":
            return strategy_class(  # type: ignore[call-arg]
                period=int(params.get("period", 20)),
                std_dev=float(params.get("std_dev", 2.0)),
            )
        elif strategy_name == "ichimoku":
            return strategy_class()  # type: ignore[call-arg]
        elif strategy_name == "ml_randomforest":
            return strategy_class(  # type: ignore[call-arg]
                lookback=int(params.get("lookback", 50)),
                n_estimators=int(params.get("n_estimators", 100)),
                max_depth=int(params.get("max_depth", 10)),
                min_samples_split=int(params.get("min_samples_split", 5)),
                confidence_threshold=float(params.get("confidence_threshold", 0.65)),
            )
        elif strategy_name == "stop_hunt":
            return strategy_class(  # type: ignore[call-arg]
                support_lookback=int(params.get("support_lookback", 20)),
                atr_period=int(params.get("atr_period", 14)),
                cluster_min_factors=int(params.get("cluster_min_factors", 3)),
                entry_distance_pct=float(params.get("entry_distance_pct", 0.5)),
                volume_spike_multiplier=float(params.get("volume_spike_multiplier", 2.0)),
                reversal_candles=int(params.get("reversal_candles", 2)),
                stop_distance_atr=float(params.get("stop_distance_atr", 2.0)),
                use_round_numbers=bool(params.get("use_round_numbers", True)),
            )
        elif strategy_name == "multi_indicator":
            return strategy_class(  # type: ignore[call-arg]
                supertrend_period=int(params.get("supertrend_period", 10)),
                supertrend_multiplier=float(params.get("supertrend_multiplier", 3.0)),
                rsi_period=int(params.get("rsi_period", 14)),
                rsi_overbought=float(params.get("rsi_overbought", 70.0)),
                rsi_oversold=float(params.get("rsi_oversold", 30.0)),
                confirmation_threshold=float(params.get("confirmation_threshold", 0.6)),
            )
        else:
            # Try to create with params as kwargs (for strategies with standard init)
            filtered_params: dict[str, Any] = {}
            for k, v in params.items():
                if v is not None:
                    filtered_params[k] = v
            logger.debug(f"Creating strategy with filtered params: {filtered_params}")
            return strategy_class(**filtered_params)  # type: ignore[call-arg]
    except ValueError as e:
        logger.error(f"Invalid parameters for strategy '{strategy_name}': {e}")
        raise
    except TypeError as e:
        logger.error(f"Type error creating strategy '{strategy_name}': {e}")
        raise ValueError(f"Invalid parameter types: {e!s}") from e
    except Exception as e:
        logger.exception(f"Failed to create strategy '{strategy_name}': {e}")
        raise
