"""A new catalog row stores the frozen product-name embedding. No network."""

import tests.orm  # noqa: F401
from sqlalchemy import delete
from tests.fakes import FROZEN_PRODUCT_EMBEDDING, FrozenProductNameEmbedder

from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS, ProductIndex
from src.product_indexes.schemas import ProductIndexCreate
from src.product_indexes.services import ProductIndexService

NAME = "mleko testowe embedding"


async def test_create_persists_frozen_embedding(db_session) -> None:
    await db_session.execute(delete(ProductIndex).where(ProductIndex.name == NAME))
    await db_session.commit()
    embedder = FrozenProductNameEmbedder()
    service = ProductIndexService(db_session, embedder)

    try:
        created = await service.create(ProductIndexCreate(name=NAME))
        await db_session.refresh(created)
        assert embedder.calls == [NAME]
        assert created.embedding == FROZEN_PRODUCT_EMBEDDING
        assert len(created.embedding or []) == PRODUCT_INDEX_EMBEDDING_DIMENSIONS
    finally:
        await db_session.rollback()
        await db_session.execute(delete(ProductIndex).where(ProductIndex.name == NAME))
        await db_session.commit()
