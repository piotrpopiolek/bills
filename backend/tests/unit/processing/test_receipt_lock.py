"""A missed lock retries only while the bill is still in progress."""

import pytest

from src.bills.models import ProcessingStatus
from src.processing.exceptions import ReceiptInProgress, lock_miss_is_finished


def test_a_finished_bill_does_not_need_another_attempt() -> None:
    assert lock_miss_is_finished(ProcessingStatus.COMPLETED) is True
    assert lock_miss_is_finished(ProcessingStatus.TO_VERIFY) is True
    assert lock_miss_is_finished(ProcessingStatus.ERROR) is True


def test_an_open_bill_must_be_retried() -> None:
    assert lock_miss_is_finished(ProcessingStatus.PROCESSING) is False
    assert lock_miss_is_finished(ProcessingStatus.PENDING) is False


def test_lock_miss_is_not_a_successful_job() -> None:
    with pytest.raises(ReceiptInProgress, match="4"):
        raise ReceiptInProgress(4)
