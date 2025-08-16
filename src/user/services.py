from typing import List, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import User
from src.user.schemas import UserCreate, UserUpdate


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Pobiera jednego użytkownika po jego ID."""
    return await session.get(User, user_id)

async def get_user_by_external_id(session: AsyncSession, external_id: str) -> Optional[User]:
    """Pobiera jednego użytkownika po jego zewnętrznym ID."""
    statement = select(User).where(User.external_id == external_id)
    result = await session.execute(statement)
    return result.first()

async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Pobiera listę użytkowników z paginacją."""
    statement = select(User).offset(skip).limit(limit)
    result = await session.execute(statement)
    return result.all()

async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    """Tworzy nowego użytkownika."""
    db_user = User.model_validate(user_in)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

async def update_user(session: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    """Aktualizuje dane użytkownika."""
    user_data = user_in.model_dump(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user