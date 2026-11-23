from src.bills.models import ProcessingStatus
from src.common.exceptions import AppError


class ProcessingError(AppError):
    def __init__(self, message: str, bill_id: int | None = None):
        self.message = message
        self.bill_id = bill_id
        super().__init__(self.message)


class ReceiptInProgress(Exception):
    """The processing lock is held. ARQ must retry; this is not a finished job."""

    def __init__(self, bill_id: int) -> None:
        self.bill_id = bill_id
        super().__init__(f"Paragon {bill_id} jest już przetwarzany")


def lock_miss_is_finished(status: ProcessingStatus) -> bool:
    """A finished bill does not need another attempt when the lock is taken."""
    return status in (
        ProcessingStatus.COMPLETED,
        ProcessingStatus.TO_VERIFY,
        ProcessingStatus.ERROR,
    )
