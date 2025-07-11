from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# from src.models import Base

# This creates a SQLite file in the project folder
engine = create_engine("sqlite:///game_bot.db")

# Create tables if they don’t exist
# Base.metadata.create_all(engine)

# Session factory: lets us talk to the DB
SessionLocal = sessionmaker(bind=engine)
