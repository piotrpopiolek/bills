from contextvars import ContextVar
from typing import Protocol, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.config import settings
from src.product_indexes.catalog import CatalogHit
from src.product_indexes.embeddings import EmbeddingTask, ProductNameEmbedder
from src.product_indexes.exceptions import EmbeddingBudgetExceeded, EmbeddingError
from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS, ProductIndex
from src.product_indexes.schemas import ProductIndexCreate, ProductIndexUpdate


class EmbeddingUsage(Protocol):
    async def try_reserve_embedding(self, *, model: str) -> int | None: ...

    async def finish_embedding(self, call_id: int, *, latency_ms: int) -> None: ...


_embedding_reservation: ContextVar[int | None] = ContextVar(
    "embedding_reservation", default=None
)


class ProductIndexService(
    AppService[ProductIndex, ProductIndexCreate, ProductIndexUpdate]
):
    def __init__(
        self,
        session: AsyncSession,
        embedder: ProductNameEmbedder | None = None,
        usage: EmbeddingUsage | None = None,
    ):
        super().__init__(model=ProductIndex, session=session)
        self._embedder = embedder
        self._usage = usage

    def _name_embedder(self) -> ProductNameEmbedder:
        if self._embedder is None:
            from src.product_indexes.gemini_embedding import GeminiProductNameEmbedder

            self._embedder = GeminiProductNameEmbedder()
        return self._embedder

    async def _embedding_for(
        self, name: str, *, task_type: EmbeddingTask = "retrieval_document"
    ) -> list[float]:
        vector = await self._name_embedder().embed_name(
            name,
            task_type=task_type,
            before_attempt=self._reject_if_over_budget,
            on_attempt=self._record_embedding_attempt,
        )
        if len(vector) != PRODUCT_INDEX_EMBEDDING_DIMENSIONS:
            raise EmbeddingError(
                f"Embedding ma {len(vector)} wymiarów, "
                f"oczekiwano {PRODUCT_INDEX_EMBEDDING_DIMENSIONS}."
            )
        return vector

    async def _reject_if_over_budget(self) -> None:
        if self._usage is None:
            return
        call_id = await self._usage.try_reserve_embedding(
            model=settings.GEMINI_EMBEDDING_MODEL
        )
        if call_id is None:
            raise EmbeddingBudgetExceeded
        _embedding_reservation.set(call_id)

    async def _record_embedding_attempt(self, latency_ms: int) -> None:
        call_id = _embedding_reservation.get()
        if self._usage is None or call_id is None:
            return
        await self._usage.finish_embedding(call_id, latency_ms=latency_ms)
        _embedding_reservation.set(None)

    async def _embedding_or_none(self, name: str) -> list[float] | None:
        try:
            return await self._embedding_for(name)
        except EmbeddingBudgetExceeded:
            return None

    async def embed_name(self, name: str) -> list[float]:
        """Embed an OCR query. Catalog rows stay retrieval_document."""
        return await self._embedding_for(name, task_type="retrieval_query")

    async def _backfill_embedding(self, product: ProductIndex) -> ProductIndex:
        """Store a missing embedding without committing the shared session."""
        if product.embedding is not None:
            return product
        try:
            product.embedding = await self._embedding_for(product.name)
        except EmbeddingBudgetExceeded:
            return product
        await self.session.flush([product])
        return product

    async def nearest_catalog(
        self, query: list[float], *, top_k: int
    ) -> list[tuple[ProductIndex, CatalogHit]]:
        """Top-k catalog rows nearest to the query, with category names."""
        if len(query) != PRODUCT_INDEX_EMBEDDING_DIMENSIONS:
            raise EmbeddingError(
                f"Embedding ma {len(query)} wymiarów, "
                f"oczekiwano {PRODUCT_INDEX_EMBEDDING_DIMENSIONS}."
            )
        if top_k < 1:
            return []
        distance = ProductIndex.embedding.cosine_distance(query)
        similarity = (1 - distance).label("similarity")
        stmt = (
            select(ProductIndex, Category.name, similarity)
            .outerjoin(Category, Category.id == ProductIndex.category_id)
            .where(ProductIndex.embedding.is_not(None))
            .order_by(distance.asc())
            .limit(top_k)
        )
        found: list[tuple[ProductIndex, CatalogHit]] = []
        for row in (await self.session.execute(stmt)).all():
            product = cast(ProductIndex, row[0])
            category_name = cast(str | None, row[1])
            score = 0.0 if row[2] is None else float(row[2])
            found.append(
                (
                    product,
                    CatalogHit(
                        name=product.name,
                        category_name=category_name,
                        similarity=score,
                    ),
                )
            )
        return found

    async def search_by_embedding(
        self,
        query: list[float],
        *,
        threshold: float,
        top_k: int,
    ) -> ProductIndex | None:
        """Nearest catalog name at or above the cosine similarity threshold."""
        rows = await self.nearest_catalog(query, top_k=top_k)
        if not rows or rows[0][1].similarity < threshold:
            return None
        return rows[0][0]

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

        embedding = await self._embedding_or_none(data.name)
        new_product_index = ProductIndex(
            name=data.name,
            synonyms=data.synonyms,
            category_id=data.category_id,
            embedding=embedding,
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

        new_name = update_data.get("name")
        if isinstance(new_name, str) and new_name != product_index.name:
            await self._ensure_unique_name(new_name, exclude_id=product_index.id)
            update_data["embedding"] = await self._embedding_or_none(new_name)

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

    async def create_or_get_existing(
        self, data: ProductIndexCreate, *, commit: bool = True
    ) -> ProductIndex:
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
            return await self._backfill_embedding(existing)

        embedding = await self._embedding_or_none(data.name)
        new_product_index = ProductIndex(
            name=data.name,
            synonyms=data.synonyms,
            category_id=data.category_id,
            embedding=embedding,
        )

        # Persistence (Unit of Work)
        self.session.add(new_product_index)

        try:
            if commit:
                await self.session.commit()
            else:
                await self.session.flush()
            await self.session.refresh(new_product_index)
        except IntegrityError as e:
            await self.session.rollback()
            # Jeśli ktoś inny utworzył w międzyczasie (race condition), spróbuj ponownie znaleźć
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return await self._backfill_embedding(existing)
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

        await self.session.delete(product_index)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
