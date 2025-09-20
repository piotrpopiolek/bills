"""
Endpointy API do zarządzania plikami w aplikacji Bills.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.files.services import FileService
from src.files.schemas import FileInfo, FileResponse

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/info/{file_path:path}", response_model=FileResponse)
async def get_file_info(
    file_path: str,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera informacje o pliku.
    
    Args:
        file_path: Ścieżka do pliku (względna do katalogu uploads)
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Informacje o pliku
    """
    try:
        # Waliduj ścieżkę pliku
        safe_path = FileService.get_safe_file_path(file_path)
        
        # Pobierz informacje o pliku
        file_info = FileService._get_file_info(safe_path)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            status="success",
            message="File info retrieved successfully",
            file_info=file_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file info: {str(e)}"
        )


@router.get("/{file_path:path}")
async def serve_file(
    file_path: str,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Serwuje plik do pobrania.
    
    Args:
        file_path: Ścieżka do pliku (względna do katalogu uploads)
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Plik do pobrania
    """
    try:
        # Upewnij się, że katalogi istnieją
        FileService._ensure_directories()
        
        # DEBUG: Wyświetl wszystkie pliki w katalogu uploads
        print("🔍 DEBUG: Listing all files in uploads directory...")
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
        
        print(f"🎯 Requested file path: {file_path}")
        
        # Waliduj ścieżkę pliku
        safe_path = FileService.get_safe_file_path(file_path)
        print(f"✅ Safe file path: {safe_path}")
        
        # Sprawdź czy plik istnieje
        if not Path(safe_path).exists():
            print(f"❌ File does not exist: {safe_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        print(f"✅ File exists: {safe_path}")
        
        # Pobierz typ MIME
        media_type = FileService.get_file_content_type(safe_path)
        print(f"📄 Media type: {media_type}")
        
        # Zwróć plik
        return FileResponse(
            path=safe_path,
            media_type=media_type,
            filename=Path(safe_path).name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error serving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )


@router.get("/telegram/{message_id}/file")
async def get_telegram_message_file(
    message_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera plik z wiadomości Telegram.
    
    Args:
        message_id: ID wiadomości Telegram
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Plik do pobrania
    """
    try:
        print(f"🔍 DEBUG: Getting file for Telegram message ID: {message_id}")
        
        # Upewnij się, że katalogi istnieją
        FileService._ensure_directories()
        
        # DEBUG: Wyświetl wszystkie pliki w katalogu uploads
        print("🔍 DEBUG: Listing all files in uploads directory...")
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
                detail="File not found"
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


@router.get("/telegram/{message_id}/file/info", response_model=FileResponse)
async def get_telegram_message_file_info(
    message_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera informacje o pliku z wiadomości Telegram.
    
    Args:
        message_id: ID wiadomości Telegram
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Informacje o pliku
    """
    try:
        # Pobierz plik z wiadomości Telegram
        file_path, file_info = await FileService.get_file_by_telegram_message(
            session, message_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
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


@router.get("/bill/{bill_id}/file")
async def get_bill_file(
    bill_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera plik rachunku.
    
    Args:
        bill_id: ID rachunku
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Plik do pobrania
    """
    try:
        print(f"🔍 DEBUG: Getting file for bill ID: {bill_id}")
        
        # Upewnij się, że katalogi istnieją
        FileService._ensure_directories()
        
        # DEBUG: Wyświetl wszystkie pliki w katalogu uploads
        print("🔍 DEBUG: Listing all files in uploads directory...")
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
        
        # Pobierz plik z rachunku
        file_path, file_info = await FileService.get_file_by_bill(
            session, bill_id
        )
        
        print(f"📄 Retrieved file path: {file_path}")
        print(f"📄 File info: {file_info}")
        
        if not file_path or not file_info:
            print(f"❌ No file found for bill ID: {bill_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
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
        print(f"❌ Error getting bill file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bill file: {str(e)}"
        )


@router.get("/bill/{bill_id}/file/info", response_model=FileResponse)
async def get_bill_file_info(
    bill_id: int,
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera informacje o pliku rachunku.
    
    Args:
        bill_id: ID rachunku
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Informacje o pliku
    """
    try:
        # Pobierz plik z rachunku
        file_path, file_info = await FileService.get_file_by_bill(
            session, bill_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            status="success",
            message="File info retrieved successfully",
            file_info=file_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bill file info: {str(e)}"
        )
