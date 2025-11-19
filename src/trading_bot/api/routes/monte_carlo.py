"""Monte Carlo simulation endpoints."""

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from trading_bot.api.bot_instance import get_bot
from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.strategy_registry import _strategy_registry

# Global job storage (in production, use Redis/database)
import asyncio
from typing import Dict
monte_carlo_jobs: Dict[str, Dict[str, Any]] = {}

logger = logging.getLogger(__name__)

router = APIRouter()


async def run_monte_carlo_background(job_id: str, request: "MonteCarloRequest"):
    """Run Monte Carlo simulation in background."""
    logger.info(f"🟢 BACKGROUND FUNCTION CALLED for job {job_id}")

    try:
        # Update job status
        monte_carlo_jobs[job_id]["status"] = "running"
        monte_carlo_jobs[job_id]["started_at"] = time.time()

        logger.info(f"Starting background Monte Carlo job {job_id}")

        # Get bot instance
        bot = get_bot()

        # Validate strategy
        strategy_class = _strategy_registry.get_strategy_class(request.strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {request.strategy_name}")

        # Create strategy instance
        params = request.strategy_params or {}
        strategy = _create_strategy_instance(request.strategy_name, strategy_class, params)

        # Fetch data
        data = bot.data_fetcher.fetch_ohlcv(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=request.limit,
        )

        # Create Monte Carlo engine
        mc_engine = MonteCarloEngine(
            initial_capital=request.initial_capital,
            commission=request.commission,
            slippage=request.slippage,
            random_seed=request.random_seed,
        )

        # Progress callback to update job status
        def progress_callback(completed_simulations: int):
            progress_percentage = (completed_simulations / request.n_simulations) * 100
            monte_carlo_jobs[job_id]["progress"] = {
                "completed_simulations": completed_simulations,
                "total_simulations": request.n_simulations,
                "percentage": progress_percentage
            }
            logger.debug(f"Monte Carlo progress: {completed_simulations}/{request.n_simulations} ({progress_percentage:.1f}%)")

        # Run Monte Carlo simulation
        start_time = time.time()
        results = mc_engine.run(
            strategy=strategy,
            data=data,
            symbol=request.symbol,
            method=request.method,
            progress_callback=progress_callback,
        )
        simulation_time = time.time() - start_time

        # Store results
        monte_carlo_jobs[job_id]["status"] = "completed"
        monte_carlo_jobs[job_id]["completed_at"] = time.time()
        monte_carlo_jobs[job_id]["results"] = results
        monte_carlo_jobs[job_id]["simulation_time"] = simulation_time

        logger.info(f"Background Monte Carlo job {job_id} completed successfully in {simulation_time:.2f}s")

    except Exception as e:
        logger.exception(f"Background Monte Carlo job {job_id} failed: {e}")
        monte_carlo_jobs[job_id]["status"] = "failed"
        monte_carlo_jobs[job_id]["error"] = str(e)
        monte_carlo_jobs[job_id]["completed_at"] = time.time()


class MonteCarloRequest(BaseModel):
    """Monte Carlo simulation request model."""

    strategy_name: str
    symbol: str
    timeframe: str = "1d"
    limit: int = 365
    start_date: str | None = None
    end_date: str | None = None
    method: str = "bootstrap"  # bootstrap, shuffle_trades, randomize_returns
    n_simulations: int = 1000
    initial_capital: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    random_seed: int | None = None
    strategy_params: dict[str, Any] | None = None


@router.post("/monte-carlo/run")
async def run_monte_carlo(request: MonteCarloRequest, background_tasks: BackgroundTasks):
    """Submit a Monte Carlo simulation job."""
    logger.info("=" * 60)
    logger.info("MONTE CARLO JOB SUBMISSION ENDPOINT CALLED")
    logger.info("=" * 60)
    logger.info(f"Request parameters:")
    logger.info(f"  - strategy: {request.strategy_name}")
    logger.info(f"  - symbol: {request.symbol}")
    logger.info(f"  - method: {request.method}")
    logger.info(f"  - n_simulations: {request.n_simulations}")
    logger.info(f"  - timeframe: {request.timeframe}")
    logger.info(f"  - limit: {request.limit}")
    logger.info(f"  - initial_capital: {request.initial_capital}")
    logger.info(f"  - commission: {request.commission}")
    logger.info(f"  - slippage: {request.slippage}")
    logger.info(f"  - random_seed: {request.random_seed}")
    logger.info(f"  - strategy_params: {request.strategy_params}")

    monte_carlo_start_time = time.time()

    try:
        # Validate request
        logger.info("Step 1: Validating request parameters...")
        if not request.strategy_name:
            logger.warning("Monte Carlo request missing strategy_name")
            raise HTTPException(status_code=400, detail="strategy_name is required")
        if not request.symbol:
            logger.warning("Monte Carlo request missing symbol")
            raise HTTPException(status_code=400, detail="symbol is required")
        if request.method not in ["bootstrap", "shuffle_trades", "randomize_returns"]:
            logger.warning(f"Invalid Monte Carlo method: {request.method}")
            raise HTTPException(
                status_code=400,
                detail="method must be one of: bootstrap, shuffle_trades, randomize_returns",
            )
        if request.n_simulations < 1:
            logger.warning(f"Invalid n_simulations: {request.n_simulations}")
            raise HTTPException(status_code=400, detail="n_simulations must be >= 1")
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

        # Create strategy instance (reuse backtest logic)
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

        # Create job
        job_id = str(uuid.uuid4())
        logger.info(f"Step 5: Created job ID: {job_id}")

        # Initialize job status
        monte_carlo_jobs[job_id] = {
            "status": "pending",
            "created_at": time.time(),
            "request": request.dict(),
            "strategy": request.strategy_name,
            "symbol": request.symbol,
            "method": request.method,
            "n_simulations": request.n_simulations,
        }

        # Submit background task using asyncio
        asyncio.create_task(run_monte_carlo_background(job_id, request))

        total_time = time.time() - monte_carlo_start_time
        logger.info(
            f"Monte Carlo job submitted successfully: job_id={job_id}, "
            f"strategy={request.strategy_name}, symbol={request.symbol} | "
            f"Total time: {total_time:.2f}s"
        )

        return {
            "status": "job_submitted",
            "job_id": job_id,
            "message": "Monte Carlo simulation job submitted successfully",
            "strategy": request.strategy_name,
            "symbol": request.symbol,
            "method": request.method,
            "n_simulations": request.n_simulations,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in Monte Carlo endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.get("/monte-carlo/status/{job_id}")
async def get_monte_carlo_status(job_id: str):
    """Get the status of a Monte Carlo simulation job."""
    if job_id not in monte_carlo_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = monte_carlo_jobs[job_id]
    response = {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "strategy": job["strategy"],
        "symbol": job["symbol"],
        "method": job["method"],
        "n_simulations": job["n_simulations"],
    }

    if "started_at" in job:
        response["started_at"] = job["started_at"]

    if "completed_at" in job:
        response["completed_at"] = job["completed_at"]
        response["execution_time_seconds"] = job["completed_at"] - job["started_at"]

    if job["status"] == "failed":
        response["error"] = job.get("error", "Unknown error")

    return response


@router.get("/monte-carlo/results/{job_id}")
async def get_monte_carlo_results(job_id: str):
    """Get the results of a completed Monte Carlo simulation job."""
    if job_id not in monte_carlo_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = monte_carlo_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job['status']}"
        )

    # Convert results to JSON-serializable format
    results = job["results"]
    serializable_results = {}
    for key, value in results.items():
        try:
            if key in ["all_returns", "all_final_values", "all_max_drawdowns"]:
                # Convert large arrays to lists (may be truncated for performance)
                if hasattr(value, "tolist"):
                    serializable_results[key] = value.tolist()
                elif isinstance(value, list):
                    serializable_results[key] = value
                else:
                    serializable_results[key] = str(value)
            elif hasattr(value, "tolist"):
                serializable_results[key] = value.tolist()
            elif hasattr(value, "item"):
                serializable_results[key] = value.item()
            else:
                serializable_results[key] = value
        except Exception as e:
            logger.warning(f"Failed to serialize result key '{key}': {e}")
            serializable_results[key] = str(value)

    return {
        "job_id": job_id,
        "status": "completed",
        "results": serializable_results,
        "strategy": job["strategy"],
        "symbol": job["symbol"],
        "method": job["method"],
        "n_simulations": job["n_simulations"],
        "execution_time_seconds": round(job.get("simulation_time", 0), 2),
        "completed_at": job["completed_at"],
    }


