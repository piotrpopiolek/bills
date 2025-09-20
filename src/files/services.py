"""
Serwisy do zarządzania plikami w aplikacji Bills.
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.db.models import TelegramMessage, Bill, User
from src.files.schemas import FileInfo, FileAccessRequest, FileAccessResponse


class FileService:
    """Serwis do zarządzania plikami."""
    
    # Katalog główny dla plików
    UPLOADS_DIR = Path("uploads")
    PHOTOS_DIR = UPLOADS_DIR / "photos"
    DOCUMENTS_DIR = UPLOADS_DIR / "documents"
    
    # Dozwolone typy plików
    ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ALLOWED_DOCUMENT_TYPES = {".pdf", ".doc", ".docx", ".txt"}
    
    @classmethod
    def _ensure_directories(cls) -> None:
        """Tworzy katalogi jeśli nie istnieją."""
        print(f"🔧 Creating directories: {cls.UPLOADS_DIR}")
        cls.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        cls.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Directories created successfully")
    
    @classmethod
    def _get_file_info(cls, file_path: str) -> Optional[FileInfo]:
        """Pobiera informacje o pliku."""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return FileInfo(
                    file_path=file_path,
                    file_name=path.name,
                    file_size=0,
                    file_type="unknown",
                    created_at=datetime.utcnow(),
                    modified_at=datetime.utcnow(),
                    exists=False
                )
            
            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))
            
            return FileInfo(
                file_path=str(path),
                file_name=path.name,
                file_size=stat.st_size,
                file_type=mime_type or "unknown",
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                exists=True
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting file info: {str(e)}"
            )
    
    @classmethod
    async def get_file_by_telegram_message(
        cls, 
        session: AsyncSession, 
        message_id: int
    ) -> Tuple[Optional[str], Optional[FileInfo]]:
        """Pobiera plik na podstawie wiadomości Telegram."""
        try:
            # Znajdź wiadomość Telegram
            stmt = select(TelegramMessage).where(TelegramMessage.id == message_id)
            result = await session.exec(stmt)
            message = result.first()
            
            if not message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message not found"
                )
            
            if not message.file_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No file associated with this message"
                )
            
            # Sprawdź czy plik istnieje
            file_info = cls._get_file_info(message.file_path)
            
            if not file_info.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found on disk"
                )
            
            return message.file_path, file_info
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting file: {str(e)}"
            )
    
    @classmethod
    async def get_file_by_bill(
        cls, 
        session: AsyncSession, 
        bill_id: int
    ) -> Tuple[Optional[str], Optional[FileInfo]]:
        """Pobiera plik na podstawie rachunku."""
        try:
            # Znajdź rachunek
            stmt = select(Bill).where(Bill.id == bill_id)
            result = await session.exec(stmt)
            bill = result.first()
            
            if not bill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bill not found"
                )
            
            # Znajdź powiązaną wiadomość Telegram z plikiem
            stmt = select(TelegramMessage).where(
                TelegramMessage.bill_id == bill_id,
                TelegramMessage.file_path.isnot(None)
            )
            result = await session.exec(stmt)
            message = result.first()
            
            if not message or not message.file_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No file associated with this bill"
                )
            
            # Sprawdź czy plik istnieje
            file_info = cls._get_file_info(message.file_path)
            
            if not file_info.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found on disk"
                )
            
            return message.file_path, file_info
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting file: {str(e)}"
            )
    
    @classmethod
    async def validate_file_access(
        cls, 
        session: AsyncSession, 
        file_path: str, 
        user_id: Optional[int] = None
    ) -> bool:
        """Waliduje czy użytkownik ma dostęp do pliku."""
        try:
            # Sprawdź czy plik istnieje
            if not Path(file_path).exists():
                return False
            
            # Jeśli nie podano user_id, sprawdź tylko czy plik istnieje
            if not user_id:
                return True
            
            # Sprawdź czy plik należy do użytkownika
            stmt = select(TelegramMessage).where(
                TelegramMessage.file_path == file_path,
                TelegramMessage.user_id == user_id
            )
            result = await session.exec(stmt)
            message = result.first()
            
            return message is not None
            
        except Exception:
            return False
    
    @classmethod
    def get_safe_file_path(cls, file_path: str) -> str:
        """Zwraca bezpieczną ścieżkę pliku."""
        try:
            path = Path(file_path).resolve()
            
            # Sprawdź czy plik jest w katalogu uploads
            uploads_path = Path(cls.UPLOADS_DIR).resolve()
            
            if not str(path).startswith(str(uploads_path)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: File outside uploads directory"
                )
            
            return str(path)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating file path: {str(e)}"
            )
    
    @classmethod
    def get_file_content_type(cls, file_path: str) -> str:
        """Pobiera typ MIME pliku."""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
