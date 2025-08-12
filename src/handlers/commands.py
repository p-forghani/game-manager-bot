import re
from src.functions import generate_rankings_text
from datetime import datetime

import pytz
from sqlalchemy.exc import IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import MessageEntityType
from telegram.ext import ContextTypes

from src.db import SessionLocal
from src.decorators import reject_if_private_chat
from src.functions import calculate_ranking, generate_games_history_message
from src.logging_config import logger
from src.models import Game, Player
from src.templates import HELP_MESSAGE, START_MESSAGE
from src.utils import with_emoji


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("start() called")
    if not update.message:
        return
    await update.message.reply_text(
        with_emoji(START_MESSAGE),
        parse_mode="HTML"
    )
    return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("help_command() called")
    message = with_emoji(HELP_MESSAGE)
    if not update.effective_chat:
        logger.debug("No chat found")
        return
    if update.callback_query:
        await update.effective_chat.send_message(message, parse_mode="HTML")
        return
    if not update.message:
        logger.debug("No message found")
        return
    await update.message.reply_text(message, parse_mode="HTML")
    return


@reject_if_private_chat
async def played(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("played() called")
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
        and context.args[-1].lower().startswith("date=")
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
    keyboard = []
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
         # This assigns the ID without committing
        session.flush()
        success_message += (
            f"<i>{games_created}</i>. Game ID <b>{game.id}:</b> <b>{winner.first_name}</b> won "
            f"<b>{loser.first_name}</b>\n"
        )
        keyboard.append([InlineKeyboardButton(
            text=with_emoji(f":wastebasket: Delete Game {game.id}"),
            callback_data=f"delete_game_{game.id}"
        )])

    session.commit()
    await update.message.reply_text(
        success_message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    session.close()
    return


@reject_if_private_chat
async def add_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("add_me() called")
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


@reject_if_private_chat
async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("ranking() called")
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

    if not rankings:
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

    ranking_message += generate_rankings_text(rankings)

    ranking_message += with_emoji(
        "\n\n:rocket: <b>Let's keep the games rolling!</b>")
    await update.message.reply_text(ranking_message, parse_mode="HTML")
    session.close()
    return


@reject_if_private_chat
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu with inline keyboard buttons."""
    logger.debug("show_menu() called")

    menu_text = with_emoji(
        ":game_die: <b>Game Manager Menu</b>\n\n"
        "Choose an option from the menu below OR use\n"
        "<code>/played [date=yyyy-mm-dd]</code> to record a game;\n"
        "<code>/games [date=yyyy-mm-dd]</code> to see the games history."
    )

    keyboard = [
        [InlineKeyboardButton(
            text=with_emoji(":trophy: Rankings"),
            callback_data="menu_rankings"
        )],
        # [InlineKeyboardButton(
        #     text=with_emoji(":video_game: Start Session"),
        #     callback_data="menu_start_session"
        # )],
        # [InlineKeyboardButton(
        #     text=with_emoji(":stop_button: End Session"),
        #     callback_data="menu_end_session"
        # )],
        [InlineKeyboardButton(
            text=with_emoji(":bust_in_silhouette: Add Me"),
            callback_data="menu_add_me"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":question: Help"),
            callback_data="menu_help"
        )],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # If the command is called from a callback query ie back to menu
    # from other menu, edit the message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            menu_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return

    if not update.message:
        logger.debug("No message found")
        return
    # If the command is called from a message, send a new message
    await update.message.reply_text(
        menu_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return


@reject_if_private_chat
async def handle_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("handle_test_command() called")
    # Log all attributes of the context object for debugging
    if context.args:
        logger.debug("\n".join([arg for arg in context.args]))
    else:
        logger.debug("No arguments provided")
    return


@reject_if_private_chat
async def handle_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("handle_games_command() called")
    """If date is provided, show the games for that date,
    otherwise show all games played on that chat today."""
    if not update.message:
        return

    session = SessionLocal()
    pattern = r"date=(\d{4}-\d{2}-\d{2})$"
    date = None

    if context.args and len(context.args) > 0:
        last_arg = context.args[-1].lower()
        if re.match(pattern, last_arg, re.IGNORECASE):
            date_str = context.args[-1].split("=")[1]
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            await update.message.reply_text(
                "Invalid date format. Use date=YYYY-MM-DD."
            )
            session.close()
            return

    if not date:
        date = datetime.now(pytz.timezone("Asia/Tehran")).date()
    if not update.effective_chat:
        session.close()
        return

    games_message, games_keyboard = generate_games_history_message(
        session=session,
        chat_id=update.effective_chat.id,
        game_date=date
    )
    logger.debug(f"Games message: {games_message}")
    logger.debug(f"Games keyboard: {games_keyboard}")
    if not games_message:
        await update.message.reply_text(
            with_emoji(":no_entry: No games played on this date in this chat.")
        )
        session.close()
        return

    games_list_message = with_emoji(f"Games played on {date}:\n\n" + games_message)


    await update.message.reply_text(
        games_list_message,
        parse_mode="HTML",
        reply_markup=games_keyboard if games_keyboard else None
    )
    session.close()
    return


@reject_if_private_chat
async def handle_delete_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("handle_delete_game_command() called")
    """Handle delete game command."""
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text(
            with_emoji(":x: Please provide a game ID."))
        return
    game_id = context.args[0]
    if not game_id.isdigit():
        await update.message.reply_text(
            with_emoji(":x: Invalid game ID."))
        return
    session = SessionLocal()
    game = session.query(Game).filter_by(id=game_id).first()
    if not game:
        await update.message.reply_text(
            with_emoji(f":x: Game ID {game_id} not found."))
        return
    game.deleted_at = datetime.now()  # type: ignore
    session.add(game)
    session.commit()
    await update.message.reply_text(with_emoji(f":wastebasket: Game {game_id} deleted."))
    # FUTURE: Add an undo button to restore the game
    session.close()
    return