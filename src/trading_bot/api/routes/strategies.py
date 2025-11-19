"""Strategy management endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from trading_bot.strategies.strategy_registry import _strategy_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/strategies")
async def list_strategies():
    """List all available strategies."""
    logger.info("=" * 60)
    logger.info("STRATEGIES ENDPOINT CALLED")
    logger.info("=" * 60)

    try:
        logger.info("Step 1: Getting strategies list from registry...")
        strategies_list = _strategy_registry.get_strategies_list()
        logger.info(f"Step 1: Registry returned {len(strategies_list)} strategy entries")

        logger.info("Step 2: Processing strategies...")
        strategies_info = []
        available_count = 0
        for _display_name, internal_name in strategies_list:
            try:
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
                logger.debug(f"  - {internal_name}: available={is_available}")
            except Exception as e:
                logger.warning(f"Failed to process strategy {internal_name}: {e}")
                strategies_info.append(
                    {
                        "name": internal_name,
                        "display_name": internal_name,
                        "available": False,
                    }
                )

        logger.info("=" * 60)
        logger.info("STRATEGIES ENDPOINT SUCCESS")
        logger.info(f"Total: {len(strategies_info)}, Available: {available_count}, Unavailable: {len(strategies_info) - available_count}")
        logger.info("=" * 60)
        return {"strategies": strategies_info}
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Failed to list strategies")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list strategies: {e!s}",
        ) from e


@router.get("/strategies/{strategy_name}")
async def get_strategy_info(strategy_name: str):
    """Get information about a specific strategy."""
    logger.info("=" * 60)
    logger.info("GET STRATEGY INFO ENDPOINT CALLED")
    logger.info("=" * 60)
    logger.info(f"Strategy name: {strategy_name}")

    try:
        logger.info("Step 1: Checking if strategy is available...")
        is_available = _strategy_registry.is_available(strategy_name)
        logger.info(f"Step 1: Strategy available: {is_available}")

        if not is_available:
            logger.error("=" * 60)
            logger.error(f"ERROR: Strategy '{strategy_name}' not found or not available")
            logger.error("=" * 60)
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found or not available",
            )

        logger.info("Step 2: Getting strategy display name...")
        display_name = _strategy_registry.get_display_name(strategy_name)
        logger.info(f"Step 2: ✅ Display name: {display_name}")

        logger.info("Step 3: Getting strategy class...")
        strategy_class = _strategy_registry.get_strategy_class(strategy_name)
        if strategy_class is None:
            logger.error("=" * 60)
            logger.error(f"ERROR: Strategy '{strategy_name}' class not available")
            logger.error("=" * 60)
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not available",
            )
        logger.info(f"Step 3: ✅ Strategy class: {strategy_class.__name__}")

        logger.info("Step 4: Getting parameter schema...")
        params_schema = _get_strategy_params_schema(strategy_name)
        logger.info(f"Step 4: ✅ Found {len(params_schema)} parameters")

        result = {
            "name": strategy_name,
            "display_name": display_name,
            "class_name": strategy_class.__name__,
            "available": True,
            "parameters": params_schema,
        }
        logger.info("=" * 60)
        logger.info("GET STRATEGY INFO SUCCESS")
        logger.info(f"Returning info for: {strategy_name}")
        logger.info("=" * 60)
        return result
    except HTTPException as e:
        logger.warning(f"HTTPException raised: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Failed to get strategy info")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
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
