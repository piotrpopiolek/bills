"""A failed OCR pass must not consume one of the 100 monthly receipts."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tests.support import bill_count

EXTERNAL_ID = 8_100_001_801


async def test_ocr_failure_does_not_consume_monthly_quota(db_session, owned) -> None:
    from src.telegram.context import (
        clear_db_session,
        clear_storage_service,
        clear_user,
        set_db_session,
        set_storage_service,
        set_user,
    )
    from src.telegram.handlers import handle_receipt_image

    user = await owned(EXTERNAL_ID)
    storage = _storage(EXTERNAL_ID)
    processor = AsyncMock()
    processor.process_receipt = AsyncMock(side_effect=ValueError("ocr failed"))
    set_user(user)
    set_db_session(db_session)
    set_storage_service(storage)
    try:
        with patch(
            "src.telegram.handlers.get_bills_processor_service",
            AsyncMock(return_value=processor),
        ):
            await handle_receipt_image(_update(EXTERNAL_ID), _context())
    finally:
        clear_user()
        clear_db_session()
        clear_storage_service()

    assert storage.upload_file_content.await_count == 1
    assert processor.process_receipt.await_count == 1
    counted = await bill_count(db_session, user.id)
    assert counted == 0, (
        f"OCR failure left {counted} bill(s) in the monthly count. "
        "handle_receipt_image inserts the bill before process_receipt, "
        "and get_bills_count_this_month counts every row."
    )


def _storage(external_id: int) -> MagicMock:
    storage = MagicMock()
    storage.upload_file_content = AsyncMock(
        return_value=(f"bills/qa/{external_id}.jpg", "ab" * 32)
    )
    storage.calculate_expiration_date = MagicMock(
        return_value=datetime(2026, 7, 15, tzinfo=UTC)
    )
    storage.get_signed_url = MagicMock(return_value="http://localhost/signed")
    return storage


def _update(external_id: int) -> MagicMock:
    photo = MagicMock()
    photo.file_id = f"file-{external_id}"
    status = MagicMock()
    status.edit_text = AsyncMock()
    message = MagicMock()
    message.document = None
    message.photo = [photo]
    message.reply_text = AsyncMock(return_value=status)
    update = MagicMock()
    update.message = message
    update.effective_user = MagicMock()
    update.effective_user.id = external_id
    return update


def _context() -> MagicMock:
    downloaded = MagicMock()
    downloaded.file_path = "photos/receipt.jpg"
    downloaded.download_as_bytearray = AsyncMock(return_value=bytearray(b"jpeg-bytes"))
    context = MagicMock()
    context.bot.get_file = AsyncMock(return_value=downloaded)
    return context
