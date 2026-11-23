"""Two reservations at the same time take only one slot."""

import asyncio

import tests.orm  # noqa: F401
from sqlalchemy import delete

from src.ai.models import ModelCall
from src.ai.usage import ModelUsage
from src.config import settings


async def test_parallel_embedding_reserves_take_one_slot(
    db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_DAILY_LIMIT", 1)
    await db_session.execute(
        delete(ModelCall).where(ModelCall.call_kind == "embedding")
    )
    await db_session.commit()
    usage = ModelUsage(db_session)

    try:
        first, second = await asyncio.gather(
            usage.try_reserve_embedding(model="budget-lock-test"),
            usage.try_reserve_embedding(model="budget-lock-test"),
        )
        reserved = [call_id for call_id in (first, second) if call_id is not None]
        assert len(reserved) == 1
        assert first is None or second is None
    finally:
        await db_session.execute(
            delete(ModelCall).where(ModelCall.model == "budget-lock-test")
        )
        await db_session.commit()
