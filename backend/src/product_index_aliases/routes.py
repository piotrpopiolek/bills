from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.product_index_aliases.schemas import (
    ProductIndexAliasCreate,
    ProductIndexAliasListResponse,
    ProductIndexAliasResponse,
    ProductIndexAliasUpdate,
)
from src.product_index_aliases.services import ProductIndexAliasService

router = APIRouter()


async def get_product_index_alias_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductIndexAliasService:
    return ProductIndexAliasService(session)


ServiceDependency = Annotated[
    ProductIndexAliasService, Depends(get_product_index_alias_service)
]


@router.get(
    "",
    response_model=ProductIndexAliasListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all product index aliases",
)
async def get_product_index_aliases(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all product index aliases.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{alias_id}",
    response_model=ProductIndexAliasResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product index alias by ID",
)
async def get_product_index_alias(
    alias_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Get product index alias by ID.
    Requires authentication.
    """
    return await service.get_by_id(alias_id)


@router.post(
    "/",
    response_model=ProductIndexAliasResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product index alias",
)
async def create_product_index_alias(
    data: ProductIndexAliasCreate, user: CurrentUser, service: ServiceDependency
):
    """
    Create a new product index alias.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{alias_id}",
    response_model=ProductIndexAliasResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a product index alias",
)
async def update_product_index_alias(
    alias_id: int,
    data: ProductIndexAliasUpdate,
    user: CurrentUser,
    service: ServiceDependency,
):
    """
    Update a product index alias.
    Requires authentication.
    """
    return await service.update(alias_id, data)


@router.delete(
    "/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product index alias",
)
async def delete_product_index_alias(
    alias_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Delete a product index alias.
    Requires authentication.
    """
    await service.delete(alias_id)
    return None
