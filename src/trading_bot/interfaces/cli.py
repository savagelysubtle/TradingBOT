"""Command-line interface for the trading bot."""

import click
from rich.console import Console
from rich.table import Table

from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine
from trading_bot.bot import TradingBot
from trading_bot.broker.ccxt_broker import CCXTBroker
from trading_bot.broker.paper import PaperBroker
from trading_bot.config import load_config
from trading_bot.strategies.moving_average import MovingAverageCrossover

# Try to import TA-Lib strategies (optional)
try:
    from trading_bot.strategies.ta_lib_strategy import (
        TALibMACDStrategy,
        TALibMovingAverageCrossover,
    )
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

console = Console()


@click.group()
def cli():
    """Trading Bot CLI - Algorithmic trading made easy."""
    pass


@cli.command()
@click.option("--symbol", "-s", required=True, help="Trading symbol (e.g., BTC/USDT, AAPL)")
@click.option("--exchange", "-e", default="binance", help="Exchange ID (for crypto: binance, coinbase, etc.)")
@click.option("--strategy", "-st", default="talib_ma", help="Strategy name (ma_crossover, talib_ma, talib_macd)")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--period", default="1y", help="Data period for stocks (1d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)")
@click.option("--timeframe", "-tf", default="1d", help="Timeframe for crypto (1m, 5m, 15m, 1h, 4h, 1d, 1w)")
@click.option("--limit", default=1000, type=int, help="Max candles to fetch (for crypto)")
@click.option("--short-window", default=50, type=int, help="Short MA window")
@click.option("--long-window", default=200, type=int, help="Long MA window")
@click.option("--engine", default="backtrader", help="Backtest engine (backtrader, custom)")
def backtest(symbol, exchange, strategy, start_date, end_date, period, timeframe, limit, short_window, long_window, engine):
    """Run a backtest on a trading strategy with live data."""
    console.print(f"[bold green]Running backtest for {symbol}[/bold green]")

    # Initialize bot
    config = load_config()
    if "/" in symbol:  # Crypto symbol
        config.data_provider = "ccxt"
        config.exchange_id = exchange
    bot = TradingBot(config)

    # Create strategy
    if strategy == "ma_crossover":
        strategy_obj = MovingAverageCrossover(
            short_window=short_window,
            long_window=long_window,
        )
    elif strategy == "talib_ma":
        if not TALIB_AVAILABLE:
            console.print("[bold red]TA-Lib is not installed. Install it with:[/bold red]")
            console.print("[yellow]  conda install -c conda-forge ta-lib[/yellow]")
            console.print("[yellow]  or see INSTALLATION.md for manual installation[/yellow]")
            return
        strategy_obj = TALibMovingAverageCrossover(
            short_period=short_window,
            long_period=long_window,
        )
    elif strategy == "talib_macd":
        if not TALIB_AVAILABLE:
            console.print("[bold red]TA-Lib is not installed. Install it with:[/bold red]")
            console.print("[yellow]  conda install -c conda-forge ta-lib[/yellow]")
            console.print("[yellow]  or see INSTALLATION.md for manual installation[/yellow]")
            return
        strategy_obj = TALibMACDStrategy()
    else:
        available = "ma_crossover"
        if TALIB_AVAILABLE:
            available += ", talib_ma, talib_macd"
        console.print(f"[bold red]Unknown strategy: {strategy}[/bold red]")
        console.print(f"[yellow]Available strategies: {available}[/yellow]")
        return

    # Run backtest
    try:
        results = bot.backtest(
            strategy=strategy_obj,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            period=period,
            timeframe=timeframe,
            limit=limit,
            use_backtrader=(engine == "backtrader"),
        )

        # Display results
        table = Table(title="Backtest Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Strategy", results["strategy"])
        table.add_row("Symbol", results["symbol"])
        table.add_row("Initial Capital", f"${results['initial_capital']:,.2f}")
        table.add_row("Final Value", f"${results['final_value']:,.2f}")
        table.add_row("Total Return", f"{results['total_return_pct']:.2f}%")
        table.add_row("Buy & Hold Return", f"{results['buy_hold_return_pct']:.2f}%")
        table.add_row("Total Trades", str(results["total_trades"]))
        table.add_row("Win Rate", f"{results['win_rate_pct']:.2f}%")
        if "profit_factor" in results:
            table.add_row("Profit Factor", f"{results['profit_factor']:.2f}")
        if "sharpe_ratio" in results:
            table.add_row("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
        table.add_row("Max Drawdown", f"{results['max_drawdown_pct']:.2f}%")

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise


@cli.command()
@click.option("--symbol", "-s", required=True, help="Stock symbol (e.g., AAPL)")
@click.option("--strategy", "-st", default="ma_crossover", help="Strategy name")
@click.option("--short-window", default=50, type=int, help="Short MA window")
@click.option("--long-window", default=200, type=int, help="Long MA window")
def paper(symbol, strategy, short_window, long_window):
    """Run paper trading (simulated trading)."""
    console.print(f"[bold green]Starting paper trading for {symbol}[/bold green]")

    # Initialize bot
    config = load_config()
    bot = TradingBot(config)

    # Create broker
    broker = PaperBroker(initial_capital=config.initial_capital)
    bot.set_broker(broker)

    # Create strategy
    if strategy == "ma_crossover":
        strategy_obj = MovingAverageCrossover(
            short_window=short_window,
            long_window=long_window,
        )
    else:
        console.print(f"[bold red]Unknown strategy: {strategy}[/bold red]")
        return

    # Run live trading
    try:
        bot.run_live(strategy=strategy_obj, symbol=symbol)

        # Display account status
        account = broker.get_account()
        positions = broker.get_positions()

        table = Table(title="Account Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Cash", f"${account['cash']:,.2f}")
        table.add_row("Equity", f"${account['equity']:,.2f}")
        table.add_row("Positions", str(len(positions)))

        console.print(table)

        if positions:
            pos_table = Table(title="Positions")
            pos_table.add_column("Symbol", style="cyan")
            pos_table.add_column("Quantity", style="magenta")
            pos_table.add_column("Market Value", style="green")

            for pos in positions:
                pos_table.add_row(
                    pos["symbol"],
                    f"{pos['quantity']:.2f}",
                    f"${pos['market_value']:,.2f}",
                )

            console.print(pos_table)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise


@cli.command()
def list_strategies():
    """List available trading strategies."""
    table = Table(title="Available Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="magenta")

    table.add_row(
        "ma_crossover",
        "Moving Average Crossover - Buys when short MA crosses above long MA",
    )
    table.add_row(
        "talib_ma",
        "TA-Lib Moving Average Crossover with RSI filter",
    )
    table.add_row(
        "talib_macd",
        "TA-Lib MACD crossover strategy",
    )

    console.print(table)


@cli.command()
@click.option("--symbol", "-s", required=True, help="Trading symbol (e.g., BTC/USDT, AAPL)")
@click.option("--exchange", "-e", default="binance", help="Exchange ID (for crypto)")
@click.option("--strategy", "-st", default="talib_ma", help="Strategy name (ma_crossover, talib_ma, talib_macd)")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--period", default="1y", help="Data period for stocks")
@click.option("--timeframe", "-tf", default="1d", help="Timeframe for crypto")
@click.option("--limit", default=1000, type=int, help="Max candles to fetch (for crypto)")
@click.option("--short-window", default=50, type=int, help="Short MA window")
@click.option("--long-window", default=200, type=int, help="Long MA window")
@click.option("--n-simulations", "-n", default=1000, type=int, help="Number of Monte Carlo simulations")
@click.option("--method", "-m", default="bootstrap", help="Simulation method (bootstrap, shuffle_trades, randomize_returns)")
@click.option("--seed", type=int, help="Random seed for reproducibility")
def montecarlo(symbol, exchange, strategy, start_date, end_date, period, timeframe, limit,
               short_window, long_window, n_simulations, method, seed):
    """Run Monte Carlo simulation on a trading strategy."""
    console.print(f"[bold green]Running Monte Carlo simulation for {symbol}[/bold green]")
    console.print(f"[cyan]Method: {method}, Simulations: {n_simulations}[/cyan]")

    # Initialize bot
    config = load_config()
    if "/" in symbol:  # Crypto symbol
        config.data_provider = "ccxt"
        config.exchange_id = exchange
    bot = TradingBot(config)

    # Create strategy
    if strategy == "ma_crossover":
        strategy_obj = MovingAverageCrossover(
            short_window=short_window,
            long_window=long_window,
        )
    elif strategy == "talib_ma":
        if not TALIB_AVAILABLE:
            console.print("[bold red]TA-Lib is not installed. Install it with:[/bold red]")
            console.print("[yellow]  conda install -c conda-forge ta-lib[/yellow]")
            console.print("[yellow]  or see INSTALLATION.md for manual installation[/yellow]")
            return
        strategy_obj = TALibMovingAverageCrossover(
            short_period=short_window,
            long_period=long_window,
        )
    elif strategy == "talib_macd":
        if not TALIB_AVAILABLE:
            console.print("[bold red]TA-Lib is not installed. Install it with:[/bold red]")
            console.print("[yellow]  conda install -c conda-forge ta-lib[/yellow]")
            console.print("[yellow]  or see INSTALLATION.md for manual installation[/yellow]")
            return
        strategy_obj = TALibMACDStrategy()
    else:
        available = "ma_crossover"
        if TALIB_AVAILABLE:
            available += ", talib_ma, talib_macd"
        console.print(f"[bold red]Unknown strategy: {strategy}[/bold red]")
        console.print(f"[yellow]Available strategies: {available}[/yellow]")
        return

    # Fetch data
    try:
        if isinstance(bot.data_fetcher, type(bot.data_fetcher)) and hasattr(bot.data_fetcher, 'exchange'):
            # CCXT fetcher
            data = bot.data_fetcher.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        else:
            # yfinance fetcher
            data = bot.data_fetcher.fetch_ohlcv(
                symbol,
                start_date=start_date,
                end_date=end_date,
                period=period,
            )

        # Create Monte Carlo engine
        mc_engine = MonteCarloEngine(
            initial_capital=config.initial_capital,
            commission=0.001,
            slippage=0.0005,
            n_simulations=n_simulations,
            random_seed=seed,
        )

        # Run Monte Carlo simulation
        console.print(f"[yellow]Running {n_simulations} simulations... This may take a while.[/yellow]")
        results = mc_engine.run(strategy_obj, data, symbol, method=method)

        # Save results
        result_dir = mc_engine.save_results(results)
        console.print(f"[green]Results saved to: {result_dir}[/green]")

        # Display results
        table = Table(title="Monte Carlo Simulation Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Strategy", results["strategy"])
        table.add_row("Symbol", results["symbol"])
        table.add_row("Method", results["method"])
        table.add_row("Simulations", str(results["n_simulations"]))
        table.add_row("", "")  # Spacer

        table.add_row("[bold]Return Statistics[/bold]", "")
        table.add_row("Mean Return", f"{results['mean_return'] * 100:.2f}%")
        table.add_row("Median Return", f"{results['median_return'] * 100:.2f}%")
        table.add_row("Std Dev", f"{results['std_return'] * 100:.2f}%")
        table.add_row("5th Percentile", f"{results['percentile_5'] * 100:.2f}%")
        table.add_row("95th Percentile", f"{results['percentile_95'] * 100:.2f}%")
        table.add_row("Min Return", f"{results['min_return'] * 100:.2f}%")
        table.add_row("Max Return", f"{results['max_return'] * 100:.2f}%")
        table.add_row("", "")  # Spacer

        table.add_row("[bold]Risk Metrics[/bold]", "")
        table.add_row("Probability of Profit", f"{results['probability_of_profit'] * 100:.2f}%")
        table.add_row("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
        table.add_row("Value at Risk (95%)", f"{results['var_95'] * 100:.2f}%")
        table.add_row("Conditional VaR (95%)", f"{results['cvar_95'] * 100:.2f}%")
        table.add_row("Mean Max Drawdown", f"{results['mean_max_drawdown'] * 100:.2f}%")
        table.add_row("Worst Drawdown", f"{results['worst_drawdown'] * 100:.2f}%")
        table.add_row("", "")  # Spacer

        table.add_row("[bold]Final Value Statistics[/bold]", "")
        table.add_row("Mean Final Value", f"${results['mean_final_value']:,.2f}")
        table.add_row("Median Final Value", f"${results['median_final_value']:,.2f}")
        table.add_row("Min Final Value", f"${results['min_final_value']:,.2f}")
        table.add_row("Max Final Value", f"${results['max_final_value']:,.2f}")

        console.print(table)

        # Display interpretation
        console.print("\n[bold cyan]Interpretation:[/bold cyan]")
        if results['probability_of_profit'] >= 0.7:
            console.print("[green]✓ High probability of profit (≥70%)[/green]")
        elif results['probability_of_profit'] >= 0.5:
            console.print("[yellow]⚠ Moderate probability of profit (50-70%)[/yellow]")
        else:
            console.print("[red]✗ Low probability of profit (<50%)[/red]")

        if results['sharpe_ratio'] >= 1.0:
            console.print("[green]✓ Good risk-adjusted returns (Sharpe ≥ 1.0)[/green]")
        elif results['sharpe_ratio'] >= 0.5:
            console.print("[yellow]⚠ Moderate risk-adjusted returns (Sharpe 0.5-1.0)[/yellow]")
        else:
            console.print("[red]✗ Poor risk-adjusted returns (Sharpe < 0.5)[/red]")

        if abs(results['worst_drawdown']) <= 0.2:
            console.print("[green]✓ Acceptable worst-case drawdown (≤20%)[/green]")
        elif abs(results['worst_drawdown']) <= 0.3:
            console.print("[yellow]⚠ Moderate worst-case drawdown (20-30%)[/yellow]")
        else:
            console.print("[red]✗ High worst-case drawdown (>30%)[/red]")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise


@cli.command()
def tui():
    """Launch the Text User Interface (TUI)."""
    from trading_bot.tui import TradingBotTUI

    app = TradingBotTUI()
    app.run()


if __name__ == "__main__":
    cli()

