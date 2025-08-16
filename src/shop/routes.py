from src.db.main import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from src.shop.schemas import ShopCreate, ShopRead
from sqlmodel.ext.asyncio.session import AsyncSession
from src.shop import services

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.post("", response_model=ShopRead, status_code=status.HTTP_201_CREATED)
async def create_shop(shop_in: ShopCreate, session: AsyncSession = Depends(get_session)):
    """
    Tworzy nowy sklep, jeśli nazwa nie jest jeszcze zajęta.
    """
    db_shop = await services.get_shop_by_name(session, name=shop_in.name)
    if db_shop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop with this name already exists"
        )
    return await services.create_shop(session, shop_in=shop_in)

# @router.get("/", response_model=List[ShopRead])
# async def get_shops(skip: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera listę wszystkich sklepów z paginacją.
#     """
#     # Uwaga: Ta funkcja wymaga dodania `get_shops` do pliku services/shop_service.py
#     return await services.get_shops(session, skip=skip, limit=limit)

# @router.get("/{shop_id}", response_model=ShopRead)
# async def get_shop(shop_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Pobiera jeden sklep po jego ID.
#     """
#     # Uwaga: Ta funkcja wymaga dodania `get_shop` do pliku services/shop_service.py
#     db_shop = await services.get_shop(session, shop_id=shop_id)
#     if not db_shop:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
#     return db_shop

# @router.patch("/{shop_id}", response_model=ShopRead)
# async def update_shop(shop_id: int, shop_in: ShopUpdate, session: AsyncSession = Depends(get_session)):
#     """
#     Aktualizuje dane sklepu.
#     """
#     # Uwaga: Ta funkcja wymaga dodania `get_shop` i `update_shop` do pliku services/shop_service.py
#     db_shop = await services.get_shop(session, shop_id=shop_id)
#     if not db_shop:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
#     return await services.update_shop(session, db_shop=db_shop, shop_in=shop_in)

# @router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_shop(shop_id: int, session: AsyncSession = Depends(get_session)):
#     """
#     Usuwa sklep.
#     """
#     # Uwaga: Ta funkcja wymaga dodania `get_shop` i `delete_shop` do pliku services/shop_service.py
#     db_shop = await services.get_shop(session, shop_id=shop_id)
#     if not db_shop:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
#     await services.delete_shop(session, db_shop=db_shop)
#     return None