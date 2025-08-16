from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Telegram Message Types
# =============================================================================

class TelegramMessageType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    VOICE = "voice"
    STICKER = "sticker"

class TelegramMessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

# =============================================================================
# Telegram Webhook Schemas
# =============================================================================

class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None

class TelegramChat(BaseModel):
    id: int
    type: str  # private, group, supergroup, channel
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class TelegramPhotoSize(BaseModel):
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None

class TelegramDocument(BaseModel):
    file_id: str
    file_unique_id: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

class TelegramMessageSchema(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = Field(alias="from")
    chat: TelegramChat
    date: int  # Unix timestamp
    text: Optional[str] = None
    photo: Optional[List[TelegramPhotoSize]] = None
    document: Optional[TelegramDocument] = None
    caption: Optional[str] = None

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessageSchema] = None
    edited_message: Optional[TelegramMessageSchema] = None
    callback_query: Optional[Dict[str, Any]] = None

class TelegramWebhook(BaseModel):
    # Telegram webhook to po prostu TelegramUpdate
    update_id: int
    message: Optional[TelegramMessageSchema] = None
    edited_message: Optional[TelegramMessageSchema] = None
    callback_query: Optional[Dict[str, Any]] = None

# =============================================================================
# Telegram API Request Schemas
# =============================================================================

class TelegramTextMessage(BaseModel):
    chat_id: int
    text: str
    parse_mode: Optional[str] = None  # HTML, Markdown
    reply_to_message_id: Optional[int] = None

class TelegramPhotoMessage(BaseModel):
    chat_id: int
    photo: str  # file_id or URL
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    reply_to_message_id: Optional[int] = None

class TelegramDocumentMessage(BaseModel):
    chat_id: int
    document: str  # file_id or URL
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    reply_to_message_id: Optional[int] = None

# =============================================================================
# Internal Application Schemas
# =============================================================================

class TelegramMessageCreate(BaseModel):
    chat_id: int
    message_type: TelegramMessageType
    content: str
    file_id: Optional[str] = None
    user_id: int

class TelegramMessageRead(BaseModel):
    id: int
    telegram_message_id: int
    chat_id: int
    message_type: TelegramMessageType
    content: str
    file_id: Optional[str] = None
    status: TelegramMessageStatus
    created_at: datetime
    user_id: int

class TelegramMessageUpdate(BaseModel):
    status: Optional[TelegramMessageStatus] = None
    error_message: Optional[str] = None

# =============================================================================
# Bill Processing Schemas
# =============================================================================

class BillProcessingRequest(BaseModel):
    chat_id: int
    file_id: str
    user_id: int

class BillProcessingResponse(BaseModel):
    success: bool
    bill_id: Optional[int] = None
    message: str
    error_details: Optional[str] = None

# =============================================================================
# Bot Command Schemas
# =============================================================================

class BotCommand(BaseModel):
    command: str
    description: str

class BotCommandList(BaseModel):
    commands: List[BotCommand] 