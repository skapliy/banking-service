import logging
from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field

class Settings(BaseSettings):
    """Manages application settings using Pydantic."""
    # Default to SQLite in the current directory for local dev
    database_url: str = Field(default="sqlite:///./bank.db") # Keep only one definition
    # Define allowed origins using a default list
    allowed_origins: List[str] = Field(default=[ # Keep only one definition
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://172.16.173.94:8080"
    ])
    log_level: str = Field(default="INFO")
    # Removed duplicate database_url and allowed_origins definitions from here

    class Config:
        env_file = '.env' # Если вы используете .env файл

settings = Settings()

# Настройка логирования (убедитесь, что она использует settings.log_level)
logging.basicConfig(
    level=settings.log_level.upper(), # Используем уровень из настроек
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # Возможно, у вас есть FileHandler, проверьте и его
        # logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler() # Этот должен выводить в консоль
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Log level set to: {settings.log_level.upper()}")