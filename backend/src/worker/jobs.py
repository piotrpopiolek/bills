"""ARQ job that runs process_receipt. The last failed try marks the bill error."""

import logging
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Retry, func
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bills.models import Bill, ProcessingStatus
from src.config import settings
from src.db.main import AsyncSessionLocal
from src.worker.queue import PROCESS_RECEIPT_JOB

logger = logging.getLogger(__name__)


def session_factory() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionLocal


def _load_models() -> None:
    """Register every mapper before a worker session touches Bill."""
    import src.ai.models  # noqa: F401
    import src.auth.models  # noqa: F401
    import src.bill_items.models  # noqa: F401
    import src.bills.models  # noqa: F401
    import src.categories.models  # noqa: F401
    import src.product_candidates.models  # noqa: F401
    import src.product_index_aliases.models  # noqa: F401
    import src.product_indexes.models  # noqa: F401
    import src.shops.models  # noqa: F401
    import src.telegram_messages.models  # noqa: F401
    import src.users.models  # noqa: F401


def _job_try(ctx: dict[str, Any]) -> int:
    raw = ctx.get("job_try", 1)
    try:
        return int(raw)
    except TypeError, ValueError:
        return 1


async def reopen_receipt(bill_id: int) -> None:
    """Let the next try take the processing lock again."""
    _load_models()
    async with session_factory()() as session:
        await session.execute(
            update(Bill)
            .where(Bill.id == bill_id)
            .where(
                Bill.status.in_((ProcessingStatus.ERROR, ProcessingStatus.PROCESSING))
            )
            .values(status=ProcessingStatus.PENDING, error_message=None)
        )
        await session.commit()


async def mark_receipt_failed(bill_id: int, error_message: str) -> None:
    """Keep a specific error already stored by process_receipt."""
    _load_models()
    message = (error_message or "Przetwarzanie paragonu nie powiodło się")[:1000]
    async with session_factory()() as session:
        bill = await session.get(Bill, bill_id)
        if bill is None:
            logger.error("Brak paragonu %s przy zapisie błędu", bill_id)
            return
        if bill.status == ProcessingStatus.ERROR and bill.error_message:
            return
        bill.status = ProcessingStatus.ERROR
        bill.error_message = message
        await session.commit()


async def run_receipt(bill_id: int) -> None:
    from src.processing.dependencies import get_bills_processor_service

    async with session_factory()() as session:
        processor = await get_bills_processor_service(session)
        await processor.process_receipt(bill_id)


async def process_receipt_job(ctx: dict[str, Any], bill_id: int) -> None:
    """One ARQ attempt. Retry while tries remain; the last failure stays error."""
    attempt = _job_try(ctx)
    if attempt > 1:
        await reopen_receipt(bill_id)
    try:
        await run_receipt(bill_id)
    except Exception as exc:
        if attempt >= settings.RECEIPT_JOB_MAX_TRIES:
            try:
                await mark_receipt_failed(bill_id, str(exc))
            except Exception:
                logger.exception("Nie zapisano błędu paragonu %s", bill_id)
            raise
        await reopen_receipt(bill_id)
        raise Retry(defer=settings.RECEIPT_JOB_RETRY_SECONDS) from exc


class WorkerSettings:
    functions = [
        func(
            process_receipt_job,
            name=PROCESS_RECEIPT_JOB,
            max_tries=settings.RECEIPT_JOB_MAX_TRIES,
            timeout=settings.RECEIPT_JOB_TIMEOUT_SECONDS,
        )
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_tries = settings.RECEIPT_JOB_MAX_TRIES
    job_timeout = settings.RECEIPT_JOB_TIMEOUT_SECONDS
    retry_jobs = True
