from datetime import datetime

from src.common.exceptions import AppError


class AuthError(AppError):
    """Base class for all authentication and authorization exceptions."""

    pass


class InvalidTokenError(AuthError):
    """
    Raised when JWT token is invalid, malformed, or has wrong type.

    This exception does NOT cover token expiration (use TokenExpiredError)
    or magic link tokens that were already used (use TokenAlreadyUsedError).

    Used by:
    - jwt.py: decode_token() when token cannot be decoded or has wrong type
    - jwt.py: get_user_id_from_token() when token doesn't contain 'sub' claim
    - jwt.py: verify_refresh_token() when refresh token is invalid
    - services.py: verify_magic_link() when magic link token not found in database
    """

    def __init__(self, detail: str = "Token jest nieprawidłowy."):
        super().__init__(detail)


class TokenExpiredError(AuthError):
    """
    Raised when magic link token has expired.

    Used by:
    - services.py: verify_magic_link() when magic link expires_at < now

    Note: JWT token expiration is handled by PyJWT and raises InvalidTokenError.
    """

    def __init__(self, expires_at: datetime | None = None):
        if expires_at:
            super().__init__(
                f"Token wygasł. Data wygaśnięcia: {expires_at.isoformat()}"
            )
        else:
            super().__init__("Token wygasł.")


class TokenAlreadyUsedError(AuthError):
    """
    Raised when magic link token has already been used.

    Magic links are single-use only for security reasons.

    Used by:
    - services.py: verify_magic_link() when magic_link.used == True
    """

    def __init__(self, used_at: datetime | None = None):
        if used_at:
            super().__init__(
                f"Token został już użyty. Data użycia: {used_at.isoformat()}"
            )
        else:
            super().__init__("Token został już użyty.")


class RefreshTokenError(AuthError):
    """
    Raised when refresh token is invalid or cannot be used to refresh access token.

    This is a more specific exception than InvalidTokenError for refresh token flow.

    Used by:
    - routes.py: refresh_tokens() when refresh token validation fails
    """

    def __init__(self, detail: str = "Refresh token jest nieprawidłowy lub wygasł."):
        super().__init__(detail)


class UserNotFoundError(AuthError):
    """
    Raised when user with given Telegram ID does not exist in database.

    Reserved for lookups by Telegram ID. Login links are not issued over HTTP.
    """

    def __init__(self, telegram_user_id: int):
        super().__init__(
            f"Użytkownik z Telegram ID {telegram_user_id} nie został znaleziony."
        )


class InvalidCredentialsError(AuthError):
    """
    Raised when user provides invalid login credentials.

    Note: Currently not used. Reserved for future password-based authentication.
    TODO: Implement when adding traditional login/password authentication.
    """

    def __init__(self):
        super().__init__("Nieprawidłowe dane uwierzytelniające.")
