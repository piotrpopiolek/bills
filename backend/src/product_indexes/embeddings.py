from typing import Literal, Protocol

from src.product_indexes.exceptions import EmbeddingError
from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS

EmbeddingTask = Literal["retrieval_document", "retrieval_query"]


class ProductNameEmbedder(Protocol):
    async def embed_name(self, name: str, *, task_type: EmbeddingTask) -> list[float]:
        """Return a 768-dimensional embedding of a product name."""


def embedding_values(payload: object) -> list[float]:
    """Read one embedding list from a Gemini embed_content response."""
    raw = payload.get("embedding") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        raise EmbeddingError("Odpowiedź modelu embeddingów nie zawiera listy liczb.")
    try:
        values = [float(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise EmbeddingError(
            "Odpowiedź modelu embeddingów nie zawiera listy liczb."
        ) from exc
    if len(values) != PRODUCT_INDEX_EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"Embedding ma {len(values)} wymiarów, "
            f"oczekiwano {PRODUCT_INDEX_EMBEDDING_DIMENSIONS}."
        )
    return values
