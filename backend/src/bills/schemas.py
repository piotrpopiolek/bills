from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from src.bills.models import ProcessingStatus
from src.common.schemas import AppBaseModel, PaginatedResponse


class BillValidationMixin:

    @field_validator("total_amount", check_fields=False)
    @classmethod
    def validate_total_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            if v < 0:
                raise ValueError("Total amount cannot be negative")
        return v

    @field_validator("user_id", check_fields=False)
    @classmethod
    def validate_user_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("User ID must be a positive integer")
        return v

    @field_validator("shop_id", check_fields=False)
    @classmethod
    def validate_shop_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Shop ID must be a positive integer")
        return v

    @field_validator("image_hash", check_fields=False)
    @classmethod
    def validate_image_hash(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 64:
                raise ValueError("Image hash cannot exceed 64 characters")
        return v or None

    @field_validator("image_status", check_fields=False)
    @classmethod
    def validate_image_status(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 50:
                raise ValueError("Image status cannot exceed 50 characters")
        return v or None

    @field_validator("error_message", check_fields=False)
    @classmethod
    def validate_error_message(cls, v: str | None) -> str | None:
        return v or None

    @field_validator("image_url", check_fields=False)
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        return v or None


# --- BASE MODEL ---
class BillBase(AppBaseModel, BillValidationMixin):

    status: ProcessingStatus = Field(
        ProcessingStatus.PENDING, description="Processing status (default: pending)"
    )

    bill_date: datetime | None = Field(
        None,
        description="Bill date extracted from receipt via OCR (optional, set during processing)",
    )

    total_amount: Decimal | None = Field(
        None,
        ge=0,
        description="Total amount (optional, must be non-negative, max 12 digits with 2 decimal places)",
    )

    user_id: int = Field(..., gt=0, description="User ID (required, must be positive)")

    shop_id: int | None = Field(
        None, gt=0, description="Shop ID (optional, must be positive)"
    )

    image_url: str | None = Field(None, description="Image URL (optional)")

    image_hash: str | None = Field(
        None, max_length=64, description="Image hash (optional, max 64 characters)"
    )

    image_expires_at: datetime | None = Field(
        None, description="Image expiration date for automatic cleanup (optional)"
    )

    image_status: str | None = Field(
        "active",
        max_length=50,
        description="Image status (optional, default: active, max 50 characters)",
    )

    error_message: str | None = Field(
        None, description="Error message if processing failed (optional)"
    )


class BillCreate(BillBase):
    pass


class BillUpdate(AppBaseModel, BillValidationMixin):

    status: ProcessingStatus | None = Field(None, description="Processing status")

    bill_date: datetime | None = Field(None, description="Bill date")

    total_amount: Decimal | None = Field(None, ge=0, description="Total amount")

    user_id: int | None = Field(None, gt=0, description="User ID")

    shop_id: int | None = Field(None, gt=0, description="Shop ID")

    image_url: str | None = Field(None, description="Image URL")

    image_hash: str | None = Field(None, max_length=64, description="Image hash")

    image_expires_at: datetime | None = Field(None, description="Image expiration date")

    image_status: str | None = Field(None, max_length=50, description="Image status")

    error_message: str | None = Field(
        None, description="Error message if processing failed"
    )


# --- RESPONSES ---
class BillResponse(BillBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime
    shop_name: str | None = Field(
        None,
        description="Name of the shop associated with this bill (loaded from shop relationship)",
    )
    image_signed_url: str | None = Field(
        None,
        description="Temporary signed URL for accessing the receipt image (valid for 1 hour)",
    )


class BillListResponse(PaginatedResponse[BillResponse]):
    pass
