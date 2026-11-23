"""The receipt job retries, then leaves the bill in error."""

import pytest
from arq.worker import Retry

from src.config import settings
from src.worker.jobs import process_receipt_job


async def test_a_failed_attempt_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RECEIPT_JOB_MAX_TRIES", 3)
    calls: list[str] = []

    async def boom(_bill_id: int) -> None:
        raise RuntimeError("ocr down")

    async def reopen(bill_id: int) -> None:
        calls.append(f"reopen:{bill_id}")

    async def mark(bill_id: int, message: str) -> None:
        calls.append(f"mark:{bill_id}:{message}")

    monkeypatch.setattr("src.worker.jobs.run_receipt", boom)
    monkeypatch.setattr("src.worker.jobs.reopen_receipt", reopen)
    monkeypatch.setattr("src.worker.jobs.mark_receipt_failed", mark)

    with pytest.raises(Retry):
        await process_receipt_job({"job_try": 1}, 9)

    assert calls == ["reopen:9"]


async def test_the_last_try_keeps_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RECEIPT_JOB_MAX_TRIES", 3)
    calls: list[str] = []

    async def boom(_bill_id: int) -> None:
        raise RuntimeError("ocr down")

    async def reopen(bill_id: int) -> None:
        calls.append(f"reopen:{bill_id}")

    async def mark(bill_id: int, message: str) -> None:
        calls.append(f"mark:{bill_id}:{message}")

    monkeypatch.setattr("src.worker.jobs.run_receipt", boom)
    monkeypatch.setattr("src.worker.jobs.reopen_receipt", reopen)
    monkeypatch.setattr("src.worker.jobs.mark_receipt_failed", mark)

    with pytest.raises(RuntimeError, match="ocr down") as caught:
        await process_receipt_job({"job_try": 3}, 9)

    assert type(caught.value) is RuntimeError
    assert calls == ["reopen:9", "mark:9:ocr down"]


async def test_a_later_try_reopens_before_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []

    async def run(_bill_id: int) -> None:
        order.append("run")

    async def reopen(_bill_id: int) -> None:
        order.append("reopen")

    monkeypatch.setattr("src.worker.jobs.run_receipt", run)
    monkeypatch.setattr("src.worker.jobs.reopen_receipt", reopen)

    await process_receipt_job({"job_try": 2}, 9)

    assert order == ["reopen", "run"]
