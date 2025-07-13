import os

from dotenv import load_dotenv
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler)

from src.handlers import (add_me, error_handler, handle_delete_button, played,
                          ranking, start, help_command)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")


def app_factory(token=TOKEN):
    """Factory function to create the Telegram bot application."""

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("played", played))
    app.add_handler(CommandHandler("add_me", add_me))
    app.add_handler(CommandHandler("rank", ranking))
    app.add_handler(CallbackQueryHandler(
        handle_delete_button, pattern="^delete_game:"))
    app.add_error_handler(error_handler)

    return app
