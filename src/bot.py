import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler

from src.handlers import start, played, add_me, ranking, error_handler

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")


def app_factory(token=TOKEN):
    """Factory function to create the Telegram bot application."""

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("played", played))
    app.add_handler(CommandHandler("add_me", add_me))
    app.add_handler(CommandHandler("rank", ranking))

    return app
