from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.users.schemas import (
    UsageStats,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserWithUsageResponse,
)
from src.users.services import UserService

router = APIRouter()


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserService:
    return UserService(session)


ServiceDependency = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "/me",
    response_model=UserWithUsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile with usage statistics",
    description="Get current authenticated user profile including freemium usage statistics (bills processed this month, monthly limit, remaining bills).",
)
async def get_current_user_profile(
    current_user: CurrentUser, service: ServiceDependency
) -> UserWithUsageResponse:
    """
    Get current authenticated user profile with usage statistics.

    This endpoint requires authentication via JWT access token.
    Returns user profile along with freemium usage tracking:
    - Number of bills processed in current month
    - Monthly limit (100 for free tier)
    - Remaining bills available this month

    Args:
        current_user: Current authenticated user (injected by dependency)
        service: UserService dependency

    Returns:
        UserWithUsageResponse with user profile and usage statistics

    Raises:
        401: If token is invalid or user not found
    """

    usage_data = await service.get_user_usage_stats(current_user.id)

    # Build response
    return UserWithUsageResponse(
        id=current_user.id,
        external_id=current_user.external_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        usage=UsageStats(**usage_data),
    )


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users",
)
async def get_users(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all users.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user(user_id: int, user: CurrentUser, service: ServiceDependency):
    """
    Get user by ID.
    Requires authentication.
    """
    return await service.get_by_id(user_id)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(data: UserCreate, user: CurrentUser, service: ServiceDependency):
    """
    Create a new user.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a user",
)
async def update_user(
    user_id: int, data: UserUpdate, user: CurrentUser, service: ServiceDependency
):
    """
    Update a user.
    Requires authentication.
    """
    return await service.update(user_id, data)


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user"
)
async def delete_user(user_id: int, user: CurrentUser, service: ServiceDependency):
    """
    Delete a user.
    Requires authentication.
    """
    await service.delete(user_id)
    return None
