from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.main import Base


class ModelCall(Base):
    """One generative or embedding model invocation."""

    __tablename__ = "model_calls"
    __table_args__ = (
        Index(
            "idx_model_calls_user_kind_created", "user_id", "call_kind", "created_at"
        ),
        {"comment": "Logged model calls for cost and daily limits"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    call_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
