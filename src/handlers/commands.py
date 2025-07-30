import os
import re
import traceback
from datetime import datetime, date

import pytz
from sqlalchemy.exc import IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import (ContextTypes, ConversationHandler,
                          MessageHandler, filters)

from src.db import SessionLocal
from src.decorators import reject_if_private_chat
from src.functions import calculate_ranking
from src.logging_config import logger
from src.models import Game, Player
from src.utils import with_emoji


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        with_emoji(
            ":wave: *Welcome to the Game Manager Bot!*\n\n"
            "Track your group's daily games, wins, and rankings — all "
            "automatically.\n\n"
            "Type /menu to see the menu.\n"
            "Type /help to learn how to use the bot."),
        parse_mode="MarkdownV2"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = with_emoji(
        "<b>:book: How to Use the Game Manager Bot:</b>\n\n"
        "<b>:white_check_mark: 1. Register Yourself (one-time):</b>\n"
        "`/add_me`\n"
        "You *must* register before using other commands.\n\n"
        "<b>:video_game: 2. Record a Game:</b>\n"
        "`/played @winner @loser [date=yyyy-mm-dd]`\n"
        "Example: `/played @alice @bob date=2025-07-13`\n"
        "Date is optional - defaults to today.\n\n"
        "<b>:bar_chart: 3. Check Rankings:</b>\n"
        "`/rank [yyyy-mm-dd | today]`\n"
        "Use `/rank today` for today's results.\n"
        "Use `/rank` (with no date) for all-time rankings.\n\n"
        "<b>:gear: Menu:</b>\n"
        "`/menu`\n"
        "Use `/menu` to see the menu (This feature is under development).\n\n"
        "<b>:man_technologist: Developer:</b> "
        "<a href='https://www.pouria.site/'>Pouria Forghani</a>"
    )
    if not update.message:
        return
    await update.message.reply_text(message, parse_mode="HTML")


@reject_if_private_chat
async def played(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()

    if not update.message:
        logger.error("No message found")
        session.close()
        return
    text = update.message.text or ""
    entities = update.message.entities or []
    if len(entities) < 3:
        await update.message.reply_text(
            "Please provide 2 mentions or text mentions in the message."
        )
        session.close()
        return
    if not update.effective_chat:
        await update.message.reply_text("Unable to get chat info. Try again.")
        logger.error("Unable to get chat info. Try again.")
        session.close()
        return
    chat_id = update.effective_chat.id

    player_objs = []
    for entity in entities:
        if entity.type == MessageEntityType.TEXT_MENTION:
            if not entity.user:
                logger.debug(f"No user found for entity: {entity}")
                continue
            player = session.query(Player).filter_by(
                telegram_id=entity.user.id).first()
            logger.debug(f"Player object: {player}")
        elif entity.type == MessageEntityType.MENTION:
            username = text[entity.offset + 1: entity.offset + entity.length]
            player = session.query(Player).filter_by(
                username=username).first()
        else:
            continue

        if not player:
            if entity.type == MessageEntityType.TEXT_MENTION:
                if not entity.user:
                    logger.debug(f"No user found for entity: {entity}")
                    continue
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
        player_objs.append(player)
    logger.debug(f"Player objects: {player_objs}")
    if len(player_objs) < 2 or len(player_objs) % 2 != 0:
        await update.message.reply_text(
            "Please provide an even number of players (@winner @loser\n@winner @loser\n.\n.)."
        )
        session.close()
        return

    # If date is provided in the message set it, otherwise use the message date
    game_date = None
    pattern = r"^date=(\d{4}-\d{2}-\d{2})$"
    if (
        context.args
        and len(context.args) > 3
    ):
        if re.match(pattern, context.args[-1].lower(), re.IGNORECASE):
            game_date = datetime.strptime(
                context.args[-1].split("=")[1], "%Y-%m-%d").date()
        else:
            await update.message.reply_text(
                "Invalid date format. Use date=YYYY-MM-DD."
            )
            session.close()
            return
    if not game_date:
        msg_date_utc = update.message.date
        timezone = pytz.timezone("Asia/Tehran")
        game_date = msg_date_utc.astimezone(timezone).date()

    success_message = f"Games Played on {game_date}:\n\n"
    games_created = 0
    # Step 4: Save the game record
    for i in range(0, len(player_objs), 2):
        winner = player_objs[i]
        loser = player_objs[i + 1]
        if winner.id == loser.id:
            await update.message.reply_text(
                "Winner and loser cannot be the same person: "
                f"{winner.username or winner.first_name}"
                "Try again."
            )
            session.close()
            return

        game = Game(
            winner_id=winner.id,
            loser_id=loser.id,
            date=game_date,
            chat_id=chat_id
        )
        games_created += 1

        session.add(game)
        session.flush()  # This assigns the ID without committing
        success_message += (
            f"{games_created}.Game {game.id}: <b>{winner.first_name}</b> won "
            f"<b>{loser.first_name}</b>  /delete_game_{game.id}\n"
        )

    session.commit()

    await update.message.reply_text(
        success_message,
        parse_mode="HTML",
    )
    session.close()


@reject_if_private_chat
async def add_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message:
        return
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


@reject_if_private_chat
async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
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
            session.close()
            return

    if not update.effective_chat:
        session.close()
        return
    chat_id = update.effective_chat.id
    rankings = calculate_ranking(session, chat_id, date)

    players_with_ratio = sorted(
        [
            (p, r)
            for p, r in rankings
            if r is not None  # Only include players with valid win ratios
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
            f"— <i>Win Ratio:</i> {score * 100:.0f}%\n"
        )

    ranking_message += with_emoji(
        "\n\n:rocket: <b>Let's keep the games rolling!</b>")
    await update.message.reply_text(ranking_message, parse_mode="HTML")
    session.close()


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu with inline keyboard buttons."""
    if not update.message:
        return

    menu_text = with_emoji(
        ":game_die: <b>Game Manager Menu</b>\n\n"
        "Choose an option from the menu below:"
    )

    keyboard = [
        [InlineKeyboardButton(
            text=with_emoji(":trophy: Rankings"),
            callback_data="menu_rankings"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":video_game: Start Session"),
            callback_data="menu_start_session"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":stop_button: End Session"),
            callback_data="menu_end_session"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":bust_in_silhouette: Add Me"),
            callback_data="menu_add_me"
        )]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        menu_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def handle_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Log all attributes of the context object for debugging
    if context.args:
        logger.debug("\n".join([arg for arg in context.args]))
    else:
        logger.debug("No arguments provided")

# TODO: Build the del_game_id command