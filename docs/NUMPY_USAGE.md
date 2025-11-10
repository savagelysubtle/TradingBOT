# NumPy Usage in Trading Bot

This document lists all locations where NumPy is used in the codebase.

## Dependency

**Version**: `numpy>=2.3.4` (Python 3.14 compatible)
**Location**: `pyproject.toml`

## Usage Locations

### 1. **Monte Carlo Engine** (`src/trading_bot/backtesting/monte_carlo_engine.py`)

**Purpose**: Statistical simulations and random sampling

**Uses**:
- `np.random.seed()` - Set random seed for reproducibility
- `np.random.choice()` - Bootstrap resampling (random sampling with replacement)
- `np.random.normal()` - Generate synthetic returns with normal distribution
- `np.random.shuffle()` - Randomize trade order
- `np.mean()`, `np.median()`, `np.std()` - Statistical calculations
- `np.min()`, `np.max()` - Min/max calculations
- `np.percentile()` - Percentile calculations (VaR, CVaR)

**Key Functions**:
```python
# Random seed
np.random.seed(random_seed)

# Bootstrap resampling
sampled_indices = np.random.choice(data_length, size=data_length, replace=True)

# Statistical metrics
"mean_return": np.mean(returns)
"median_return": np.median(returns)
"std_return": np.std(returns)
"percentile_5": np.percentile(returns, 5)  # Value at Risk
```

### 2. **Monte Carlo Visualization** (`src/trading_bot/utils/monte_carlo_viz.py`)

**Purpose**: Statistical analysis and plotting

**Uses**:
- `np.percentile()` - Calculate percentiles for distribution plots
- `np.sort()` - Sort returns for cumulative distribution
- `np.arange()` - Generate array indices for plotting
- `np.random.choice()` - Sample indices for visualization

**Key Functions**:
```python
percentile_values = [np.percentile(returns_pct, p) for p in percentiles]
sorted_returns = np.sort(returns_pct)
cumulative_prob = np.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
```

### 3. **TA-Lib Strategies** (`src/trading_bot/strategies/ta_lib_strategy.py`)

**Purpose**: Convert pandas DataFrames to NumPy arrays for TA-Lib

**Uses**:
- `df["close"].values.astype(np.float64)` - Convert DataFrame columns to NumPy arrays
- Required by TA-Lib which expects NumPy arrays

**Key Functions**:
```python
# Convert to numpy arrays for TA-Lib
close = df["close"].values.astype(np.float64)
df["ma_short"] = talib.MA(close, timeperiod=self.short_period, matype=self.ma_type)
df["rsi"] = talib.RSI(close, timeperiod=self.rsi_period)
```

**Files**:
- `TALibMovingAverageCrossover` - Lines 64
- `TALibMACDStrategy` - Lines 156

### 4. **Advanced Indicators** (`src/trading_bot/strategies/advanced_indicators.py`)

**Purpose**: Custom indicator calculations using NumPy arrays

**Uses**:
- `np.ndarray` - Type hints for array parameters
- `np.zeros_like()` - Initialize arrays with zeros
- `df["close"].values.astype(np.float64)` - Convert to NumPy arrays

**Key Functions**:
```python
# Supertrend calculation
supertrend = np.zeros_like(close)
trend = np.zeros_like(close)

# Convert DataFrame to NumPy arrays
high = df["high"].values.astype(np.float64)
low = df["low"].values.astype(np.float64)
close = df["close"].values.astype(np.float64)
```

**Strategies**:
- `SupertrendStrategy` - Lines 38-41, 61-62, 93-95
- `BollingerBandsStrategy` - Line 186
- `IchimokuStrategy` - Lines 277-280, 332-334

### 5. **ML Strategy** (`src/trading_bot/strategies/ml_strategy.py`)

**Purpose**: Feature engineering and ML model integration

**Uses**:
- `np.log()` - Calculate logarithmic returns
- `df["close"].values.astype(np.float64)` - Convert to NumPy arrays for TA-Lib
- `np.mean()` - Calculate average cross-validation scores

