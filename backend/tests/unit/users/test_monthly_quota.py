"""A monthly slot is a receipt OCR kept, not a photo still in the queue."""

from src.bills.models import ProcessingStatus
from src.users.services import receipt_counts_toward_monthly_limit


def test_only_a_kept_receipt_uses_a_slot() -> None:
    assert receipt_counts_toward_monthly_limit(ProcessingStatus.COMPLETED) is True
    assert receipt_counts_toward_monthly_limit(ProcessingStatus.TO_VERIFY) is True


def test_a_queued_or_failed_pass_does_not_use_a_slot() -> None:
    assert receipt_counts_toward_monthly_limit(ProcessingStatus.PENDING) is False
    assert receipt_counts_toward_monthly_limit(ProcessingStatus.PROCESSING) is False
    assert receipt_counts_toward_monthly_limit(ProcessingStatus.ERROR) is False
