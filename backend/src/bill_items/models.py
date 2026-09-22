from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression, func

from src.db.main import Base

if TYPE_CHECKING:
    from src.bills.models import Bill
    from src.categories.models import Category
    from src.product_indexes.models import ProductIndex


class VerificationSource(StrEnum):
    AUTO = "auto"
    USER = "user"
    ADMIN = "admin"


class BillItem(Base):
    """
    BillItem model representing a single line item on a receipt.

    Attributes:
        id: Primary key (auto-incremented)
        quantity: Quantity of the item (not nullable, positive)
        unit_price: Unit price of the item (not nullable, non-negative)
        total_price: Total price of the item (not nullable, calculated from quantity and unit_price)
        is_verified: Manual verification status (not nullable, default false)
        verification_source: Source of verification (not nullable, default auto)
        bill_id: Foreign key to bill (not nullable, indexed)
        index_id: Foreign key to product index (nullable, indexed)
        original_text: Original OCR text of the item (nullable)
        confidence_score: Confidence score of the OCR (nullable, range 0.00-1.00)
        created_at: Timestamp of creation (not nullable, server default now())
        bill: Reference to bill (self-referential)
        index: Reference to product index (back-populates 'bill_items')
    """

    __tablename__ = "bill_items"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_unit_price_non_negative"),
        Index("idx_bill_items_bill_id", "bill_id"),
        Index("idx_bill_items_index_id", "index_id"),
        Index(
            "idx_bill_items_unverified",
            "is_verified",
            postgresql_where=(expression.column("is_verified").is_(False)),
        ),
        {"comment": "Individual bill items with verification and confidence tracking"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=expression.false(),
        comment="Manual verification status",
    )
    verification_source: Mapped[VerificationSource] = mapped_column(
        SAEnum(
            VerificationSource,
            name="verification_source",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=VerificationSource.AUTO,
        server_default=VerificationSource.AUTO.value,
    )
    bill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    index_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_indexes.id", ondelete="SET NULL"), nullable=True
    )
    original_text: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), comment="OCR confidence score (0.00-1.00)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    bill: Mapped[Bill] = relationship("Bill", back_populates="bill_items")
    index: Mapped[ProductIndex | None] = relationship(
        "ProductIndex", back_populates="bill_items"
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    category: Mapped[Category | None] = relationship(
        "Category", back_populates="bill_items"
    )
