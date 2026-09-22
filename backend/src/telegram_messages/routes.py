from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.telegram_messages.schemas import (
    TelegramMessageCreate,
    TelegramMessageListResponse,
    TelegramMessageResponse,
    TelegramMessageUpdate,
)
from src.telegram_messages.services import TelegramMessageService

router = APIRouter()


async def get_telegram_message_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TelegramMessageService:
    return TelegramMessageService(session)


ServiceDependency = Annotated[
    TelegramMessageService, Depends(get_telegram_message_service)
]


@router.get(
    "",
    response_model=TelegramMessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all telegram messages",
)
async def get_telegram_messages(
    user: CurrentUser,
    service: ServiceDependency,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of items to return"),
):
    """
    List all telegram messages.
    Requires authentication.
    """
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/{message_id}",
    response_model=TelegramMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get telegram message by ID",
)
async def get_telegram_message(
    message_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Get telegram message by ID.
    Requires authentication.
    """
    return await service.get_by_id(message_id)


@router.post(
    "/",
    response_model=TelegramMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new telegram message",
)
async def create_telegram_message(
    data: TelegramMessageCreate, user: CurrentUser, service: ServiceDependency
):
    """
    Create a new telegram message.
    Requires authentication.
    """
    return await service.create(data)


@router.patch(
    "/{message_id}",
    response_model=TelegramMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a telegram message",
)
async def update_telegram_message(
    message_id: int,
    data: TelegramMessageUpdate,
    user: CurrentUser,
    service: ServiceDependency,
):
    """
    Update a telegram message.
    Requires authentication.
    """
    return await service.update(message_id, data)


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a telegram message",
)
async def delete_telegram_message(
    message_id: int, user: CurrentUser, service: ServiceDependency
):
    """
    Delete a telegram message.
    Requires authentication.
    """
    await service.delete(message_id)
    return None
