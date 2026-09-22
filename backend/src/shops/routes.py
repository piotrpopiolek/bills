from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.shops.schemas import ShopCreate, ShopListResponse, ShopResponse, ShopUpdate
from src.shops.services import ShopService

router = APIRouter()


async def get_shop_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ShopService:
    return ShopService(session)


ServiceDependency = Annotated[ShopService, Depends(get_shop_service)]


@router.get(
    "",
    response_model=ShopListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all shops",
)
async def get_shops(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all shops.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{shop_id}",
    response_model=ShopResponse,
    status_code=status.HTTP_200_OK,
    summary="Get shop by ID",
)
async def get_shop(shop_id: int, user: CurrentUser, service: ServiceDependency):
    """
    Get shop by ID.
    Requires authentication.
    """
    return await service.get_by_id(shop_id)


@router.post(
    "/",
    response_model=ShopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shop",
)
async def create_shop(data: ShopCreate, user: CurrentUser, service: ServiceDependency):
    """
    Create a new shop.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{shop_id}",
    response_model=ShopResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a shop",
)
async def update_shop(
    shop_id: int, data: ShopUpdate, user: CurrentUser, service: ServiceDependency
):
    """
    Update a shop.
    Requires authentication.
    """
    return await service.update(shop_id, data)


@router.delete(
    "/{shop_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a shop"
)
async def delete_shop(shop_id: int, user: CurrentUser, service: ServiceDependency):
    """
    Delete a shop.
    Requires authentication.
    """
    await service.delete(shop_id)
    return None
