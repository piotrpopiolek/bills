from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/bills"
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_SAMPLE_RATE: float = 0.1
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-app-secret-key-change-in-production"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
config = Settings()

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
    print(f"🌐 Port: {config.PORT}")
    print(f"🚨 Sentry DSN: {'Set' if config.SENTRY_DSN else 'Not set'}")
    print(f"🚨 Sentry Environment: {config.SENTRY_ENVIRONMENT}")

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