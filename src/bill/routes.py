from src.bill.schemas import BillCreate, BillRead, BillUpdate, BillReadWithDetails
from src.billitem.schemas import BillItemCreate
from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.bill import services

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