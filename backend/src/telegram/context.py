import logging
from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import AsyncSessionLocal
from src.storage.service import StorageService

if TYPE_CHECKING:
    from src.users.models import User

logger = logging.getLogger(__name__)

# Context variable to store database session per-request
_db_session: ContextVar[AsyncSession | None] = ContextVar("db_session", default=None)

# Context variable to store storage service per-request
_storage_service: ContextVar[StorageService | None] = ContextVar(
    "storage_service", default=None
)

# Context variable to store current authenticated user per-request
_user: ContextVar[Optional["User"]] = ContextVar("user", default=None)


class SessionContextManager:
    """
    Context manager wrapper for existing AsyncSession from DI.

    This allows us to use an existing session (from FastAPI DI) as a context manager
    without closing it or managing transactions manually in the handler,
    since FastAPI manages the session lifecycle via get_session() yield pattern.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close or commit - FastAPI manages session lifecycle
        # Just pass through any exceptions
        return False


def set_db_session(session: AsyncSession):
    """Set the database session for the current context."""
    _db_session.set(session)


def get_db_session() -> AsyncSession | None:
    """Get the current database session from context."""
    return _db_session.get()


def clear_db_session():
    """Clear the database session from the current context."""
    _db_session.set(None)


def set_storage_service(service: StorageService):
    """Set the storage service for the current context."""
    _storage_service.set(service)


def clear_storage_service():
    """Clear the storage service from the current context."""
    _storage_service.set(None)


def set_user(user: "User"):
    """Set the current user for the context."""
    _user.set(user)


def get_user() -> Optional["User"]:
    """Get the current user from context."""
    return _user.get()


def clear_user():
    """Clear the current user from context."""
    _user.set(None)


def get_or_create_session():
    """
    Get session from context or create a new one as async context manager.

    This is a helper to handle both DI (from FastAPI) and fallback scenarios (tests/background).
    Returns an async context manager that can be used with 'async with'.
    """
    session = _db_session.get()
    if session is not None:
        # Session is provided via DI (FastAPI), use it directly
        return SessionContextManager(session)
    else:
        # Fallback: create new session (for tests or direct calls outside request scope)
        logger.warning(
            "No session in context, creating new session. Ensure this is intended (e.g. tests)."
        )
        return AsyncSessionLocal()


def get_storage_service_for_telegram() -> StorageService:
    """
    Get StorageService from context or create a new one.

    This function provides StorageService for Telegram handlers (outside FastAPI DI).
    It follows the same pattern as get_or_create_session() - uses ContextVar
    for DI when available (e.g., from FastAPI middleware), or creates a new
    instance as fallback (for tests or direct calls).

    Returns:
        StorageService: StorageService instance from context or newly created

    Usage:
        # In Telegram handlers:
        storage_service = get_storage_service_for_telegram()

        # In FastAPI middleware (optional, for consistency):
        storage_service = get_storage_service_for_telegram()
        set_storage_service(storage_service)
    """
    service = _storage_service.get()
    if service is not None:
        # Service is provided via DI (e.g., from FastAPI middleware)
        return service
    else:
        # Fallback: create new instance (for Telegram handlers or tests)
        logger.debug("No storage service in context, creating new instance.")
        return StorageService()
