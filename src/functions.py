import os
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Float, cast, func

from src.logging_config import logger
from src.models import Game, Player
from src.utils import with_emoji



def calculate_ranking(session, chat_id, date=None):
    # Subquery for wins
    win_query = session.query(
        Game.winner_id.label("player_id"),
        func.count(Game.id).label("wins")
    ).filter(Game.chat_id == chat_id)
    if date:
        win_query = win_query.filter(Game.date == date)
    win_query = win_query.group_by(Game.winner_id).subquery()

    # Subquery for losses
    loss_query = session.query(
        Game.loser_id.label("player_id"),
        func.count(Game.id).label("losses")
    ).filter(Game.chat_id == chat_id)
    if date:
        loss_query = loss_query.filter(Game.date == date)
    loss_query = loss_query.group_by(Game.loser_id).subquery()

    # Join Player with wins and losses subqueries
    query = session.query(
        Player,
        (cast(func.coalesce(win_query.c.wins, 0), Float) /
         cast(
             func.nullif(
                 func.coalesce(win_query.c.wins, 0) +
                 func.coalesce(loss_query.c.losses, 0), 0
             ), Float
         )).label("win_ratio")
    ).outerjoin(
        win_query, Player.id == win_query.c.player_id
        ).outerjoin(loss_query, Player.id == loss_query.c.player_id)

    return query.all()


def generate_rankings_text(rankings):
    rankings_text = ""
    for i, (player, win_ratio) in enumerate(rankings, 1):
        if not player:
            continue
        MEDALS = {
            1: ':first_place_medal:',
            2: ':second_place_medal:',
            3: ':third_place_medal:',
        }
        if i in MEDALS:
            rankings_text += f"{MEDALS[i]} "
        if win_ratio is not None:
            rankings_text += f"{i}. {player.first_name} - {win_ratio * 100:.0f}%\n"
        else:
            rankings_text += f"{i}. {player.first_name} - No games played\n"
    return with_emoji(rankings_text)


async def report_developer(context, message):
    """
    Sends a message to the developer (if DEVELOPER_ID is set) for error reporting.

    Args:
        context: The context of the bot.
        message: The message to send to the developer.
    """
    developer_id = os.getenv("DEVELOPER_ID")
    if not developer_id:
        logger.warning("DEVELOPER_ID environment variable is not set.")
        return
    try:
        await context.bot.send_message(
            chat_id=int(developer_id),
            text=message,
            parse_mode="HTML"
        )
    except Exception as notify_err:
        logger.error("Failed to notify developer: %s", notify_err)


def generate_games_history_message(
    session,
    chat_id: int,
    message: str = "",
    game_date: date = datetime.now().date(),
    include_delete_buttons: bool = True,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Create a formatted message and keyboard for displaying games by date with optional delete buttons.

    Args:
        session: SQLAlchemy session
        chat_id: Chat ID to filter games by
        message: Message to prepend to the games list
        game_date: Date to filter games by
        include_delete_buttons: Whether to include delete buttons for each game

    Returns:
        Tuple of (formatted_message, keyboard_markup)
    """
    formatted_message = message
    keyboard = []

    games = session.query(Game).filter(
        Game.date == game_date,
        Game.chat_id == chat_id
    ).all()

    if not games:
        return "", None

    for idx, game in enumerate(games, start=1):
        # Add game to message
        formatted_message += (
            f"{idx}. Game ID <b>{game.id}:</b> "
            f"<b>{game.winner.first_name}</b> won "
            f"<b>{game.loser.first_name}</b>\n"
        )

        # Add delete button if requested
        if include_delete_buttons:
            keyboard.append([InlineKeyboardButton(
                text=with_emoji(f":wastebasket: Delete Game {game.id}"),
                callback_data=f"delete_game_{game.id}"
            )])

    return (
        formatted_message,
        InlineKeyboardMarkup(keyboard) if keyboard else None
    )