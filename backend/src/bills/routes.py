from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.schemas import BillItemListResponse
from src.bill_items.services import BillItemService
from src.bills.schemas import BillCreate, BillListResponse, BillResponse, BillUpdate
from src.bills.services import BillService
from src.db.main import get_session
from src.deps import CurrentUser
from src.middleware.rate_limit import check_monthly_bills_limit
from src.storage.service import StorageService, get_storage_service

router = APIRouter()


async def get_bill_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> BillService:
    return BillService(session, storage_service)


ServiceDependency = Annotated[BillService, Depends(get_bill_service)]


@router.get(
    "",
    response_model=BillListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all bills for current user",
)
async def get_bills(
    service: ServiceDependency,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    Get all bills for the authenticated user.
    Enforces user isolation - returns only bills belonging to the current user.
    """
    return await service.get_all(user_id=user.id, skip=skip, limit=limit)


@router.get(
    "/{bill_id}",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bill by ID",
)
async def get_bill(bill_id: int, service: ServiceDependency, user: CurrentUser):
    """
    Get a specific bill by ID for the authenticated user.
    Enforces user isolation - returns 403 if bill doesn't belong to the current user.
    """
    return await service.get_by_id_and_user(bill_id=bill_id, user_id=user.id)


@router.get(
    "/{bill_id}/items",
    response_model=BillItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all items for a specific bill",
)
async def get_bill_items(
    bill_id: int,
    service: ServiceDependency,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    Get all items for a specific bill.
    Automatically verifies ownership - returns 403 if bill doesn't belong to the current user.
    """
    # Utwórz BillItemService z tą samą sesją
    bill_item_service = BillItemService(service.session)
    return await bill_item_service.get_by_bill_id(
        bill_id=bill_id, user_id=user.id, skip=skip, limit=limit
    )


@router.post(
    "/",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bill",
    dependencies=[Depends(check_monthly_bills_limit)],
)
async def create_bill(data: BillCreate, service: ServiceDependency, user: CurrentUser):
    # Enforce user isolation: user_id from token takes precedence
    data.user_id = user.id
    return await service.create(data)


@router.patch(
    "/{bill_id}",
    response_model=BillResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a bill",
)
async def update_bill(
    bill_id: int, data: BillUpdate, service: ServiceDependency, user: CurrentUser
):
    """
    Update a bill by ID for the authenticated user.
    Enforces user isolation - returns 403 if bill doesn't belong to the current user.
    Note: user_id cannot be changed via this endpoint.
    """
    return await service.update(bill_id=bill_id, data=data, user_id=user.id)


@router.delete(
    "/{bill_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a bill"
)
async def delete_bill(bill_id: int, service: ServiceDependency, user: CurrentUser):
    """
    Delete a bill by ID for the authenticated user.
    Enforces user isolation - returns 403 if bill doesn't belong to the current user.
    """
    await service.delete(bill_id=bill_id, user_id=user.id)
    return None
