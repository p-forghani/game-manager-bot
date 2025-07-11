import pytz
from sqlalchemy.exc import IntegrityError
from telegram import Update
from telegram.constants import MessageEntityType
from telegram.ext import ContextTypes

from src.db import SessionLocal
from src.logging_config import logger
from src.models import Game, Player
from src.utils import with_emoji
from datetime import datetime


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        with_emoji(":wave: Hello! I'm the Game Manager Bot. "
                   "type / to see suggested commands")
    )


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
    logger.info(f"Message entities: {entities}")

    for entity in entities:
        if entity.type == MessageEntityType.TEXT_MENTION:
            player = session.query(Player).filter_by(
                telegram_id=entity.user.id).first()
        elif entity.type == MessageEntityType.MENTION:
            username = text[entity.offset + 1: entity.offset + entity.length]
            player = session.query(Player).filter_by(username=username).first()
        else:
            continue

        if not player:
            await update.message.reply_text(
                f"Player {entity.user.first_name} not found. "
                "Ask them to send /add_me first."
            )
            session.close()
            return

        if not winner_user:
            winner_user = player
        else:
            loser_user = player

    # Step 2: Convert message date to local date
    msg_date_utc = update.message.date
    timezone = pytz.timezone("Asia/Tehran")
    msg_date_local = msg_date_utc.astimezone(timezone).date()

    # Step 4: Save the game record
    game = Game(
        winner_id=winner_user.id, loser_id=loser_user.id, date=msg_date_local)
    session.add(game)
    session.commit()

    await update.message.reply_text(
        # TODO: Add delete button to this message.
        f"Game with ID {game.id} recorded successfully!\n"
        f"Recorded: {winner_user.first_name} won "
        f"against <b>{loser_user.first_name}</b> "
        f"on {msg_date_local}",
        parse_mode="HTML"
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
        await update.message.reply_text(
            "You're already registered as a player!")
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
        await update.message.reply_text("Something went wrong.")
        session.rollback()
    finally:
        session.close()


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()

    # Check if user requested today's ranking
    is_today = False
    if (
        context.args
        and len(context.args) > 0
        and context.args[0].lower() == "today"
    ):
        is_today = True

    players = session.query(Player).all()
    if not players:
        await update.message.reply_text("No players found.")
        session.close()
        return

    players_ranking = []

    for player in players:
        if is_today:
            # Get today's date in Asia/Tehran timezone
            timezone = pytz.timezone("Asia/Tehran")
            today = datetime.now(timezone).date()
            # Filter games played today
            games_won_today = [
                g for g in player.games_won if g.date == today]
            games_lost_today = [
                g for g in player.games_lost if g.date == today]
            total_games = len(games_won_today) + len(games_lost_today)
            score = (
                len(games_won_today) / total_games
                ) * 100 if total_games > 0 else 0
        else:
            games_won = player.games_won or []
            games_lost = player.games_lost or []
            total_games = len(games_won) + len(games_lost)
            score = (
                len(games_won) / total_games
                ) * 100 if total_games > 0 else 0
        players_ranking.append((player, score))

    players_ranking.sort(key=lambda x: x[1], reverse=True)

    if is_today:
        ranking_message = with_emoji(
            ":trophy: <b>Today's Champions Are Here!</b> :sparkles:\n\n")
    else:
        ranking_message = with_emoji(
            ":trophy: <b>All-Time Champions Are Here!</b> :sparkles:\n\n")

    for idx, (player, score) in enumerate(players_ranking, start=1):
        medals = [
            ":1st_place_medal:",
            ":2nd_place_medal:",
            ":3rd_place_medal:",
        ]
        medal = with_emoji(medals[idx-1] if idx <= 3 else ":dart:")
        ranking_message += with_emoji(
            f"{medal} <b>{idx}. {player.first_name}</b> "
            f"— <i>Score (out of 100):</i> {score:.2f}%\n"
        )

    ranking_message += with_emoji(
        "\n\n:rocket: <b>Let's keep the games rolling!</b>")
    await update.message.reply_text(ranking_message, parse_mode="HTML")
    session.close()


# TODO: Register this error handler in the bot factory
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="An error occurred. Please try again later."
    )
