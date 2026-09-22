import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.models import BillItem
from src.categories.exceptions import CategoryCycleError, CategoryHasChildrenError
from src.categories.models import Category
from src.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.config import settings
from src.product_indexes.models import ProductIndex

logger = logging.getLogger(__name__)


class CategoryService(AppService[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=Category, session=session)

    async def _to_response(self, category: Category) -> CategoryResponse:
        """
        Convert Category model to CategoryResponse schema with counts of related products and bill items.

        This method encapsulates the logic for counting related entities
        and converting Category models to CategoryResponse schemas, following
        the DRY principle to avoid code duplication.

        Args:
            category: The Category model instance to convert

        Returns:
            CategoryResponse with products_count and bill_items_count populated
        """
        # Count related products (ProductIndex)
        products_count_stmt = select(func.count(ProductIndex.id)).where(
            ProductIndex.category_id == category.id
        )
        products_count_result = await self.session.execute(products_count_stmt)
        products_count = products_count_result.scalar() or 0

        # Count related bill items
        bill_items_count_stmt = select(func.count(BillItem.id)).where(
            BillItem.category_id == category.id
        )
        bill_items_count_result = await self.session.execute(bill_items_count_stmt)
        bill_items_count = bill_items_count_result.scalar() or 0

        response = CategoryResponse.model_validate(category, from_attributes=True)
        response.products_count = products_count
        response.bill_items_count = bill_items_count
        return response

    async def create(self, data: CategoryCreate) -> CategoryResponse:
        await self._ensure_unique(
            model=Category,
            field=Category.name,
            value=data.name,
            resource_name="Category",
            field_name="name",
        )

        # Parent Existence Check (Referential Integrity check before DB hit)
        if data.parent_id:
            await self._ensure_exists(
                model=Category,
                field=Category.id,
                value=data.parent_id,
                resource_name="Parent Category",
            )

        # Object Construction
        new_category = Category(name=data.name, parent_id=data.parent_id)

        # Persistence (Unit of Work)
        self.session.add(new_category)

        try:
            await self.session.commit()
            await self.session.refresh(new_category)
        except IntegrityError as e:
            await self.session.rollback()
            raise ResourceAlreadyExistsError("Category", "name", data.name) from e

        return await self._to_response(new_category)

    async def update(self, category_id: int, data: CategoryUpdate) -> CategoryResponse:
        category = await self.get_by_id(category_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return await self._to_response(category)

        if "name" in update_data and update_data["name"] != category.name:
            await self._ensure_unique(
                model=Category,
                field=Category.name,
                value=update_data["name"],
                resource_name="Category",
                field_name="name",
            )

        if (
            "parent_id" in update_data
            and update_data["parent_id"] != category.parent_id
        ):
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                # Sprawdzenie istnienia rodzica
                await self._ensure_exists(
                    model=Category,
                    field=Category.id,
                    value=new_parent_id,
                    resource_name="Parent Category",
                )

                # Zabezpieczenie przed cyklami (sprawdzenie czy nowy rodzic nie jest potomkiem edytowanej kategorii)
                if await self._check_is_descendant(
                    ancestor_id=category.id, descendant_id=new_parent_id
                ):
                    raise CategoryCycleError()

        # Apply updates
        for key, value in update_data.items():
            setattr(category, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(category)
        except IntegrityError as e:
            await self.session.rollback()
            raise ResourceAlreadyExistsError("Category", "name", data.name) from e

        return await self._to_response(category)

    async def delete(self, category_id: int) -> None:

        category = await self.get_by_id(category_id)

        self.session.delete(category)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()

            if self._is_foreign_key_violation(e):
                raise CategoryHasChildrenError() from e

            raise e

    async def _check_is_descendant(self, ancestor_id: int, descendant_id: int) -> bool:
        """
        Checks if descendant_id is actually a descendant of ancestor_id (or the same).
        Used to prevent cycles when moving a category.
        """
        if ancestor_id == descendant_id:
            return True

        # Recursive CTE to walk up the tree (from descendant to root)
        cte = (
            select(Category.id, Category.parent_id)
            .where(Category.id == descendant_id)
            .cte(name="ancestry", recursive=True)
        )

        parent_alias = select(Category.id, Category.parent_id).join(
            cte, Category.id == cte.c.parent_id
        )
        cte = cte.union_all(parent_alias)

        stmt = select(cte.c.id).where(cte.c.id == ancestor_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_fallback_category(self) -> Category:
        """
        Zwraca kategorię domyślną (fallback) używaną dla nieznanych produktów.

        Strategia:
        1. Próbuje znaleźć kategorię po nazwie z configu (AI_FALLBACK_CATEGORY_NAME)
        2. Jeśli nie istnieje, tworzy ją automatycznie

        Returns:
            Category: Kategoria domyślna (np. "Inne")

        """
        fallback_name = settings.AI_FALLBACK_CATEGORY_NAME

        stmt = select(Category).where(
            func.lower(Category.name) == func.lower(fallback_name)
        )
        result = await self.session.execute(stmt)
        category = result.scalar_one_or_none()

        # Jeśli kategoria nie istnieje, utwórz ją
        if not category:
            from src.categories.schemas import CategoryCreate

            category_data = CategoryCreate(name=fallback_name, parent_id=None)
            category = await self.create(category_data)
            logger.info(f"Utworzono kategorię fallback: {fallback_name}")

        return category

    async def get_by_id(self, category_id: int) -> CategoryResponse:
        """
        Get category by ID with counts of related products and bill items.
        Overrides base method to add counting and convert to response schema.

        Args:
            category_id: ID of the category to retrieve

        Returns:
            CategoryResponse with products_count and bill_items_count populated

        Raises:
            ResourceNotFoundError: If category doesn't exist
        """
        category = await super().get_by_id(category_id)
        return await self._to_response(category)

    async def get_all(self, skip: int = 0, limit: int = 100) -> dict[str, Any]:
        """
        Get all categories with pagination and counts of related products and bill items.
        Uses efficient subqueries to count related entities in a single query per category.

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Dictionary with paginated categories and products_count/bill_items_count populated
        """
        # Count total categories
        count_stmt = select(func.count()).select_from(Category)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Subqueries for counting related entities
        products_count_subq = (
            select(func.count(ProductIndex.id))
            .where(ProductIndex.category_id == Category.id)
            .scalar_subquery()
        )

        bill_items_count_subq = (
            select(func.count(BillItem.id))
            .where(BillItem.category_id == Category.id)
            .scalar_subquery()
        )

        # Fetch categories with counts using subqueries
        stmt = (
            select(
                Category,
                products_count_subq.label("products_count"),
                bill_items_count_subq.label("bill_items_count"),
            )
            .offset(skip)
            .limit(limit)
            .order_by(Category.name)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Convert to response schemas with counts
        categories_with_counts = []
        for row in rows:
            category = row[0]
            products_count = row[1] or 0
            bill_items_count = row[2] or 0

            response = CategoryResponse.model_validate(category, from_attributes=True)
            response.products_count = products_count
            response.bill_items_count = bill_items_count
            categories_with_counts.append(response)

        return {
            "items": categories_with_counts,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_all_categories(self) -> list[Category]:
        """
        Zwraca listę wszystkich kategorii z bazy danych.
        Używane przez AI Categorization do wyboru kategorii przez Gemini API.

        Returns:
            list[Category]: Lista wszystkich kategorii (posortowana alfabetycznie)
        """
        stmt = select(Category).order_by(Category.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
