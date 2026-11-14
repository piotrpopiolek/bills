"""Empty OCR and a rejected payload do not persist receipt lines."""

import json
from decimal import Decimal

import pytest
from tests.support import insert_pending_bill, line_item_count, processor_for

from src.bills.models import ProcessingStatus
from src.ocr.schemas import OCRReceiptData

EXTERNAL_EMPTY = 8_100_001_701
EXTERNAL_INVALID = 8_100_001_702


async def test_empty_ocr_creates_no_line_items(db_session, owned) -> None:
    user = await owned(EXTERNAL_EMPTY)
    bill = await insert_pending_bill(db_session, user.id)
    receipt = OCRReceiptData(
        shop_name=None,
        shop_address=None,
        total_amount=Decimal("0"),
        items=[],
    )
    processor = processor_for(db_session, receipt=receipt)

    await processor.process_receipt(bill.id)

    assert await line_item_count(db_session, bill.id) == 0


async def test_invalid_ocr_payload_does_not_leave_a_partial_bill(
    db_session, owned
) -> None:
    user = await owned(EXTERNAL_INVALID)
    bill = await insert_pending_bill(db_session, user.id)
    processor = processor_for(
        db_session,
        ocr_error=json.JSONDecodeError("Expecting value", "not-json", 0),
    )

    with pytest.raises(json.JSONDecodeError):
        await processor.process_receipt(bill.id)

    await db_session.refresh(bill)
    assert bill.status == ProcessingStatus.ERROR
    assert bill.total_amount is None
    assert await line_item_count(db_session, bill.id) == 0