**Key Functions**:
```python
# Log returns
df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

# Convert to NumPy for TA-Lib
close = df["close"].values.astype(np.float64)
high = df["high"].values.astype(np.float64)
low = df["low"].values.astype(np.float64)
volume = df["volume"].values.astype(np.float64)

# Average CV score
avg_score = np.mean(scores)
```

### 6. **VectorBT Engine** (`src/trading_bot/backtesting/vectorbt_engine.py`)

**Purpose**: Sharpe ratio calculation

**Uses**:
- `np.sqrt()` - Square root for annualized Sharpe ratio

**Key Functions**:
```python
# Annualized Sharpe ratio
sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
```

### 7. **Config Serialization** (`src/trading_bot/config.py`)

**Purpose**: JSON serialization helper

**Uses**:
- `np.integer`, `np.floating` - Type checking for NumPy scalars
- `np.ndarray` - Type checking for arrays
- `.item()` - Convert NumPy scalar to Python native type
- `.tolist()` - Convert NumPy array to list

**Key Functions**:
```python
def _make_json_serializable(self, obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()  # Convert numpy scalar to Python native type
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy array to list
```

## Summary by Category

### Statistical Operations
- **Monte Carlo Engine**: Mean, median, std, min, max, percentiles
- **Monte Carlo Viz**: Percentiles, sorting, array generation
- **VectorBT Engine**: Square root for Sharpe ratio

### Random Number Generation
- **Monte Carlo Engine**: `np.random.seed()`, `np.random.choice()`, `np.random.normal()`, `np.random.shuffle()`

### Array Operations
- **TA-Lib Strategies**: DataFrame to NumPy array conversion
- **Advanced Indicators**: Array initialization (`np.zeros_like()`)
- **ML Strategy**: Array conversion for TA-Lib

### Type Conversion
- **Config**: NumPy scalar/array to Python native types for JSON serialization

### Mathematical Functions
- **ML Strategy**: `np.log()` for logarithmic returns
- **VectorBT Engine**: `np.sqrt()` for Sharpe ratio

## Why NumPy?

1. **TA-Lib Integration**: TA-Lib requires NumPy arrays as input
2. **Performance**: NumPy operations are faster than pure Python for numerical computations
3. **Statistical Functions**: Built-in statistical functions (mean, std, percentiles)
4. **Random Number Generation**: High-quality random number generators
5. **Array Operations**: Efficient array manipulation and mathematical operations

## NumPy 2.3.4+ Compatibility

The project uses NumPy 2.3.4+ which is compatible with Python 3.14:
- Enhanced performance
- Better type hints
- Improved array operations
- Free-threading support (no GIL)

## Dependencies That Use NumPy

These libraries also depend on NumPy (indirect usage):
- **pandas** - Built on NumPy
- **scikit-learn** - Uses NumPy arrays
- **TA-Lib** - Requires NumPy arrays
- **vectorbt** - Uses NumPy for vectorized operations
- **matplotlib** - Uses NumPy for plotting
- **xgboost**, **lightgbm** - Use NumPy arrays

## Files Using NumPy Directly

1. `src/trading_bot/backtesting/monte_carlo_engine.py` - Heavy usage (30+ calls)
2. `src/trading_bot/utils/monte_carlo_viz.py` - Statistical visualization (10+ calls)
3. `src/trading_bot/strategies/ta_lib_strategy.py` - TA-Lib integration (2 calls)
4. `src/trading_bot/strategies/advanced_indicators.py` - Custom indicators (10+ calls)
5. `src/trading_bot/strategies/ml_strategy.py` - ML features (5+ calls)
6. `src/trading_bot/backtesting/vectorbt_engine.py` - Sharpe ratio (1 call)
7. `src/trading_bot/config.py` - JSON serialization (3 calls)

## Total Usage

- **Direct imports**: 7 files
- **Total numpy calls**: ~60+ instances
- **Primary use cases**: Statistical analysis, TA-Lib integration, Monte Carlo simulation
