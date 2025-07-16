from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes


def reject_if_private_chat(func):
    """Decorator to reject commands in private chats."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "👋 Please add me to a group to use the bot.\n"
                "This bot is designed to work inside group chats!"
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
