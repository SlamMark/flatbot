import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from scraper import fetch_listings

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Filters to apply when querying the API
SEARCH_FILTERS = {
    "city": "Barcelona",
    "max_price": 1200,
}

# IDs of listings already sent, to avoid duplicates
seen_ids: set[str] = set()


async def check_listings(context: ContextTypes.DEFAULT_TYPE) -> None:
    listings = await fetch_listings(SEARCH_FILTERS)
    bot: Bot = context.bot

    for listing in listings:
        listing_id = str(listing.get("id"))
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        message = format_listing(listing)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")


def format_listing(listing: dict) -> str:
    return (
        f"<b>{listing.get('title', 'Sin título')}</b>\n"
        f"💶 {listing.get('price', '?')} €/mes\n"
        f"📍 {listing.get('location', '?')}\n"
        f"🔗 {listing.get('url', '')}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot activo. Buscando pisos...")


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Check every 5 minutes
    app.job_queue.run_repeating(check_listings, interval=300, first=10)

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
