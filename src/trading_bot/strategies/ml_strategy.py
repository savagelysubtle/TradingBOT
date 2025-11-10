"""Machine Learning-based trading strategies."""

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]
from sklearn.model_selection import TimeSeriesSplit  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

try:
    import talib  # type: ignore[import-untyped]

    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None  # type: ignore[assignment]


class MLRandomForestStrategy(BaseStrategy):
    """Machine Learning-based strategy using Random Forest classifier."""

    def __init__(
        self,
        lookback: int = 50,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_split: int = 5,
        confidence_threshold: float = 0.65,
    ):
        """Initialize ML Random Forest strategy.

        Args:
            lookback: Number of periods to look back for features
            n_estimators: Number of trees in Random Forest
            max_depth: Maximum depth of trees
            min_samples_split: Minimum samples required to split
            confidence_threshold: Minimum probability to generate signal
        """
        super().__init__(
            name="MLRandomForestStrategy",
            lookback=lookback,
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            confidence_threshold=confidence_threshold,
        )
        self.lookback = lookback
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
            n_jobs=-1,  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.confidence_threshold = confidence_threshold
        self.is_trained = False

    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Engineer features for ML model.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with features added
        """
        df = data.copy()

        # Price features
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))  # type: ignore[attr-defined]
        df["price_change"] = df["close"] - df["close"].shift(1)
        df["price_change_pct"] = df["close"].pct_change()

        # Technical indicators (if TA-Lib available)
        if TALIB_AVAILABLE and talib is not None:
            close = df["close"].values.astype(np.float64)  # type: ignore[attr-defined]
            high = df["high"].values.astype(np.float64)  # type: ignore[attr-defined]
            low = df["low"].values.astype(np.float64)  # type: ignore[attr-defined]
            volume = df["volume"].values.astype(np.float64)  # type: ignore[attr-defined]

            # Momentum indicators
            df["rsi"] = talib.RSI(close, timeperiod=14)  # type: ignore[call-overload]
            macd, macd_signal, macd_hist = talib.MACD(close)  # type: ignore[call-overload]
            df["macd"] = macd
            df["macd_signal"] = macd_signal
            df["macd_hist"] = macd_hist

            # Volatility
            df["atr"] = talib.ATR(high, low, close, timeperiod=14)  # type: ignore[call-overload]
            df["volatility"] = df["returns"].rolling(20).std()

            # Moving averages
            df["sma_20"] = talib.SMA(close, timeperiod=20)  # type: ignore[call-overload]
            df["sma_50"] = talib.SMA(close, timeperiod=50)  # type: ignore[call-overload]
            df["ema_12"] = talib.EMA(close, timeperiod=12)  # type: ignore[call-overload]

            # Volume indicators
            df["volume_ma"] = talib.SMA(volume, timeperiod=20)  # type: ignore[call-overload]
            df["volume_ratio"] = volume / df["volume_ma"]

        else:
            # Fallback: simple indicators without TA-Lib
            df["rsi"] = self._calculate_rsi_simple(df["close"], period=14)  # type: ignore[arg-type]
            df["volatility"] = df["returns"].rolling(20).std()
            df["sma_20"] = df["close"].rolling(20).mean()
            df["sma_50"] = df["close"].rolling(50).mean()
            df["volume_ma"] = df["volume"].rolling(20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_ma"]

        # Momentum
        df["momentum"] = df["close"] - df["close"].shift(10)
        df["momentum_pct"] = df["momentum"] / df["close"].shift(10)

        # Price position in range
        df["high_low_ratio"] = (df["close"] - df["low"]) / (df["high"] - df["low"])

        # Lagged features
        for lag in [1, 2, 3, 5]:
            df[f"returns_lag_{lag}"] = df["returns"].shift(lag)
            df[f"volume_lag_{lag}"] = df["volume"].shift(lag)

        return df.dropna()

    def _calculate_rsi_simple(self, prices: pd.Series, period: int = 14) -> pd.Series:  # type: ignore[return]
        """Simple RSI calculation without TA-Lib."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi  # type: ignore[return]

    def train(self, historical_data: pd.DataFrame) -> None:  # type: ignore[arg-type]
        """Train ML model on historical data.

        Args:
            historical_data: Historical OHLCV data for training
        """
        logger.info(f"Training ML model on {len(historical_data)} data points")

        # Create features
        df = self.create_features(historical_data)

        # Create target: 1 if price goes up next period, 0 otherwise
        df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
        df = df.dropna()

        if len(df) < self.lookback:
            logger.warning("Insufficient data for training")
            return

        # Select feature columns
        feature_cols = [
            col
            for col in df.columns
            if col
            not in [
                "target",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "datetime",
                "timestamp",
            ]
        ]

        X = df[feature_cols]
        y = df["target"]

        # Time-series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)  # type: ignore[attr-defined]
            X_val_scaled = self.scaler.transform(X_val)  # type: ignore[attr-defined]

            # Train model
            self.model.fit(X_train_scaled, y_train)  # type: ignore[attr-defined]

            # Evaluate
            score = self.model.score(X_val_scaled, y_val)  # type: ignore[attr-defined]
            scores.append(score)

        avg_score = np.mean(scores)  # type: ignore[attr-defined]
        logger.info(f"ML model training completed. Average CV score: {avg_score:.3f}")
        self.is_trained = True
        self.feature_cols = feature_cols

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:  # type: ignore[return]
        """Generate ML-based trading signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals added
        """
        df = self.create_features(data)

        if not self.is_trained:
            logger.warning("Model not trained. Generating random signals.")
            df["signal"] = 0
            return df

        # Select features
        if not hasattr(self, "feature_cols"):
            feature_cols = [
                col
                for col in df.columns
                if col
                not in [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "datetime",
                    "timestamp",
                ]
            ]
        else:
            feature_cols = self.feature_cols

        # Ensure all feature columns exist
        available_features = [col for col in feature_cols if col in df.columns]
        X = df[available_features].fillna(0)

        if len(X) == 0:
            df["signal"] = 0
            return df

        # Scale features
        try:
            X_scaled = self.scaler.transform(X)  # type: ignore[attr-defined]
        except Exception:
            # If scaler not fitted, fit it now
            X_scaled = self.scaler.fit_transform(X)  # type: ignore[attr-defined]

        # Predict
        predictions = self.model.predict(X_scaled)  # type: ignore[attr-defined]
        probabilities = self.model.predict_proba(X_scaled)  # type: ignore[attr-defined]

        # Generate signals based on confidence
        df["signal"] = 0
        df["ml_prediction"] = predictions
        df["ml_confidence"] = probabilities.max(axis=1)  # type: ignore[attr-defined]

        # Buy signal: predict up AND high confidence
        buy_mask = (predictions == 1) & (probabilities[:, 1] > self.confidence_threshold)  # type: ignore[index]
        df.loc[buy_mask, "signal"] = 1

        # Sell signal: predict down AND high confidence
        sell_mask = (predictions == 0) & (probabilities[:, 0] > self.confidence_threshold)  # type: ignore[index]
        df.loc[sell_mask, "signal"] = -1

        return df

    def calculate_position_size(
        self,
        price: float,
        account_value: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size."""
        risk_amount = account_value * risk_per_trade
        stop_loss_pct = 0.02
        stop_loss_price = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss_price

        if risk_per_share <= 0:
            return 0.0

        position_size = risk_amount / risk_per_share
        max_position_value = account_value * 0.1
        max_shares = max_position_value / price

        return min(position_size, max_shares)
