"""A spent daily limit does not call the generative model."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from tests.fakes import FrozenProductNameEmbedder

from src.ai.usage import (
    budget_covers,
    call_cost,
    generative_call_allowed,
    run_if_allowed,
)
from src.product_indexes.exceptions import EmbeddingBudgetExceeded
from src.product_indexes.services import ProductIndexService


def test_call_cost_uses_the_per_thousand_token_rate() -> None:
    assert call_cost(2000, 0.15) == Decimal("0.30")
    assert call_cost(None, 0.15) == Decimal("0")


def test_lock_keys_do_not_collide() -> None:
    from src.ai.usage import _lock_key

    assert _lock_key("embedding", None) != _lock_key("generative", 1)
    assert _lock_key("generative", 1) != _lock_key("generative", 2)


def test_receipt_needs_a_slot_for_every_line() -> None:
    assert budget_covers(48, 2, 50) is True
    assert budget_covers(49, 2, 50) is False


def test_limit_blocks_at_the_boundary() -> None:
    assert generative_call_allowed(49, 50) is True
    assert generative_call_allowed(50, 50) is False


async def test_spent_limit_does_not_call_the_model() -> None:
    called = False

    async def call() -> str:
        nonlocal called
        called = True
        return "gemini"

    result = await run_if_allowed(used_today=50, limit=50, call=call)

    assert result is None
    assert called is False


async def test_embedding_budget_does_not_call_the_model() -> None:
    class SpentBudget:
        async def try_reserve_embedding(self, *, model: str) -> int | None:
            return None

        async def finish_embedding(self, call_id: int, *, latency_ms: int) -> None:
            raise AssertionError(call_id)

    embedder = FrozenProductNameEmbedder()
    service = ProductIndexService(AsyncMock(), embedder, usage=SpentBudget())

    with pytest.raises(EmbeddingBudgetExceeded):
        await service.embed_name("mleko")

    assert embedder.calls == []
