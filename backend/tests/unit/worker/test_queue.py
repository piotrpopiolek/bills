"""Enqueue sends one job per bill and can see a job that is still running."""

import pytest

from src.worker.queue import (
    PROCESS_RECEIPT_JOB,
    enqueue_receipt,
    receipt_job_active,
    receipt_job_id,
)


class _Pool:
    def __init__(self, job: object | None, *, present: int = 0) -> None:
        self.job = job
        self.present = present
        self.calls: list[tuple[str, tuple[object, ...], object]] = []
        self.exists_keys: tuple[str, ...] = ()
        self.closed = False

    async def enqueue_job(
        self, function: str, *args: object, **kwargs: object
    ) -> object | None:
        self.calls.append((function, args, kwargs.get("_job_id")))
        return self.job

    async def exists(self, *keys: str) -> int:
        self.exists_keys = keys
        return self.present

    async def close(self, close_connection_pool: bool | None = None) -> None:
        self.closed = True


def _patch_pool(monkeypatch: pytest.MonkeyPatch, pool: _Pool) -> None:
    async def create_pool(_settings: object) -> _Pool:
        return pool

    monkeypatch.setattr("src.worker.queue.create_pool", create_pool)


async def test_enqueue_sends_the_bill_id(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _Pool(object())
    _patch_pool(monkeypatch, pool)

    assert await enqueue_receipt(12) is True

    assert pool.calls == [(PROCESS_RECEIPT_JOB, (12,), receipt_job_id(12))]
    assert pool.closed is True


async def test_an_existing_job_is_not_queued_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _Pool(None)
    _patch_pool(monkeypatch, pool)

    assert await enqueue_receipt(12) is False
    assert pool.closed is True


async def test_a_gone_job_is_not_active(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _Pool(None, present=0)
    _patch_pool(monkeypatch, pool)

    assert await receipt_job_active(4) is False
    assert pool.exists_keys == (
        f"arq:job:{receipt_job_id(4)}",
        f"arq:in-progress:{receipt_job_id(4)}",
    )
    assert pool.closed is True


async def test_a_running_job_is_active(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _Pool(None, present=1)
    _patch_pool(monkeypatch, pool)

    assert await receipt_job_active(4) is True
