"""Vector search keeps a near catalog name and drops one below the threshold."""

import tests.orm  # noqa: F401
from sqlalchemy import delete
from tests.fakes import FrozenProductNameEmbedder

from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS, ProductIndex
from src.product_indexes.schemas import ProductIndexCreate
from src.product_indexes.services import ProductIndexService

NEAR_NAME = "mleko wektor bliskie"
FAR_NAME = "kefir wektor daleki"
THRESHOLD = 0.85


def _basis(index: int) -> list[float]:
    vector = [0.0] * PRODUCT_INDEX_EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


class NamedEmbedder(FrozenProductNameEmbedder):
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        super().__init__()
        self._vectors = vectors

    async def embed_name(self, name: str) -> list[float]:
        self.calls.append(name)
        return list(self._vectors[name])


async def test_vector_search_uses_the_threshold(db_session) -> None:
    near = _basis(0)
    far = _basis(1)
    other = _basis(2)
    await db_session.execute(
        delete(ProductIndex).where(ProductIndex.name.in_([NEAR_NAME, FAR_NAME]))
    )
    await db_session.commit()
    embedder = NamedEmbedder({NEAR_NAME: near, FAR_NAME: far})
    service = ProductIndexService(db_session, embedder)

    try:
        assert (
            await service.search_by_embedding(near, threshold=THRESHOLD, top_k=5)
            is None
        )
        await service.create(ProductIndexCreate(name=NEAR_NAME))
        await service.create(ProductIndexCreate(name=FAR_NAME))

        matched = await service.search_by_embedding(near, threshold=THRESHOLD, top_k=5)
        assert matched is not None
        assert matched.name == NEAR_NAME

        rejected = await service.search_by_embedding(
            other, threshold=THRESHOLD, top_k=5
        )
        assert rejected is None
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(ProductIndex).where(ProductIndex.name.in_([NEAR_NAME, FAR_NAME]))
        )
        await db_session.commit()
