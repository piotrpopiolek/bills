from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression, func

from src.db.main import Base

if TYPE_CHECKING:
    from src.auth.models import MagicLink
    from src.bills.models import Bill
    from src.product_index_aliases.models import ProductIndexAlias
    from src.telegram.models import TelegramMessage


class User(Base):
    """
    User model representing a system user (linked mainly via Telegram).

    Attributes:
        id: Primary key (auto-incremented)
        external_id: External ID (not nullable, unique)
        created_at: Timestamp of creation (not nullable, server default now())
        updated_at: Timestamp of last update (not nullable, server default now(), onupdate=now())
        is_active: User activity status (not nullable, default true)
        bills: List of bills (back-populates 'user')
        product_index_aliases: List of product index aliases (back-populates 'user')
        telegram_messages: List of telegram messages (back-populates 'user')
        magic_links: List of magic links (back-populates 'user')
    """

    __tablename__ = "users"

    __table_args__ = {
        "comment": "User accounts managed by Supabase Auth with Telegram external references"
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        comment="Telegram user ID for external authentication",
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
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=expression.true()
    )
    bills: Mapped[list[Bill]] = relationship("Bill", back_populates="user")
    product_index_aliases: Mapped[list[ProductIndexAlias]] = relationship(
        "ProductIndexAlias", back_populates="user"
    )
    telegram_messages: Mapped[list[TelegramMessage]] = relationship(
        "TelegramMessage", back_populates="user"
    )
    magic_links: Mapped[list[MagicLink]] = relationship(
        "MagicLink", back_populates="user"
    )
