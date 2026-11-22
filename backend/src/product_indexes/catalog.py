from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogHit:
    """One catalog row recovered for a product name."""

    name: str
    category_name: str | None
    similarity: float
