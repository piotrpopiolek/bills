import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Konfiguracja aplikacji dla Railway - z wartościami domyślnymi dla development."""
    
    # Baza danych - Railway automatycznie ustawia DATABASE_URL
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/bills",
        env="DATABASE_URL",
        description="URL połączenia z bazą danych PostgreSQL (Railway)"
    )
    
    # JWT
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        env="JWT_SECRET_KEY",
        description="Sekretny klucz do podpisywania tokenów JWT"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="Algorytm podpisywania JWT"
    )
    
    # Redis - Railway ustawia te zmienne
    redis_host: str = Field(
        default="localhost",
        env="REDIS_HOST",
        description="Host serwera Redis (Railway)"
    )
    redis_port: int = Field(
        default=6379,
        env="REDIS_PORT",
        description="Port serwera Redis (Railway)"
    )
    redis_password: Optional[str] = Field(
        default=None,
        env="REDIS_PASSWORD",
        description="Hasło Redis (Railway)"
    )
    
    # Telegram
    telegram_bot_token: Optional[str] = Field(
        default=None,
        env="TELEGRAM_BOT_TOKEN",
        description="Token bota Telegram"
    )
    telegram_webhook_url: Optional[str] = Field(
        default=None,
        env="TELEGRAM_WEBHOOK_URL",
        description="URL webhook dla bota Telegram"
    )
    
    # Aplikacja - Railway ustawia PORT
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Środowisko uruchomienia aplikacji"
    )
    secret_key: str = Field(
        default="dev-app-secret-key-change-in-production",
        env="SECRET_KEY",
        description="Główny klucz sekretny aplikacji"
    )
    debug: bool = Field(
        default=True,
        env="DEBUG",
        description="Tryb debugowania"
    )
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Host na którym nasłuchuje aplikacja"
    )
    port: int = Field(
        default=8000,
        env="PORT",  # Railway zawsze ustawia PORT
        description="Port na którym nasłuchuje aplikacja (Railway)"
    )
    
    @validator('debug', pre=True)
    def parse_debug(cls, v):
        """Konwertuje string 'true'/'false' na boolean dla Railway"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    @validator('port', pre=True)
    def parse_port(cls, v):
        """Konwertuje string na int dla Railway"""
        if isinstance(v, str):
            return int(v)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instancja konfiguracji
settings = Settings()

# Redis URLs - z obsługą hasła
if settings.redis_password:
    broker_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0"
    result_backend = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0"
else:
    broker_url = f"redis://{settings.redis_host}:{settings.redis_port}/0"
    result_backend = f"redis://{settings.redis_host}:{settings.redis_port}/0"

broker_connection_retry_on_startup = True

# Zachowujemy kompatybilność wsteczną dla istniejącego kodu
class Config:
    """Klasa kompatybilności wstecznej - DEPRECATED, użyj settings"""
    DATABASE_URL: str = settings.database_url
    JWT_SECRET_KEY: str = settings.jwt_secret_key
    JWT_ALGORITHM: str = settings.jwt_algorithm
    REDIS_HOST: str = settings.redis_host
    REDIS_PORT: int = settings.redis_port
    TELEGRAM_BOT_TOKEN: Optional[str] = settings.telegram_bot_token
    TELEGRAM_WEBHOOK_URL: Optional[str] = settings.telegram_webhook_url
    ENVIRONMENT: str = settings.environment
    SECRET_KEY: str = settings.secret_key
    DEBUG: bool = settings.debug
    HOST: str = settings.host
    PORT: int = settings.port

# Instancja konfiguracji dla kompatybilności wstecznej
config = Config()