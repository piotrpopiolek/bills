from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.main import Base

if TYPE_CHECKING:
    from src.bill_items.models import BillItem
    from src.categories.models import Category
    from src.product_index_aliases.models import ProductIndexAlias


class ProductIndex(Base):
    """
    ProductIndex model representing a normalized product dictionary (Golden Record).
    Optimized for OCR matching (Trigram) and Data Integrity (Case-Insensitive Unique).

    Attributes:
        id: Primary key (auto-incremented)
        name: Product name (unique, indexed) (not nullable)
        synonyms: JSONB dictionary of synonyms (nullable)
        created_at: Timestamp of creation (not nullable, server default now())
        updated_at: Timestamp of last update (not nullable, server default now(), onupdate=now())
        category_id: Foreign key to category (nullable, indexed)
        category: Reference to category (self-referential)
        bill_items: List of bill items (back-populates 'index')
        product_index_aliases: List of product index aliases (back-populates 'index')
    """

    __tablename__ = "product_indexes"

    __table_args__ = (
        # INDEKS TRAGRAMOWY (GIN) DLA NAZWY
        # Pozwala na super szybkie fuzzy search i 'LIKE %text%'
        # Wymaga w postgresie: CREATE EXTENSION pg_trgm;
        Index(
            "idx_product_indexes_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("uq_product_indexes_name_lower", text("lower(name)"), unique=True),
        Index("idx_product_indexes_synonyms", "synonyms", postgresql_using="gin"),
        Index("idx_product_indexes_category_id", "category_id"),
        {"comment": "Normalized product dictionary with fuzzy search capabilities"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    synonyms: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    category: Mapped[Category | None] = relationship(
        "Category", back_populates="product_indexes"
    )
    bill_items: Mapped[list[BillItem]] = relationship(
        "BillItem", back_populates="index"
    )
    product_index_aliases: Mapped[list[ProductIndexAlias]] = relationship(
        "ProductIndexAlias", back_populates="index"
    )
