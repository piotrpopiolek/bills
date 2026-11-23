"""Put a saved receipt on the ARQ queue. The worker does the OCR."""

import logging
from collections.abc import Awaitable, Callable

from arq.connections import ArqRedis, RedisSettings, create_pool
from arq.constants import in_progress_key_prefix, job_key_prefix

from src.config import settings

logger = logging.getLogger(__name__)

PROCESS_RECEIPT_JOB = "process_receipt"


def receipt_job_id(bill_id: int) -> str:
    """One live queue entry per bill, so a resend can see the running job."""
    return f"receipt-{bill_id}"


async def _use_redis[T](action: Callable[[ArqRedis], Awaitable[T]]) -> T:
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        return await action(redis)
    finally:
        await redis.close(close_connection_pool=True)


async def receipt_job_active(bill_id: int) -> bool:
    """True while ARQ still has this bill queued or in progress."""
    job_id = receipt_job_id(bill_id)

    async def active(redis: ArqRedis) -> bool:
        found = await redis.exists(
            job_key_prefix + job_id,
            in_progress_key_prefix + job_id,
        )
        return bool(found)

    return await _use_redis(active)


async def enqueue_receipt(bill_id: int) -> bool:
    """Queue one receipt. False means this bill is already queued or running."""

    async def put(redis: ArqRedis) -> bool:
        job = await redis.enqueue_job(
            PROCESS_RECEIPT_JOB,
            bill_id,
            _job_id=receipt_job_id(bill_id),
        )
        return job is not None

    queued = await _use_redis(put)
    if queued:
        logger.info("Paragon %s wszedł do kolejki", bill_id)
        return True
    logger.info("Paragon %s jest już w kolejce", bill_id)
    return False
