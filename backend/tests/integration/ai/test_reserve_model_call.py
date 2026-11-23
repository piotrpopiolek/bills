"""Two reservations at the same time take only one slot."""

import asyncio

import tests.orm  # noqa: F401
from sqlalchemy import delete, func, select, text

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


async def test_receipt_reserves_every_line_or_none(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "GENERATIVE_DAILY_LIMIT", 1)
    user_id = await db_session.scalar(
        text("insert into users (external_id) values (910099) returning id")
    )
    await db_session.commit()
    usage = ModelUsage(db_session)
    try:
        assert (
            await usage.try_reserve_generative_many(
                user_id=user_id, model="receipt-budget", count=2
            )
            is None
        )
        monkeypatch.setattr(settings, "GENERATIVE_DAILY_LIMIT", 2)
        slots = await usage.try_reserve_generative_many(
            user_id=user_id, model="receipt-budget", count=2
        )
        assert slots is not None and len(slots) == 2
    finally:
        await db_session.execute(
            delete(ModelCall).where(ModelCall.model == "receipt-budget")
        )
        await db_session.execute(text("delete from users where external_id = 910099"))
        await db_session.commit()


async def test_recorded_call_survives_caller_rollback(db_session) -> None:
    usage = ModelUsage(db_session)
    await usage.record_embedding(model="rollback-test", latency_ms=4)
    await db_session.rollback()
    factory = usage._session_factory()
    async with factory() as other:
        kept = await other.scalar(
            select(func.count())
            .select_from(ModelCall)
            .where(ModelCall.model == "rollback-test")
        )
    await db_session.execute(
        delete(ModelCall).where(ModelCall.model == "rollback-test")
    )
    await db_session.commit()
    assert kept == 1
