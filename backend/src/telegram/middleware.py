import logging

from src.auth.services import AuthService
from src.common.exceptions import ResourceAlreadyExistsError, UserCreationError
from src.telegram.context import get_db_session, set_user
from src.telegram_messages.services import (
    TelegramLoggingService,
    TelegramMessageService,
)
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def logging_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Middleware to log incoming messages and set user in context.
    This runs before other handlers.
    """
    if not update.effective_user:
        return

    session = get_db_session()
    if not session:
        # This might happen if middleware is called outside of request scope setup
        # But we expect session to be set by TelegramBotService.process_webhook_update
        logger.error("No DB session in logging middleware")
        return

    telegram_id = update.effective_user.id
    auth_service = AuthService(session)

    try:
        # Get or create user
        # This acts as a centralized point for user creation
        # We handle concurrency via DB unique constraints inside AuthService
        user = await auth_service.get_or_create_user_by_telegram_id(telegram_id)

        # Store in ContextVar for downstream handlers
        set_user(user)

        # Log message if it's a message
        if update.message:
            logging_service = TelegramLoggingService(TelegramMessageService(session))
            await logging_service.log_incoming_message(update, user)

    except (ResourceAlreadyExistsError, UserCreationError) as e:
        logger.error(f"Error in logging middleware (user creation): {e}")
    except Exception as e:
        logger.error(f"Unexpected error in logging middleware: {e}", exc_info=True)