@router.delete("/monte-carlo/job/{job_id}")
async def delete_monte_carlo_job(job_id: str):
    """Delete a Monte Carlo simulation job."""
    if job_id not in monte_carlo_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    del monte_carlo_jobs[job_id]
    return {"message": f"Job {job_id} deleted successfully"}


@router.get("/monte-carlo/jobs")
async def list_monte_carlo_jobs():
    """List all Monte Carlo simulation jobs."""
    jobs = []
    for job_id, job in monte_carlo_jobs.items():
        job_info = {
            "job_id": job_id,
            "status": job["status"],
            "created_at": job["created_at"],
            "strategy": job["strategy"],
            "symbol": job["symbol"],
            "method": job["method"],
            "n_simulations": job["n_simulations"],
        }

        if "completed_at" in job:
            job_info["completed_at"] = job["completed_at"]
            job_info["execution_time_seconds"] = job["completed_at"] - job["started_at"]

        jobs.append(job_info)

    return {"jobs": jobs, "total": len(jobs)}


@router.get("/monte-carlo/stream/{job_id}")
async def stream_monte_carlo_status(job_id: str):
    """Stream Monte Carlo simulation status and progress in real-time using Server-Sent Events."""

    async def generate():
        last_heartbeat = 0
        heartbeat_interval = 15  # Send heartbeat every 15 seconds for better connection stability

        try:
            while True:
                current_time = time.time()

                if job_id not in monte_carlo_jobs:
                    yield f"event: error\ndata: {{\"error\": \"Job {job_id} not found\", \"timestamp\": {current_time}}}\n\n"
                    break

                job = monte_carlo_jobs[job_id]

                # Send heartbeat to keep connection alive
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield f"event: heartbeat\ndata: {{\"timestamp\": {current_time}, \"message\": \"Connection alive\"}}\n\n"
                    last_heartbeat = current_time
                    logger.debug(f"Sent heartbeat for job {job_id}")

                # Send current status
                status_data = {
                    "job_id": job_id,
                    "status": job["status"],
                    "created_at": job["created_at"],
                    "strategy": job["strategy"],
                    "symbol": job["symbol"],
                    "method": job["method"],
                    "n_simulations": job["n_simulations"],
                    "timestamp": current_time,
                }

                # Include progress information if available
                if "progress" in job:
                    status_data["progress"] = job["progress"]

                if "started_at" in job:
                    status_data["started_at"] = job["started_at"]
                    status_data["elapsed_seconds"] = current_time - job["started_at"]

                if "completed_at" in job:
                    status_data["completed_at"] = job["completed_at"]
                    status_data["execution_time_seconds"] = job["completed_at"] - job["started_at"]

                if job["status"] == "failed":
                    status_data["error"] = job.get("error", "Unknown error")

                if job["status"] == "completed":
                    # Send completion event with results
                    logger.info(f"Job {job_id} completed, sending results via streaming")
                    yield f"event: complete\ndata: {{\"status\": \"completed\", \"job_id\": \"{job_id}\", \"results\": {job.get('results', {})}, \"timestamp\": {current_time}}}\n\n"
                    break

                # Send status update
                yield f"event: status\ndata: {status_data}\n\n"

                # Wait before next update (shorter for running jobs)
                sleep_time = 1 if job["status"] == "running" else 2
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info(f"Streaming cancelled for job {job_id}")
            yield f"event: cancelled\ndata: {{\"message\": \"Connection cancelled\", \"timestamp\": {time.time()}}}\n\n"
        except Exception as e:
            logger.exception(f"Error in Monte Carlo streaming for job {job_id}: {e}")
            yield f"event: error\ndata: {{\"error\": \"Streaming error: {str(e)}\", \"timestamp\": {time.time()}}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if present
            "Keep-Alive": "timeout=300, max=1000",  # Keep connection alive for proxies
        }
    )


def _create_strategy_instance(
    strategy_name: str, strategy_class: type[BaseStrategy], params: dict[str, Any]
) -> BaseStrategy:
    """Create strategy instance from parameters.

    Reuses the same logic as backtest.py to ensure consistency.
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

