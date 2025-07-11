from db import SessionLocal
from models import Player, Game
import datetime

session = SessionLocal()

# Check if player exists
telegram_id = 123456
player = session.query(Player).filter_by(telegram_id=telegram_id).first()

if not player:
    player = Player(name="Pouria", telegram_id=telegram_id, username="p_forghani")
    session.add(player)
    session.commit()

# Insert a new game
game = Game(winner_id=player.id, loser_id=player.id, date=datetime.date.today())
session.add(game)
session.commit()

print("✅ Game added successfully!")
