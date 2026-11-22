"""Product-name embeddings are stored on write. The vector is frozen, with no network."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import tests.orm  # noqa: F401
from tests.fakes import FROZEN_PRODUCT_EMBEDDING, FrozenProductNameEmbedder

from src.product_indexes.embeddings import embedding_values
from src.product_indexes.exceptions import EmbeddingError
from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS, ProductIndex
from src.product_indexes.schemas import ProductIndexCreate, ProductIndexUpdate
from src.product_indexes.services import ProductIndexService


def _session(*, existing: ProductIndex | None = None) -> AsyncMock:
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    result.scalar_one_or_none.return_value = existing
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


def test_embedding_values_reads_a_768_vector() -> None:
    assert embedding_values({"embedding": FROZEN_PRODUCT_EMBEDDING}) == (
        FROZEN_PRODUCT_EMBEDDING
    )


def test_embedding_values_rejects_the_wrong_width() -> None:
    with pytest.raises(EmbeddingError, match="3072"):
        embedding_values({"embedding": [0.1] * 3072})


def test_embedding_values_rejects_a_response_without_numbers() -> None:
    with pytest.raises(EmbeddingError, match="listy liczb"):
        embedding_values({"embedding": ["mleko"]})


async def test_create_stores_the_frozen_embedding() -> None:
    embedder = FrozenProductNameEmbedder()
    session = _session()
    service = ProductIndexService(session, embedder)

    created = await service.create(ProductIndexCreate(name="Mleko 3.2%"))

    assert embedder.calls == ["Mleko 3.2%"]
    assert embedder.tasks == ["retrieval_document"]
    assert created.embedding == FROZEN_PRODUCT_EMBEDDING
    session.add.assert_called_once_with(created)


async def test_create_does_not_save_when_the_vector_has_the_wrong_width() -> None:
    session = _session()
    service = ProductIndexService(session, FrozenProductNameEmbedder([0.1, 0.2]))

    with pytest.raises(EmbeddingError, match="2 wymiarów"):
        await service.create(ProductIndexCreate(name="Mleko 3.2%"))

    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_existing_name_does_not_embed_again() -> None:
    existing = ProductIndex(id=4, name="Mleko 3.2%", embedding=FROZEN_PRODUCT_EMBEDDING)
    embedder = FrozenProductNameEmbedder()
    service = ProductIndexService(_session(existing=existing), embedder)

    found = await service.create_or_get_existing(ProductIndexCreate(name="Mleko 3.2%"))

    assert found is existing
    assert embedder.calls == []


async def test_existing_row_without_embedding_is_backfilled() -> None:
    existing = ProductIndex(id=4, name="Mleko 3.2%", embedding=None)
    embedder = FrozenProductNameEmbedder()
    session = _session(existing=existing)
    service = ProductIndexService(session, embedder)

    found = await service.create_or_get_existing(ProductIndexCreate(name="mleko 3.2%"))

    assert found is existing
    assert found.embedding == FROZEN_PRODUCT_EMBEDDING
    assert embedder.calls == ["Mleko 3.2%"]
    assert embedder.tasks == ["retrieval_document"]
    session.flush.assert_awaited_once_with([existing])
    session.commit.assert_not_called()


async def test_receipt_query_uses_retrieval_query() -> None:
    embedder = FrozenProductNameEmbedder()
    service = ProductIndexService(AsyncMock(), embedder)

    await service.embed_name("MLEKO 3.2%")

    assert embedder.tasks == ["retrieval_query"]


async def test_renaming_recomputes_the_embedding() -> None:
    existing = ProductIndex(id=4, name="Mleko", embedding=[0.0] * 768)
    embedder = FrozenProductNameEmbedder()
    service = ProductIndexService(_session(existing=existing), embedder)

    updated = await service.update(4, ProductIndexUpdate(name="Kefir"))

    assert updated.embedding == FROZEN_PRODUCT_EMBEDDING
    assert embedder.calls == ["Kefir"]


async def test_category_change_does_not_embed() -> None:
    existing = ProductIndex(
        id=4, name="Mleko", category_id=1, embedding=FROZEN_PRODUCT_EMBEDDING
    )
    embedder = FrozenProductNameEmbedder()
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing
    category = MagicMock()
    category.scalars.return_value.first.return_value = object()
    session = _session(existing=existing)
    session.execute = AsyncMock(side_effect=[found, category])
    service = ProductIndexService(session, embedder)

    updated = await service.update(4, ProductIndexUpdate(category_id=9))

    assert updated.embedding == FROZEN_PRODUCT_EMBEDDING
    assert embedder.calls == []


async def test_injected_embedder_never_calls_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in {
        "ENV": "test",
        "PORT": "8000",
        "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5433/postgres",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "OPENAI_API_KEY": "test-openai",
        "GEMINI_API_KEY": "test-gemini",
        "JWT_SECRET_KEY": "test-jwt",
    }.items():
        monkeypatch.setenv(key, value)

    from src.config import settings
    from src.product_indexes.gemini_embedding import GeminiProductNameEmbedder

    seen: dict[str, Any] = {}

    async def embed(**kwargs: Any) -> dict[str, list[float]]:
        seen.update(kwargs)
        return {"embedding": FROZEN_PRODUCT_EMBEDDING}

    embedder = GeminiProductNameEmbedder(embed=embed)
    stored = await embedder.embed_name("Mleko 3.2%")
    assert stored == FROZEN_PRODUCT_EMBEDDING
    assert seen["task_type"] == "retrieval_document"

    query = await embedder.embed_name("Mleko 3.2%", task_type="retrieval_query")
    assert query == FROZEN_PRODUCT_EMBEDDING
    assert seen["content"] == "Mleko 3.2%"
    assert seen["task_type"] == "retrieval_query"
    assert seen["output_dimensionality"] == PRODUCT_INDEX_EMBEDDING_DIMENSIONS
    assert seen["model"] == settings.GEMINI_EMBEDDING_MODEL
