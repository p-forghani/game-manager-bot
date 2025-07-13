from sqlalchemy import func, case, cast, Float
from sqlalchemy.orm import aliased
from src.models import Player, Game


def calculate_ranking(session, chat_id, date=None):
    WinGame = aliased(Game)
    LossGame = aliased(Game)

    wins = func.count(WinGame.id)
    losses = func.count(LossGame.id)
    total_games = wins + losses

    win_ratio = case(
        (total_games != 0, cast(wins, Float) / total_games),
        else_=None
    )

    query = session.query(
        Player,
        win_ratio.label("win_ratio")
    )

    if date:
        query = query.outerjoin(
            WinGame,
            (WinGame.winner_id == Player.id) &
            (WinGame.chat_id == chat_id) &
            (WinGame.date == date)
        ).outerjoin(
            LossGame,
            (LossGame.loser_id == Player.id) &
            (LossGame.chat_id == chat_id) &
            (LossGame.date == date)
        )
    else:
        query = query.outerjoin(
            WinGame,
            (WinGame.winner_id == Player.id) &
            (WinGame.chat_id == chat_id)
        ).outerjoin(
            LossGame,
            (LossGame.loser_id == Player.id) &
            (LossGame.chat_id == chat_id)
        )

    query = query.group_by(Player.id)
    return query.all()
