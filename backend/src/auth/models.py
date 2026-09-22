from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.main import Base

if TYPE_CHECKING:
    from src.users.models import User


class MagicLink(Base):
    """
    MagicLink model for passwordless authentication.

    Attributes:
        id: Primary key (auto-incremented)
        token: Unique token for magic link (not nullable, unique, indexed)
        user_id: Foreign key to user (not nullable, indexed)
        expires_at: Token expiration timestamp (not nullable)
        used: Whether the token has been used (not nullable, default false)
        used_at: Timestamp when token was used (nullable)
        redirect_url: URL to redirect after successful authentication (nullable)
        created_at: Timestamp of creation (not nullable, server default now())
        user: Reference to user (back-populates 'magic_links')
    """

    __tablename__ = "magic_links"

    __table_args__ = (
        Index("idx_magic_links_token", "token"),
        Index("idx_magic_links_user_id", "user_id"),
        Index("idx_magic_links_expires_at", "expires_at"),
        {"comment": "Magic link tokens for passwordless authentication"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redirect_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    user: Mapped[User] = relationship("User", back_populates="magic_links")
