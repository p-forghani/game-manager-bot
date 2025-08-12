import logging

# Configure logger
logging.basicConfig(
    filename='logs.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s - Ln: %(lineno)d - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Set httpx logger to WARNING or higher
logging.getLogger('httpx').setLevel(logging.WARNING)

# Mute specific libraries
# logging.getLogger("httpcore").setLevel(logging.WARNING)
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("telegram").setLevel(logging.INFO)
# logging.getLogger("telegram.ext").setLevel(logging.INFO)
