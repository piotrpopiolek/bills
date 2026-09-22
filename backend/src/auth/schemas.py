from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse


class MagicLinkValidationMixin:

    @field_validator("user_id", check_fields=False)
    @classmethod
    def validate_user_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("User ID must be a positive integer")
        return v

    @field_validator("token", check_fields=False)
    @classmethod
    def validate_token(cls, v: str | None) -> str | None:
        # Normalize empty strings to None
        return v or None

    @field_validator("redirect_url", check_fields=False)
    @classmethod
    def validate_redirect_url(cls, v: str | None) -> str | None:
        # Normalize empty strings to None
        return v or None


# --- BASE MODEL ---
class MagicLinkBase(AppBaseModel, MagicLinkValidationMixin):
    token: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique magic link token (required, 1-255 characters)",
    )

    user_id: int = Field(..., gt=0, description="User ID (required, must be positive)")

    expires_at: datetime = Field(
        ..., description="Token expiration timestamp (required)"
    )

    used: bool = Field(
        False, description="Whether token has been used (default: false)"
    )

    used_at: datetime | None = Field(
        None, description="Timestamp when token was used (optional)"
    )

    redirect_url: str | None = Field(
        None,
        max_length=512,
        description="URL to redirect after authentication (optional, max 512 characters)",
    )


class MagicLinkCreate(MagicLinkBase):
    """Schema for creating a new MagicLink (internal use)."""

    pass


class MagicLinkUpdate(AppBaseModel, MagicLinkValidationMixin):
    """Schema for updating an existing MagicLink (internal use)."""

    token: str | None = Field(
        None, min_length=1, max_length=255, description="Magic link token"
    )

    user_id: int | None = Field(None, gt=0, description="User ID")

    expires_at: datetime | None = Field(None, description="Token expiration timestamp")

    used: bool | None = Field(None, description="Whether token has been used")

    used_at: datetime | None = Field(None, description="Timestamp when token was used")

    redirect_url: str | None = Field(None, max_length=512, description="Redirect URL")


# --- RESPONSE SCHEMAS (Internal) ---
class MagicLinkInternalResponse(MagicLinkBase):
    """
    Internal response schema for MagicLink entity.
    Returns full database record (for admin/debugging).
    """

    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime


class MagicLinkListResponse(PaginatedResponse[MagicLinkInternalResponse]):
    """Paginated list of magic links (for admin/debugging)."""

    pass


# --- REQUEST SCHEMAS (API Endpoints) ---
class MagicLinkCreateRequest(AppBaseModel):
    """
    Request schema for creating a magic link via API.
    Used by Telegram bot to generate authentication link for user.

    Note: This is different from MagicLinkCreate - this schema accepts telegram_user_id,
    while MagicLinkCreate expects user_id (internal database ID).
    """

    telegram_user_id: int = Field(
        ..., gt=0, description="Telegram user ID (must be positive)"
    )

    redirect_url: str | None = Field(
        None,
        max_length=512,
        description="URL to redirect after successful authentication (optional)",
    )


class TokenVerifyRequest(AppBaseModel):
    """
    Request schema for verifying a magic link token.
    Token is typically passed as query parameter in URL.
    """

    token: str = Field(
        ..., min_length=1, max_length=255, description="Magic link token to verify"
    )


class TokenRefreshRequest(AppBaseModel):
    """
    Request schema for refreshing access token using refresh token.
    """

    refresh_token: str = Field(..., description="Valid refresh token")


# --- RESPONSE SCHEMAS (API Endpoints) ---


class MagicLinkResponse(AppBaseModel):
    """
    Response schema for magic link creation.
    """

    magic_link: str = Field(..., description="Full magic link URL with token")

    expires_at: datetime = Field(..., description="Token expiration timestamp")

    sent_to_telegram: bool = Field(
        default=True,
        description="Whether link was sent to Telegram (always true for now)",
    )


class UserResponse(AppBaseModel):
    """
    Minimal user info returned after authentication.
    """

    id: int = Field(..., gt=0)
    external_id: int = Field(..., description="Telegram user ID")
    is_active: bool
    created_at: datetime


class TokenResponse(AppBaseModel):
    """
    Response schema for successful authentication.
    Returns both access and refresh tokens.
    """

    access_token: str = Field(
        ..., description="Short-lived JWT access token (15 minutes)"
    )

    refresh_token: str = Field(..., description="Long-lived JWT refresh token (7 days)")

    token_type: str = Field(default="bearer")

    user: UserResponse = Field(..., description="Authenticated user information")
