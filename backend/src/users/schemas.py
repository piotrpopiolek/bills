from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse


class UserValidationMixin:

    @field_validator("external_id", check_fields=False)
    @classmethod
    def validate_external_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("External ID must be a positive integer")
        return v

    @field_validator("is_active", check_fields=False)
    @classmethod
    def validate_is_active(cls, v: bool | None) -> bool | None:
        # Boolean validation is handled by Pydantic, but we can add custom logic if needed
        return v


# --- BASE MODEL ---
class UserBase(AppBaseModel, UserValidationMixin):

    external_id: int = Field(
        ...,
        gt=0,
        description="Telegram user ID for external authentication (required, must be positive)",
    )

    is_active: bool = Field(True, description="User activity status (default: true)")


class UserCreate(UserBase):
    pass


class UserUpdate(AppBaseModel, UserValidationMixin):

    external_id: int | None = Field(
        None, gt=0, description="Telegram user ID (typically should not be changed)"
    )

    is_active: bool | None = Field(None, description="User activity status")


# --- RESPONSES ---
class UserResponse(UserBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime


class UserListResponse(PaginatedResponse[UserResponse]):
    pass


# --- USAGE STATISTICS ---
class UsageStats(AppBaseModel):
    """
    Usage statistics for freemium model tracking.
    """

    bills_this_month: int = Field(
        ..., ge=0, description="Number of bills processed in current month"
    )

    monthly_limit: int = Field(
        ..., gt=0, description="Monthly limit for bills (100 for free tier)"
    )

    remaining_bills: int = Field(
        ..., ge=0, description="Remaining bills available this month"
    )


class UserWithUsageResponse(UserResponse):
    """
    User profile with usage statistics.
    Used by GET /users/me endpoint.
    """

    usage: UsageStats = Field(..., description="Usage statistics for freemium model")
