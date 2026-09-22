from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.categories.models import Category
from src.common.exceptions import ResourceNotFoundError
from src.common.services import AppService
from src.product_candidates.models import ProductCandidate
from src.product_candidates.schemas import (
    ProductCandidateCreate,
    ProductCandidateUpdate,
)
from src.product_indexes.models import ProductIndex


class ProductCandidateService(
    AppService[ProductCandidate, ProductCandidateCreate, ProductCandidateUpdate]
):
    """
    Service layer dla ProductCandidate.

    Dziedziczy z AppService, który zapewnia podstawowe operacje CRUD.
    Dodaje walidację powiązań (category_id, product_index_id).
    """

    def __init__(self, session: AsyncSession):
        super().__init__(model=ProductCandidate, session=session)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
        category_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Pobiera listę product candidates z opcjonalnym filtrowaniem.

        Args:
            skip: Liczba elementów do pominięcia
            limit: Maksymalna liczba elementów do zwrócenia
            search: Wyszukiwanie po representative_name (case-insensitive, partial match)
            status: Filtr po statusie (pending, approved, rejected)
            category_id: Filtr po kategorii

        Returns:
            Słownik z items, total, skip, limit
        """
        # Buduj zapytanie z filtrami
        stmt = select(ProductCandidate)
        count_stmt = select(func.count()).select_from(ProductCandidate)

        # Załaduj relacje
        stmt = stmt.options(
            selectinload(ProductCandidate.category),
            selectinload(ProductCandidate.product_index),
        )

        # Filtry
        conditions = []

        if search:
            conditions.append(ProductCandidate.representative_name.ilike(f"%{search}%"))

        if status:
            conditions.append(ProductCandidate.status == status)

        if category_id is not None:
            conditions.append(ProductCandidate.category_id == category_id)

        # Zastosuj warunki
        if conditions:
            where_clause = conditions[0]
            for condition in conditions[1:]:
                where_clause = where_clause & condition
            stmt = stmt.where(where_clause)
            count_stmt = count_stmt.where(where_clause)

        # Liczenie total
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Pobranie danych z paginacją i sortowaniem
        stmt = (
            stmt.order_by(ProductCandidate.created_at.desc()).offset(skip).limit(limit)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def create(self, data: ProductCandidateCreate) -> ProductCandidate:
        """
        Tworzy nowy ProductCandidate z walidacją powiązań.

        Args:
            data: Dane do utworzenia ProductCandidate

        Returns:
            ProductCandidate: Utworzony obiekt

        Raises:
            ResourceNotFoundError: Jeśli category_id lub product_index_id nie istnieją
        """
        # Walidacja category_id (jeśli podane)
        if data.category_id:
            await self._ensure_exists(
                model=Category,
                field=Category.id,
                value=data.category_id,
                resource_name="Category",
            )

        # Walidacja product_index_id (jeśli podane)
        if data.product_index_id:
            await self._ensure_exists(
                model=ProductIndex,
                field=ProductIndex.id,
                value=data.product_index_id,
                resource_name="ProductIndex",
            )

        # Utworzenie obiektu
        new_product_candidate = ProductCandidate(
            representative_name=data.representative_name,
            user_confirmations=data.user_confirmations,
            category_id=data.category_id,
            product_index_id=data.product_index_id,
            status=data.status,
        )

        # Persystencja (Unit of Work)
        self.session.add(new_product_candidate)

        try:
            await self.session.commit()
            await self.session.refresh(new_product_candidate)
        except IntegrityError as e:
            await self.session.rollback()
            # Sprawdzenie czy to naruszenie foreign key
            if self._is_foreign_key_violation(e):
                # Określenie, które powiązanie nie istnieje
                if data.category_id:
                    raise ResourceNotFoundError("Category", data.category_id) from e
                if data.product_index_id:
                    raise ResourceNotFoundError(
                        "ProductIndex", data.product_index_id
                    ) from e
            raise e

        return new_product_candidate

    async def update(
        self, product_candidate_id: int, data: ProductCandidateUpdate
    ) -> ProductCandidate:
        """
        Aktualizuje ProductCandidate z walidacją powiązań.

        Args:
            product_candidate_id: ID ProductCandidate do aktualizacji
            data: Dane do aktualizacji

        Returns:
            ProductCandidate: Zaktualizowany obiekt

        Raises:
            ResourceNotFoundError: Jeśli ProductCandidate nie istnieje lub powiązanie nie istnieje
        """
        product_candidate = await self.get_by_id(product_candidate_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return product_candidate

        # Walidacja category_id (jeśli jest aktualizowane)
        if (
            "category_id" in update_data
            and update_data["category_id"] != product_candidate.category_id
        ):
            new_category_id = update_data["category_id"]
            if new_category_id is not None:
                await self._ensure_exists(
                    model=Category,
                    field=Category.id,
                    value=new_category_id,
                    resource_name="Category",
                )

        # Walidacja product_index_id (jeśli jest aktualizowane)
        if (
            "product_index_id" in update_data
            and update_data["product_index_id"] != product_candidate.product_index_id
        ):
            new_product_index_id = update_data["product_index_id"]
            if new_product_index_id is not None:
                await self._ensure_exists(
                    model=ProductIndex,
                    field=ProductIndex.id,
                    value=new_product_index_id,
                    resource_name="ProductIndex",
                )

        # Zastosowanie aktualizacji
        for key, value in update_data.items():
            setattr(product_candidate, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(product_candidate)
        except IntegrityError as e:
            await self.session.rollback()
            # Sprawdzenie czy to naruszenie foreign key
            if self._is_foreign_key_violation(e):
                if "category_id" in update_data and update_data.get("category_id"):
                    raise ResourceNotFoundError(
                        "Category", update_data["category_id"]
                    ) from e
                if "product_index_id" in update_data and update_data.get(
                    "product_index_id"
                ):
                    raise ResourceNotFoundError(
                        "ProductIndex", update_data["product_index_id"]
                    ) from e
            raise e

        return product_candidate

    async def delete(self, product_candidate_id: int) -> None:
        """
        Usuwa ProductCandidate.

        Args:
            product_candidate_id: ID ProductCandidate do usunięcia

        Raises:
            ResourceNotFoundError: Jeśli ProductCandidate nie istnieje
        """
        product_candidate = await self.get_by_id(product_candidate_id)

        self.session.delete(product_candidate)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
