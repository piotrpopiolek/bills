"""Put a saved receipt on the ARQ queue. The worker does the OCR."""

import logging

from arq.connections import RedisSettings, create_pool

from src.config import settings

logger = logging.getLogger(__name__)

PROCESS_RECEIPT_JOB = "process_receipt"


async def enqueue_receipt(bill_id: int) -> None:
    """Queue one receipt. A missing Redis or a dropped job raises."""
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        job = await redis.enqueue_job(PROCESS_RECEIPT_JOB, bill_id)
    finally:
        await redis.close(close_connection_pool=True)
    if job is None:
        raise RuntimeError(f"Paragon {bill_id} nie wszedł do kolejki")
    logger.info("Paragon %s wszedł do kolejki", bill_id)
