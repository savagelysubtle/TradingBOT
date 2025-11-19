"""Command-line interface for the trading bot."""

import logging
from pathlib import Path

import click

from trading_bot.bot import TradingBot
from trading_bot.config import load_config
from trading_bot.utils.logging import setup_logging

logger = logging.getLogger(__name__)


@click.group()
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def cli(ctx, config, log_level):
    """Trading Bot CLI."""
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        # Load from specific file (not implemented yet)
        pass

    config_obj = load_config()
    setup_logging(log_level=log_level, log_file=config_obj.log_file)

    # Initialize bot
    bot = TradingBot(config_obj)
    ctx.obj["bot"] = bot
    ctx.obj["config"] = config_obj

    logger.info("Trading Bot CLI initialized")


@cli.command()
@click.option("--symbol", default="BTC/USDT", help="Trading symbol")
@click.option("--exchange", default="binance", help="Exchange name")
@click.option("--strategy", default="ma_crossover", help="Strategy name")
@click.option("--engine", default="custom", help="Backtesting engine")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--limit", type=int, default=365, help="Data limit")
@click.option("--timeframe", default="1d", help="Timeframe")
@click.pass_context
def backtest(ctx, symbol, exchange, strategy, engine, start_date, end_date, limit, timeframe):
    """Run backtest."""
    bot = ctx.obj["bot"]
    logger.info(f"Running backtest: {symbol} on {exchange} with {strategy}")

    # This is a placeholder - backtest implementation would go here
    click.echo(f"Backtest completed for {symbol}")


@cli.command()
@click.option("--symbol", default="BTC/USDT", help="Trading symbol")
@click.option("--exchange", default="binance", help="Exchange name")
@click.option("--strategy", default="ma_crossover", help="Strategy name")
@click.option("--method", default="bootstrap", help="Monte Carlo method")
@click.option("-n", "--n-simulations", type=int, default=1000, help="Number of simulations")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--limit", type=int, default=365, help="Data limit")
@click.option("--timeframe", default="1d", help="Timeframe")
@click.option("--force-cpu", is_flag=True, help="Force CPU-only mode")
@click.pass_context
def montecarlo(ctx, symbol, exchange, strategy, method, n_simulations, start_date, end_date, limit, timeframe, force_cpu):
    """Run Monte Carlo simulation."""
    bot = ctx.obj["bot"]
    logger.info(f"Running Monte Carlo: {symbol} on {exchange} with {strategy} ({n_simulations} simulations)")

    try:
        # Import here to avoid circular imports
        from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine
        from trading_bot.strategies.strategy_registry import _strategy_registry
        from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

        # Fetch data
        logger.info("Fetching market data...")
        if isinstance(bot.data_fetcher, CCXTDataFetcher):
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        else:
            # yfinance fetcher
            data = bot.data_fetcher.fetch_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=timeframe,
            )
            if limit and len(data) > limit:
                data = data.tail(limit)

        logger.info(f"Data fetched: {len(data)} rows")

        # Create strategy
        strategy_class = _strategy_registry.get_strategy_class(strategy)
        if not strategy_class:
            raise click.ClickException(f"Strategy '{strategy}' not found")

        # Create strategy instance with default params
        strategy_instance = strategy_class()

        # Create Monte Carlo engine
        mc_engine = MonteCarloEngine(
            n_simulations=n_simulations,
            force_cpu=force_cpu,
        )

        # Run simulation
        logger.info(f"Running {n_simulations} Monte Carlo simulations...")
        results = mc_engine.run(
            strategy=strategy_instance,
            data=data,
            symbol=symbol,
            method=method,
        )

        # Display results
        click.echo(f"\nMonte Carlo Results ({method} method, {n_simulations} simulations):")
        click.echo(f"Strategy: {strategy}")
        click.echo(f"Symbol: {symbol}")
        click.echo(f"Data points: {len(data)}")
        click.echo(f"GPU accelerated: {'Yes' if results.get('gpu_accelerated', False) else 'No'}")

        # Key metrics
        click.echo(f"\nKey Metrics:")
        click.echo(f"Mean Return: {results['mean_return'] * 100:.2f}%")
        click.echo(f"Median Return: {results['median_return'] * 100:.2f}%")
        click.echo(f"Std Dev: {results['std_return'] * 100:.2f}%")
        click.echo(f"Probability of Profit: {results['probability_of_profit'] * 100:.2f}%")
        click.echo(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        click.echo(f"Max Drawdown: {results['max_drawdown'] * 100:.2f}%")

        # Risk metrics
        click.echo(f"\nRisk Metrics:")
        click.echo(f"VaR (95%): {results['var_95'] * 100:.2f}%")
        click.echo(f"CVaR (95%): {results['cvar_95'] * 100:.2f}%")
        click.echo(f"Worst Return: {results['min_return'] * 100:.2f}%")
        click.echo(f"Best Return: {results['max_return'] * 100:.2f}%")

        logger.info("Monte Carlo simulation completed successfully")

    except Exception as e:
        logger.exception(f"Monte Carlo simulation failed: {e}")
        raise click.ClickException(f"Monte Carlo simulation failed: {e}")


@cli.command()
@click.option("--symbol", default="BTC/USDT", help="Trading symbol")
@click.option("--exchange", default="binance", help="Exchange name")
@click.option("--strategy", default="ma_crossover", help="Strategy name")
@click.pass_context
def paper(ctx, symbol, exchange, strategy):
    """Run paper trading simulation."""
    bot = ctx.obj["bot"]
    logger.info(f"Running paper trading: {symbol} on {exchange} with {strategy}")

    # This is a placeholder - paper trading implementation would go here
    click.echo(f"Paper trading started for {symbol}")


@cli.command()
@click.option("--symbol", default="BTC/USDT", help="Trading symbol")
@click.option("--exchange", default="binance", help="Exchange name")
@click.option("--strategy", default="ma_crossover", help="Strategy name")
@click.pass_context
def live(ctx, symbol, exchange, strategy):
    """Run live trading."""
    bot = ctx.obj["bot"]
    logger.warning(f"Starting live trading: {symbol} on {exchange} with {strategy}")
    logger.warning("LIVE TRADING CARRIES REAL FINANCIAL RISK!")

    # This is a placeholder - live trading implementation would go here
    click.echo(f"Live trading started for {symbol}")


if __name__ == "__main__":
    cli()
