import os

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