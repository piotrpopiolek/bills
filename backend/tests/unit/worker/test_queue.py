"""Enqueue sends the bill id and does not swallow a dropped job."""

import pytest

from src.worker.queue import PROCESS_RECEIPT_JOB, enqueue_receipt


class _Pool:
    def __init__(self, job: object | None) -> None:
        self.job = job
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False

    async def enqueue_job(self, function: str, *args: object) -> object | None:
        self.calls.append((function, args))
        return self.job

    async def close(self, close_connection_pool: bool | None = None) -> None:
        self.closed = True


async def test_enqueue_sends_the_bill_id(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _Pool(object())

    async def create_pool(_settings: object) -> _Pool:
        return pool

    monkeypatch.setattr("src.worker.queue.create_pool", create_pool)

    await enqueue_receipt(12)

    assert pool.calls == [(PROCESS_RECEIPT_JOB, (12,))]
    assert pool.closed is True


async def test_a_dropped_job_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _Pool(None)

    async def create_pool(_settings: object) -> _Pool:
        return pool

    monkeypatch.setattr("src.worker.queue.create_pool", create_pool)

    with pytest.raises(RuntimeError, match="12"):
        await enqueue_receipt(12)
    assert pool.closed is True
