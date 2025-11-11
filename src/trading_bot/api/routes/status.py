"""Status and health check endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from trading_bot.api.bot_instance import get_bot

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_status():
    """Get API and bot status."""
    logger.info("Status endpoint called")
    try:
        logger.debug("Getting bot instance")
        bot = get_bot()
        logger.debug(f"Bot instance retrieved: {bot is not None}")

        if bot is None:
            logger.error("Bot instance is None")
            raise HTTPException(status_code=503, detail="Bot instance not initialized")

        # Safely access config attributes
        logger.debug("Checking bot config")
        if not hasattr(bot, "config") or bot.config is None:
            logger.error("Bot config is None or missing")
            raise HTTPException(status_code=500, detail="Bot configuration not available")

        logger.debug("Accessing config attributes")
        try:
            exchange = str(bot.config.exchange_id)
            data_provider = str(bot.config.data_provider)
            sandbox_mode = bool(bot.config.exchange_sandbox)
            logger.debug(
                f"Config values: exchange={exchange}, data_provider={data_provider}, sandbox={sandbox_mode}"
            )
        except AttributeError as e:
            logger.error(f"Config attribute error: {e}")
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
        logger.info(f"Status endpoint returning: {result}")
        return result
    except RuntimeError as e:
        logger.error(f"Bot instance not initialized: {e}")
        raise HTTPException(status_code=503, detail="Bot instance not initialized") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {e!s}") from e


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        logger.debug("Health check requested")
        return {"status": "healthy", "service": "trading-bot-api"}
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
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
