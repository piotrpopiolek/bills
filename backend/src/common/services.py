from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import ColumnElement

from src.common.exceptions import ResourceAlreadyExistsError, ResourceNotFoundError
from src.common.schemas import AppBaseModel


class AppService[
    ModelType: DeclarativeBase,
    CreateSchemaType: AppBaseModel,
    UpdateSchemaType: AppBaseModel,
]:
    """
    Base service class that provides common functionality
    like session management and generic validation checks.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelType:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()

        if not obj:
            raise ResourceNotFoundError(self.model.__name__, id)

        return obj

    async def get_all(self, skip: int = 0, limit: int = 100) -> dict[str, Any]:
        count_stmt = select(func.count()).select_from(self.model)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0
        stmt = select(self.model).offset(skip).limit(limit).order_by(self.model.id)
        result = await self.session.execute(stmt)
        return {
            "items": result.scalars().all(),
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def create(self, data: CreateSchemaType) -> ModelType:
        await self._ensure_unique(
            model=self.model,
            field=self.model.name,
            value=data.name,
            resource_name=self.model.__name__,
            field_name="name",
        )

        obj_in_data = data.model_dump()
        db_obj = self.model(**obj_in_data)

        self.session.add(db_obj)
        try:
            await self.session.commit()
            await self.session.refresh(db_obj)
        except IntegrityError as e:
            await self.session.rollback()
            if self._is_foreign_key_violation(e):
                raise ValueError("Foreign key violation") from e
            raise e

        return db_obj

    async def update(self, id: int, data: UpdateSchemaType) -> ModelType:
        db_obj = await self.get_by_id(id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return db_obj

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        try:
            await self.session.commit()
            await self.session.refresh(db_obj)
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        return db_obj

    async def delete(self, id: int) -> None:
        db_obj = await self.get_by_id(id)

        await self.session.delete(db_obj)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def _ensure_unique(
        self,
        model: type[ModelType],
        field: ColumnElement,
        value: Any,
        resource_name: str,
        field_name: str,
    ) -> None:
        """
        Generic check if a record with a given field value already exists.

        Args:
            model: The SQLAlchemy model class (e.g., Category)
            field: The SQLAlchemy column attribute (e.g., Category.name)
            value: The value to check
            resource_name: Name of the resource for the error message (e.g., "Category")
            field_name: Name of the field for the error message (e.g., "name")
        """
        stmt = select(model).where(field == value)
        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise ResourceAlreadyExistsError(resource_name, field_name, value)

    async def _ensure_exists(
        self,
        model: type[ModelType],
        field: ColumnElement,
        value: Any,
        resource_name: str,
    ) -> None:
        """
        Generic check to ensure a related record exists (e.g. parent_id).

        Args:
            model: The SQLAlchemy model class (e.g., Category)
            field: The SQLAlchemy column attribute (e.g., Category.id)
            value: The value to check
            resource_name: Name of the resource for the error message (e.g., "Parent Category")
        """
        stmt = select(model).where(field == value)
        result = await self.session.execute(stmt)
        if not result.scalars().first():
            raise ResourceNotFoundError(resource_name, value)

    def _is_foreign_key_violation(self, e: IntegrityError) -> bool:
        """
        Checks if the IntegrityError is caused by a foreign key violation.
        Supports both asyncpg (sqlstate) and psycopg2 (pgcode).

        Args:
            e: The IntegrityError object

        Returns:
            True if the IntegrityError is caused by a foreign key violation, False otherwise
        """
        # asyncpg puts sqlstate in e.orig.sqlstate
        if hasattr(e.orig, "sqlstate") and e.orig.sqlstate == "23503":
            return True
        # psycopg2 puts pgcode in e.orig.pgcode
        if hasattr(e.orig, "pgcode") and e.orig.pgcode == "23503":
            return True
        return False
