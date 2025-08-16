# Game Manager Bot 🎮

A comprehensive Telegram bot designed to manage competitive games, track player scores, and maintain rankings within group chats. Perfect for gaming communities, office competitions, or any group activity where you want to keep track of wins and losses.

## Features ✨

- **Player Registration**: Easy player registration system with `/add_me` command
- **Game Recording**: Record single or multiple games with `/played` command
- **Score Tracking**: Automatic win/loss tracking and statistics
- **Rankings System**: View all-time, daily, or custom date rankings
- **Game History**: View games played on specific dates
- **Interactive Menus**: User-friendly inline keyboard menus
- **Game Deletion**: Delete incorrectly recorded games
- **Multi-Chat Support**: Isolated game tracking per chat/group
- **Timezone Support**: Asia/Tehran timezone for accurate date handling
- **Error Handling**: Comprehensive error handling with developer notifications
- **Database Migrations**: Alembic-powered database schema management

## Bot Commands 🤖

### Basic Commands
- `/start` - Welcome message and introduction to the bot
- `/help` - Display comprehensive help information
- `/menu` - Show interactive main menu with all options

### Player Management
- `/add_me` - Register yourself as a player (required before recording games)

### Game Management
- `/played @winner @loser [date=YYYY-MM-DD]` - Record a game
  - Example: `/played @alice @bob`
  - Example: `/played @alice @bob date=2024-01-15`
  - Can record multiple games: `/played @alice @bob @charlie @dave`
