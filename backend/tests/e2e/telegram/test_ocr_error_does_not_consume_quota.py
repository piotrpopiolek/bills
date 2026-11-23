"""A queued photo counts. A queue failure does not."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tests.support import bill_count

EXTERNAL_ID = 8_100_001_801


async def test_accepted_photo_is_queued_and_counts(db_session, owned) -> None:
    user = await owned(EXTERNAL_ID)
    queued: list[int] = []

    async def enqueue(bill_id: int) -> None:
        queued.append(bill_id)

    update = _update(EXTERNAL_ID)
    await _run(db_session, user, update, enqueue)

    assert queued
    counted = await bill_count(db_session, user.id)
    assert counted == 1
    update.message.reply_text.return_value.edit_text.assert_awaited_with(
        f"Zdjęcie przyjęte.\nID: {queued[0]}"
    )


async def test_queue_failure_does_not_consume_monthly_quota(db_session, owned) -> None:
    user = await owned(EXTERNAL_ID + 1)

    async def enqueue(_bill_id: int) -> None:
        raise ConnectionError("redis down")

    update = _update(EXTERNAL_ID + 1)
    await _run(db_session, user, update, enqueue)

    counted = await bill_count(db_session, user.id)
    assert counted == 0
    update.message.reply_text.return_value.edit_text.assert_awaited_with(
        "Nie udało się przyjąć zdjęcia. Spróbuj ponownie."
    )


async def _run(db_session, user, update, enqueue) -> None:
    from src.telegram.context import (
        clear_db_session,
        clear_storage_service,
        clear_user,
        set_db_session,
        set_storage_service,
        set_user,
    )
    from src.telegram.handlers import handle_receipt_image

    set_user(user)
    set_db_session(db_session)
    set_storage_service(_storage(user.external_id))
    try:
        with patch("src.telegram.handlers.enqueue_receipt", enqueue):
            await handle_receipt_image(update, _context())
    finally:
        clear_user()
        clear_db_session()
        clear_storage_service()


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
