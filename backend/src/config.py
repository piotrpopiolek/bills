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
    
    # OpenAI / Gemini (optional when using Ollama locally)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT: int = 30
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT: int = 30

    # LLM providers: gemini | ollama
    OCR_PROVIDER: str = "gemini"
    AI_PROVIDER: str | None = None  # defaults to OCR_PROVIDER when unset
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_VISION_MODEL: str = "llama3.2-vision"
    OLLAMA_TEXT_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT: int = 180
    
    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAGIC_LINK_EXPIRE_MINUTES: int = 30
    
    # Frontend
    WEB_APP_URL: str = "bills-ai.up.railway.app"
    
    # Freemium Limits
    MONTHLY_BILLS_LIMIT: int = 100
    
    # AI Categorization Service
    AI_SIMILARITY_THRESHOLD: float = 0.75
    AI_MIN_WORD_LENGTH_STRICT: int = 5
    AI_STRICT_THRESHOLD: float = 0.9
    AI_FALLBACK_CATEGORY_NAME: str = "Inne"
    AI_CATEGORIZATION_CONFIDENCE_THRESHOLD: float = 0.8
    AI_CATEGORIZATION_TEMPERATURE: float = 0.3
    
    # Product Learning Service
    PRODUCT_INDEX_ACCEPTANCE_THRESHOLD: int = 3
    FUZZY_MATCH_GROUPING_THRESHOLD: float = 0.85
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore" 
    }

settings = Settings()
