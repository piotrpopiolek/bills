from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.product_indexes.models import ProductIndex
from src.product_indexes.schemas import ProductIndexCreate, ProductIndexUpdate


class ProductIndexService(
    AppService[ProductIndex, ProductIndexCreate, ProductIndexUpdate]
):
    def __init__(self, session: AsyncSession):
        super().__init__(model=ProductIndex, session=session)

    async def _ensure_unique_name(
        self, name: str, exclude_id: int | None = None
    ) -> None:
        """
        Checks if a product name (case-insensitive) already exists.
        Used to prevent duplicate product names.
        """
        stmt = select(ProductIndex).where(
            func.lower(ProductIndex.name) == func.lower(name)
        )

        if exclude_id is not None:
            stmt = stmt.where(ProductIndex.id != exclude_id)

        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise ResourceAlreadyExistsError("ProductIndex", "name", name)

    async def create(self, data: ProductIndexCreate) -> ProductIndex:
        # Category Existence Check (if provided)
        if data.category_id:
            await self._ensure_exists(
                model=Category,
                field=Category.id,
                value=data.category_id,
                resource_name="Category",
            )

        # Uniqueness Check (case-insensitive name)
        await self._ensure_unique_name(data.name)

        # Object Construction
        new_product_index = ProductIndex(
            name=data.name, synonyms=data.synonyms, category_id=data.category_id
        )

        # Persistence (Unit of Work)
        self.session.add(new_product_index)

        try:
            await self.session.commit()
            await self.session.refresh(new_product_index)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "uq_product_indexes_name_lower" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "ProductIndex", "name", data.name
                ) from e
            raise e

        return new_product_index

    async def update(
        self, product_index_id: int, data: ProductIndexUpdate
    ) -> ProductIndex:
        product_index = await self.get_by_id(product_index_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return product_index

        # Category Existence Check (if category_id is being updated)
        if (
            "category_id" in update_data
            and update_data["category_id"] != product_index.category_id
        ):
            new_category_id = update_data["category_id"]
            if new_category_id is not None:
                await self._ensure_exists(
                    model=Category,
                    field=Category.id,
                    value=new_category_id,
                    resource_name="Category",
                )

        # Uniqueness Check (if name is being updated)
        if "name" in update_data and update_data["name"] != product_index.name:
            await self._ensure_unique_name(
                update_data["name"], exclude_id=product_index.id
            )

        # Apply updates
        for key, value in update_data.items():
            setattr(product_index, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(product_index)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "uq_product_indexes_name_lower" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "ProductIndex", "name", update_data.get("name", product_index.name)
                ) from e
            raise e

        return product_index

    async def create_or_get_existing(self, data: ProductIndexCreate) -> ProductIndex:
        """
        Tworzy nowy ProductIndex lub zwraca istniejący, jeśli nazwa już istnieje (case-insensitive).

        Most Koncepcyjny (PHP → Python):
        W Doctrine używałbyś findOneBy() z LOWER() w DQL, a następnie create() jeśli nie znaleziono.
        W SQLAlchemy używamy func.lower() do case-insensitive porównania - idiomatyczne dla PostgreSQL.

        Args:
            data: Dane do utworzenia ProductIndex

        Returns:
            ProductIndex: Utworzony lub istniejący ProductIndex

        Raises:
            ResourceNotFoundError: Jeśli category_id podane i kategoria nie istnieje
        """
        # Category Existence Check (if provided)
        if data.category_id:
            await self._ensure_exists(
                model=Category,
                field=Category.id,
                value=data.category_id,
                resource_name="Category",
            )

        # Sprawdź czy ProductIndex o tej samej nazwie już istnieje (case-insensitive)
        stmt = select(ProductIndex).where(
            func.lower(ProductIndex.name) == func.lower(data.name)
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Utwórz nowy ProductIndex
        new_product_index = ProductIndex(
            name=data.name, synonyms=data.synonyms, category_id=data.category_id
        )

        # Persistence (Unit of Work)
        self.session.add(new_product_index)

        try:
            await self.session.commit()
            await self.session.refresh(new_product_index)
        except IntegrityError as e:
            await self.session.rollback()
            # Jeśli ktoś inny utworzył w międzyczasie (race condition), spróbuj ponownie znaleźć
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise e

        return new_product_index

    async def fuzzy_search(
        self, search_text: str, threshold: float = 0.75
    ) -> ProductIndex | None:
        """
        Wyszukuje ProductIndex używając fuzzy search (PostgreSQL pg_trgm).

        Most Koncepcyjny (PHP → Python):
        W Doctrine używałbyś natywnego SQL z similarity() z pg_trgm.
        W SQLAlchemy używamy func.similarity() - idiomatyczne dla PostgreSQL.

        Args:
            search_text: Tekst do wyszukania
            threshold: Próg podobieństwa (0.0-1.0), domyślnie 0.75

        Returns:
            ProductIndex jeśli znaleziono match, None w przeciwnym razie
        """
        stmt = (
            select(
                ProductIndex,
                func.similarity(
                    func.lower(ProductIndex.name), func.lower(search_text)
                ).label("score"),
            )
            .where(
                func.similarity(func.lower(ProductIndex.name), func.lower(search_text))
                >= threshold
            )
            .order_by(
                func.similarity(
                    func.lower(ProductIndex.name), func.lower(search_text)
                ).desc()
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        return row[0] if row else None

    async def delete(self, product_index_id: int) -> None:
        product_index = await self.get_by_id(product_index_id)

        self.session.delete(product_index)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
