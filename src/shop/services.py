from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import Shop
from src.shop.schemas import ShopCreate


async def get_shop_by_name(session: AsyncSession, name: str) -> Optional[Shop]:
    """Pobiera sklep po jego nazwie."""
    statement = select(Shop).where(Shop.name == name)
    result = await session.execute(statement)
    return result.first()

async def create_shop(session: AsyncSession, shop_in: ShopCreate) -> Shop:
    """Tworzy nowy sklep."""
    db_shop = Shop.model_validate(shop_in)
    session.add(db_shop)
    await session.commit()
    await session.refresh(db_shop)
    return db_shop

async def get_or_create_shop(session: AsyncSession, shop_in: ShopCreate) -> Shop:
    """Pobiera sklep po nazwie lub tworzy nowy, jeśli nie istnieje."""
    db_shop = await get_shop_by_name(session, name=shop_in.name)
    if not db_shop:
        db_shop = await create_shop(session, shop_in)
    return db_shop