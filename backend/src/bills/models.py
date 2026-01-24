from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    Integer, String, DateTime, Text, 
    ForeignKey, Index, CheckConstraint, Numeric, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.main import Base

if TYPE_CHECKING:
    from src.shops.models import Shop
    from src.users.models import User
    from src.bill_items.models import BillItem
    from src.telegram.models import TelegramMessage


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    TO_VERIFY = "to_verify"
    COMPLETED = "completed"
    ERROR = "error"

class Bill(Base):
    """
    Bill model representing a receipt or invoice.
    Central entity of the system.
    """
    __tablename__ = 'bills'
    
    __table_args__ = (
        CheckConstraint('total_amount >= 0', name='check_total_amount_positive'),
        Index('idx_bills_image_expires_at', 'image_expires_at'),
        Index('idx_bills_shop_id', 'shop_id'),
        Index('idx_bills_status', 'status'),
        Index('idx_bills_user_id_bill_date', 'user_id', 'bill_date'),
        {'comment': 'Main bills table with processing status and image lifecycle management'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
 
    status: Mapped[ProcessingStatus] = mapped_column(SAEnum(ProcessingStatus, name='processing_status', create_type=True, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ProcessingStatus.PENDING, server_default=ProcessingStatus.PENDING.value)
    bill_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment='Date extracted from receipt via OCR (set during processing)')
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    shop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('shops.id', ondelete='SET NULL'), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    image_hash: Mapped[Optional[str]] = mapped_column(String(64))
    image_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), comment='Image expiration date for automatic cleanup (6 months retention)')
    image_status: Mapped[Optional[str]] = mapped_column(String(50), server_default="active")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    shop: Mapped[Optional['Shop']] = relationship('Shop', back_populates='bills')
    user: Mapped['User'] = relationship('User', back_populates='bills')
    telegram_messages: Mapped[List['TelegramMessage']] = relationship('TelegramMessage', back_populates='bill')
    bill_items: Mapped[List['BillItem']] = relationship('BillItem', back_populates='bill')