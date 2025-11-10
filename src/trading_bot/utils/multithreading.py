"""Multi-threading utilities leveraging Python 3.14 free-threading."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def parallel_fetch_data(
    fetcher_func: Callable[[str], T],
    symbols: list[str],
    max_workers: int | None = None,
) -> dict[str, T]:
    """Fetch data for multiple symbols in parallel using Python 3.14 free-threading.

    Args:
        fetcher_func: Function that takes a symbol and returns data
        symbols: List of symbols to fetch
        max_workers: Maximum number of worker threads (None = auto)

    Returns:
        Dictionary mapping symbols to their fetched data
    """
    results = {}
    errors = {}

    def fetch_with_error_handling(symbol: str) -> tuple[str, T | None, Exception | None]:
        """Fetch data with error handling."""
        try:
            data = fetcher_func(symbol)
            return (symbol, data, None)
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return (symbol, None, e)

    # Use ThreadPoolExecutor for parallel execution
    # Python 3.14's free-threading allows true parallelism
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(fetch_with_error_handling, symbol): symbol
            for symbol in symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_symbol):
            symbol, data, error = future.result()
            if error:
                errors[symbol] = error
            else:
                results[symbol] = data

    if errors:
        logger.warning(f"Failed to fetch {len(errors)} symbols: {list(errors.keys())}")

    return results


def parallel_backtest(
    backtest_func: Callable[[str], dict],
    symbols: list[str],
    max_workers: int | None = None,
) -> dict[str, dict]:
    """Run backtests for multiple symbols in parallel.

    Args:
        backtest_func: Function that takes a symbol and returns backtest results
        symbols: List of symbols to backtest
        max_workers: Maximum number of worker threads

    Returns:
        Dictionary mapping symbols to their backtest results
    """
    results = {}

    def backtest_with_error_handling(symbol: str) -> tuple[str, dict | None, Exception | None]:
        """Run backtest with error handling."""
        try:
            result = backtest_func(symbol)
            return (symbol, result, None)
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {e}")
            return (symbol, None, e)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(backtest_with_error_handling, symbol): symbol
            for symbol in symbols
        }

        for future in as_completed(future_to_symbol):
            symbol, result, error = future.result()
            if error:
                logger.error(f"Backtest failed for {symbol}: {error}")
            else:
                results[symbol] = result

    return results


class ThreadSafeCache:
    """Thread-safe cache using Python 3.14 free-threading."""

    def __init__(self):
        """Initialize thread-safe cache."""
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        """Get value from cache."""
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value) -> None:
        """Set value in cache."""
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._cache.clear()

