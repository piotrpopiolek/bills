from src.category.schemas import CategoryCreate, CategoryRead
from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.category import services

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(category_in: CategoryCreate, session: AsyncSession = Depends(get_session)):
    """
    Tworzy nową kategorię, jeśli nazwa nie jest jeszcze zajęta.
    """
    db_category = await services.get_category_by_name(session, name=category_in.name)
    if db_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    return await services.create_category(session, category_in=category_in)

# @router.get("/", response_model=List[CategoryRead])
# async def get_categories(skip: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera listę wszystkich kategorii z paginacją.
#     """
#     # Uwaga: Wymaga implementacji `get_categories` w services/category_service.py
#     return await services.get_categories(session, skip=skip, limit=limit)

# @router.get("/{category_id}", response_model=CategoryRead)
# async def get_category(category_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera jedną kategorię po jej ID.
#     """
#     # Uwaga: Wymaga implementacji `get_category` w services/category_service.py
#     db_category = await services.get_category(session, category_id=category_id)
#     if not db_category:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
#     return db_category

# @router.patch("/{category_id}", response_model=CategoryRead)
# async def update_category(category_id: int, category_in: CategoryUpdate, session: AsyncSession = Depends(get_session)):
#     """
#     Aktualizuje dane kategorii.
#     """
#     # Uwaga: Wymaga implementacji `get_category` i `update_category` w services/category_service.py
#     db_category = await services.get_category(session, category_id=category_id)
#     if not db_category:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
#     return await services.update_category(session, db_category=db_category, category_in=category_in)

# @router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_category(category_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Usuwa kategorię.
#     """
#     # Uwaga: Wymaga implementacji `get_category` i `delete_category` w services/category_service.py
#     db_category = await services.get_category(session, category_id=category_id)
#     if not db_category:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
#     await services.delete_category(session, db_category=db_category)
#     return None