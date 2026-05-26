"""F7 — Bot service entry point. Runs a PTB polling application."""
import logging

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler
from telegram.ext import filters as ext_filters

from flatbot.bot.handlers import (
    handle_activar,
    handle_buscar,
    handle_carousel_nav,
    handle_estado,
    handle_filtros,
    handle_pausar,
    handle_scan,
    handle_start,
)
from flatbot.config import settings
from flatbot.logging_conf import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging(settings.log_level)

    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN not set — bot cannot start")
        return

    app = ApplicationBuilder().token(settings.telegram_token).build()

    # Restrict to the configured chat if provided; otherwise open to all
    if settings.telegram_chat_id:
        try:
            chat_filter: ext_filters.BaseFilter = ext_filters.Chat(
                chat_id=int(settings.telegram_chat_id)
            )
        except ValueError:
            logger.warning("TELEGRAM_CHAT_ID is not a valid integer — ignoring filter")
            chat_filter = ext_filters.ALL
    else:
        chat_filter = ext_filters.ALL

    for cmd, handler in [
        (["start", "help"], handle_start),
        ("filtros", handle_filtros),
        ("estado", handle_estado),
        ("pausar", handle_pausar),
        ("activar", handle_activar),
        ("scan", handle_scan),
        ("buscar", handle_buscar),
    ]:
        app.add_handler(CommandHandler(cmd, handler, filters=chat_filter))

    app.add_handler(CallbackQueryHandler(handle_carousel_nav, pattern=r"^n:"))

    logger.info("Bot polling started")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
