from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.schemas import (
    BillItemCreate,
    BillItemListResponse,
    BillItemResponse,
    BillItemUpdate,
)
from src.bill_items.services import BillItemService
from src.db.main import get_session
from src.deps import CurrentUser

router = APIRouter()


async def get_bill_item_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillItemService:
    return BillItemService(session)


ServiceDependency = Annotated[BillItemService, Depends(get_bill_item_service)]


@router.get(
    "",
    response_model=BillItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all bill items",
)
async def get_bill_items(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all bill items.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{bill_item_id}",
    response_model=BillItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bill item by ID",
)
async def get_bill_item(
    bill_item_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Get bill item by ID.
    Requires authentication.
    """
    return await service.get_by_id(bill_item_id)


@router.post(
    "/",
    response_model=BillItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bill item",
)
async def create_bill_item(
    data: BillItemCreate, user: CurrentUser, service: ServiceDependency
):
    """
    Create a new bill item.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{bill_item_id}",
    response_model=BillItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a bill item",
)
async def update_bill_item(
    bill_item_id: int,
    data: BillItemUpdate,
    user: CurrentUser,
    service: ServiceDependency,
):
    """
    Update a bill item.
    Requires authentication.
    """
    return await service.update(bill_item_id, data)


@router.delete(
    "/{bill_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a bill item",
)
async def delete_bill_item(
    bill_item_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Delete a bill item.
    Requires authentication.
    """
    await service.delete(bill_item_id)
    return None
