from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import Index
from src.index.schemas import IndexCreate


async def get_index_by_name(session: AsyncSession, name: str) -> Optional[Index]:
    """Pobiera indeks produktu po jego znormalizowanej nazwie."""
    statement = select(Index).where(Index.name == name)
    result = await session.execute(statement)
    return result.first()

async def create_index(session: AsyncSession, index_in: IndexCreate) -> Index:
    """Tworzy nowy indeks produktu."""
    db_index = Index.model_validate(index_in)
    session.add(db_index)
    await session.commit()
    await session.refresh(db_index)
    return db_index

async def get_or_create_index(session: AsyncSession, index_in: IndexCreate) -> Index:
    """Pobiera indeks po nazwie lub tworzy nowy, jeśli nie istnieje."""
    db_index = await get_index_by_name(session, name=index_in.name)
    if not db_index:
        db_index = await create_index(session, index_in)
    return db_index