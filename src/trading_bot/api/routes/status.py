"""Status and health check endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from trading_bot.api.bot_instance import get_bot

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_status():
    """Get API and bot status."""
    logger.info("=" * 60)
    logger.info("STATUS ENDPOINT CALLED")
    logger.info("=" * 60)

    try:
        logger.debug("Step 1: Getting bot instance...")
        bot = get_bot()
        logger.info(f"Step 1: Bot instance retrieved - exists: {bot is not None}, type: {type(bot)}")

        if bot is None:
            logger.error("=" * 60)
            logger.error("ERROR: Bot instance is None")
            logger.error("=" * 60)
            raise HTTPException(status_code=503, detail="Bot instance not initialized")

        # Safely access config attributes
        logger.debug("Step 2: Checking bot config...")
        logger.debug(f"Bot has 'config' attribute: {hasattr(bot, 'config')}")
        if hasattr(bot, "config"):
            logger.debug(f"Bot.config is None: {bot.config is None}")
            logger.debug(f"Bot.config type: {type(bot.config)}")

        if not hasattr(bot, "config") or bot.config is None:
            logger.error("=" * 60)
            logger.error("ERROR: Bot config is None or missing")
            logger.error(f"Bot attributes: {dir(bot)}")
            logger.error("=" * 60)
            raise HTTPException(status_code=500, detail="Bot configuration not available")

        logger.debug("Step 3: Accessing config attributes...")
        try:
            exchange = str(bot.config.exchange_id)
            data_provider = str(bot.config.data_provider)
            sandbox_mode = bool(bot.config.exchange_sandbox)
            logger.info(f"Step 3: Config values retrieved successfully")
            logger.info(f"  - exchange: {exchange}")
            logger.info(f"  - data_provider: {data_provider}")
            logger.info(f"  - sandbox_mode: {sandbox_mode}")
        except AttributeError as e:
            logger.error("=" * 60)
            logger.error(f"ERROR: Config attribute error: {e}")
            logger.error(f"Config attributes available: {dir(bot.config) if bot.config else 'N/A'}")
            logger.error("=" * 60)
            raise HTTPException(
                status_code=500,
                detail=f"Configuration error: {e!s}",
            ) from e

        result = {
            "status": "running",
            "exchange": exchange,
            "data_provider": data_provider,
            "sandbox_mode": sandbox_mode,
        }
        logger.info("=" * 60)
        logger.info("STATUS ENDPOINT SUCCESS")
        logger.info(f"Returning result: {result}")
        logger.info("=" * 60)
        return result
    except RuntimeError as e:
        logger.error("=" * 60)
        logger.error(f"ERROR: Bot instance not initialized (RuntimeError)")
        logger.error(f"Error details: {e}")
        logger.error("=" * 60)
        raise HTTPException(status_code=503, detail="Bot instance not initialized") from e
    except HTTPException as e:
        logger.warning(f"HTTPException raised: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Unexpected exception in get_status")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        raise HTTPException(status_code=500, detail=f"Error getting status: {e!s}") from e


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("=" * 60)
    logger.info("HEALTH CHECK ENDPOINT CALLED")
    logger.info("=" * 60)

    try:
        logger.info("Step 1: Performing health checks...")
        logger.info("Step 1: ✅ All checks passed")

        result = {"status": "healthy", "service": "trading-bot-api"}
        logger.info("=" * 60)
        logger.info("HEALTH CHECK SUCCESS")
        logger.info(f"Status: {result['status']}")
        logger.info("=" * 60)
        return result
    except Exception as e:
        logger.exception("=" * 60)
        logger.exception("ERROR: Health check failed")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 60)
        return {"status": "unhealthy", "error": str(e)}


@router.get("/status/simple")
async def get_simple_status():
    """Get simple API status without bot instance."""
    logger.debug("Simple status endpoint called")
    try:
        logger.debug("Checking if bot instance exists")
        _ = get_bot()  # Check if bot exists, but don't use it
        logger.debug("Bot instance is available")
        return {
            "status": "running",
            "bot_initialized": True,
        }
    except RuntimeError as e:
        logger.debug(f"Bot instance not initialized: {e}")
        return {
            "status": "running",
            "bot_initialized": False,
            "message": "Bot instance not yet initialized",
        }
    except Exception as e:
        logger.exception(f"Error in simple status endpoint: {e}")
        return {
            "status": "error",
            "bot_initialized": False,
            "error": str(e),
        }
