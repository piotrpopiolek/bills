from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse


class ProductCandidateValidationMixin:
    """Mixin zawierający walidatory dla ProductCandidate."""

    @field_validator("representative_name", check_fields=False)
    @classmethod
    def validate_representative_name(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError("Representative name cannot be empty")
        return v.strip() if v else v

    @field_validator("user_confirmations", check_fields=False)
    @classmethod
    def validate_user_confirmations(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("User confirmations must be non-negative")
        return v

    @field_validator("category_id", check_fields=False)
    @classmethod
    def validate_category_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Category ID must be a positive integer")
        return v

    @field_validator("product_index_id", check_fields=False)
    @classmethod
    def validate_product_index_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Product index ID must be a positive integer")
        return v

    @field_validator("status", check_fields=False)
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None:
            valid_statuses = ["pending", "approved", "rejected"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


# --- BASE MODEL ---
class ProductCandidateBase(AppBaseModel, ProductCandidateValidationMixin):
    """Base model dla ProductCandidate z walidacją."""

    representative_name: str = Field(
        ...,
        min_length=1,
        description="Representative name of the product candidate (required)",
    )

    user_confirmations: int = Field(
        default=0,
        ge=0,
        description="Number of user confirmations (default: 0, must be non-negative)",
    )

    category_id: int | None = Field(
        None, gt=0, description="Category ID (optional, must be positive)"
    )

    product_index_id: int | None = Field(
        None, gt=0, description="Product index ID (optional, must be positive)"
    )

    status: str = Field(
        default="pending",
        description="Status of the product candidate (pending, approved, rejected)",
    )


# --- CREATE/UPDATE SCHEMAS ---
class ProductCandidateCreate(ProductCandidateBase):
    """Schema for creating a new product candidate."""

    pass


class ProductCandidateUpdate(AppBaseModel, ProductCandidateValidationMixin):
    """Schema for updating a product candidate (all fields optional)."""

    representative_name: str | None = Field(
        None, min_length=1, description="Representative name of the product candidate"
    )

    user_confirmations: int | None = Field(
        None, ge=0, description="Number of user confirmations"
    )

    category_id: int | None = Field(None, gt=0, description="Category ID")

    product_index_id: int | None = Field(None, gt=0, description="Product index ID")

    status: str | None = Field(None, description="Status of the product candidate")


# --- RESPONSE SCHEMAS ---
class ProductCandidateResponse(ProductCandidateBase):
    """Schema for product candidate response."""

    id: int = Field(..., gt=0, description="Product candidate ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ProductCandidateListResponse(PaginatedResponse[ProductCandidateResponse]):
    """Schema for paginated list of product candidates."""

    pass
