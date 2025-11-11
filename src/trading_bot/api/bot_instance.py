"""Bot instance management for API routes."""

from trading_bot.bot import TradingBot

# Global bot instance
bot_instance: TradingBot | None = None


def get_bot() -> TradingBot:
    """Get the global bot instance.

    Raises:
        RuntimeError: If bot instance is not initialized
    """
    if bot_instance is None:
        raise RuntimeError("Bot instance not initialized")
    return bot_instance


def set_bot(bot: TradingBot) -> None:
    """Set the global bot instance.

    Args:
        bot: TradingBot instance to set
    """
    global bot_instance
    bot_instance = bot


def clear_bot() -> None:
    """Clear the global bot instance."""
    global bot_instance
    bot_instance = None

