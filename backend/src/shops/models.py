from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.main import Base

if TYPE_CHECKING:
    from src.bills.models import Bill
    from src.product_index_aliases.models import ProductIndexAlias


class Shop(Base):
    """
    Shop model representing a retail location.

    Attributes:
        id: Primary key (auto-incremented)
        name: Name of the shop (not nullable, indexed)
        address: Address of the shop (nullable)
        created_at: Timestamp of creation (not nullable, server default now())
        updated_at: Timestamp of last update (not nullable, server default now(), onupdate=now())
        bills: List of bills (back-populates 'shop')
        product_index_aliases: List of product index aliases (back-populates 'shop')
    """

    __tablename__ = "shops"

    __table_args__ = (
        Index("idx_shops_name", "name"),
        UniqueConstraint("name", "address", name="uq_shops_name_address"),
        {"comment": "Shop information with unique name+address constraints"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    bills: Mapped[list[Bill]] = relationship("Bill", back_populates="shop")
    product_index_aliases: Mapped[list[ProductIndexAlias]] = relationship(
        "ProductIndexAlias", back_populates="shop"
    )
