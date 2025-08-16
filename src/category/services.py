from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import Category
from src.category.schemas import CategoryCreate


async def get_category_by_name(session: AsyncSession, name: str) -> Optional[Category]:
    """Pobiera kategorię po jej nazwie."""
    statement = select(Category).where(Category.name == name)
    result = await session.execute(statement)
    return result.first()

async def create_category(session: AsyncSession, category_in: CategoryCreate) -> Category:
    """Tworzy nową kategorię."""
    db_category = Category.model_validate(category_in)
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def get_or_create_category(session: AsyncSession, category_in: CategoryCreate) -> Category:
    """Pobiera kategorię po nazwie lub tworzy nową, jeśli nie istnieje."""
    db_category = await get_category_by_name(session, name=category_in.name)
    if not db_category:
        db_category = await create_category(session, category_in)
    return db_category