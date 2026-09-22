from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from src.db.main import Base

if TYPE_CHECKING:
    from src.product_indexes.models import ProductIndex
    from src.shops.models import Shop
    from src.users.models import User


class ProductIndexAlias(Base):
    """
    ProductIndexAlias model.
    Maps raw OCR text (e.g., "Mleko 3.2%") to a normalized ProductIndex.
    Acts as the system's learning memory.

    Attributes:
        id: Primary key (auto-incremented)
        raw_name: Raw OCR text (not nullable)
        confirmations_count: Number of times this alias was confirmed as correct (not nullable, server default 0)
        shop_id: Foreign key to shop (nullable, indexed)
        user_id: Foreign key to user (nullable, indexed)
        index_id: Foreign key to product index (not nullable, indexed)
        locale: Locale of the alias (nullable, default 'pl_PL')
        first_seen_at: Timestamp of first seen (nullable, server default now())
        last_seen_at: Timestamp of last seen (nullable, onupdate=now())
        created_at: Timestamp of creation (not nullable, server default now())
        updated_at: Timestamp of last update (not nullable, server default now(), onupdate=now())
        index: Reference to product index (self-referential)
        shop: Reference to shop (back-populates 'product_index_aliases')
        user: Reference to user (back-populates 'product_index_aliases')
    """

    __tablename__ = "product_index_aliases"

    __table_args__ = (
        # GIN indeks z trigram dla szybkiego fuzzy search na raw_name
        # Wymaga w postgresie: CREATE EXTENSION pg_trgm;
        # Uwaga: Dla wyrażeń funkcji (LOWER), definicja operator class musi być w migracji SQL
        # W modelu definiujemy tylko podstawową strukturę indeksu
        Index(
            "idx_product_index_aliases_raw_name",
            text("lower(raw_name)"),
            postgresql_using="gin",
        ),
        Index("idx_product_index_aliases_index_id", "index_id"),
        Index("idx_product_index_aliases_shop_id", "shop_id"),
        Index("idx_product_index_aliases_user_id", "user_id"),
        Index(
            "uq_alias_raw_name_index", text("lower(raw_name)"), "index_id", unique=True
        ),
        {
            "comment": "OCR text variants linked to normalized products with confirmation tracking"
        },
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    confirmations_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Number of times this alias was confirmed as correct",
    )
    shop_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shops.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_indexes.id", ondelete="CASCADE"), nullable=False
    )
    locale: Mapped[str | None] = mapped_column(String(10), default="pl_PL")
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    index: Mapped[ProductIndex] = relationship(
        "ProductIndex", back_populates="product_index_aliases"
    )
    shop: Mapped[Shop | None] = relationship(
        "Shop", back_populates="product_index_aliases"
    )
    user: Mapped[User | None] = relationship(
        "User", back_populates="product_index_aliases"
    )
