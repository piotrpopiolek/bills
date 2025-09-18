import os
from typing import Optional

class Config:
    """Konfiguracja aplikacji dla Railway - używamy os.environ.get()"""

    # Baza danych - Railway automatycznie ustawia DATABASE_URL
    @property
    def DATABASE_URL(self) -> str:
        return os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/bills")
    
    # JWT
    @property
    def JWT_SECRET_KEY(self) -> str:
        return os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return os.environ.get("JWT_ALGORITHM", "HS256")
    
    # Redis - Railway ustawia te zmienne
    @property
    def REDIS_HOST(self) -> str:
        return os.environ.get("REDIS_HOST", "localhost")
    
    @property
    def REDIS_PORT(self) -> int:
        port = os.environ.get("REDIS_PORT", "6379")
        return int(port) if port else 6379
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        return os.environ.get("REDIS_PASSWORD")
    
    # Telegram
    @property
    def TELEGRAM_BOT_TOKEN(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_BOT_TOKEN")
    
    @property
    def TELEGRAM_WEBHOOK_URL(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_WEBHOOK_URL")
    
    # Sentry
    @property
    def SENTRY_DSN(self) -> Optional[str]:
        return os.environ.get("SENTRY_DSN")
    
    @property
    def SENTRY_ENVIRONMENT(self) -> str:
        return os.environ.get("SENTRY_ENVIRONMENT", self.ENVIRONMENT)
    
    @property
    def SENTRY_SAMPLE_RATE(self) -> float:
        rate = os.environ.get("SENTRY_SAMPLE_RATE", "1.0")
        return float(rate) if rate else 1.0
    
    # Aplikacja - Railway ustawia PORT
    @property
    def ENVIRONMENT(self) -> str:
        return os.environ.get("ENVIRONMENT", "development")
    
    @property
    def SECRET_KEY(self) -> str:
        return os.environ.get("SECRET_KEY", "dev-app-secret-key-change-in-production")
    
    @property
    def DEBUG(self) -> bool:
        debug = os.environ.get("DEBUG", "true")
        return debug.lower() in ('true', '1', 'yes', 'on')
    
    @property
    def HOST(self) -> str:
        return os.environ.get("HOST", "0.0.0.0")
    
    @property
    def PORT(self) -> int:
        port = os.environ.get("PORT", "8000")
        return int(port) if port else 8000

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