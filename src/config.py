import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Config(BaseSettings):
    """Konfiguracja aplikacji dla Railway - z wartościami domyślnymi dla development."""

    # Baza danych - Railway automatycznie ustawia DATABASE_URL
    DATABASE_URL: str = Field(
        default="${{production.DATABASE_URL}}",
        env="${{production.DATABASE_URL}}",
        description="URL połączenia z bazą danych PostgreSQL (Railway)"
    )
    
    # JWT
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        env="JWT_SECRET_KEY",
        description="Sekretny klucz do podpisywania tokenów JWT"
    )
    
    JWT_ALGORITHM: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="Algorytm podpisywania JWT"
    )
    
    # Redis - Railway ustawia te zmienne
    REDIS_HOST: str = Field(
        default="localhost",
        env="REDIS_HOST",
        description="Host serwera Redis (Railway)"
    )
    
    REDIS_PORT: int = Field(
        default=6379,
        env="REDIS_PORT",
        description="Port serwera Redis (Railway)"
    )
    
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        env="REDIS_PASSWORD",
        description="Hasło Redis (Railway)"
    )
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(
        default=None,
        env="TELEGRAM_BOT_TOKEN",
        description="Token bota Telegram"
    )
    
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(
        default=None,
        env="TELEGRAM_WEBHOOK_URL",
        description="URL webhook dla bota Telegram"
    )
    
    # Aplikacja - Railway ustawia PORT
    ENVIRONMENT: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Środowisko uruchomienia aplikacji"
    )
    
    SECRET_KEY: str = Field(
        default="dev-app-secret-key-change-in-production",
        env="SECRET_KEY",
        description="Główny klucz sekretny aplikacji"
    )
    
    DEBUG: bool = Field(
        default=True,
        env="DEBUG",
        description="Tryb debugowania"
    )
    
    HOST: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Host na którym nasłuchuje aplikacja"
    )
    
    PORT: int = Field(
        default=8000,
        env="PORT",  # Railway zawsze ustawia PORT
        description="Port na którym nasłuchuje aplikacja (Railway)"
    )
    
    # ✅ WALIDATORY - konwertują stringi z Railway na odpowiednie typy
    @validator('DEBUG', pre=True)
    def parse_debug(cls, v):
        """Konwertuje string 'true'/'false' na boolean dla Railway"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    @validator('PORT', pre=True)
    def parse_port(cls, v):
        """Konwertuje string na int dla Railway"""
        if isinstance(v, str):
            return int(v)
        return v
    
    @validator('REDIS_PORT', pre=True)
    def parse_redis_port(cls, v):
        """Konwertuje string na int dla Railway"""
        if isinstance(v, str):
            return int(v)
        return v
    
    # ✅ KONFIGURACJA PYDANTIC
    class Config:
        env_file = "process.env"  # Plik .env dla development
        env_file_encoding = "utf-8"
        case_sensitive = False  # Railway używa UPPERCASE
        env_prefix = ""  # Brak prefiksu dla zmiennych Railway

# Instancja konfiguracji
config = Config()

# ✅ FUNKCJA WALIDACJI - sprawdza czy Railway ustawił wymagane zmienne
def validate_railway_config():
    """Sprawdza czy wymagane zmienne Railway są ustawione."""
    required_vars = {
        "DATABASE_URL": config.DATABASE_URL,
        "JWT_SECRET_KEY": config.JWT_SECRET_KEY,
        "PORT": config.PORT,
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    
    if missing_vars:
        print(f"⚠️  Warning: Missing Railway variables: {missing_vars}")
        print("   Using default values for development...")
    else:
        print("✅ Railway configuration validated successfully!")
    
    # Debug info
    print(f"📊 Database URL: {config.DATABASE_URL}")
    print(f"🔐 JWT Secret: {config.JWT_SECRET_KEY[:10]}...")
    print(f"🌍 Environment: {config.ENVIRONMENT}")
    print(f"�� Port: {config.PORT}")

# Redis URLs - z obsługą hasła
if config.REDIS_PASSWORD:
    broker_url = f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/0"
    result_backend = f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/0"
else:
    broker_url = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"
    result_backend = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"

broker_connection_retry_on_startup = True

# ✅ TEST KONFIGURACJI - uruchom: python src/config.py
if __name__ == "__main__":
    print("🔍 Testing Railway configuration...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'Not set')}")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print(f"JWT_SECRET_KEY: {os.getenv('JWT_SECRET_KEY', 'Not set')}")
    
    try:
        validate_railway_config()
        print("✅ Configuration is valid!")
    except Exception as e:
        print(f"❌ Configuration error: {e}")