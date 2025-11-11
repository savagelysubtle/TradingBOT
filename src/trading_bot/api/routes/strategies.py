"""Strategy management endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from trading_bot.strategies.strategy_registry import _strategy_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/strategies")
async def list_strategies():
    """List all available strategies."""
    try:
        logger.info("Listing all available strategies")
        strategies_list = _strategy_registry.get_strategies_list()
        logger.debug(f"Registry returned {len(strategies_list)} strategy entries")
        strategies_info = []
        available_count = 0
        for _display_name, internal_name in strategies_list:
            is_available = _strategy_registry.is_available(internal_name)
            display_name_full = _strategy_registry.get_display_name(internal_name)
            if is_available:
                available_count += 1
            strategies_info.append(
                {
                    "name": internal_name,
                    "display_name": display_name_full,
                    "available": is_available,
                }
            )
        logger.info(
            f"Found {len(strategies_info)} total strategies ({available_count} available, "
            f"{len(strategies_info) - available_count} unavailable)"
        )
        return {"strategies": strategies_info}
    except Exception as e:
        logger.exception(f"Failed to list strategies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list strategies: {e!s}",
        ) from e


@router.get("/strategies/{strategy_name}")
async def get_strategy_info(strategy_name: str):
    """Get information about a specific strategy."""
    logger.info(f"Getting strategy info for: {strategy_name}")
    try:
        if not _strategy_registry.is_available(strategy_name):
            logger.warning(f"Strategy '{strategy_name}' not found or not available")
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found or not available",
            )

        display_name = _strategy_registry.get_display_name(strategy_name)
        strategy_class = _strategy_registry.get_strategy_class(strategy_name)
        if strategy_class is None:
            logger.warning(f"Strategy '{strategy_name}' class not available")
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not available",
            )

        # Get parameter schema based on strategy name
        params_schema = _get_strategy_params_schema(strategy_name)
        logger.debug(f"Found strategy '{strategy_name}' with {len(params_schema)} parameters")

        return {
            "name": strategy_name,
            "display_name": display_name,
            "class_name": strategy_class.__name__,
            "available": True,
            "parameters": params_schema,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get strategy info for '{strategy_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy info: {e!s}",
        ) from e


def _get_strategy_params_schema(strategy_name: str) -> dict[str, dict]:
    """Get parameter schema for a strategy.

    Returns:
        Dictionary mapping parameter names to their schema (type, default, description)
    """
    schemas = {
        "ma_crossover": {
            "short_window": {
                "type": "integer",
                "default": 50,
                "min": 1,
                "max": 500,
                "description": "Short moving average period",
            },
            "long_window": {
                "type": "integer",
                "default": 200,
                "min": 1,
                "max": 500,
                "description": "Long moving average period",
            },
            "use_rsi": {"type": "boolean", "default": True, "description": "Use RSI filter"},
            "rsi_period": {
                "type": "integer",
                "default": 14,
                "min": 1,
                "max": 100,
                "description": "RSI period",
            },
            "rsi_overbought": {
                "type": "float",
                "default": 70.0,
                "min": 50,
                "max": 100,
                "description": "RSI overbought threshold",
            },
            "rsi_oversold": {
                "type": "float",
                "default": 30.0,
                "min": 0,
                "max": 50,
                "description": "RSI oversold threshold",
            },
        },
        "talib_ma": {
            "short_period": {
                "type": "integer",
                "default": 50,
                "min": 1,
                "max": 500,
                "description": "Short moving average period",
            },
            "long_period": {
                "type": "integer",
                "default": 200,
                "min": 1,
                "max": 500,
                "description": "Long moving average period",
            },
            "use_rsi": {"type": "boolean", "default": True, "description": "Use RSI filter"},
            "rsi_period": {
                "type": "integer",
                "default": 14,
                "min": 1,
                "max": 100,
                "description": "RSI period",
            },
            "rsi_overbought": {
                "type": "float",
                "default": 70.0,
                "min": 50,
                "max": 100,
                "description": "RSI overbought threshold",
            },
            "rsi_oversold": {
                "type": "float",
                "default": 30.0,
                "min": 0,
                "max": 50,
                "description": "RSI oversold threshold",
            },
        },
        "talib_macd": {},
        "supertrend": {
            "period": {
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "ATR period for Supertrend",
            },
            "multiplier": {
                "type": "float",
                "default": 3.0,
                "min": 1.0,
                "max": 10.0,
                "description": "ATR multiplier",
            },
            "use_atr": {
                "type": "boolean",
                "default": True,
                "description": "Use ATR for dynamic stop loss",
            },
        },
        "bollinger": {
            "period": {
                "type": "integer",
                "default": 20,
                "min": 1,
                "max": 100,
                "description": "Bollinger Bands period",
            },
            "std_dev": {
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 5.0,
                "description": "Standard deviation multiplier",
            },
        },
        "ichimoku": {},
        "ml_randomforest": {
            "lookback": {
                "type": "integer",
                "default": 50,
                "min": 10,
                "max": 200,
                "description": "Number of periods to look back",
            },
            "n_estimators": {
                "type": "integer",
                "default": 100,
                "min": 10,
                "max": 500,
                "description": "Number of trees in Random Forest",
            },
            "max_depth": {
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 50,
                "description": "Maximum depth of trees",
            },
            "min_samples_split": {
                "type": "integer",
                "default": 5,
                "min": 2,
                "max": 50,
                "description": "Minimum samples required to split",
            },
            "confidence_threshold": {
                "type": "float",
                "default": 0.65,
                "min": 0.5,
                "max": 1.0,
                "description": "Minimum probability to generate signal",
            },
        },
        "stop_hunt": {
            "support_lookback": {
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 100,
                "description": "Periods to look back for support/resistance",
            },
            "atr_period": {
                "type": "integer",
                "default": 14,
                "min": 1,
                "max": 50,
                "description": "Period for ATR calculation",
            },
            "cluster_min_factors": {
                "type": "integer",
                "default": 3,
                "min": 1,
                "max": 10,
                "description": "Minimum converging factors for stop cluster",
            },
            "entry_distance_pct": {
                "type": "float",
                "default": 0.5,
                "min": 0.1,
                "max": 5.0,
                "description": "Percentage distance from cluster to enter",
            },
            "volume_spike_multiplier": {
                "type": "float",
                "default": 2.0,
                "min": 1.0,
                "max": 10.0,
                "description": "Volume spike threshold multiplier",
            },
            "reversal_candles": {
                "type": "integer",
                "default": 2,
                "min": 1,
                "max": 10,
                "description": "Number of candles to confirm reversal",
            },
            "stop_distance_atr": {
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 5.0,
                "description": "Stop loss distance in ATR multiples",
            },
            "use_round_numbers": {
                "type": "boolean",
                "default": True,
                "description": "Whether to consider round numbers",
            },
        },
        "multi_indicator": {
            "supertrend_period": {
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "Supertrend period",
            },
            "supertrend_multiplier": {
                "type": "float",
                "default": 3.0,
                "min": 1.0,
                "max": 10.0,
                "description": "Supertrend multiplier",
            },
            "rsi_period": {
                "type": "integer",
                "default": 14,
                "min": 1,
                "max": 100,
                "description": "RSI period",
            },
            "rsi_overbought": {
                "type": "float",
                "default": 70.0,
                "min": 50,
                "max": 100,
                "description": "RSI overbought threshold",
            },
            "rsi_oversold": {
                "type": "float",
                "default": 30.0,
                "min": 0,
                "max": 50,
                "description": "RSI oversold threshold",
            },
            "confirmation_threshold": {
                "type": "float",
                "default": 0.6,
                "min": 0.0,
                "max": 1.0,
                "description": "Confirmation threshold",
            },
        },
    }
    return schemas.get(strategy_name, {})
