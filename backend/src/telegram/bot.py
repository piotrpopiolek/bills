import logging
from typing import Any

from sqlalchemy import select

from src.telegram.context import get_db_session
from src.telegram_messages.services import (
    TelegramLoggingService,
    TelegramMessageService,
)
from src.users.models import User
from telegram import Message
from telegram.ext import ExtBot

logger = logging.getLogger(__name__)


class LoggingBot(ExtBot):  # Inherit from ExtBot which is used by Application
    """
    Custom Bot class that automatically logs outgoing messages.
    """

    async def _log_message(self, message: Message, chat_id: int):
        """
        Log outgoing message to database using the current session.
        """
        session = get_db_session()
        if not session:
            logger.warning(
                "No DB session found for logging outgoing message. Skipping."
            )
            return

        try:
            # We need to find the internal user_id based on chat_id (which is external_id)
            # This assumes private chat where chat_id == user_id (external_id)
            stmt = select(User).where(User.external_id == chat_id)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    f"User with external_id {chat_id} not found. Cannot log outgoing message."
                )
                return

            service = TelegramLoggingService(TelegramMessageService(session))
            await service.log_outgoing_message(message, user.id)

        except Exception as e:
            logger.error(f"Failed to log outgoing message: {e}", exc_info=True)

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *args: Any,
        **kwargs: Any,
    ) -> Message:
        message = await super().send_message(chat_id, text, *args, **kwargs)

        if isinstance(chat_id, int):
            # Fire and forget logging to avoid blocking?
            # For now, await it to ensure consistency, it's fast DB insert.
            await self._log_message(message, chat_id)
        return message

    async def send_photo(
        self,
        chat_id: int | str,
        photo: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Message:
        message = await super().send_photo(chat_id, photo, *args, **kwargs)
        if isinstance(chat_id, int):
            await self._log_message(message, chat_id)
        return message

    async def send_document(
        self,
        chat_id: int | str,
        document: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Message:
        message = await super().send_document(chat_id, document, *args, **kwargs)
        if isinstance(chat_id, int):
            await self._log_message(message, chat_id)
        return message
