"""ASGI client for e2e/api. Lifespan stays off so Telegram is not started."""

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture
async def api_client(db_engine: AsyncEngine):
    from main import app
    from tests.support import session_factory

    from src.db.main import get_session
    from src.storage.service import get_storage_service

    maker = session_factory(db_engine)

    async def override_get_session():
        async with maker() as session:
            yield session

    def override_storage():
        storage = MagicMock()
        storage.get_signed_url = MagicMock(return_value="http://localhost/signed")
        return storage

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage_service] = override_storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
