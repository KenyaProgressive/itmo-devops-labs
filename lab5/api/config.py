import os

from dotenv import load_dotenv

load_dotenv(".env")

HEALTH_FAIL: bool = os.getenv("HEALTH_FAIL", "false").lower() == "true"
POSTGRES_URL: str = (
    f"{os.getenv("POSTGRES_DRIVER")}://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@{os.getenv("POSTGRES_HOST")}:{os.getenv("POSTGRES_PORT")}/{os.getenv("POSTGRES_DB")}"
)
LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
