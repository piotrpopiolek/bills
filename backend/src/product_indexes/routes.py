from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.product_indexes.schemas import (
    ProductIndexCreate,
    ProductIndexListResponse,
    ProductIndexResponse,
    ProductIndexUpdate,
)
from src.product_indexes.services import ProductIndexService

router = APIRouter()


async def get_product_index_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductIndexService:
    return ProductIndexService(session)


ServiceDependency = Annotated[ProductIndexService, Depends(get_product_index_service)]


@router.get(
    "",
    response_model=ProductIndexListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all product indexes",
)
async def get_product_indexes(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all product indexes.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{product_index_id}",
    response_model=ProductIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product index by ID",
)
async def get_product_index(
    product_index_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Get product index by ID.
    Requires authentication.
    """
    return await service.get_by_id(product_index_id)


@router.post(
    "/",
    response_model=ProductIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product index",
)
async def create_product_index(
    data: ProductIndexCreate, user: CurrentUser, service: ServiceDependency
):
    """
    Create a new product index.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{product_index_id}",
    response_model=ProductIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a product index",
)
async def update_product_index(
    product_index_id: int,
    data: ProductIndexUpdate,
    user: CurrentUser,
    service: ServiceDependency,
):
    """
    Update a product index.
    Requires authentication.
    """
    return await service.update(product_index_id, data)


@router.delete(
    "/{product_index_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product index",
)
async def delete_product_index(
    product_index_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Delete a product index.
    Requires authentication.
    """
    await service.delete(product_index_id)
    return None
