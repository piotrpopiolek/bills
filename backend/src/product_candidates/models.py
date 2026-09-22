from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.main import Base

if TYPE_CHECKING:
    from src.categories.models import Category
    from src.product_indexes.models import ProductIndex


class ProductCandidate(Base):
    """
    ProductCandidate model reprezentujący kandydata na produkt.

    Attributes:
        id: Primary key (auto-incremented)
        representative_name: Reprezentatywna nazwa produktu (not nullable)
        user_confirmations: Liczba potwierdzeń użytkowników (default: 0)
        category_id: Foreign key do category (nullable)
        product_index_id: Foreign key do product_index (nullable)
        status: Status kandydata (pending, approved, rejected)
        created_at: Timestamp utworzenia (not nullable, server default now())
        updated_at: Timestamp ostatniej aktualizacji (not nullable, server default now(), onupdate=now())
        category: Referencja do category (relationship)
        product_index: Referencja do product_index (relationship)
    """

    __tablename__ = "product_candidates"

    __table_args__ = (
        Index("idx_product_candidates_category_id", "category_id"),
        Index("idx_product_candidates_product_index_id", "product_index_id"),
        Index("idx_product_candidates_status", "status"),
        {"comment": "Product candidates awaiting approval"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    representative_name: Mapped[str] = mapped_column(Text, nullable=False)
    user_confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    product_index_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_indexes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    category: Mapped[Category | None] = relationship(
        "Category", backref="product_candidates"
    )
    product_index: Mapped[ProductIndex | None] = relationship(
        "ProductIndex", backref="product_candidates"
    )
