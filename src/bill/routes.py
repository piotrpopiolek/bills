from src.bill.schemas import BillCreate, BillRead, BillUpdate, BillReadWithDetails
from src.billitem.schemas import BillItemCreate
from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.bill import services
from src.files.services import FileService
from src.files.schemas import FileResponse as FileResponseSchema

router = APIRouter(prefix="/bills", tags=["Bills"])


@router.post("/", response_model=BillRead, status_code=status.HTTP_201_CREATED)
async def create_bill(bill_in: BillCreate, session: AsyncSession = Depends(get_session)):
    """
    Tworzy nowy wpis dla rachunku (np. po otrzymaniu zdjęcia).
    Początkowo rachunek nie ma żadnych pozycji.
    """
    return await services.create_bill(session=session, bill_in=bill_in)


@router.get("/{bill_id}", response_model=BillReadWithDetails)
async def get_bill(bill_id: int, session: AsyncSession = Depends(get_session)):
    """
    Pobiera pełne informacje o rachunku wraz z pozycjami.
    """
    db_bill = await services.get_bill(session, bill_id=bill_id)
    if not db_bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return db_bill


@router.patch("/{bill_id}", response_model=BillRead)
async def update_bill(bill_id: int, bill_in: BillUpdate, session: AsyncSession = Depends(get_session)):
    """
    Aktualizuje dane rachunku (np. status po przetworzeniu).
    """
    db_bill = await services.get_bill(session, bill_id=bill_id)
    if not db_bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    return await services.update_bill(session=session, db_bill=db_bill, bill_in=bill_in)


@router.post("/{bill_id}/items", response_model=BillReadWithDetails)
async def add_items_to_bill(bill_id: int, items_in: List[BillItemCreate], session: AsyncSession = Depends(get_session)):
    """
    Dodaje listę przetworzonych pozycji do istniejącego rachunku.
    """
    db_bill = await services.get_bill(session, bill_id=bill_id)
    if not db_bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    
    # Tutaj powinna znaleźć się logika biznesowa:
    # 1. Dla każdej pozycji w `items_in` znajdź lub stwórz sklep, kategorię, indeks.
    # 2. Stwórz obiekty BillItemCreate.
    # 3. Wywołaj serwis `add_items_to_bill`.
    # Poniżej uproszczony przykład:

    return await services.add_items_to_bill(session=session, db_bill=db_bill, items_in=items_in)


# =============================================================================
# File Management Endpoints
# =============================================================================

@router.get("/{bill_id}/file")
async def get_bill_file(
    bill_id: int, 
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Pobiera plik rachunku.
    
    Zwraca plik (zdjęcie/dokument) powiązany z rachunkiem.
    Plik jest pobierany z wiadomości Telegram, która została użyta do utworzenia rachunku.
    
    Args:
        bill_id: ID rachunku
        session: Sesja bazy danych
    
    Returns:
        FileResponse: Plik do pobrania (zdjęcie lub dokument)
    
    Raises:
        HTTPException: 404 jeśli rachunek lub plik nie istnieje
        HTTPException: 500 w przypadku błędu serwera
    """
    try:
        # Pobierz plik z rachunku
        file_path, file_info = await FileService.get_file_by_bill(
            session, bill_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file associated with this bill"
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


@router.get("/{bill_id}/file/info", response_model=FileResponseSchema)
async def get_bill_file_info(
    bill_id: int, 
    session: AsyncSession = Depends(get_session)
) -> FileResponseSchema:
    """
    Pobiera informacje o pliku rachunku.
    
    Zwraca metadane pliku (nazwa, rozmiar, typ, daty) bez pobierania samego pliku.
    Przydatne do wyświetlania informacji o pliku przed pobraniem.
    
    Args:
        bill_id: ID rachunku
        session: Sesja bazy danych
    
    Returns:
        FileResponseSchema: Informacje o pliku
    
    Raises:
        HTTPException: 404 jeśli rachunek lub plik nie istnieje
        HTTPException: 500 w przypadku błędu serwera
    """
    try:
        # Pobierz plik z rachunku
        file_path, file_info = await FileService.get_file_by_bill(
            session, bill_id
        )
        
        if not file_path or not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file associated with this bill"
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
            detail=f"Error getting bill file info: {str(e)}"
        )