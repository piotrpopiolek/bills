from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from src.auth.exceptions import InvalidTokenError
from src.config import settings


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token (must include 'sub' - user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        token = create_access_token({"sub": "123"})

    Note:
        Uses timezone-aware datetime (datetime.now(timezone.utc)) instead of deprecated utcnow().
        Token includes 'type': 'access' to distinguish from refresh tokens.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Payload data to encode in the token (must include 'sub' - user_id)

    Returns:
        Encoded JWT refresh token string

    Note:
        Uses timezone-aware datetime (datetime.now(timezone.utc)) instead of deprecated utcnow().
        Token includes 'type': 'refresh' to distinguish from access tokens.
        Expires in REFRESH_TOKEN_EXPIRE_DAYS (default: 7 days).
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string to decode
        expected_type: Expected token type ('access' or 'refresh').
                      If provided, validates that token has correct type.

    Returns:
        Decoded token payload

    Raises:
        InvalidTokenError: If token is invalid, expired, or has wrong type

    Example:
        # Decode any token
        payload = decode_token(token)

        # Decode and validate it's an access token
        payload = decode_token(token, expected_type="access")
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Validate token type if specified
        if expected_type and payload.get("type") != expected_type:
            raise InvalidTokenError()

        return payload
    except JWTError as e:
        raise InvalidTokenError() from e


def get_user_id_from_token(token: str, token_type: str = "access") -> int:
    """
    Extract user_id from JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type (default: "access")

    Returns:
        User ID from token's 'sub' claim

    Raises:
        InvalidTokenError: If token is invalid, wrong type, or doesn't contain 'sub'

    Example:
        # Extract user_id from access token (validates it's an access token)
        user_id = get_user_id_from_token(token)

        # Extract user_id from any token (no type validation)
        user_id = get_user_id_from_token(token, token_type=None)
    """
    payload = decode_token(token, expected_type=token_type)
    user_id: str | None = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return int(user_id)
    except ValueError as e:
        raise InvalidTokenError() from e


def verify_refresh_token(token: str) -> int:
    """
    Verify refresh token and extract user_id.

    This is a convenience function specifically for refresh token flow.
    It validates that the token is indeed a refresh token.

    Args:
        token: JWT refresh token string

    Returns:
        User ID from token's 'sub' claim

    Raises:
        InvalidTokenError: If token is invalid, expired, not a refresh token, or doesn't contain 'sub'

    Example:
        user_id = verify_refresh_token(refresh_token)
    """
    payload = decode_token(token, expected_type="refresh")
    user_id: str | None = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return int(user_id)
    except ValueError as e:
        raise InvalidTokenError() from e
