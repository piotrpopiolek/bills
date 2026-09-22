"""
Pytest configuration and shared fixtures for backend tests.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from main import app
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.models import MagicLink  # noqa: F401
from src.bill_items.models import BillItem  # noqa: F401
from src.bills.models import Bill  # noqa: F401
from src.categories.models import Category  # noqa: F401
from src.config import Settings
from src.db.main import Base, get_session
from src.product_index_aliases.models import ProductIndexAlias  # noqa: F401
from src.product_indexes.models import ProductIndex  # noqa: F401
from src.shops.models import Shop  # noqa: F401
from src.telegram_messages.models import TelegramMessage  # noqa: F401

# Import all models to ensure they are registered with Base
# This ensures Base.metadata contains all table definitions
from src.users.models import User  # noqa: F401


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with overridden values."""
    return Settings(
        ENV="test",
        PORT=8000,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_db",
        JWT_SECRET_KEY="test-secret-key-for-testing-only",
        JWT_ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        MAGIC_LINK_EXPIRE_MINUTES=30,
        TELEGRAM_BOT_TOKEN="test-token",
        OPENAI_API_KEY="test-openai-key",
        WEB_APP_URL="http://localhost:4321",
        MONTHLY_BILLS_LIMIT=100,
    )


def _convert_jsonb_to_json_for_sqlite(metadata):
    """
    Convert all JSONB columns to JSON for SQLite compatibility.
    SQLite doesn't support JSONB, so we need to convert it to JSON.
    """
    for table in metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession]:
    """
    Create a test database session with in-memory SQLite database.
    Uses StaticPool for synchronous access in async context.
    Converts JSONB to JSON for SQLite compatibility.
    """
    # Convert JSONB to JSON for SQLite compatibility
    _convert_jsonb_to_json_for_sqlite(Base.metadata)

    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    Create a test client for FastAPI application.
    Overrides database dependency with test session.
    """

    async def override_get_session():
        yield test_db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_telegram_service(monkeypatch: pytest.MonkeyPatch):
    """Mock TelegramBotService to avoid actual Telegram API calls."""
    mock_service = MagicMock()
    mock_application = AsyncMock()
    mock_service.get_application = AsyncMock(return_value=mock_application)
    mock_service.shutdown = AsyncMock()

    monkeypatch.setattr("src.telegram.services.TelegramBotService", mock_service)
    return mock_service


@pytest.fixture
def mock_openai_client(monkeypatch: pytest.MonkeyPatch):
    """Mock OpenAI client for testing."""
    mock_client = AsyncMock()
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_client)
    return mock_client


@pytest.fixture
def mock_supabase_client(monkeypatch: pytest.MonkeyPatch):
    """Mock Supabase client for testing."""
    mock_client = MagicMock()
    monkeypatch.setattr("supabase.create_client", lambda **kwargs: mock_client)
    return mock_client
