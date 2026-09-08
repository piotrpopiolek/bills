import asyncio
import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update, BotCommand, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, TypeHandler, CallbackQueryHandler, filters

from src.config import settings
from src.db.main import AsyncSessionLocal
from src.telegram import handlers
from src.telegram.bot import LoggingBot
from src.telegram.middleware import logging_middleware
from src.telegram.context import set_db_session, clear_db_session, clear_user

logger = logging.getLogger(__name__)


class TelegramBotService:
    """
    Service responsible for the lifecycle of the Telegram Bot application.
    It manages initialization, handler registration, and webhook processing.
    """
    _application: Application | None = None
    _polling_task: asyncio.Task | None = None
    _polling_offset: int | None = None

    @classmethod
    async def get_application(cls) -> Application:
        """
        Get or create the singleton Telegram Application instance.
        """
        if cls._application is None:
            # Initialize custom bot with logging capabilities
            bot = LoggingBot(token=settings.TELEGRAM_BOT_TOKEN)
            
            # .updater(None) is crucial here because we are using webhooks via FastAPI
            # and don't want python-telegram-bot to initialize its own Updater
            # We pass our custom bot instance
            cls._application = Application.builder().bot(bot).updater(None).build()
            
            await cls._register_handlers(cls._application)
            await cls._application.initialize()
            await cls._application.start()
        return cls._application
    
    @classmethod
    async def register_commands(cls):
        """
        Public method to register bot commands.
        Should be called after application is fully initialized.
        """
        if cls._application is None:
            logger.warning("Cannot register commands: application not initialized")
            return
        
        await cls._register_bot_commands(cls._application.bot)

    @classmethod
    def should_use_polling(cls) -> bool:
        """Use long polling locally when no public webhook URL is configured."""
        return not settings.TELEGRAM_WEBHOOK_URL

    @classmethod
    async def start_polling(cls):
        """
        Start long polling for local development.
        Telegram cannot reach localhost via webhook, so we pull updates instead.
        """
        if cls._polling_task and not cls._polling_task.done():
            return

        app = await cls.get_application()
        await app.bot.delete_webhook(drop_pending_updates=False)
        logger.info("Webhook deleted; starting Telegram long polling for local development")
        cls._polling_task = asyncio.create_task(cls._polling_loop())

    @classmethod
    async def _polling_loop(cls):
        app = await cls.get_application()
        while True:
            try:
                updates = await app.bot.get_updates(
                    offset=cls._polling_offset,
                    timeout=30,
                    allowed_updates=Update.ALL_TYPES,
                )
                for update in updates:
                    cls._polling_offset = update.update_id + 1
                    await cls._process_update_with_session(app, update)
            except asyncio.CancelledError:
                logger.info("Telegram polling stopped")
                raise
            except Exception as e:
                logger.error(f"Telegram polling error: {e}", exc_info=True)
                await asyncio.sleep(3)

    @classmethod
    async def _process_update_with_session(cls, app: Application, update: Update):
        async with AsyncSessionLocal() as session:
            set_db_session(session)
            clear_user()
            try:
                await app.process_update(update)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to process update: {e}", exc_info=True)
            finally:
                clear_db_session()
                clear_user()

    @classmethod
    async def shutdown(cls):
        """
        Shutdown the application on server stop.
        """
        if cls._polling_task and not cls._polling_task.done():
            cls._polling_task.cancel()
            try:
                await cls._polling_task
            except asyncio.CancelledError:
                pass
            cls._polling_task = None

        if cls._application:
            await cls._application.stop()
            await cls._application.shutdown()

    @classmethod
    async def _register_bot_commands(cls, bot: Bot):
        """
        Register bot commands for Telegram UI command suggestions.
        
        Most Koncepcyjny (PHP → Python):
        W Symfony/Laravel używałbyś konfiguracji w pliku YAML/JSON do definiowania komend CLI.
        W python-telegram-bot używamy BotCommand i set_my_commands() - idiomatyczne podejście
        do rejestracji komend w Telegram Bot API, które automatycznie wyświetla je jako podpowiedzi
        w interfejsie użytkownika (przycisk menu komend).
        
        Args:
            bot: Bot instance (LoggingBot extends Bot, so this works)
        """
        commands = [
            BotCommand("start", "Rozpocznij pracę z botem"),
            BotCommand("login", "Zaloguj się do aplikacji webowej"),
            BotCommand("dzis", "Raport wydatków za dzisiaj"),
            BotCommand("tydzien", "Raport wydatków za tydzień"),
            BotCommand("miesiac", "Raport wydatków za miesiąc"),
            BotCommand("prywatnosc", "Polityka prywatności"),
            BotCommand("verify", "Weryfikuj pozycje z rachunku"),
        ]
        
        try:
            result = await bot.set_my_commands(commands)
            logger.info(f"Bot commands registered successfully. Result: {result}")
            # Verify commands were set by retrieving them
            registered_commands = await bot.get_my_commands()
            logger.info(f"Verified registered commands: {[cmd.command for cmd in registered_commands]}")
        except Exception as e:
            logger.error(f"Failed to register bot commands: {e}", exc_info=True)
            # Don't fail initialization if command registration fails
            # Commands will still work, just won't show in UI suggestions

    @classmethod
    async def _register_handlers(cls, app: Application):
        """
        Register command and message handlers from the handlers module.
        """
        # Register middleware (group -1 ensures it runs before others)
        app.add_handler(TypeHandler(Update, logging_middleware), group=-1)

        app.add_handler(CommandHandler("start", handlers.start_command))
        app.add_handler(CommandHandler("login", handlers.login_command))
        app.add_handler(CommandHandler("dzis", handlers.daily_report_command))
        app.add_handler(CommandHandler("tydzien", handlers.weekly_report_command))
        app.add_handler(CommandHandler("miesiac", handlers.monthly_report_command))
        app.add_handler(CommandHandler("prywatnosc", handlers.privacy_command))
        app.add_handler(CommandHandler("verify", handlers.verify_command))
        
        # Handle photos (receipts)
        app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handlers.handle_receipt_image))
        
        # Handle verification callbacks (inline keyboard buttons)
        app.add_handler(
            CallbackQueryHandler(
                handlers.handle_item_verification_callback,
                pattern=r"^verify:"
            )
        )
        
        # Handle text messages (for item editing during verification)
        # This handler should run after other message handlers
        # We check in the handler itself if user is in edit mode
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handlers.handle_item_edit_text
            )
        )

    @classmethod
    async def process_webhook_update(
        cls, 
        request: Request, 
        session: AsyncSession,
        secret_token: str | None = None
    ):
        """
        Process incoming webhook update from Telegram.
        
        This method acts as a bridge between FastAPI and python-telegram-bot.
        It injects the database session into the context so handlers can access it.
        
        Args:
            request: FastAPI Request object
            session: Database session injected via FastAPI Depends(get_session)
            secret_token: Optional secret token for webhook validation
        """
        # Set session in context variable so handlers can access it
        set_db_session(session)
        # Clear any previous user context to be safe
        clear_user()
        
        try:
            # Validate secret token if configured
            # (Telegram sends 'X-Telegram-Bot-Api-Secret-Token' header)
            
            body = await request.json()
            app = await cls.get_application()
            
            try:
                update = Update.de_json(body, app.bot)
                if update:
                    await app.process_update(update)
            except Exception as e:
                logger.error(f"Failed to process update: {e}", exc_info=True)
                # We still return 200 to Telegram so it doesn't retry infinitely
        finally:
            # Clear context variable after request to prevent leaks
            clear_db_session()
            clear_user()
