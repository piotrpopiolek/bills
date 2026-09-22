from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse


class CategoryValidationMixin:

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            if not v:
                raise ValueError("Category name cannot be empty")
        return v

    @field_validator("parent_id", check_fields=False)
    @classmethod
    def validate_parent_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Parent ID must be a positive integer")
        return v


# --- BASE MODEL ---
class CategoryBase(AppBaseModel, CategoryValidationMixin):

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Category name (required, 1-255 characters, unique)",
    )

    parent_id: int | None = Field(
        None,
        gt=0,
        description="Parent category ID (optional, must be positive, null for root categories)",
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(AppBaseModel, CategoryValidationMixin):

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Category name"
    )

    parent_id: int | None = Field(None, gt=0, description="Parent category ID")


# --- RESPONSES ---
class CategoryResponse(CategoryBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime
    products_count: int = Field(
        0,
        ge=0,
        description="Number of products (ProductIndex) associated with this category",
    )
    bill_items_count: int = Field(
        0, ge=0, description="Number of bill items associated with this category"
    )


class CategoryListResponse(PaginatedResponse[CategoryResponse]):
    pass
