"""Data fetching endpoints."""

import logging
import time

from fastapi import APIRouter, HTTPException

from trading_bot.api.bot_instance import get_bot
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/data/fetch")
async def fetch_data(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Fetch market data for a symbol."""
    logger.info(
        f"Fetching data: symbol={symbol}, timeframe={timeframe}, limit={limit}, "
        f"start_date={start_date}, end_date={end_date}"
    )
    try:
        bot = get_bot()
    except RuntimeError as e:
        logger.error(f"Bot instance not initialized: {e}")
        raise HTTPException(
            status_code=503,
            detail="Bot instance not initialized. Please wait for server to fully start.",
        ) from e

    try:
        # Check if it's CCXT fetcher using isinstance for proper type narrowing
        if isinstance(bot.data_fetcher, CCXTDataFetcher):
            # CCXT fetcher - accepts timeframe and limit
            logger.debug(f"Using CCXT fetcher for {symbol}")
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        else:
            # yfinance fetcher - uses interval instead of timeframe, no limit parameter
            logger.debug(f"Using yfinance fetcher for {symbol}")
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=timeframe,
            )
            # yfinance doesn't support limit parameter, so we slice the result if needed
            if limit and len(data) > limit:
                logger.debug(f"Limiting yfinance data from {len(data)} to {limit} rows")
                data = data.tail(limit)

        if data is None or data.empty:
            logger.warning(f"No data available for symbol {symbol}")
            raise HTTPException(
                status_code=404,
                detail=f"No data available for symbol {symbol}",
            )

        logger.info(f"Successfully fetched {len(data)} rows for {symbol}")
        logger.debug(f"Data date range: {data.index.min()} to {data.index.max()}")
        logger.debug(f"Data columns: {list(data.columns)}")

        # Convert DataFrame to JSON-serializable format
        logger.debug("Converting DataFrame to JSON format")
        serialization_start = time.time()
        data_dict = data.reset_index().to_dict(orient="records")
        serialization_time = time.time() - serialization_start
        logger.debug(f"Data serialization completed in {serialization_time:.3f}s")

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "rows": len(data),
            "data": data_dict,
        }
        logger.info(f"Data fetch completed successfully: {len(data)} rows returned")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid request parameters: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {e!s}") from e
    except Exception as e:
        logger.exception(f"Failed to fetch data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data: {e!s}",
        ) from e


@router.get("/exchanges")
async def list_exchanges():
    """List available exchanges."""
    try:
        logger.debug("Listing available exchanges")
        return {
            "exchanges": [
                {"id": "binance", "name": "Binance"},
                {"id": "coinbase", "name": "Coinbase Pro"},
                {"id": "kraken", "name": "Kraken"},
            ]
        }
    except Exception as e:
        logger.exception(f"Failed to list exchanges: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list exchanges: {e!s}",
        ) from e
