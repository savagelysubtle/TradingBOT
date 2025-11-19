# Monte Carlo GPU Acceleration Helper Script
# Runs Monte Carlo simulations with Python 3.13.4 for GPU acceleration (CuPy)
# Usage: .\scripts\montecarlo-gpu.ps1 --symbol BTC/USDT --strategy talib_ma

param(
    [Parameter(Mandatory=$false)]
    [string]$Symbol,

    [Parameter(Mandatory=$false)]
    [string]$Strategy,

    [Parameter(Mandatory=$false)]
    [string]$Method = "bootstrap",

    [Parameter(Mandatory=$false)]
    [int]$NSimulations = 1000,

    [Parameter(Mandatory=$false)]
    [string]$Exchange = "binance",

    [Parameter(Mandatory=$false)]
    [int]$RandomSeed,

    [Parameter(Mandatory=$false)]
    [switch]$ForceCpu,

    [Parameter(Mandatory=$false)]
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Monte Carlo GPU Acceleration Helper
====================================

Runs Monte Carlo simulations with Python 3.13.4 for GPU acceleration (CuPy).
This provides 10-100x faster performance compared to CPU-only mode.

Usage:
    .\scripts\montecarlo-gpu.ps1 --symbol BTC/USDT --strategy talib_ma
    .\scripts\montecarlo-gpu.ps1 --symbol BTC/USDT --strategy talib_ma --method bootstrap -n 1000
    .\scripts\montecarlo-gpu.ps1 --symbol BTC/USDT --strategy talib_ma --method shuffle_trades -n 500

Options:
    --symbol <SYMBOL>        Trading pair (e.g., BTC/USDT)
    --strategy <STRATEGY>    Strategy name (e.g., talib_ma)
    --method <METHOD>        Simulation method: bootstrap, shuffle_trades, randomize_returns (default: bootstrap)
    -n, --n-simulations <N>  Number of simulations (default: 1000)
    --exchange <EXCHANGE>    Exchange name (default: binance)
    --seed <SEED>            Random seed for reproducibility
    --help                   Show this help message

Note: This script uses Python 3.13.4 specifically for GPU acceleration.
      For other bot operations (backtesting, live trading), use Python 3.14 for free-threading.
"@
    exit 0
}

# Build command arguments
$args = @()
if ($Symbol) { $args += "--symbol", $Symbol }
if ($Strategy) { $args += "--strategy", $Strategy }
if ($Method) { $args += "--method", $Method }
if ($NSimulations) { $args += "-n", $NSimulations.ToString() }
if ($Exchange) { $args += "--exchange", $Exchange }
if ($RandomSeed -ne $null) { $args += "--seed", $RandomSeed.ToString() }
if ($ForceCpu) { $args += "--force-cpu" }

# Run with Python 3.13.4
if ($ForceCpu) {
    Write-Host "Running Monte Carlo simulation with Python 3.13.4 (CPU-only mode)..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to cancel at any time" -ForegroundColor Cyan
} else {
    Write-Host "Running Monte Carlo simulation with Python 3.13.4 (GPU-accelerated)..." -ForegroundColor Green
    Write-Host "Note: If this crashes, try --force-cpu flag for CPU-only mode" -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to cancel at any time" -ForegroundColor Cyan
}
uv run --python 3.13.4 trading-bot montecarlo @args


