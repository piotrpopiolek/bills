from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bills.models import Bill
from src.common.exceptions import ResourceAlreadyExistsError, UserCreationError
from src.common.services import AppService
from src.config import settings
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate


class UserService(AppService[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=User, session=session)

    async def _ensure_unique_external_id(
        self, external_id: int, exclude_id: int | None = None
    ) -> None:
        """
        Checks if an external_id already exists.
        Used to prevent duplicate Telegram user IDs.
        """
        stmt = select(User).where(User.external_id == external_id)

        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)

        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise ResourceAlreadyExistsError("User", "external_id", external_id)

    async def create(self, data: UserCreate) -> User:
        # Uniqueness Check (external_id)
        await self._ensure_unique_external_id(data.external_id)

        # Object Construction
        new_user = User(external_id=data.external_id, is_active=data.is_active)

        # Persistence (Unit of Work)
        self.session.add(new_user)

        try:
            await self.session.commit()
            await self.session.refresh(new_user)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation (PostgreSQL error code 23505)
            if (
                "external_id" in str(e.orig)
                or "idx_users_external_id" in str(e.orig)
                or "23505" in str(e.orig)
            ):
                raise ResourceAlreadyExistsError(
                    "User", "external_id", data.external_id
                ) from e
            # Other integrity errors (e.g., foreign key violations, check constraints)
            raise UserCreationError(f"Błąd bazy danych: {str(e)}") from e
        except Exception as e:
            await self.session.rollback()
            # Wrap unexpected errors in UserCreationError
            if isinstance(e, (ResourceAlreadyExistsError, UserCreationError)):
                raise
            raise UserCreationError(
                f"Nieoczekiwany błąd podczas tworzenia użytkownika: {str(e)}"
            ) from e

        return new_user

    async def update(self, user_id: int, data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return user

        # Uniqueness Check (if external_id is being updated)
        if (
            "external_id" in update_data
            and update_data["external_id"] != user.external_id
        ):
            await self._ensure_unique_external_id(
                update_data["external_id"], exclude_id=user.id
            )

        # Apply updates
        for key, value in update_data.items():
            setattr(user, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if (
                "external_id" in str(e.orig)
                or "idx_users_external_id" in str(e.orig)
                or "23505" in str(e.orig)
            ):
                raise ResourceAlreadyExistsError(
                    "User",
                    "external_id",
                    update_data.get("external_id", user.external_id),
                ) from e
            raise e

        return user

    async def delete(self, user_id: int) -> None:
        user = await self.get_by_id(user_id)

        self.session.delete(user)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_bills_count_this_month(self, user_id: int) -> int:
        """
        Count bills created by user in the current month.

        Used for freemium limit tracking (100 bills per month).

        Args:
            user_id: User ID to count bills for

        Returns:
            Number of bills created in current month
        """
        # Get first and last day of current month (timezone-aware)
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        # Next month's first day (exclusive)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            month_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

        # Count bills in current month
        stmt = select(func.count(Bill.id)).where(
            Bill.user_id == user_id,
            Bill.created_at >= month_start,
            Bill.created_at < month_end,
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        return count

    async def get_user_usage_stats(self, user_id: int) -> dict:
        """
        Get comprehensive usage statistics for a user.

        Calculates bills processed this month against the monthly limit.
        Used for both the profile endpoint and rate limiting checks.

        Args:
            user_id: User ID to get stats for

        Returns:
            Dictionary with keys: bills_this_month, monthly_limit, remaining_bills
        """
        count = await self.get_bills_count_this_month(user_id)
        limit = settings.MONTHLY_BILLS_LIMIT
        remaining = max(0, limit - count)

        return {
            "bills_this_month": count,
            "monthly_limit": limit,
            "remaining_bills": remaining,
        }
