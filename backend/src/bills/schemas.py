from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator
from src.common.schemas import AppBaseModel, PaginatedResponse
from src.bills.models import ProcessingStatus

class BillValidationMixin:
    
    @field_validator('total_amount', check_fields=False)
    @classmethod
    def validate_total_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < 0:
                raise ValueError("Total amount cannot be negative")
        return v

    @field_validator('user_id', check_fields=False)
    @classmethod
    def validate_user_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v <= 0:
                raise ValueError("User ID must be a positive integer")
        return v

    @field_validator('shop_id', check_fields=False)
    @classmethod
    def validate_shop_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v <= 0:
                raise ValueError("Shop ID must be a positive integer")
        return v

    @field_validator('image_hash', check_fields=False)
    @classmethod
    def validate_image_hash(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) > 64:
                raise ValueError("Image hash cannot exceed 64 characters")
        return v or None

    @field_validator('image_status', check_fields=False)
    @classmethod
    def validate_image_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) > 50:
                raise ValueError("Image status cannot exceed 50 characters")
        return v or None

    @field_validator('error_message', check_fields=False)
    @classmethod
    def validate_error_message(cls, v: Optional[str]) -> Optional[str]:
        return v or None

    @field_validator('image_url', check_fields=False)
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        return v or None

# --- BASE MODEL ---
class BillBase(AppBaseModel, BillValidationMixin):

    status: ProcessingStatus = Field(
        ProcessingStatus.PENDING,
        description="Processing status (default: pending)"
    )
    
    bill_date: Optional[datetime] = Field(
        None,
        description="Bill date extracted from receipt via OCR (optional, set during processing)"
    )
    
    total_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Total amount (optional, must be non-negative, max 12 digits with 2 decimal places)"
    )
    
    user_id: int = Field(
        ...,
        gt=0,
        description="User ID (required, must be positive)"
    )
    
    shop_id: Optional[int] = Field(
        None,
        gt=0,
        description="Shop ID (optional, must be positive)"
    )
    
    image_url: Optional[str] = Field(
        None,
        description="Image URL (optional)"
    )
    
    image_hash: Optional[str] = Field(
        None,
        max_length=64,
        description="Image hash (optional, max 64 characters)"
    )
    
    image_expires_at: Optional[datetime] = Field(
        None,
        description="Image expiration date for automatic cleanup (optional)"
    )
    
    image_status: Optional[str] = Field(
        "active",
        max_length=50,
        description="Image status (optional, default: active, max 50 characters)"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed (optional)"
    )

class BillCreate(BillBase):
    pass

class BillUpdate(AppBaseModel, BillValidationMixin):
    
    status: Optional[ProcessingStatus] = Field(
        None,
        description="Processing status"
    )
    
    bill_date: Optional[datetime] = Field(
        None,
        description="Bill date"
    )
    
    total_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Total amount"
    )
    
    user_id: Optional[int] = Field(
        None,
        gt=0,
        description="User ID"
    )
    
    shop_id: Optional[int] = Field(
        None,
        gt=0,
        description="Shop ID"
    )
    
    image_url: Optional[str] = Field(
        None,
        description="Image URL"
    )
    
    image_hash: Optional[str] = Field(
        None,
        max_length=64,
        description="Image hash"
    )
    
    image_expires_at: Optional[datetime] = Field(
        None,
        description="Image expiration date"
    )
    
    image_status: Optional[str] = Field(
        None,
        max_length=50,
        description="Image status"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )

# --- RESPONSES ---
class BillResponse(BillBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime
    shop_name: Optional[str] = Field(
        None,
        description="Name of the shop associated with this bill (loaded from shop relationship)"
    )
    image_signed_url: Optional[str] = Field(
        None,
        description="Temporary signed URL for accessing the receipt image (valid for 1 hour)"
    )

class BillListResponse(PaginatedResponse[BillResponse]):
    pass

