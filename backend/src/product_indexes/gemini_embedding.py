import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from google.api_core import exceptions as google_exceptions
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import settings
from src.product_indexes.embeddings import (
    BeforeAttempt,
    EmbeddingTask,
    OnAttempt,
    embedding_values,
)
from src.product_indexes.models import PRODUCT_INDEX_EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


def _should_retry_embedding_error(exception: BaseException) -> bool:
    return isinstance(
        exception,
        (
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
            google_exceptions.InternalServerError,
            google_exceptions.DeadlineExceeded,
            google_exceptions.Aborted,
        ),
    )


class GeminiProductNameEmbedder:
    """One Gemini embedding model for product names stored in the catalog."""

    def __init__(
        self,
        embed: Callable[..., Awaitable[object]] | None = None,
    ) -> None:
        self._embed = embed

    async def embed_name(
        self,
        name: str,
        *,
        task_type: EmbeddingTask = "retrieval_document",
        before_attempt: BeforeAttempt | None = None,
        on_attempt: OnAttempt | None = None,
    ) -> list[float]:
        vector = embedding_values(
            await self._request(name, task_type, before_attempt, on_attempt)
        )
        logger.info(
            "Embedded product name with %s (%s, %s dimensions).",
            settings.GEMINI_EMBEDDING_MODEL,
            task_type,
            len(vector),
        )
        return vector

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry_embedding_error),
        reraise=True,
    )
    async def _request(
        self,
        name: str,
        task_type: EmbeddingTask,
        before_attempt: BeforeAttempt | None,
        on_attempt: OnAttempt | None,
    ) -> object:
        if before_attempt is not None:
            await before_attempt()
        started = time.perf_counter()
        try:
            embed = self._embed or _gemini_embed_content
            return await embed(
                model=settings.GEMINI_EMBEDDING_MODEL,
                content=name,
                task_type=task_type,
                output_dimensionality=PRODUCT_INDEX_EMBEDDING_DIMENSIONS,
                request_options={"timeout": settings.GEMINI_TIMEOUT},
            )
        finally:
            if on_attempt is not None:
                await on_attempt(int((time.perf_counter() - started) * 1000))


async def _gemini_embed_content(**kwargs: Any) -> object:
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
    return await genai.embed_content_async(**kwargs)  # type: ignore[attr-defined]
