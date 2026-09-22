from datetime import datetime

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel, PaginatedResponse
from src.telegram_messages.models import TelegramMessageStatus, TelegramMessageType


class TelegramMessageValidationMixin:

    @field_validator("telegram_message_id", check_fields=False)
    @classmethod
    def validate_telegram_message_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Telegram message ID must be a positive integer")
        return v

    @field_validator("chat_id", check_fields=False)
    @classmethod
    def validate_chat_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Chat ID must be a positive integer")
        return v

    @field_validator("content", check_fields=False)
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError("Content cannot be empty or whitespace only")
        return v

    @field_validator("file_id", check_fields=False)
    @classmethod
    def validate_file_id(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 255:
                raise ValueError("File ID cannot exceed 255 characters")
        return v or None

    @field_validator("file_path", check_fields=False)
    @classmethod
    def validate_file_path(cls, v: str | None) -> str | None:
        return v or None

    @field_validator("error_message", check_fields=False)
    @classmethod
    def validate_error_message(cls, v: str | None) -> str | None:
        return v or None

    @field_validator("user_id", check_fields=False)
    @classmethod
    def validate_user_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("User ID must be a positive integer")
        return v

    @field_validator("bill_id", check_fields=False)
    @classmethod
    def validate_bill_id(cls, v: int | None) -> int | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Bill ID must be a positive integer")
        return v


# --- BASE MODEL ---
class TelegramMessageBase(AppBaseModel, TelegramMessageValidationMixin):

    telegram_message_id: int = Field(
        ...,
        gt=0,
        description="Telegram message ID (required, must be positive, unique)",
    )

    chat_id: int = Field(..., gt=0, description="Chat ID (required, must be positive)")

    message_type: TelegramMessageType = Field(
        ..., description="Type of the message (required)"
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Message text or caption (required, cannot be empty)",
    )

    status: TelegramMessageStatus = Field(
        TelegramMessageStatus.SENT, description="Message status (default: sent)"
    )

    file_id: str | None = Field(
        None,
        max_length=255,
        description="Telegram file ID (optional, max 255 characters)",
    )

    file_path: str | None = Field(None, description="File path on server (optional)")

    error_message: str | None = Field(
        None, description="Error message if processing failed (optional)"
    )

    user_id: int = Field(..., gt=0, description="User ID (required, must be positive)")

    bill_id: int | None = Field(
        None,
        gt=0,
        description="Bill ID if message is associated with a bill (optional, must be positive)",
    )


class TelegramMessageCreate(TelegramMessageBase):
    pass


class TelegramMessageUpdate(AppBaseModel, TelegramMessageValidationMixin):

    telegram_message_id: int | None = Field(
        None, gt=0, description="Telegram message ID (typically should not be changed)"
    )

    chat_id: int | None = Field(None, gt=0, description="Chat ID")

    message_type: TelegramMessageType | None = Field(
        None, description="Type of the message"
    )

    content: str | None = Field(
        None, min_length=1, description="Message text or caption"
    )

    status: TelegramMessageStatus | None = Field(None, description="Message status")

    file_id: str | None = Field(None, max_length=255, description="Telegram file ID")

    file_path: str | None = Field(None, description="File path on server")

    error_message: str | None = Field(
        None, description="Error message if processing failed"
    )

    user_id: int | None = Field(None, gt=0, description="User ID")

    bill_id: int | None = Field(
        None, gt=0, description="Bill ID if message is associated with a bill"
    )


# --- RESPONSES ---
class TelegramMessageResponse(TelegramMessageBase):
    id: int = Field(..., gt=0)
    created_at: datetime
    updated_at: datetime


class TelegramMessageListResponse(PaginatedResponse[TelegramMessageResponse]):
    pass
