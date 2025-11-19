#!/bin/bash
# Monte Carlo GPU Acceleration Helper Script
# Runs Monte Carlo simulations with Python 3.13.4 for GPU acceleration (CuPy)
# Usage: ./scripts/montecarlo-gpu.sh --symbol BTC/USDT --strategy talib_ma

set -e

# Default values
SYMBOL=""
STRATEGY=""
METHOD="bootstrap"
N_SIMULATIONS=1000
EXCHANGE="binance"
RANDOM_SEED=""
FORCE_CPU=false
HELP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --symbol)
            SYMBOL="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --method)
            METHOD="$2"
            shift 2
            ;;
        -n|--n-simulations)
            N_SIMULATIONS="$2"
            shift 2
            ;;
        --exchange)
            EXCHANGE="$2"
            shift 2
            ;;
        --seed)
            RANDOM_SEED="$2"
            shift 2
            ;;
        --force-cpu)
            FORCE_CPU=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$HELP" = true ]; then
    cat << EOF
Monte Carlo GPU Acceleration Helper
====================================

Runs Monte Carlo simulations with Python 3.13.4 for GPU acceleration (CuPy).
This provides 10-100x faster performance compared to CPU-only mode.

Usage:
    ./scripts/montecarlo-gpu.sh --symbol BTC/USDT --strategy talib_ma
    ./scripts/montecarlo-gpu.sh --symbol BTC/USDT --strategy talib_ma --method bootstrap -n 1000
    ./scripts/montecarlo-gpu.sh --symbol BTC/USDT --strategy talib_ma --method shuffle_trades -n 500

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
EOF
    exit 0
fi

# Build command arguments
ARGS=()
[ -n "$SYMBOL" ] && ARGS+=("--symbol" "$SYMBOL")
[ -n "$STRATEGY" ] && ARGS+=("--strategy" "$STRATEGY")
[ -n "$METHOD" ] && ARGS+=("--method" "$METHOD")
[ -n "$N_SIMULATIONS" ] && ARGS+=("-n" "$N_SIMULATIONS")
[ -n "$EXCHANGE" ] && ARGS+=("--exchange" "$EXCHANGE")
[ -n "$RANDOM_SEED" ] && ARGS+=("--seed" "$RANDOM_SEED")
[ "$FORCE_CPU" = true ] && ARGS+=("--force-cpu")

# Run with Python 3.13.4
if [ "$FORCE_CPU" = true ]; then
    echo "Running Monte Carlo simulation with Python 3.13.4 (CPU-only mode)..."
    echo "Press Ctrl+C to cancel at any time"
else
    echo "Running Monte Carlo simulation with Python 3.13.4 (GPU-accelerated)..."
    echo "Note: If this crashes, try --force-cpu flag for CPU-only mode"
    echo "Press Ctrl+C to cancel at any time"
fi
uv run --python 3.13.4 trading-bot montecarlo "${ARGS[@]}"


