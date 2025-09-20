from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.telegram import services
from src.telegram.schemas import TelegramWebhook, BotCommand, BotCommandList
from src.config import config
from src.files.services import FileService
from src.files.schemas import FileResponse as FileResponseSchema

router = APIRouter()

# =============================================================================
# Telegram Webhook Endpoint
# =============================================================================

@router.get("/webhook")
async def webhook_test():
    """
    Test endpoint dla webhooka - sprawdza czy endpoint jest dostępny
    """
    return {"status": "ok", "message": "Webhook endpoint is working"}

@router.post("/webhook")
async def process_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Przetwarzanie webhooków z Telegram Bot API
    
    Ten endpoint otrzymuje wiadomości z Telegram Bot API.
    Przetwarza różne typy wiadomości (tekst, zdjęcia, dokumenty).
    """
    try:
        # Sprawdź Content-Type
        content_type = request.headers.get("content-type", "")
        print(f"🔍 Content-Type: {content_type}")
        
        # Pobierz dane z request w zależności od Content-Type
        if "application/json" in content_type:
            webhook_data = await request.json()
        elif "application/x-www-form-urlencoded" in content_type:
            # Telegram może wysyłać dane w formacie form-data
            form_data = await request.form()
            webhook_data = dict(form_data)
            print(f"📝 Form data: {webhook_data}")
        else:
            # Spróbuj pobrać jako JSON (fallback)
            try:
                webhook_data = await request.json()
            except:
                # Jeśli nie JSON, pobierz jako tekst
                body = await request.body()
                print(f"📄 Raw body: {body}")
                raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")
        
        print(f"📊 Webhook data: {webhook_data}")
        
        # Waliduj dane webhooka
        try:
            webhook = TelegramWebhook(**webhook_data)
        except Exception as e:
            print(f"❌ Validation error: {e}")
            print(f"📊 Data that failed validation: {webhook_data}")
            raise HTTPException(status_code=400, detail=f"Invalid webhook data: {str(e)}")
        
        # Przetwórz webhook
        success = await services.process_webhook(session, webhook)
        
        if success:
            return {"status": "success", "message": "Webhook processed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")

# =============================================================================
# Telegram API Endpoints (for testing and manual operations)
# =============================================================================

@router.post("/send-message")
async def send_message(
    chat_id: int,
    message: str
) -> dict:
    """
    Wysyłanie wiadomości tekstowej przez Telegram
    
    Endpoint do testowania wysyłania wiadomości.
    """
    try:
        success = await services.send_text_message(chat_id, message)
        
        if success:
            return {
                "status": "success",
                "message": f"Message sent to chat {chat_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@router.post("/set-webhook")
async def set_webhook(webhook_url: str) -> dict:
    """
    Ustawienie webhooka dla bota
    
    """
    try:
        success = await services.set_webhook(webhook_url)
        
        if success:
            return {
                "status": "success",
                "message": f"Webhook set to {webhook_url}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting webhook: {str(e)}")

@router.post("/set-commands")
async def set_commands(commands: BotCommandList) -> dict:
    """
    Ustawienie komend bota
    
    Endpoint do konfiguracji komend bota.
    """
    try:
        success = await services.set_commands(commands.commands)
        
        if success:
            return {
                "status": "success",
                "message": "Bot commands set successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to set commands")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting commands: {str(e)}")

@router.get("/health")
async def telegram_health_check() -> dict:
    """
    Sprawdzenie stanu integracji Telegram
    
    Weryfikuje czy konfiguracja Telegram jest poprawna.
    """
    try:
        # Sprawdź czy zmienne środowiskowe są ustawione
        required_vars = [
            "TELEGRAM_BOT_TOKEN"
        ]
        
        missing_vars = []
        if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your-bot-token":
            missing_vars.append("TELEGRAM_BOT_TOKEN")
        
        if missing_vars:
            return {
                "status": "error",
                "message": "Missing Telegram configuration",
                "missing_variables": missing_vars
            }
        
        return {
            "status": "healthy",
            "message": "Telegram integration is configured",
            "bot_token": f"{config.TELEGRAM_BOT_TOKEN[:10]}..." if config.TELEGRAM_BOT_TOKEN else None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }

# =============================================================================
# Message Management Endpoints
# =============================================================================

@router.get("/messages")
async def get_all_messages(
    limit: int = 50,
    offset: int = 0,
    chat_id: Optional[int] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Pobieranie wszystkich wiadomości z filtrami
    
    Endpoint do pobierania wiadomości z opcjonalnymi filtrami.
    """
    try:
        messages = await services.get_telegram_messages(
            session, 
            skip=offset, 
            limit=limit,
            chat_id=chat_id,
            message_type=message_type,
            status=status
        )
        
        total_count = await services.count_telegram_messages(
            session,
            chat_id=chat_id,
            message_type=message_type,
            status=status
        )
        
        return {
            "status": "success",
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "messages": [
                {
                    "id": msg.id,
                    "telegram_message_id": msg.telegram_message_id,
                    "chat_id": msg.chat_id,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "file_id": msg.file_id,
                    "status": msg.status,
                    "created_at": msg.created_at.isoformat(),
                    "updated_at": msg.updated_at.isoformat() if msg.updated_at else None,
                    "user_id": msg.user_id,
                    "bill_id": msg.bill_id,
                    "error_message": msg.error_message
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")

@router.get("/messages/{message_id}")
async def get_message_by_id(
    message_id: int,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Pobieranie konkretnej wiadomości po ID
    
    Endpoint do pobierania szczegółów konkretnej wiadomości.
    """
    try:
        message = await services.get_telegram_message(session, message_id)
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {
            "status": "success",
            "message": {
                "id": message.id,
                "telegram_message_id": message.telegram_message_id,
                "chat_id": message.chat_id,
                "message_type": message.message_type,
                "content": message.content,
                "file_id": message.file_id,
                "status": message.status,
                "created_at": message.created_at.isoformat(),
                "updated_at": message.updated_at.isoformat() if message.updated_at else None,
                "user_id": message.user_id,
                "bill_id": message.bill_id,
                "error_message": message.error_message
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching message: {str(e)}")

@router.get("/messages/chat/{chat_id}")
async def get_messages_by_chat(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Pobieranie wiadomości dla konkretnego czatu
    
    Endpoint do pobierania historii wiadomości dla danego użytkownika.
    """
    try:
        messages = await services.get_telegram_messages(
            session,
            skip=offset,
            limit=limit,
            chat_id=chat_id
        )
        
        total_count = await services.count_telegram_messages(session, chat_id=chat_id)
        
        if total_count == 0:
            return {
                "status": "success",
                "message": f"No messages found for chat_id {chat_id}",
                "pagination": {
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_more": False
                },
                "messages": []
            }
        
        return {
            "status": "success",
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "messages": [
                {
                    "id": msg.id,
                    "telegram_message_id": msg.telegram_message_id,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "file_id": msg.file_id,
                    "status": msg.status,
                    "created_at": msg.created_at.isoformat(),
                    "updated_at": msg.updated_at.isoformat() if msg.updated_at else None,
                    "user_id": msg.user_id,
                    "bill_id": msg.bill_id,
                    "error_message": msg.error_message
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat messages: {str(e)}")

@router.get("/messages/stats")
async def get_messages_stats(
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Statystyki wiadomości
    
    Endpoint do pobierania statystyk wiadomości.
    """
    try:
        stats = await services.get_telegram_messages_stats(session)
        
        return {
            "status": "success",
            "stats": {
                "total_messages": stats["total_messages"],
                "unique_users": stats["unique_users"],
                "last_activity": stats["last_activity"].isoformat() if stats["last_activity"] else None,
                "by_type": stats["by_type"],
                "by_status": stats["by_status"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@router.get("/messages/search")
async def search_messages(
    query: str,
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Wyszukiwanie wiadomości
    
    Endpoint do wyszukiwania wiadomości po treści.
    """
    try:
        messages = await services.search_telegram_messages(
            session,
            query=query,
            skip=offset,
            limit=limit
        )
        
        total_count = await services.count_search_results(session, query)
        
        return {
            "status": "success",
            "search_query": query,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "messages": [
                {
                    "id": msg.id,
                    "telegram_message_id": msg.telegram_message_id,
                    "chat_id": msg.chat_id,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "file_id": msg.file_id,
                    "status": msg.status,
                    "created_at": msg.created_at.isoformat(),
                    "user_id": msg.user_id,
                    "bill_id": msg.bill_id
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching messages: {str(e)}")

# =============================================================================
# Debug Endpoints (tylko w trybie development)
# =============================================================================

@router.get("/debug/messages")
async def get_telegram_messages_debug(
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Pobieranie ostatnich wiadomości Telegram (debug)
    
    Endpoint tylko do celów debugowania.
    """
    try:
        messages = await services.get_telegram_messages(session, skip=0, limit=limit)
        
        return {
            "status": "success",
            "messages": [
                {
                    "id": msg.id,
                    "telegram_message_id": msg.telegram_message_id,
                    "chat_id": msg.chat_id,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "file_id": msg.file_id,
                    "status": msg.status,
                    "created_at": msg.created_at.isoformat(),
                    "user_id": msg.user_id,
                    "bill_id": msg.bill_id
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")

@router.get("/bot-info")
async def get_bot_info() -> dict:
    """
    Pobieranie informacji o bocie
    
    Endpoint do sprawdzenia informacji o bocie.
    """
    try:
        bot_info = await services.get_bot_info()
        
        if bot_info:
            return {
                "status": "success",
                "bot_info": bot_info
            }
        else:
            return {
                "status": "error",
                "message": "Failed to get bot info"
            }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting bot info: {str(e)}")

# =============================================================================
# Bill Processing Endpoints
# =============================================================================

@router.post("/process-bill")
async def process_bill_manual(
    chat_id: int,
    file_id: str,
    user_id: int,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Ręczne przetwarzanie rachunku
    
    Endpoint do testowania przetwarzania rachunków bez Telegram.
    """
    try:
        # TODO: Implement bill processing logic
        # For now, just send confirmation
        
        return {
            "status": "success",
            "message": "Bill processing started",
            "chat_id": chat_id,
            "user_id": user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bill: {str(e)}")


# =============================================================================
# File Management Endpoints
# =============================================================================

@router.get("/messages/{message_id}/file")
async def get_telegram_message_file(
    message_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera plik z wiadomości Telegram.
    
    Zwraca plik (zdjęcie/dokument) powiązany z wiadomością Telegram.
    Plik jest pobierany z lokalnego katalogu uploads.
    
    Args:
        message_id: ID wiadomości Telegram w bazie danych
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Plik do pobrania (zdjęcie lub dokument)
    
    Raises:
        HTTPException: 404 jeśli wiadomość lub plik nie istnieje
        HTTPException: 500 w przypadku błędu serwera
    """
    try:
        print(f"🔍 DEBUG: Getting file for Telegram message ID: {message_id}")
        
        # Upewnij się, że katalogi istnieją
        FileService._ensure_directories()
        
        # DEBUG: Wyświetl wszystkie pliki w katalogu uploads
        print("🔍 DEBUG: Listing all files in uploads directory...")
        from pathlib import Path
        uploads_dir = Path(FileService.UPLOADS_DIR)
        if uploads_dir.exists():
            print(f"📁 Uploads directory: {uploads_dir.absolute()}")
            for root, dirs, files in uploads_dir.rglob("*"):
                if files:
                    print(f"  📂 {root}:")
                    for file in files:
                        file_path_full = root / file
                        file_size = file_path_full.stat().st_size if file_path_full.exists() else 0
                        print(f"    📄 {file} ({file_size} bytes)")
        else:
            print(f"❌ Uploads directory does not exist: {uploads_dir.absolute()}")
        
        # Pobierz plik z wiadomości Telegram
        file_path, file_info = await FileService.get_file_by_telegram_message(
            session, message_id
        )
        
        print(f"📄 Retrieved file path: {file_path}")
        print(f"📄 File info: {file_info}")
        
        if not file_path or not file_info:
            print(f"❌ No file found for message ID: {message_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file associated with this message"
            )
        
        # Pobierz typ MIME
        media_type = FileService.get_file_content_type(file_path)
        print(f"📄 Media type: {media_type}")
        
        # Zwróć plik
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_info.file_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting telegram file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting telegram file: {str(e)}"
        )


@router.get("/messages/{message_id}/file/info", response_model=FileResponseSchema)
async def get_telegram_message_file_info(
    message_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponseSchema:
    """
    Pobiera informacje o pliku z wiadomości Telegram.
    
    Zwraca metadane pliku (nazwa, rozmiar, typ, daty) bez pobierania samego pliku.
    Przydatne do wyświetlania informacji o pliku przed pobraniem.
    
    Args:
        message_id: ID wiadomości Telegram w bazie danych
        session: Sesja bazy danych
    
    Returns:
        FileResponseSchema: Informacje o pliku
    
    Raises:
        HTTPException: 404 jeśli wiadomość lub plik nie istnieje
        HTTPException: 500 w przypadku błędu serwera
    """
    try:
        # Pobierz plik z wiadomości Telegram
        file_path, file_info = await FileService.get_file_by_telegram_message(
            session, message_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file associated with this message"
            )
        
        return FileResponseSchema(
            status="success",
            message="File info retrieved successfully",
            file_info=file_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting telegram file info: {str(e)}"
        ) 