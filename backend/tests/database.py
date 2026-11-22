"""Postgres connections for tests. This module does not import the model client."""

import os

from pgvector.asyncpg import register_vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Local Compose publishes Postgres on 5433. CI sets TEST_DATABASE_URL or DATABASE_URL.
COMPOSE_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/postgres"


def test_database_url() -> str:
    raw = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or COMPOSE_DATABASE_URL
    )
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def create_test_engine() -> AsyncEngine:
    engine = create_async_engine(test_database_url(), pool_pre_ping=True, echo=False)

    def _register_vector(dbapi_connection: object, _connection_record: object) -> None:
        run_async = getattr(dbapi_connection, "run_async", None)
        if run_async is None:
            return
        run_async(register_vector)

    event.listen(engine.sync_engine, "connect", _register_vector)
    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
