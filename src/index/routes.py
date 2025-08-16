from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from src.index.schemas import IndexCreate, IndexRead
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.index import services

router = APIRouter(prefix="/indexes", tags=["Indexes"])

@router.post("/", response_model=IndexRead, status_code=status.HTTP_201_CREATED)
async def create_index(index_in: IndexCreate, session: AsyncSession = Depends(get_session)):
    """
    Tworzy nowy indeks produktu, jeśli nazwa nie jest jeszcze zajęta.
    """
    db_index = await services.get_index_by_name(session, name=index_in.name)
    if db_index:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index with this name already exists"
        )
    return await services.create_index(session, index_in=index_in)

# @router.get("/", response_model=List[IndexReadWithCategory])
# async def get_indexes(skip: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera listę wszystkich indeksów z paginacją.
#     """
#     # Uwaga: Wymaga implementacji `get_indexes` w services/index_service.py
#     return await services.get_indexes(session, skip=skip, limit=limit)

# @router.get("/{index_id}", response_model=IndexReadWithCategory)
# async def get_index(index_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera jeden indeks po jego ID.
#     """
#     # Uwaga: Wymaga implementacji `get_index` w services/index_service.py
#     db_index = await services.get_index(session, index_id=index_id)
#     if not db_index:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
#     return db_index

# @router.patch("/{index_id}", response_model=IndexRead)
# async def update_index(index_id: int, index_in: IndexUpdate, session: AsyncSession = Depends(get_session)):
#     """
#     Aktualizuje dane indeksu.
#     """
#     # Uwaga: Wymaga implementacji `get_index` i `update_index` w services/index_service.py
#     db_index = await services.get_index(session, index_id=index_id)
#     if not db_index:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
#     return await services.update_index(session, db_index=db_index, index_in=index_in)

# @router.delete("/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_index(index_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Usuwa indeks.
#     """
#     # Uwaga: Wymaga implementacji `get_index` i `delete_index` w services/index_service.py
#     db_index = await services.get_index(session, index_id=index_id)
#     if not db_index:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
#     await services.delete_index(session, db_index=db_index)
#     return None