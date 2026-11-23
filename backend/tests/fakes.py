"""Test doubles that do not open a database or the network."""

from collections.abc import Awaitable, Callable

from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS

FROZEN_PRODUCT_EMBEDDING = [0.25] * PRODUCT_INDEX_EMBEDDING_DIMENSIONS


class FrozenProductNameEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = list(FROZEN_PRODUCT_EMBEDDING if vector is None else vector)
        self.calls: list[str] = []
        self.tasks: list[str] = []

    async def embed_name(
        self,
        name: str,
        *,
        task_type: str = "retrieval_document",
        before_attempt: Callable[[], Awaitable[None]] | None = None,
        on_attempt: Callable[[int], Awaitable[None]] | None = None,
    ) -> list[float]:
        if before_attempt is not None:
            await before_attempt()
        self.calls.append(name)
        self.tasks.append(task_type)
        if on_attempt is not None:
            await on_attempt(0)
        return list(self.vector)
