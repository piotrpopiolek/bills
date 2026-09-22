from pydantic import BaseModel, ConfigDict, Field


class AppBaseModel(BaseModel):
    """
    Global base model for the application.
    Centralizes Pydantic configuration (strict mode, stripping, etc.).
    """

    model_config = ConfigDict(
        strict=True,  # No implicit type coercion (ex: "1" != 1)
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        validate_assignment=True,  # Validate values even when setting attributes after creation
        from_attributes=True,  # Enable ORM mode (SQLAlchemy -> Pydantic)
        frozen=False,  # Allow mutation (default)
    )


class PaginatedResponse[T](AppBaseModel):
    """
    Generic wrapper for paginated responses.

    Usage:
        class ShopListResponse(PaginatedResponse[ShopResponse]): pass
    """

    items: list[T] = Field(..., description="List of items for the current page")

    total: int = Field(
        ..., ge=0, description="Total number of items matching the query"
    )

    skip: int = Field(..., ge=0, description="Number of items to skip")

    limit: int = Field(..., ge=5, le=100, description="Max number of items to return")
