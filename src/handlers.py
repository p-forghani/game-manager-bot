import os
import re
import traceback
from datetime import datetime

import pytz
from sqlalchemy.exc import IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import MessageEntityType
from telegram.ext import ContextTypes

from src.db import SessionLocal
from src.functions import calculate_ranking
from src.logging_config import logger
from src.models import Game, Player
from src.utils import with_emoji


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        with_emoji(
            ":wave: *Welcome to the Game Manager Bot\\!*\n\n"
            "Track your group’s daily games, wins, and rankings — all "
            "automatically\\.\n\n"
            "Type /help to learn how to use the bot\\."),
        parse_mode="MarkdownV2"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = with_emoji(
        "*:book: How to Use the Game Manager Bot:*\n\n"

        "*:white_check_mark: 1\\. Register Yourself \\(one\\-time\\):*\n"
        "`/add_me`\n"
        "You *must* register before using other commands\\.\n\n"

        "*:video_game: 2\\. Record a Game:*\n"
        "`/played @winner @loser \\[yyyy\\-mm\\-dd\\]`\n"
        "Example: `/played @alice @bob 2025\\-07\\-13`\n"
        "Date is optional \\- defaults to today\\.\n\n"

        "*:bar_chart: 3\\. Check Rankings:*\n"
        "`/rank \\[yyyy\\-mm\\-dd | today\\]`\n"
        "Use `/rank today` for today\\'s results\\.\n"
        "Use `/rank` \\(with no date\\) for all\\-time rankings\\.\n\n"

        "*:man_technologist: Developer:* @pouriaf99"
    )
    await update.message.reply_text(message, parse_mode="MarkdownV2")


