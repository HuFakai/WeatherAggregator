import sys
from loguru import logger
from app.core.config import settings
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logger
logger.remove() # Remove default handler
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Get service name from env, default to 'app'
service_name = os.getenv("SERVICE_NAME", "app")
log_file = f"logs/weather.{service_name}.log"

logger.add(
    log_file,
    rotation="00:00", # Rotate daily at midnight
    retention=settings.LOG_RETENTION, # Keep logs for 3 days
    level=settings.LOG_LEVEL,
    encoding="utf-8",
    # compression="zip"  # 不需要打包
)

__all__ = ["logger"]
