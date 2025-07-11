from src.bot import app_factory

if __name__ == "__main__":
    app = app_factory()
    app.run_polling()
