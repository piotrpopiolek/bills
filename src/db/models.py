import enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, Relationship, SQLModel, Column, DateTime, Numeric, func, JSON
from sqlalchemy import BigInteger, ForeignKey

# --- Enum dla statusu przetwarzania ---

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

# --- Modele Połączone (Tabela i Walidacja) ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: int = Field(
        sa_column=Column("external_id", BigInteger, index=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    is_active: bool = Field(default=True)

    bills: List["Bill"] = Relationship(back_populates="user")
    telegram_messages: List["TelegramMessage"] = Relationship(back_populates="user")

class Shop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    address: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    bills: List["Bill"] = Relationship(back_populates="shop")

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="category.id")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    indexes: List["Index"] = Relationship(back_populates="category")
    parent: Optional["Category"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "Category.id"})
    children: List["Category"] = Relationship(back_populates="parent")

class Index(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    synonyms: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="indexes")
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    bill_items: List["BillItem"] = Relationship(back_populates="index")

class Bill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_date: datetime
    total_amount: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    image_url: Optional[str] = Field(default=None)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="bills")
    
    shop_id: Optional[int] = Field(default=None, foreign_key="shop.id")
    shop: Optional[Shop] = Relationship(back_populates="bills")

    items: List["BillItem"] = Relationship(
        back_populates="bill",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    telegram_messages: List["TelegramMessage"] = Relationship(back_populates="bill")

class BillItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: Decimal = Field(sa_column=Column(Numeric(10, 3)))
    unit_price: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    total_price: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    original_text: Optional[str] = Field(default=None)
    confidence_score: Optional[float] = Field(default=None)  # dla wyników LLM
    
    bill_id: int = Field(foreign_key="bill.id")
    bill: Bill = Relationship(back_populates="items")

    index_id: Optional[int] = Field(default=None, foreign_key="index.id")
    index: Optional[Index] = Relationship(back_populates="bill_items")
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

# =============================================================================
# Telegram Integration Models
# =============================================================================

class TelegramMessageStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class TelegramMessageType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    VOICE = "voice"
    STICKER = "sticker"

class TelegramMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_message_id: int = Field(
        sa_column=Column("telegram_message_id", BigInteger, unique=True, index=True)
    )
    chat_id: int = Field(
        sa_column=Column("chat_id", BigInteger, index=True)
    )
    message_type: TelegramMessageType
    content: str
    file_id: Optional[str] = Field(default=None)
    status: TelegramMessageStatus = Field(default=TelegramMessageStatus.SENT)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    
    user_id: int = Field(foreign_key="user.external_id")
    user: User = Relationship(back_populates="telegram_messages")
    
    # Relacja do rachunku (jeśli wiadomość zawierała zdjęcie rachunku)
    bill_id: Optional[int] = Field(default=None, foreign_key="bill.id")
    bill: Optional[Bill] = Relationship(back_populates="telegram_messages")