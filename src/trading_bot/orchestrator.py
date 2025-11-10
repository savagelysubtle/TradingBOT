"""Multi-strategy orchestrator for parallel strategy execution."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

import pandas as pd

from trading_bot.backtesting.engine import BacktestEngine

if TYPE_CHECKING:
    from trading_bot.backtesting.vectorbt_engine import VectorBTEngine

try:
    from trading_bot.backtesting.vectorbt_engine import VectorBTEngine as _VectorBTEngine
    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    _VectorBTEngine = None

from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class MultiStrategyOrchestrator:
    """Orchestrator for running multiple strategies in parallel."""

    def __init__(
        self,
        strategies: list[BaseStrategy],
        initial_capital: float = 10000.0,
        use_vectorbt: bool = True,
    ):
        """Initialize multi-strategy orchestrator.

        Args:
            strategies: List of trading strategies to run
            initial_capital: Initial capital per strategy
            use_vectorbt: Use VectorBT for faster backtesting
        """
        self.strategies = strategies
        self.initial_capital = initial_capital
        self.capital_per_strategy = initial_capital / len(strategies) if strategies else initial_capital
        self.use_vectorbt = use_vectorbt

        if use_vectorbt and VECTORBT_AVAILABLE and _VectorBTEngine is not None:
            try:
                self.engine = _VectorBTEngine(initial_capital=self.capital_per_strategy)
            except ImportError:
                logger.warning(
                    "VectorBT not available, falling back to custom engine. "
                    "Install with: uv add --optional vectorbt"
                )
                self.engine = BacktestEngine(initial_capital=self.capital_per_strategy)
                self.use_vectorbt = False
        else:
            self.engine = BacktestEngine(initial_capital=self.capital_per_strategy)
            if use_vectorbt and not VECTORBT_AVAILABLE:
                logger.warning(
                    "VectorBT not available, using custom engine. "
                    "Install with: uv add --optional vectorbt"
                )
                self.use_vectorbt = False

    async def run_strategy_async(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
    ) -> dict:
        """Run single strategy asynchronously.

        Args:
            strategy: Trading strategy
            data: Market data
            symbol: Trading symbol

        Returns:
            Backtest results dictionary
        """
        try:
            # Run backtest (this is CPU-bound, but we can still use async for I/O)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.engine.run,
                strategy,
                data,
                symbol,
            )
            return {
                "strategy": strategy.name,
                "symbol": symbol,
                "results": results,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Error running strategy {strategy.name} on {symbol}: {e}")
            return {
                "strategy": strategy.name,
                "symbol": symbol,
                "error": str(e),
                "success": False,
            }

    async def backtest_all_async(
        self,
        symbols: list[str],
        data_fetcher: CCXTDataFetcher,
        timeframe: str = "1d",
        limit: int = 1000,
    ) -> list[dict]:
        """Backtest all strategies across all symbols asynchronously.

        Args:
            symbols: List of trading symbols
            data_fetcher: Data fetcher instance
            timeframe: Data timeframe
            limit: Maximum candles to fetch

        Returns:
            List of backtest results
        """
        tasks = []

        for symbol in symbols:
            try:
                # Fetch data
                data = data_fetcher.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    limit=limit,
                )

                # Create tasks for each strategy
                for strategy in self.strategies:
                    task = self.run_strategy_async(strategy, data, symbol)
                    tasks.append(task)

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
            else:
                valid_results.append(result)

        return valid_results

    def backtest_all_parallel(
        self,
        symbols: list[str],
        data_fetcher: CCXTDataFetcher,
        timeframe: str = "1d",
        limit: int = 1000,
        max_workers: int | None = None,
    ) -> list[dict]:
        """Backtest all strategies using Python 3.14 free-threading.

        Args:
            symbols: List of trading symbols
            data_fetcher: Data fetcher instance
            timeframe: Data timeframe
            limit: Maximum candles to fetch
            max_workers: Maximum worker threads

        Returns:
            List of backtest results
        """
        results: list[dict] = []

        def backtest_strategy_symbol(symbol_strategy_pair: tuple[str, BaseStrategy]) -> dict | None:
            """Backtest a single strategy-symbol pair."""
            symbol, strategy = symbol_strategy_pair
            try:
                # Fetch data
                data = data_fetcher.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    limit=limit,
                )

                # Run backtest
                result = self.engine.run(strategy, data, symbol=symbol)

                return {
                    "strategy": strategy.name,
                    "symbol": symbol,
                    "results": result,
                    "success": True,
                }
            except Exception as e:
                logger.error(f"Error backtesting {strategy.name} on {symbol}: {e}")
                return {
                    "strategy": strategy.name,
                    "symbol": symbol,
                    "error": str(e),
                    "success": False,
                }

        # Create all strategy-symbol pairs
        pairs = [(symbol, strategy) for symbol in symbols for strategy in self.strategies]

        # Run in parallel using free-threading with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pair = {
                executor.submit(backtest_strategy_symbol, pair): pair
                for pair in pairs
            }

            for future in as_completed(future_to_pair):
                result = future.result()
                if result is not None:
                    results.append(result)

        return results

    def aggregate_results(self, results: list[dict]) -> pd.DataFrame:
        """Aggregate and rank strategies by performance.

        Args:
            results: List of backtest result dictionaries

        Returns:
            DataFrame with aggregated results, sorted by composite score
        """
        rows = []

        for result in results:
            if not result.get("success", False):
                continue

            res = result.get("results", {})
            if not res:
                continue

            sharpe = res.get("sharpe_ratio", 0.0)
            total_return = res.get("total_return", 0.0)
            max_dd = abs(res.get("max_drawdown", 0.0))

            # Composite score: (Sharpe * Return) / (Max_Drawdown + 1)
            # Higher is better
            score = (sharpe * total_return) / (max_dd + 1) if max_dd > 0 else sharpe * total_return

            rows.append(
                {
                    "strategy": result["strategy"],
                    "symbol": result["symbol"],
                    "total_return": total_return,
                    "total_return_pct": res.get("total_return_pct", 0.0),
                    "sharpe_ratio": sharpe,
                    "max_drawdown": max_dd,
                    "max_drawdown_pct": res.get("max_drawdown_pct", 0.0),
                    "win_rate": res.get("win_rate", 0.0),
                    "total_trades": res.get("total_trades", 0),
                    "score": score,
                },
            )

        df = pd.DataFrame(rows)

        if len(df) > 0:
            df = df.sort_values("score", ascending=False)

        return df

    def portfolio_allocation(
        self,
        strategy_results: pd.DataFrame,
        top_n: int = 5,
    ) -> dict:
        """Allocate capital based on strategy performance.

        Args:
            strategy_results: DataFrame with strategy results (from aggregate_results)
            top_n: Number of top strategies to allocate to

        Returns:
            Dictionary with allocation weights and capital per strategy
        """
        if len(strategy_results) == 0:
            return {}

        # Select top N strategies
        top_strategies = strategy_results.head(top_n)

        # Calculate weights based on score
        total_score = top_strategies["score"].sum()
        if total_score == 0:
            # Equal weight if no scores
            weights = pd.Series([1.0 / len(top_strategies)] * len(top_strategies))
        else:
            weights = top_strategies["score"] / total_score

        allocation = {}
        for idx, row in top_strategies.iterrows():
            weight = weights.loc[idx]
            allocation[f"{row['strategy']}_{row['symbol']}"] = {
                "strategy": row["strategy"],
                "symbol": row["symbol"],
                "weight": float(weight),
                "capital": float(self.initial_capital * weight),
                "expected_return": float(row["total_return"]),
                "sharpe_ratio": float(row["sharpe_ratio"]),
            }

        return allocation

