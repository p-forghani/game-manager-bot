import os

from dotenv import load_dotenv
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, MessageHandler,
                          filters)

from src.constants import WAITING_FOR_DATE
from src.handlers.callbacks import (error_handler, handle_date_input,
                                    handle_delete_button, handle_menu_callback,
                                    handle_rank_callback)
from src.handlers.commands import (add_me, handle_test_command, help_command,
                                   played, ranking, show_menu, start, handle_games_command)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")


def app_factory(token=TOKEN):
    """Factory function to create the Telegram bot application."""

    app = ApplicationBuilder().token(token).build()
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("played", played))
    app.add_handler(CommandHandler("games", handle_games_command))
    app.add_handler(CommandHandler("add_me", add_me))
    app.add_handler(CommandHandler("rank", ranking))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("test", handle_test_command))

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(
        handle_menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(
        handle_rank_callback, pattern="^rank_"))
    app.add_handler(CallbackQueryHandler(
        handle_delete_button, pattern="^delete_game_"))
    # Uncomment These lines when the session is ready
    # app.add_handler(CallbackQueryHandler(
    #     handle_session_winner, pattern="^session_winner_"))
    # app.add_handler(CallbackQueryHandler(
    #     handle_session_loser, pattern="^session_loser_"))
    # app.add_handler(CallbackQueryHandler(
    #     handle_session_delete_game, pattern="^session_delete_game_"))
    # app.add_handler(CallbackQueryHandler(
    #     handle_session_end, pattern="^session_end$"))
    # app.add_handler(CallbackQueryHandler(
    #     handle_session_cancel_game, pattern="^session_cancel_game$"))

    # Conversation handler for date input
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            handle_rank_callback, pattern="^rank_enter_date$")],
        states={
            WAITING_FOR_DATE: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_date_input)]
        },
        fallbacks=[CallbackQueryHandler(
            handle_rank_callback, pattern="^rank_cancel$")]
    )
    app.add_handler(conv_handler)

    app.add_error_handler(error_handler)

    return app
