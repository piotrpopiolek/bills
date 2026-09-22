from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.product_candidates.schemas import (
    ProductCandidateCreate,
    ProductCandidateListResponse,
    ProductCandidateResponse,
    ProductCandidateUpdate,
)
from src.product_candidates.services import ProductCandidateService

router = APIRouter()


async def get_product_candidate_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductCandidateService:
    return ProductCandidateService(session)


ServiceDependency = Annotated[
    ProductCandidateService, Depends(get_product_candidate_service)
]


@router.get(
    "",
    response_model=ProductCandidateListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all product candidates",
)
async def get_product_candidates(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
    search: str | None = Query(None, description="Search by representative name"),
    status: str | None = Query(
        None, description="Filter by status (pending, approved, rejected)"
    ),
    category_id: int | None = Query(None, ge=1, description="Filter by category ID"),
):
    """
    List all product candidates.
    Requires authentication.
    """
    return await service.get_all(
        skip=skip, limit=limit, search=search, status=status, category_id=category_id
    )


@router.get(
    "/{product_candidate_id}",
    response_model=ProductCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product candidate by ID",
)
async def get_product_candidate(
    product_candidate_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Get product candidate by ID.
    Requires authentication.
    """
    return await service.get_by_id(product_candidate_id)


@router.post(
    "/",
    response_model=ProductCandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product candidate",
)
async def create_product_candidate(
    data: ProductCandidateCreate, user: CurrentUser, service: ServiceDependency
):
    """
    Create a new product candidate.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{product_candidate_id}",
    response_model=ProductCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a product candidate",
)
async def update_product_candidate(
    product_candidate_id: int,
    data: ProductCandidateUpdate,
    user: CurrentUser,
    service: ServiceDependency,
):
    """
    Update a product candidate.
    Requires authentication.
    """
    return await service.update(product_candidate_id, data)


@router.delete(
    "/{product_candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product candidate",
)
async def delete_product_candidate(
    product_candidate_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Delete a product candidate.
    Requires authentication.
    """
    await service.delete(product_candidate_id)
    return None
