from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    ENV: str
    PORT: int
    
    # Database (Supabase PostgreSQL)
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Supabase (for auth and storage)
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_STORAGE_BUCKET: str = "bills"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"  # Domyślny model
    OPENAI_TIMEOUT: int = 30  # Timeout w sekundach
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Domyślny model
    GEMINI_TIMEOUT: int = 30  # Timeout w sekundach
    
    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAGIC_LINK_EXPIRE_MINUTES: int = 30
    
    # Frontend
    WEB_APP_URL: str = "bills-ai.up.railway.app"
    
    # Freemium Limits
    MONTHLY_BILLS_LIMIT: int = 100  # Free tier limit per month
    
    # AI Categorization Service
    AI_SIMILARITY_THRESHOLD: float = 0.75  # Threshold dla fuzzy search (zwiększony z 0.6)
    AI_MIN_WORD_LENGTH_STRICT: int = 5  # Dla słów krótszych niż 5, wymagany wyższy threshold
    AI_STRICT_THRESHOLD: float = 0.9  # Threshold dla krótkich słów
    AI_FALLBACK_CATEGORY_NAME: str = "Inne"  # Nazwa kategorii fallback
    AI_CATEGORIZATION_CONFIDENCE_THRESHOLD: float = 0.8  # Minimalna pewność AI (0.0-1.0)
    AI_CATEGORIZATION_TEMPERATURE: float = 0.3  # Temperatura dla Gemini (niższa = bardziej deterministyczne)
    
    # Product Learning Service
    PRODUCT_INDEX_ACCEPTANCE_THRESHOLD: int = 3  # Liczba wymaganych potwierdzeń użytkowników dla utworzenia ProductIndex
    FUZZY_MATCH_GROUPING_THRESHOLD: float = 0.85  # Próg podobieństwa dla grupowania nazw w product_candidates
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore" 
    }

settings = Settings()