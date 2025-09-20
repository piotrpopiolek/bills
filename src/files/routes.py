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
        # Waliduj ścieżkę pliku
        safe_path = FileService.get_safe_file_path(file_path)
        
        # Sprawdź czy plik istnieje
        if not Path(safe_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Pobierz typ MIME
        media_type = FileService.get_file_content_type(safe_path)
        
        # Zwróć plik
        return FileResponse(
            path=safe_path,
            media_type=media_type,
            filename=Path(safe_path).name
        )
        
    except HTTPException:
        raise
    except Exception as e:
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
        # Pobierz plik z wiadomości Telegram
        file_path, file_info = await FileService.get_file_by_telegram_message(
            session, message_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Pobierz typ MIME
        media_type = FileService.get_file_content_type(file_path)
        
        # Zwróć plik
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_info.file_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
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
        # Pobierz plik z rachunku
        file_path, file_info = await FileService.get_file_by_bill(
            session, bill_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Pobierz typ MIME
        media_type = FileService.get_file_content_type(file_path)
        
        # Zwróć plik
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_info.file_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
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
