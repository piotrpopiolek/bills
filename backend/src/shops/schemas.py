from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse
from src.shops.normalization import normalize_shop_address, normalize_shop_name


class ShopValidationMixin:

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """
        Normalizuje nazwę sklepu przed walidacją.

        Transformacje: lowercase, trim, usunięcie cudzysłowów, normalizacja białych znaków.
        """
        if v is not None:
            normalized = normalize_shop_name(v)
            if not normalized:
                raise ValueError("Shop name cannot be empty after normalization")
            return normalized
        return v

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        """
        Normalizuje adres sklepu przed walidacją.

        Transformacje: lowercase, trim, usunięcie przecinków, normalizacja skrótu ul.,
        usunięcie średników (wielokrotne adresy), normalizacja białych znaków.
        """
        if v is not None:
            return normalize_shop_address(v)
        return None


# --- BASE MODEL ---
class ShopBase(AppBaseModel, ShopValidationMixin):

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the shop (required, 1-255 characters)",
    )

    address: str | None = Field(
        None,
        max_length=255,
        description="Address of the shop (optional, max 255 characters)",
    )


class ShopCreate(ShopBase):
    pass


class ShopUpdate(AppBaseModel, ShopValidationMixin):

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Name of the shop"
    )

    address: str | None = Field(None, max_length=255, description="Address of the shop")


# --- RESPONSES ---
class ShopResponse(ShopBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime


class ShopListResponse(PaginatedResponse[ShopResponse]):
    pass
