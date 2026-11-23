"""Daily model budgets and the log of each call. Does not commit the session."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.models import ModelCall
from src.config import settings

CallOutcome = Literal["accepted", "to_verify", "rejected"]
_EMBEDDING_LOCK_KEY = 1
_GENERATIVE_LOCK_OFFSET = 1_000_000_000


def _lock_key(call_kind: str, user_id: int | None) -> int:
    """Keep embedding and per-user generative reservations on different locks."""
    if call_kind == "embedding":
        return _EMBEDDING_LOCK_KEY
    if user_id is None:
        return 2
    return _GENERATIVE_LOCK_OFFSET + user_id


def generative_call_allowed(used_today: int, limit: int) -> bool:
    """The model may run only while today's count is still under the limit."""
    return used_today < limit


def call_cost(tokens: int | None, cost_per_1k_tokens: float) -> Decimal:
    """Unit price is per 1 000 tokens. A call without a token count costs nothing."""
    if tokens is None or tokens <= 0:
        return Decimal("0")
    return Decimal(str(cost_per_1k_tokens)) * Decimal(tokens) / Decimal(1000)


class ModelUsage:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generative_used_today(self, user_id: int) -> int:
        return await self._used_today("generative", user_id=user_id)

    async def embedding_used_today(self) -> int:
        return await self._used_today("embedding", user_id=None)

    async def try_reserve_generative(self, *, user_id: int, model: str) -> int | None:
        """Commit one generative slot before the API call. None means the limit is spent."""
        return await self._reserve(
            user_id=user_id,
            model=model,
            call_kind="generative",
            limit=settings.GENERATIVE_DAILY_LIMIT,
        )

    async def try_reserve_embedding(self, *, model: str) -> int | None:
        """Commit one embedding slot before the API call. None means the limit is spent."""
        return await self._reserve(
            user_id=None,
            model=model,
            call_kind="embedding",
            limit=settings.EMBEDDING_DAILY_LIMIT,
        )

    async def finish_generative(
        self,
        call_id: int,
        *,
        tokens: int | None,
        latency_ms: int,
        outcome: CallOutcome,
    ) -> None:
        await self._finish(
            call_id,
            tokens=tokens,
            latency_ms=latency_ms,
            cost=call_cost(tokens, settings.GENERATIVE_COST_PER_1K_TOKENS),
            outcome=outcome,
        )

    async def finish_embedding(self, call_id: int, *, latency_ms: int) -> None:
        await self._finish(
            call_id,
            tokens=None,
            latency_ms=latency_ms,
            cost=call_cost(1, settings.EMBEDDING_COST_PER_1K_TOKENS),
            outcome=None,
        )

    async def record_generative(
        self,
        *,
        user_id: int | None,
        model: str,
        tokens: int | None,
        latency_ms: int,
        outcome: CallOutcome,
    ) -> None:
        await self._record(
            user_id=user_id,
            model=model,
            call_kind="generative",
            tokens=tokens,
            latency_ms=latency_ms,
            cost=call_cost(tokens, settings.GENERATIVE_COST_PER_1K_TOKENS),
            outcome=outcome,
        )

    async def record_embedding(self, *, model: str, latency_ms: int) -> None:
        await self._record(
            user_id=None,
            model=model,
            call_kind="embedding",
            tokens=None,
            latency_ms=latency_ms,
            cost=call_cost(1, settings.EMBEDDING_COST_PER_1K_TOKENS),
            outcome=None,
        )

    async def _used_today(self, kind: str, *, user_id: int | None) -> int:
        return await self._used_today_on(self.session, kind, user_id=user_id)

    async def _used_today_on(
        self, session: AsyncSession, kind: str, *, user_id: int | None
    ) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count())
            .select_from(ModelCall)
            .where(ModelCall.call_kind == kind, ModelCall.created_at >= start)
        )
        if user_id is not None:
            stmt = stmt.where(ModelCall.user_id == user_id)
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    def _session_factory(self) -> async_sessionmaker[AsyncSession]:
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("ModelUsage session has no database bind")
        return async_sessionmaker(bind, expire_on_commit=False, class_=AsyncSession)

    async def _reserve(
        self,
        *,
        user_id: int | None,
        model: str,
        call_kind: str,
        limit: int,
    ) -> int | None:
        factory = self._session_factory()
        async with factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"),
                    {"key": _lock_key(call_kind, user_id)},
                )
                used = await self._used_today_on(
                    session,
                    call_kind,
                    user_id=user_id if call_kind == "generative" else None,
                )
                if not generative_call_allowed(used, limit):
                    return None
                row = ModelCall(
                    user_id=user_id,
                    model=model,
                    call_kind=call_kind,
                    tokens=None,
                    latency_ms=0,
                    cost=Decimal("0"),
                    outcome=None,
                )
                session.add(row)
                await session.flush()
                return row.id

    async def _finish(
        self,
        call_id: int,
        *,
        tokens: int | None,
        latency_ms: int,
        cost: Decimal,
        outcome: str | None,
    ) -> None:
        factory = self._session_factory()
        async with factory() as session:
            async with session.begin():
                row = await session.get(ModelCall, call_id)
                if row is None:
                    return
                row.tokens = tokens
                row.latency_ms = latency_ms
                row.cost = cost
                row.outcome = outcome

    async def _record(
        self,
        *,
        user_id: int | None,
        model: str,
        call_kind: str,
        tokens: int | None,
        latency_ms: int,
        cost: Decimal,
        outcome: str | None,
    ) -> None:
        row = ModelCall(
            user_id=user_id,
            model=model,
            call_kind=call_kind,
            tokens=tokens,
            latency_ms=latency_ms,
            cost=cost,
            outcome=outcome,
        )
        self.session.add(row)
        await self.session.flush([row])


async def run_if_allowed[T](
    *,
    used_today: int,
    limit: int,
    call: Callable[[], Awaitable[T]],
) -> T | None:
    """Return None without invoking call once the daily limit is spent."""
    if not generative_call_allowed(used_today, limit):
        return None
    return await call()
