import os
from typing import Optional

class Config:
    # Baza danych
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT"))
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_URL: str = os.getenv("TELEGRAM_WEBHOOK_URL")
    
    # Aplikacja
    ENVIRONMENT: str = os.getenv("ENVIRONMENT")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    DEBUG: bool = os.getenv("DEBUG")
    HOST: str = os.getenv("HOST")
    PORT: int = int(os.getenv("PORT"))

# Instancja konfiguracji
config = Config()

# Redis URLs
broker_url = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"
result_backend = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"
broker_connection_retry_on_startup = True