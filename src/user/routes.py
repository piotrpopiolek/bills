from src.bill.schemas import BillRead
from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.user.schemas import UserCreate, UserRead, UserUpdate
from src.user import services

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    """
    Tworzy nowego użytkownika.
    """
    db_user = await services.get_user_by_external_id(session, external_id=user_in.external_id)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this external ID already exists"
        )
    return await services.create_user(session=session, user_in=user_in)

@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    """
    Pobiera informacje o jednym użytkowniku.
    """
    db_user = await services.get_user(session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user_in: UserUpdate, session: AsyncSession = Depends(get_session)):
    """
    Aktualizuje dane użytkownika.
    """
    db_user = await services.get_user(session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return await services.update_user(session=session, db_user=db_user, user_in=user_in)

@router.get("/{user_id}/bills", response_model=List[BillRead])
async def get_user_bills(user_id: int, session: AsyncSession = Depends(get_session)):
    """
    Pobiera wszystkie rachunki dla danego użytkownika.
    """
    db_user = await services.get_user(session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return await services.get_bills_by_user(session=session, user_id=user_id)