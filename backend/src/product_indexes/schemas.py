from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse


class ProductIndexValidationMixin:

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            if not v:
                raise ValueError("Product name cannot be empty")
        return v

    @field_validator("category_id", check_fields=False)
    @classmethod
    def validate_category_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Category ID must be a positive integer")
        return v

    @field_validator("synonyms", check_fields=False)
    @classmethod
    def validate_synonyms(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        # JSONB validation - Pydantic will handle dict structure validation
        # We can add custom validation here if needed (e.g., max depth, key constraints)
        return v or None


# --- BASE MODEL ---
class ProductIndexBase(AppBaseModel, ProductIndexValidationMixin):

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Product name (required, 1-255 characters, case-insensitive unique)",
    )

    synonyms: dict[str, Any] | None = Field(
        None, description="JSONB dictionary of product synonyms (optional)"
    )

    category_id: int | None = Field(
        None, gt=0, description="Category ID (optional, must be positive)"
    )


class ProductIndexCreate(ProductIndexBase):
    pass


class ProductIndexUpdate(AppBaseModel, ProductIndexValidationMixin):

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Product name"
    )

    synonyms: dict[str, Any] | None = Field(
        None, description="JSONB dictionary of product synonyms"
    )

    category_id: int | None = Field(None, gt=0, description="Category ID")


# --- RESPONSES ---
class ProductIndexResponse(ProductIndexBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime


class ProductIndexListResponse(PaginatedResponse[ProductIndexResponse]):
    pass
