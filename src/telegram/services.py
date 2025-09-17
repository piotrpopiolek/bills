from typing import List, Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import func
import httpx
import logging

from src.db.models import TelegramMessage, User, TelegramMessageStatus
from src.telegram.schemas import TelegramWebhook, BotCommandList
from src.config import config

logger = logging.getLogger(__name__)

# =============================================================================
# Telegram Message Services
# =============================================================================

async def get_telegram_message(session: AsyncSession, message_id: int) -> Optional[TelegramMessage]:
    """Pobiera jedną wiadomość Telegram po jej ID."""
    return await session.get(TelegramMessage, message_id)

async def get_telegram_messages(
    session: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    chat_id: Optional[int] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None
) -> List[TelegramMessage]:
    """Pobiera listę wiadomości Telegram z filtrami i paginacją."""
    statement = select(TelegramMessage)
    
    if chat_id:
        statement = statement.where(TelegramMessage.chat_id == chat_id)
    
    if message_type:
        statement = statement.where(TelegramMessage.message_type == message_type)
        
    if status:
        statement = statement.where(TelegramMessage.status == status)
    
    statement = statement.order_by(TelegramMessage.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(statement)
    return result.scalars().all()

async def count_telegram_messages(
    session: AsyncSession,
    chat_id: Optional[int] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None
) -> int:
    """Liczy wiadomości z opcjonalnymi filtrami."""
    statement = select(func.count(TelegramMessage.id))
    
    if chat_id:
        statement = statement.where(TelegramMessage.chat_id == chat_id)
    
    if message_type:
        statement = statement.where(TelegramMessage.message_type == message_type)
        
    if status:
        statement = statement.where(TelegramMessage.status == status)
    
    result = await session.execute(statement)
    return result.scalar()

async def search_telegram_messages(
    session: AsyncSession,
    query: str,
    skip: int = 0,
    limit: int = 100
) -> List[TelegramMessage]:
    """Wyszukuje wiadomości po treści."""
    search_query = f"%{query}%"
    statement = select(TelegramMessage).where(TelegramMessage.content.ilike(search_query))
    statement = statement.order_by(TelegramMessage.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(statement)
    return result.scalars().all()

async def count_search_results(session: AsyncSession, query: str) -> int:
    """Liczy wyniki wyszukiwania."""
    search_query = f"%{query}%"
    statement = select(func.count(TelegramMessage.id)).where(TelegramMessage.content.ilike(search_query))
    result = await session.execute(statement)
    return result.scalar()

async def get_telegram_messages_stats(session: AsyncSession) -> Dict[str, Any]:
    """Pobiera statystyki wiadomości."""
    # Liczba wszystkich wiadomości
    total_result = await session.execute(select(func.count(TelegramMessage.id)))
    total_messages = total_result.scalar()
    
    # Liczba wiadomości według typu
    type_stats_result = await session.execute(
        select(TelegramMessage.message_type, func.count(TelegramMessage.id))
        .group_by(TelegramMessage.message_type)
    )
    type_stats = dict(type_stats_result.all())
    
    # Liczba wiadomości według statusu
    status_stats_result = await session.execute(
        select(TelegramMessage.status, func.count(TelegramMessage.id))
        .group_by(TelegramMessage.status)
    )
    status_stats = dict(status_stats_result.all())
    
    # Liczba unikalnych użytkowników
    unique_users_result = await session.execute(
        select(func.count(func.distinct(TelegramMessage.chat_id)))
    )
    unique_users = unique_users_result.scalar()
    
    # Ostatnia aktywność
    last_activity_result = await session.execute(
        select(func.max(TelegramMessage.created_at))
    )
    last_activity = last_activity_result.scalar()
    
    return {
        "total_messages": total_messages,
        "unique_users": unique_users,
        "last_activity": last_activity,
        "by_type": type_stats,
        "by_status": status_stats
    }

# =============================================================================
# Telegram Bot Services
# =============================================================================

async def send_text_message(chat_id: int, text: str) -> bool:
    """Wysyła wiadomość tekstową przez Telegram Bot API."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Message sent successfully to chat {chat_id}")
                    return True
                else:
                    logger.error(f"Failed to send message: {result}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending text message: {str(e)}")
        return False

async def set_webhook(webhook_url: str) -> bool:
    """Ustawia webhook dla bota."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {"url": webhook_url}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Webhook set successfully to {webhook_url}")
                    return True
                else:
                    logger.error(f"Failed to set webhook: {result}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return False

async def set_commands(commands: List[Dict[str, str]]) -> bool:
    """Ustawia komendy bota."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
        payload = {"commands": commands}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info("Bot commands set successfully")
                    return True
                else:
                    logger.error(f"Failed to set commands: {result}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error setting commands: {str(e)}")
        return False

async def get_bot_info() -> Optional[Dict[str, Any]]:
    """Pobiera informacje o bocie."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return None
        
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result["result"]
                else:
                    logger.error(f"Failed to get bot info: {result}")
                    return None
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting bot info: {str(e)}")
        return None

async def get_file_path(file_id: str) -> Optional[str]:
    """Pobiera file_path dla danego file_id z Telegram Bot API."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return None
        
        url = f"https://api.telegram.org/bot{bot_token}/getFile"
        payload = {"file_id": file_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result["result"]["file_path"]
                else:
                    logger.error(f"Failed to get file path: {result}")
                    return None
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting file path: {str(e)}")
        return None

async def download_file(file_path: str, local_path: str) -> bool:
    """Pobiera plik z Telegram i zapisuje lokalnie."""
    try:
        bot_token = config.TELEGRAM_BOT_TOKEN
        if not bot_token or bot_token == "your-bot-token":
            logger.error("Bot token not configured")
            return False
        
        url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                # Utwórz katalog jeśli nie istnieje
                import os
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Zapisz plik
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"File downloaded successfully: {local_path}")
                return True
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False

# =============================================================================
# Telegram Webhook Processing Services
# =============================================================================


async def process_webhook(session: AsyncSession, webhook_data: TelegramWebhook) -> bool:
    """Przetwarza webhook z Telegram."""
    try:
        if webhook_data.message:
            await _process_message(session, webhook_data.message)
        elif webhook_data.edited_message:
            await _process_message(session, webhook_data.edited_message)
        elif webhook_data.callback_query:
            await _process_callback_query(session, webhook_data.callback_query)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return False

async def _process_message(session: AsyncSession, message) -> None:
    """Przetwarza pojedynczą wiadomość."""
    try:
        # Znajdź lub stwórz użytkownika
        user = await _find_or_create_user(session, message.chat.id)
        
        # Określ typ wiadomości i file_id
        message_type = 'TEXT'
        file_id = None
        file_path = None
        content = message.text or message.caption or ''
        
        # Sprawdź czy to zdjęcie
        if message.photo:
            message_type = 'PHOTO'
            # Wybierz największe zdjęcie (ostatnie w tablicy)
            file_id = message.photo[-1].file_id
            content = message.caption or 'Zdjęcie rachunku'
        elif message.document:
            message_type = 'DOCUMENT'
            file_id = message.document.file_id
            content = message.caption or 'Dokument'
        
        # Zapisz wiadomość do bazy
        telegram_message = TelegramMessage(
            telegram_message_id=message.message_id,
            chat_id=message.chat.id,
            message_type=message_type,
            content=content,
            file_id=file_id,
            file_path=file_path,  # Będzie ustawione po pobraniu pliku
            status=TelegramMessageStatus.SENT,
            user_id=user.external_id
        )
        
        session.add(telegram_message)
        await session.commit()
        await session.refresh(telegram_message)
        
        # Przetwórz wiadomość w zależności od typu
        if message.text:
            await _process_text_message(message.chat.id, message.text)
        elif message.photo:
            await _process_photo_message(session, telegram_message, file_id, message.caption)
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await session.rollback()

async def _process_callback_query(session: AsyncSession, callback_query) -> None:
    """Przetwarza callback query."""
    try:
        logger.info(f"Callback query received: {callback_query}")
    except Exception as e:
        logger.error(f"Error processing callback query: {str(e)}")

async def _find_or_create_user(session: AsyncSession, chat_id: int) -> User:
    """Znajduje lub tworzy użytkownika na podstawie chat_id."""
    # Sprawdź czy użytkownik już istnieje
    statement = select(User).where(User.external_id == chat_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if user:
        return user
    
    # Stwórz nowego użytkownika
    user = User(
        external_id=chat_id,
        is_active=True
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return user

async def _process_text_message(chat_id: int, text: str) -> None:
    """Przetwarza wiadomość tekstową."""
    try:
        text_lower = text.lower().strip()
        
        if text_lower == '/start':
            await _send_welcome_message(chat_id)
        elif text_lower == '/help':
            await _send_help_message(chat_id)
        else:
            await _send_generic_response(chat_id, text)
            
    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        await _send_error_message(chat_id)


# =============================================================================
# Message Response Services
# =============================================================================

async def _send_welcome_message(chat_id: int) -> None:
    """Wysyła wiadomość powitalną."""
    welcome_text = """
🎉 <b>Witaj w systemie Bills!</b>

Jestem botem, który pomoże Ci przetwarzać rachunki i paragony.

📋 <b>Dostępne komendy:</b>
/start - Ta wiadomość
/help - Pomoc i instrukcje

📸 <b>Jak używać:</b>
1. Wyślij zdjęcie rachunku
2. Bot przetworzy go automatycznie
3. Otrzymasz kategoryzację produktów

Potrzebujesz pomocy? Użyj /help
    """
    await send_text_message(chat_id, welcome_text.strip())

async def _send_help_message(chat_id: int) -> None:
    """Wysyła wiadomość z pomocą."""
    help_text = """
📚 <b>Pomoc - System Bills</b>

🔹 <b>Główne funkcje:</b>
• Przetwarzanie rachunków i paragonów
• Automatyczna kategoryzacja produktów
• Indeksowanie produktów
• Analiza wydatków

🔹 <b>Jak wysłać rachunek:</b>
• Zrób zdjęcie rachunku
• Wyślij jako zdjęcie do bota
• Poczekaj na przetworzenie

🔹 <b>Komendy:</b>
/start - Powitanie
/help - Ta pomoc

🔹 <b>Wsparcie:</b>
W razie problemów skontaktuj się z administratorem.
    """
    await send_text_message(chat_id, help_text.strip())

async def _send_generic_response(chat_id: int, text: str) -> None:
    """Wysyła generyczną odpowiedź na nieznaną komendę."""
    response_text = f"""
❓ <b>Nie rozumiem komendy</b>

Wpisałeś: <code>{text}</code>

📋 <b>Dostępne komendy:</b>
/start - Powitanie
/help - Pomoc

📸 <b>Możesz też wysłać zdjęcie rachunku!</b>
    """
    await send_text_message(chat_id, response_text.strip())

async def _send_error_message(chat_id: int) -> None:
    """Wysyła wiadomość o błędzie."""
    error_text = """
⚠️ <b>Wystąpił błąd</b>

Przepraszamy, wystąpił problem podczas przetwarzania wiadomości.

🔄 <b>Spróbuj ponownie lub:</b>
• Użyj /help dla pomocy
• Skontaktuj się z administratorem

Dziękujemy za cierpliwość!
    """
    await send_text_message(chat_id, error_text.strip())

async def _process_photo_message(session: AsyncSession, telegram_message: TelegramMessage, file_id: str, caption: Optional[str] = None) -> None:
    """Przetwarza wiadomość ze zdjęciem."""
    try:
        chat_id = telegram_message.chat_id
        
        # Wyślij potwierdzenie otrzymania zdjęcia
        response_text = "📸 <b>Zdjęcie otrzymane!</b>\n\n"
        if caption:
            response_text += f"<i>Opis: {caption}</i>\n\n"
        response_text += "🔄 Pobieram zdjęcie...\n\n"
        response_text += "⏳ To może potrwać kilka sekund."
        
        await send_text_message(chat_id, response_text)
        
        # Pobierz file_path z Telegram API
        file_path = await get_file_path(file_id)
        if not file_path:
            await send_text_message(chat_id, "❌ <b>Błąd pobierania zdjęcia</b>\n\nNie udało się pobrać informacji o pliku.")
            return
        
        # Wygeneruj lokalną ścieżkę dla pliku
        import os
        from datetime import datetime
        
        # Utwórz katalog na zdjęcia
        photos_dir = "uploads/photos"
        os.makedirs(photos_dir, exist_ok=True)
        
        # Wygeneruj unikalną nazwę pliku
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file_path)[1] or '.jpg'
        local_filename = f"photo_{chat_id}_{timestamp}{file_extension}"
        local_path = os.path.join(photos_dir, local_filename)
        
        # Pobierz plik
        success = await download_file(file_path, local_path)
        if not success:
            await send_text_message(chat_id, "❌ <b>Błąd pobierania zdjęcia</b>\n\nNie udało się pobrać pliku.")
            return
        
        # Zaktualizuj rekord w bazie danych z file_path
        telegram_message.file_path = local_path
        await session.commit()
        
        # Wyślij potwierdzenie pobrania
        await send_text_message(chat_id, f"✅ <b>Zdjęcie pobrane!</b>\n\n📁 Zapisano jako: <code>{local_filename}</code>\n\n🔄 Przetwarzam rachunek...")
        
        # TODO: Tutaj będzie logika przetwarzania rachunku
        logger.info(f"Photo downloaded successfully: {local_path}")
        
    except Exception as e:
        logger.error(f"Error processing photo message: {str(e)}")
        await _send_error_message(chat_id) 