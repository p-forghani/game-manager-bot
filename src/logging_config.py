import logging

# Configure logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

# Mute Telegram bot's logging
logging.getLogger("httpx").setLevel(logging.WARNING)
