from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.product_index_aliases.models import ProductIndexAlias
from src.product_index_aliases.schemas import (
    ProductIndexAliasCreate,
    ProductIndexAliasUpdate,
)
from src.product_indexes.models import ProductIndex
from src.shops.models import Shop
from src.users.models import User


class ProductIndexAliasService(
    AppService[ProductIndexAlias, ProductIndexAliasCreate, ProductIndexAliasUpdate]
):
    def __init__(self, session: AsyncSession):
        super().__init__(model=ProductIndexAlias, session=session)

    async def _ensure_unique_alias(
        self, raw_name: str, index_id: int, exclude_id: int | None = None
    ) -> None:
        """
        Checks if a combination of raw_name (case-insensitive) and index_id already exists.
        Used to prevent duplicate aliases for the same product index.
        """
        stmt = select(ProductIndexAlias).where(
            func.lower(ProductIndexAlias.raw_name) == func.lower(raw_name),
            ProductIndexAlias.index_id == index_id,
        )

        if exclude_id is not None:
            stmt = stmt.where(ProductIndexAlias.id != exclude_id)

        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise ResourceAlreadyExistsError(
                "ProductIndexAlias", "raw_name + index_id", f"{raw_name} + {index_id}"
            )

    async def create(self, data: ProductIndexAliasCreate) -> ProductIndexAlias:
        # ProductIndex Existence Check (Referential Integrity check before DB hit)
        await self._ensure_exists(
            model=ProductIndex,
            field=ProductIndex.id,
            value=data.index_id,
            resource_name="ProductIndex",
        )

        # Shop Existence Check (if provided)
        if data.shop_id:
            await self._ensure_exists(
                model=Shop, field=Shop.id, value=data.shop_id, resource_name="Shop"
            )

        # User Existence Check (if provided)
        if data.user_id:
            await self._ensure_exists(
                model=User, field=User.id, value=data.user_id, resource_name="User"
            )

        # Uniqueness Check (case-insensitive raw_name + index_id)
        await self._ensure_unique_alias(data.raw_name, data.index_id)

        # Object Construction
        new_alias = ProductIndexAlias(
            raw_name=data.raw_name,
            confirmations_count=data.confirmations_count,
            shop_id=data.shop_id,
            user_id=data.user_id,
            index_id=data.index_id,
            locale=data.locale,
        )

        # Persistence (Unit of Work)
        self.session.add(new_alias)

        try:
            await self.session.commit()
            await self.session.refresh(new_alias)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "uq_alias_raw_name_index" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "ProductIndexAlias",
                    "raw_name + index_id",
                    f"{data.raw_name} + {data.index_id}",
                ) from e
            raise e

        return new_alias

    async def update(
        self, alias_id: int, data: ProductIndexAliasUpdate
    ) -> ProductIndexAlias:
        alias = await self.get_by_id(alias_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return alias

        # ProductIndex Existence Check (if index_id is being updated)
        if "index_id" in update_data and update_data["index_id"] != alias.index_id:
            await self._ensure_exists(
                model=ProductIndex,
                field=ProductIndex.id,
                value=update_data["index_id"],
                resource_name="ProductIndex",
            )

        # Shop Existence Check (if shop_id is being updated)
        if "shop_id" in update_data and update_data["shop_id"] != alias.shop_id:
            new_shop_id = update_data["shop_id"]
            if new_shop_id is not None:
                await self._ensure_exists(
                    model=Shop, field=Shop.id, value=new_shop_id, resource_name="Shop"
                )

        # User Existence Check (if user_id is being updated)
        if "user_id" in update_data and update_data["user_id"] != alias.user_id:
            new_user_id = update_data["user_id"]
            if new_user_id is not None:
                await self._ensure_exists(
                    model=User, field=User.id, value=new_user_id, resource_name="User"
                )

        # Uniqueness Check (if raw_name or index_id is being updated)
        new_raw_name = update_data.get("raw_name", alias.raw_name)
        new_index_id = update_data.get("index_id", alias.index_id)

        if "raw_name" in update_data or "index_id" in update_data:
            if new_raw_name != alias.raw_name or new_index_id != alias.index_id:
                await self._ensure_unique_alias(
                    new_raw_name, new_index_id, exclude_id=alias.id
                )

        # Apply updates
        for key, value in update_data.items():
            setattr(alias, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(alias)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "uq_alias_raw_name_index" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "ProductIndexAlias",
                    "raw_name + index_id",
                    f"{new_raw_name} + {new_index_id}",
                ) from e
            raise e

        return alias

    async def delete(self, alias_id: int) -> None:
        alias = await self.get_by_id(alias_id)

        self.session.delete(alias)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def upsert_alias(
        self,
        raw_name: str,
        index_id: int,
        shop_id: int | None = None,
        user_id: int | None = None,
        locale: str = "pl_PL",
    ) -> ProductIndexAlias:
        """
        Atomowo tworzy lub aktualizuje alias produktu używając wzorca UPSERT.

        Dlaczego UPSERT zamiast "Check-then-Act"?
        - W środowisku async (FastAPI + SQLAlchemy) nie możemy polegać na SELECT-then-INSERT,
          bo między tymi operacjami inna transakcja może wstawić ten sam rekord (race condition).
        - PostgreSQL UPSERT gwarantuje atomowość i rozwiązuje konflikt na poziomie bazy.

        Strategia UPSERT:
        1. Próbuje INSERT z podanymi danymi
        2. Jeśli konflikt (ten sam raw_name + index_id już istnieje):
           - Zwiększa confirmations_count o 1
           - Aktualizuje last_seen_at
        3. Zwraca utworzony lub zaktualizowany rekord

        Args:
            raw_name: Surowy tekst z OCR (np. "Mleko 3.2%")
            index_id: ID znormalizowanego produktu z ProductIndex
            shop_id: ID sklepu (opcjonalne, dla kontekstu user+shop)
            user_id: ID użytkownika (opcjonalne, dla kontekstu user+shop)
            locale: Locale aliasu (domyślnie "pl_PL")

        Returns:
            ProductIndexAlias: Utworzony lub zaktualizowany alias

        Raises:
            IntegrityError: W przypadku naruszenia FK (product_index_id nie istnieje)
        """
        # PostgreSQL-specific UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
        stmt = (
            pg_insert(ProductIndexAlias)
            .values(
                raw_name=raw_name,
                index_id=index_id,
                shop_id=shop_id,
                user_id=user_id,
                locale=locale,
                confirmations_count=1,
                first_seen_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                # Konflikt na: LOWER(raw_name) + index_id (zgodnie z uq_alias_raw_name_index)
                index_elements=[
                    func.lower(ProductIndexAlias.raw_name),
                    ProductIndexAlias.index_id,
                ],
                set_={
                    "confirmations_count": ProductIndexAlias.confirmations_count + 1,
                    "last_seen_at": datetime.utcnow(),
                },
            )
            .returning(ProductIndexAlias)
        )

        result = await self.session.execute(stmt)
        alias = result.scalar_one()

        # Commit transaction
        await self.session.commit()
        await self.session.refresh(alias)

        return alias
