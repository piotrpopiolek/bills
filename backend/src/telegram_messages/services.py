from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bills.models import Bill
from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.telegram_messages.models import (
    TelegramMessage,
    TelegramMessageStatus,
    TelegramMessageType,
)
from src.telegram_messages.schemas import TelegramMessageCreate, TelegramMessageUpdate
from src.users.models import User
from telegram import Message, Update


class TelegramMessageService(
    AppService[TelegramMessage, TelegramMessageCreate, TelegramMessageUpdate]
):
    def __init__(self, session: AsyncSession):
        super().__init__(model=TelegramMessage, session=session)

    async def _ensure_unique_telegram_message_id(
        self, telegram_message_id: int, exclude_id: int | None = None
    ) -> None:
        """
        Checks if a telegram_message_id already exists.
        Used to prevent duplicate telegram message IDs.
        """
        stmt = select(TelegramMessage).where(
            TelegramMessage.telegram_message_id == telegram_message_id
        )

        if exclude_id is not None:
            stmt = stmt.where(TelegramMessage.id != exclude_id)

        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise ResourceAlreadyExistsError(
                "TelegramMessage", "telegram_message_id", telegram_message_id
            )

    async def create(self, data: TelegramMessageCreate) -> TelegramMessage:
        # User Existence Check (Referential Integrity check before DB hit)
        await self._ensure_exists(
            model=User, field=User.id, value=data.user_id, resource_name="User"
        )

        # Bill Existence Check (if provided)
        if data.bill_id:
            await self._ensure_exists(
                model=Bill, field=Bill.id, value=data.bill_id, resource_name="Bill"
            )

        # Uniqueness Check (telegram_message_id)
        await self._ensure_unique_telegram_message_id(data.telegram_message_id)

        # Object Construction
        new_message = TelegramMessage(
            telegram_message_id=data.telegram_message_id,
            chat_id=data.chat_id,
            message_type=data.message_type,
            content=data.content,
            status=data.status,
            file_id=data.file_id,
            file_path=data.file_path,
            error_message=data.error_message,
            user_id=data.user_id,
            bill_id=data.bill_id,
        )

        # Persistence (Unit of Work)
        self.session.add(new_message)

        try:
            await self.session.commit()
            await self.session.refresh(new_message)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "telegram_message_id" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "TelegramMessage", "telegram_message_id", data.telegram_message_id
                ) from e
            raise e

        return new_message

    async def update(
        self, message_id: int, data: TelegramMessageUpdate
    ) -> TelegramMessage:
        message = await self.get_by_id(message_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return message

        # User Existence Check (if user_id is being updated)
        if "user_id" in update_data and update_data["user_id"] != message.user_id:
            await self._ensure_exists(
                model=User,
                field=User.id,
                value=update_data["user_id"],
                resource_name="User",
            )

        # Bill Existence Check (if bill_id is being updated)
        if "bill_id" in update_data and update_data["bill_id"] != message.bill_id:
            new_bill_id = update_data["bill_id"]
            if new_bill_id is not None:
                await self._ensure_exists(
                    model=Bill, field=Bill.id, value=new_bill_id, resource_name="Bill"
                )

        # Uniqueness Check (if telegram_message_id is being updated)
        if (
            "telegram_message_id" in update_data
            and update_data["telegram_message_id"] != message.telegram_message_id
        ):
            await self._ensure_unique_telegram_message_id(
                update_data["telegram_message_id"], exclude_id=message.id
            )

        # Apply updates
        for key, value in update_data.items():
            setattr(message, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(message)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "telegram_message_id" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "TelegramMessage",
                    "telegram_message_id",
                    update_data.get("telegram_message_id", message.telegram_message_id),
                ) from e
            raise e

        return message

    async def delete(self, message_id: int) -> None:
        message = await self.get_by_id(message_id)

        self.session.delete(message)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e


class TelegramLoggingService:
    """
    Service for logging incoming and outgoing Telegram messages.
    Uses TelegramMessageService for persistence.
    """

    def __init__(self, message_service: TelegramMessageService):
        self.message_service = message_service

    def _determine_message_type(self, message: Message) -> TelegramMessageType:
        if message.text:
            return TelegramMessageType.TEXT
        elif message.photo:
            return TelegramMessageType.PHOTO
        elif message.document:
            return TelegramMessageType.DOCUMENT
        elif message.voice:
            return TelegramMessageType.VOICE
        elif message.video:
            return TelegramMessageType.VIDEO
        elif message.audio:
            return TelegramMessageType.AUDIO
        elif message.sticker:
            return TelegramMessageType.STICKER
        return TelegramMessageType.TEXT  # Fallback

    def _get_content_and_file_id(
        self, message: Message, msg_type: TelegramMessageType
    ) -> tuple[str, str | None]:
        content = message.text or message.caption or ""
        file_id = None

        if msg_type == TelegramMessageType.PHOTO:
            # Get largest photo
            file_id = message.photo[-1].file_id if message.photo else None
            if not content:
                content = "[Photo]"
        elif msg_type == TelegramMessageType.DOCUMENT:
            file_id = message.document.file_id
            if not content:
                content = f"[Document] {message.document.file_name or ''}"
        elif msg_type == TelegramMessageType.VOICE:
            file_id = message.voice.file_id
            if not content:
                content = "[Voice]"
        elif msg_type == TelegramMessageType.VIDEO:
            file_id = message.video.file_id
            if not content:
                content = "[Video]"
        elif msg_type == TelegramMessageType.AUDIO:
            file_id = message.audio.file_id
            if not content:
                content = f"[Audio] {message.audio.title or ''}"
        elif msg_type == TelegramMessageType.STICKER:
            file_id = message.sticker.file_id
            if not content:
                content = f"[Sticker] {message.sticker.emoji or ''}"

        return content, file_id

    async def log_incoming_message(
        self, update: Update, user: User
    ) -> TelegramMessage | None:
        """
        Log an incoming message from a user.
        """
        if not update.message:
            return None

        message = update.message
        msg_type = self._determine_message_type(message)
        content, file_id = self._get_content_and_file_id(message, msg_type)

        try:
            return await self.message_service.create(
                TelegramMessageCreate(
                    telegram_message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type=msg_type,
                    content=content,
                    status=TelegramMessageStatus.DELIVERED,  # Incoming is considered delivered to us
                    file_id=file_id,
                    user_id=user.id,
                )
            )
        except ResourceAlreadyExistsError:
            # Message already logged (idempotency)
            return None

    async def log_outgoing_message(
        self, message: Message, user_id: int
    ) -> TelegramMessage | None:
        """
        Log an outgoing message from the bot.
        """
        msg_type = self._determine_message_type(message)
        content, file_id = self._get_content_and_file_id(message, msg_type)

        try:
            return await self.message_service.create(
                TelegramMessageCreate(
                    telegram_message_id=message.message_id,
                    chat_id=message.chat_id,
                    message_type=msg_type,
                    content=content,
                    status=TelegramMessageStatus.SENT,
                    file_id=file_id,
                    user_id=user_id,
                )
            )
        except ResourceAlreadyExistsError:
            return None
