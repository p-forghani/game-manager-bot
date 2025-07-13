import datetime

from sqlalchemy import (Column, Date, ForeignKey, Integer, String)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    telegram_id = Column(Integer, unique=True)
    username = Column(String, nullable=True)

    # For easy access to games
    games_won = relationship(
        "Game",
        back_populates="winner",
        foreign_keys='Game.winner_id'
    )
    games_lost = relationship(
        "Game",
        back_populates="loser",
        foreign_keys='Game.loser_id'
    )


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    winner_id = Column(Integer, ForeignKey('players.id'))
    loser_id = Column(Integer, ForeignKey('players.id'))
    # TODO: Remove the default arg from the date
    date = Column(Date, default=datetime.date.today)
    chat_id = Column(Integer, nullable=False)

    # Set up relationships so we can do game.winner or player.games_won
    winner = relationship(
        "Player",
        foreign_keys=[winner_id],
        back_populates="games_won"
    )
    loser = relationship(
        "Player",
        foreign_keys=[loser_id],
        back_populates="games_lost"
    )

# TODO: Add the Chat model
