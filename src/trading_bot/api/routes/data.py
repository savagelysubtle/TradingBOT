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
    logger.info("=" * 60)
    logger.info("DATA FETCH ENDPOINT CALLED")
    logger.info("=" * 60)
    logger.info(f"Parameters:")
    logger.info(f"  - symbol: {symbol}")
    logger.info(f"  - timeframe: {timeframe}")
    logger.info(f"  - limit: {limit}")
    logger.info(f"  - start_date: {start_date}")
    logger.info(f"  - end_date: {end_date}")

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
        logger.info("Step 2: Checking data fetcher type...")
        logger.info(f"Data fetcher type: {type(bot.data_fetcher)}")
        logger.info(f"Is CCXT fetcher: {isinstance(bot.data_fetcher, CCXTDataFetcher)}")

        # Check if it's CCXT fetcher using isinstance for proper type narrowing
        if isinstance(bot.data_fetcher, CCXTDataFetcher):
            # CCXT fetcher - accepts timeframe and limit
            logger.info(f"Step 3: Using CCXT fetcher for {symbol}...")
            logger.debug(f"Calling fetch_ohlcv with: symbol={symbol}, timeframe={timeframe}, limit={limit}")
            fetch_start = time.time()
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            fetch_time = time.time() - fetch_start
            logger.info(f"Step 3: ✅ Data fetched in {fetch_time:.3f}s")
        else:
            # yfinance fetcher - uses interval instead of timeframe, no limit parameter
            logger.info(f"Step 3: Using yfinance fetcher for {symbol}...")
            logger.debug(f"Calling fetch_ohlcv with: symbol={symbol}, interval={timeframe}")
            fetch_start = time.time()
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=timeframe,
            )
            fetch_time = time.time() - fetch_start
            logger.info(f"Step 3: ✅ Data fetched in {fetch_time:.3f}s")
            # yfinance doesn't support limit parameter, so we slice the result if needed
            if limit and len(data) > limit:
                logger.debug(f"Limiting yfinance data from {len(data)} to {limit} rows")
                data = data.tail(limit)

        logger.info("Step 4: Validating data...")
        if data is None:
            logger.error("Data is None")
            raise HTTPException(
                status_code=404,
                detail=f"No data available for symbol {symbol}",
            )
        if data.empty:
            logger.warning(f"Data is empty for symbol {symbol}")
            raise HTTPException(
                status_code=404,
                detail=f"No data available for symbol {symbol}",
            )
        logger.info(f"Step 4: ✅ Data validated: {len(data)} rows")

        logger.info("Step 5: Analyzing data...")
        logger.info(f"  - Rows: {len(data)}")
        logger.info(f"  - Columns: {list(data.columns)}")
        logger.info(f"  - Date range: {data.index.min()} to {data.index.max()}")
        logger.info(f"  - Data types: {data.dtypes.to_dict()}")

        # Convert DataFrame to JSON-serializable format
        logger.info("Step 6: Serializing data to JSON...")
        serialization_start = time.time()
        data_dict = data.reset_index().to_dict(orient="records")
        serialization_time = time.time() - serialization_start
        logger.info(f"Step 6: ✅ Serialization completed in {serialization_time:.3f}s")
        logger.info(f"  - Serialized records: {len(data_dict)}")

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "rows": len(data),
            "data": data_dict,
        }
        logger.info("=" * 60)
        logger.info("DATA FETCH SUCCESS")
        logger.info(f"Returning {len(data)} rows for {symbol}")
        logger.info("=" * 60)
        return result
    except HTTPException as e:
        logger.warning(f"HTTPException raised: {e.status_code} - {e.detail}")
        raise
    except ValueError as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Invalid request parameters")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        raise HTTPException(status_code=400, detail=f"Invalid request: {e!s}") from e
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Failed to fetch data")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data: {e!s}",
        ) from e


@router.get("/exchanges")
async def list_exchanges():
    """List available exchanges."""
    logger.info("=" * 60)
    logger.info("LIST EXCHANGES ENDPOINT CALLED")
    logger.info("=" * 60)

    try:
        logger.info("Step 1: Building exchanges list...")
        exchanges = [
            {"id": "binance", "name": "Binance"},
            {"id": "coinbase", "name": "Coinbase Pro"},
            {"id": "kraken", "name": "Kraken"},
        ]
        logger.info(f"Step 1: ✅ Found {len(exchanges)} exchanges")

        result = {"exchanges": exchanges}
        logger.info("=" * 60)
        logger.info("LIST EXCHANGES SUCCESS")
        logger.info(f"Returning {len(exchanges)} exchanges")
        logger.info("=" * 60)
        return result
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Failed to list exchanges")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list exchanges: {e!s}",
        ) from e
