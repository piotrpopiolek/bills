"""Test doubles that do not open a database or the network."""

from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS

FROZEN_PRODUCT_EMBEDDING = [0.25] * PRODUCT_INDEX_EMBEDDING_DIMENSIONS


class FrozenProductNameEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = list(FROZEN_PRODUCT_EMBEDDING if vector is None else vector)
        self.calls: list[str] = []
        self.tasks: list[str] = []

    async def embed_name(
        self, name: str, *, task_type: str = "retrieval_document"
    ) -> list[float]:
        self.calls.append(name)
        self.tasks.append(task_type)
        return list(self.vector)
