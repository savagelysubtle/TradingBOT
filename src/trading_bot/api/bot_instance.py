"""Bot instance management for API routes."""

import logging

from trading_bot.bot import TradingBot

logger = logging.getLogger(__name__)

# Global bot instance
bot_instance: TradingBot | None = None


def get_bot() -> TradingBot:
    """Get the global bot instance.

    Raises:
        RuntimeError: If bot instance is not initialized
    """
    logger.debug("get_bot() called")
    logger.debug(f"Bot instance exists: {bot_instance is not None}")
    logger.debug(f"Bot instance type: {type(bot_instance)}")

    if bot_instance is None:
        logger.error("=" * 60)
        logger.error("ERROR: Bot instance is None")
        logger.error("Bot instance has not been initialized")
        logger.error("This usually means the server startup failed or bot initialization failed")
        logger.error("=" * 60)
        raise RuntimeError("Bot instance not initialized")

    logger.debug(f"Bot instance retrieved successfully: {type(bot_instance)}")
    logger.debug(f"Bot has config: {hasattr(bot_instance, 'config')}")
    if hasattr(bot_instance, 'config'):
        logger.debug(f"Bot config exists: {bot_instance.config is not None}")

    return bot_instance


def set_bot(bot: TradingBot) -> None:
    """Set the global bot instance.

    Args:
        bot: TradingBot instance to set
    """
    global bot_instance
    logger.info("=" * 60)
    logger.info("SETTING BOT INSTANCE")
    logger.info("=" * 60)
    logger.info(f"Bot type: {type(bot)}")
    logger.info(f"Bot has config: {hasattr(bot, 'config')}")
    if hasattr(bot, 'config') and bot.config:
        logger.info(f"Bot config exchange: {bot.config.exchange_id}")
        logger.info(f"Bot config provider: {bot.config.data_provider}")
    logger.info("Bot instance set successfully")
    logger.info("=" * 60)
    bot_instance = bot


def clear_bot() -> None:
    """Clear the global bot instance."""
    global bot_instance
    logger.info("=" * 60)
    logger.info("CLEARING BOT INSTANCE")
    logger.info("=" * 60)
    logger.info(f"Bot instance exists before clear: {bot_instance is not None}")
    bot_instance = None
    logger.info("Bot instance cleared successfully")
    logger.info("=" * 60)

