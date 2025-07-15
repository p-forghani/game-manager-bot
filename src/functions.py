from sqlalchemy import func, cast, Float
from src.models import Player, Game


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