- `/games [date=YYYY-MM-DD]` - View games history
  - Example: `/games` (today's games)
  - Example: `/games date=2024-01-15`
- `/delete_game <id>` - Delete a specific game by ID

### Rankings
- `/rank` - View all-time rankings
- `/rank today` - View today's rankings  
- `/rank YYYY-MM-DD` - View rankings for specific date

### Development/Testing
- `/test` - Developer test command (if available)

## Prerequisites 📋

- Python 3.10 or higher
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- SQLite (included with Python) or PostgreSQL (for production)

## Configuration ⚙️

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required
BOT_TOKEN=your-telegram-bot-token-here

# Optional
DEVELOPER_ID=123456789  # Your Telegram ID for error notifications
DATABASE_URL=sqlite:///game_bot.db  # Database connection string
```

### Getting Your Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Choose a name and username for your bot
4. Copy the provided token to your `.env` file

### Getting Your Telegram ID (Optional)

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your numeric ID to the `DEVELOPER_ID` field in `.env`

## Installation & Setup 🚀

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd game-manager-bot
   ```

2. **Create a virtual environment (Python 3.10+)**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env  # If available, or create manually
   # Edit .env with your bot token and other settings
   ```

6. **Initialize the database**
   ```bash
   alembic upgrade head
   ```

7. **Run the bot**
   ```bash
   python run.py
   ```

## Development Setup 🛠️

### Development Mode with Auto-Reload

For development, you can use the auto-reload script:

```bash
python dev_runner.py
```

This will:
- Watch for file changes in the `src/` directory
- Automatically restart the bot when changes are detected
- Provide immediate feedback during development

### Database Migrations

The project uses Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade to previous version
alembic downgrade -1

# View migration history
alembic history
```

## Project Structure 📁

```
game-manager-bot/
├── src/                          # Source code directory
│   ├── handlers/                 # Telegram command and callback handlers
│   │   ├── commands.py          # Command handlers (/start, /played, etc.)
│   │   └── callbacks.py         # Callback query handlers (buttons)
│   ├── bot.py                   # Main bot application factory
│   ├── models.py                # SQLAlchemy database models
│   ├── db.py                    # Database configuration and session
│   ├── functions.py             # Core business logic functions
│   ├── templates.py             # Message templates
│   ├── constants.py             # Application constants
│   ├── decorators.py            # Custom decorators
│   ├── utils.py                 # Utility functions
│   └── logging_config.py        # Logging configuration
├── migrations/                   # Alembic database migrations
│   ├── versions/                # Migration version files
│   └── env.py                   # Alembic environment configuration
├── run.py                       # Production entry point
├── dev_runner.py               # Development entry point with auto-reload
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── test_scenarios.md           # Comprehensive test scenarios
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## Architecture Overview 🏗️

### Core Components

1. **Bot Application (`src/bot.py`)**
   - Factory function for creating the Telegram bot application
   - Registers all command and callback handlers
   - Sets up conversation handlers for complex interactions

2. **Database Layer (`src/models.py`, `src/db.py`)**
   - SQLAlchemy ORM models for Players and Games
   - Database session management
   - Support for SQLite (development) and PostgreSQL (production)

3. **Handlers (`src/handlers/`)**
   - **Commands**: Handle slash commands from users
   - **Callbacks**: Handle inline keyboard button presses
   - Clean separation of concerns for maintainability

4. **Business Logic (`src/functions.py`)**
   - Core game management functions
   - Ranking calculations
   - Game history generation

5. **Templates (`src/templates.py`)**
   - Centralized message templates
   - Consistent messaging across the application

### Key Features

- **Multi-Chat Support**: Games are isolated by chat ID
- **Soft Deletion**: Games are marked as deleted rather than removed
- **Timezone Awareness**: All dates use Asia/Tehran timezone
- **Error Handling**: Comprehensive error handling with developer notifications
- **Database Migrations**: Version-controlled schema changes with Alembic

## Deployment 🚀

### Production Deployment

#### 1. Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+ and pip
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install PostgreSQL (recommended for production)
sudo apt install postgresql postgresql-contrib -y
```

#### 2. Database Setup (PostgreSQL)

```bash
# Switch to postgres user and create database
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE gamebot;
CREATE USER gamebot_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE gamebot TO gamebot_user;
\q
```

#### 3. Application Deployment

```bash
# Clone and setup application
git clone <repo-url> /opt/game-manager-bot
cd /opt/game-manager-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create production environment file
sudo nano .env
```

Add to `.env`:
```env
BOT_TOKEN=your_production_bot_token_here
DEVELOPER_ID=your_telegram_id
DATABASE_URL=postgresql://gamebot_user:secure_password_here@localhost/gamebot
```

```bash
# Run database migrations
alembic upgrade head

# Test the bot
python run.py
```

#### 4. Systemd Service Setup

Create systemd service file:

```bash
sudo nano /etc/systemd/system/gamebot.service
```

Add the following content:

```ini
[Unit]
Description=Game Manager Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/game-manager-bot
Environment=PATH=/opt/game-manager-bot/venv/bin
ExecStart=/opt/game-manager-bot/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable gamebot

# Start the service
sudo systemctl start gamebot

# Check status
sudo systemctl status gamebot

# View logs
sudo journalctl -u gamebot -f
```

#### 5. Updating the Bot

```bash
# Navigate to bot directory
cd /opt/game-manager-bot

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies if needed
pip install -r requirements.txt

# Run any pending migrations
alembic upgrade head

# Restart the service
sudo systemctl restart gamebot
```

### Docker Deployment (Alternative)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DEVELOPER_ID=${DEVELOPER_ID}
      - DATABASE_URL=postgresql://gamebot:password@db:5432/gamebot
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=gamebot
      - POSTGRES_USER=gamebot
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

Deploy with Docker:

```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# View logs
docker-compose logs -f bot
```

## Troubleshooting 🔧

### Common Issues

#### Bot Not Responding
1. **Check bot token**: Ensure your `BOT_TOKEN` in `.env` is correct
2. **Check logs**: 
   ```bash
   # For systemd service
   sudo journalctl -u gamebot -f
   
   # For direct execution
   python run.py
   ```
3. **Verify bot permissions**: Ensure the bot can send messages in the target group

#### Database Connection Issues
1. **SQLite**: Check if `game_bot.db` file exists and is writable
2. **PostgreSQL**: Verify connection string and database credentials
3. **Migrations**: Run `alembic upgrade head` to ensure database schema is up to date

#### Permission Errors
1. **File permissions**: Ensure the bot has read/write access to its directory
2. **Database permissions**: Check SQLite file permissions or PostgreSQL user privileges

#### Memory/Performance Issues
1. **Check system resources**: Monitor CPU and memory usage
2. **Database optimization**: Consider indexing for large datasets
3. **Logs**: Check for memory leaks in application logs

### Debugging

#### Enable Debug Logging
Edit `src/logging_config.py` to set log level to `DEBUG`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    # ... rest of configuration
)
```

#### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "BOT_TOKEN environment variable is not set" | Missing or invalid `.env` file | Create `.env` with valid `BOT_TOKEN` |
| "Player not found" | User hasn't registered | Ask user to send `/add_me` first |
| "Invalid date format" | Wrong date format in command | Use `YYYY-MM-DD` format |
| "Database connection failed" | Database not accessible | Check database service and credentials |

### FAQ ❓

**Q: Can I use this bot in multiple groups?**
A: Yes! The bot supports multiple groups with isolated game tracking per group.

**Q: What happens if I accidentally record a wrong game?**
A: Use the delete button in the success message or `/delete_game <id>` command.

**Q: Can I change the timezone?**
A: The bot uses Asia/Tehran timezone by default. To change it, modify the timezone settings in the source code.

**Q: How do I backup my data?**
A: For SQLite: Copy the `game_bot.db` file. For PostgreSQL: Use `pg_dump` to create backups.

**Q: Can I migrate from SQLite to PostgreSQL?**
A: Yes, but you'll need to export data from SQLite and import it into PostgreSQL manually.

**Q: Is there a limit to the number of games I can record?**
A: No technical limit, but performance may degrade with very large datasets.

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 guidelines
- Add tests for new features
- Update documentation for any changes
- Ensure all tests pass before submitting PR

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support 💬

- **Documentation**: Check this README and `test_scenarios.md`
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Developer**: [Pouria Forghani](http://www.pouria.site/)

## Acknowledgments 🙏

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/)
- Migrations powered by [Alembic](https://alembic.sqlalchemy.org/)

---

**Made with ❤️ for gaming communities everywhere!**