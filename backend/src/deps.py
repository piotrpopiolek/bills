import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError
from src.auth.jwt import get_user_id_from_token
from src.auth.services import AuthService
from src.db.main import get_session
from src.users.models import User

# Logger for this module
logger = logging.getLogger(__name__)

# Security scheme for JWT Bearer tokens
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Dependency to get the current authenticated user from JWT access token.

    This dependency:
    - Validates JWT access token (not refresh token)
    - Checks if user exists in database
    - Verifies user account is active

    Args:
        credentials: HTTP Authorization credentials containing JWT access token
        db: Database session

    Returns:
        Authenticated and active User model

    Raises:
        HTTPException 401: If token is invalid, expired, user not found, or account inactive

    Usage:
        # Using with type alias (recommended)
        @router.get("/profile")
        async def get_profile(user: CurrentUser):
            return {"user_id": user.id}

        # Using with explicit dependency
        @router.get("/profile")
        async def get_profile(user: Annotated[User, Depends(get_current_user)]):
            return {"user_id": user.id}
    """
    try:
        # Extract token from Bearer scheme
        token = credentials.credentials

        # Decode token and get user_id (validates it's an access token, not refresh)
        user_id = get_user_id_from_token(token, token_type="access")

        # Load user from database
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Użytkownik nie znaleziony",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Konto użytkownika jest nieaktywne",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except HTTPException:
        # Re-raise HTTP exceptions (from user checks above)
        raise
    except Exception as e:
        # Log unexpected errors for debugging
        logger.error(f"Unexpected error in get_current_user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Błąd autoryzacji",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_optional)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User | None:
    """
    Optional authentication dependency - returns None if no token provided.

    This is useful for endpoints that work differently for authenticated vs anonymous users,
    but don't require authentication (e.g. public content with personalized features).

    Args:
        credentials: Optional HTTP Authorization credentials
        db: Database session

    Returns:
        User model if authenticated, None if no token provided or invalid token

    Usage:
        @router.get("/posts")
        async def list_posts(user: CurrentUserOptional):
            if user:
                # Show personalized posts
                return get_posts_for_user(user.id)
            else:
                # Show public posts
                return get_public_posts()
    """
    if not credentials:
        return None

    try:
        # Try to authenticate using regular flow
        token = credentials.credentials
        user_id = get_user_id_from_token(token, token_type="access")

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)

        # Return user only if exists and is active
        if user and user.is_active:
            return user
        return None

    except (InvalidTokenError, Exception) as e:
        # Log but don't raise - return None for invalid tokens
        logger.debug(f"Optional authentication failed: {e}")
        return None


# Type aliases for easier use in route handlers
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