async def played(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()

    winner_user = None
    loser_user = None

    text = update.message.text or ""
    entities = update.message.entities or []
    if len(entities) < 3:
        await update.message.reply_text(
            "Please provide 2 mentions or text mentions in the message."
        )
        session.close()
        return
    chat_id = update.effective_chat.id

    for entity in entities:
        if entity.type == MessageEntityType.TEXT_MENTION:
            player = session.query(Player).filter_by(
                telegram_id=entity.user.id).first()
        elif entity.type == MessageEntityType.MENTION:
            username = text[entity.offset + 1: entity.offset + entity.length]
            player = session.query(Player).filter_by(
                username=username).first()
        else:
            continue

        if not player:
            if entity.type == MessageEntityType.TEXT_MENTION:
                await update.message.reply_text(
                    f"Player {entity.user.first_name} not found. "
                    "Ask them to send /add_me first."
                )
            elif entity.type == MessageEntityType.MENTION:
                mentioned_text = text[entity.offset:
                                      entity.offset + entity.length]
                await update.message.reply_text(
                    f"Player @{mentioned_text} not found. "
                    "Ask them to send /add_me first."
                )
            session.close()
            return

        if not winner_user:
            winner_user = player
        else:
            loser_user = player

    # If date is provided in the message set it, otherwise use the message date
    game_date = None
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if (
        context.args
        and len(context.args) > 2
    ):
        if re.match(pattern, context.args[2]):
            game_date = datetime.strptime(context.args[2], "%Y-%m-%d").date()
        else:
            await update.message.reply_text(
                "Invalid date format. Use YYYY-MM-DD."
            )
            return
    if not game_date:
        msg_date_utc = update.message.date
        timezone = pytz.timezone("Asia/Tehran")
        game_date = msg_date_utc.astimezone(timezone).date()

    # Step 4: Save the game record
    game = Game(
        winner_id=winner_user.id,
        loser_id=loser_user.id,
        date=game_date,
        chat_id=chat_id)
    session.add(game)
    session.commit()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="🗑️ Delete this game",
            callback_data=f"delete_game:{game.id}"
        )
    ]])

    await update.message.reply_text(
        f"Game with ID {game.id} recorded successfully!\n"
        f"Recorded: {winner_user.first_name} won "
        f"against <b>{loser_user.first_name}</b> "
        f"on {game_date}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    session.close()


async def add_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        await update.message.reply_text("Unable to get your info. Try again.")
        return

    session = SessionLocal()

    existing_player = session.query(Player).filter_by(
        telegram_id=user.id).first()

    if existing_player:
        # Update existing player's info
        setattr(existing_player, "username", user.username or None)
        setattr(existing_player, "first_name", user.first_name or None)
        try:
            session.commit()
            await update.message.reply_text(
                "Your information has been updated!"
            )
            logger.info(f"Player updated: {user.id} - {user.first_name}")
        except Exception as e:
            logger.error("Failed to update player", exc_info=e)
            await update.message.reply_text("Something went wrong. Try again")
            session.rollback()
        finally:
            session.close()
            return

    player = Player(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    session.add(player)

    try:
        session.commit()
        await update.message.reply_text((
            "You have been added as a player! "
            "You can now use the /played command to record your games."
        ), parse_mode="HTML")
        logger.info(f"Player added: {user.id} - {user.first_name}")
    except IntegrityError:
        await update.message.reply_text("You are already in the database.")
        session.rollback()
    except Exception as e:
        logger.error("Failed to add player", exc_info=e)
        await update.message.reply_text("Something went wrong. Try again")
        session.rollback()
    finally:
        session.close()


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()

    pattern = r"^\d{4}-\d{2}-\d{2}$"
    date = None
    if (
        context.args
        and len(context.args) > 0
    ):
        if context.args[0].lower() == "today":
            date = datetime.now(pytz.timezone("Asia/Tehran")).date()
        elif re.match(pattern, context.args[0]):
            date = datetime.strptime(context.args[0], "%Y-%m-%d").date()
        else:
            await update.message.reply_text(
                "Invalid date format. Use YYYY-MM-DD or 'today'."
            )
            return

    chat_id = update.effective_chat.id

    players_with_ratio = sorted(
        [
            (p, r)
            for p, r in calculate_ranking(session, chat_id, date)
            if (p.games_won or p.games_lost)
        ],
        key=lambda x: x[1],
        reverse=True
    )

    if len(players_with_ratio) == 0:
        await update.message.reply_text(
            with_emoji(":no_entry: No games played yet in this chat.")
        )
        session.close()
        return

    if date:
        ranking_message = with_emoji(
            f":trophy: <b>{date} Champions Are Here!</b> :sparkles:\n\n")
    else:
        ranking_message = with_emoji(
            ":trophy: <b>All-Time Champions Are Here!</b> :sparkles:\n\n")
    # sample player = (Player object, score)

    for idx, (player, score) in enumerate(players_with_ratio, start=1):
        medals = [
            ":1st_place_medal:",
            ":2nd_place_medal:",
            ":3rd_place_medal:",
        ]
        medal = with_emoji(medals[idx-1] if idx <= 3 else ":dart:")
        ranking_message += with_emoji(
            f"{medal} <b>{idx}. {player.first_name}</b> "
            f"— <i>Win Ratio:</i> {score:.2f}%\n"
        )

    ranking_message += with_emoji(
        "\n\n:rocket: <b>Let's keep the games rolling!</b>")
    await update.message.reply_text(ranking_message, parse_mode="HTML")
    session.close()


async def error_handler(
        update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors and log exception details."""
    logger.error("Exception occurred:", exc_info=context.error)

    if isinstance(update, Update) and getattr(update, "message", None):
        await update.message.reply_text(
            with_emoji(
                ":warning: Something went wrong. "
                "The developers have been notified.")
        )

    traceback_str = ''.join(
        traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
    )
    logger.debug("Traceback details:\n%s", traceback_str)
    # Notify the developer
    developer_id = os.getenv("DEVELOPER_ID")
    error_message = (
        f"🚨 <b>Error in Game Manager Bot</b>\n"
        f"<b>User:</b> "
        f"{getattr(getattr(update, 'effective_user', None), 'id', 'N/A')}\n"
        f"<b>Chat:</b> "
        f"{getattr(getattr(update, 'effective_chat', None), 'id', 'N/A')}\n"
        f"<b>Error:</b> <code>{context.error}</code>"
    )
    try:
        if developer_id is not None:
            await context.bot.send_message(
                chat_id=int(developer_id),
                text=error_message,
                parse_mode="HTML"
            )
    except Exception as notify_err:
        logger.error("Failed to notify developer: %s", notify_err)


async def handle_delete_button(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    game_id = int(query.data.split(":")[1])

    session = SessionLocal()
    game = session.query(Game).filter_by(id=game_id, chat_id=chat_id).first()

    if not game:
        await query.edit_message_text(with_emoji(":x: Game not found."))
        return

    session.delete(game)
    session.commit()
    await query.edit_message_text(with_emoji(":wastebasket: Game deleted."))
