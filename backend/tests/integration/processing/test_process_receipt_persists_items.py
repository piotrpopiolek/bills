"""Mocked OCR is stored as line items and one normalized shop."""

from sqlalchemy import select
from tests.support import (
    NORMALIZED_SHOP_ADDRESS,
    RECEIPT_ITEM,
    RECEIPT_TOTAL,
    insert_pending_bill,
    normalized_shop_name,
    processor_for,
    receipt_for,
)

from src.bill_items.models import BillItem
from src.bills.models import ProcessingStatus
from src.shops.models import Shop

EXTERNAL_ID = 8_100_001_601


async def test_mocked_ocr_persists_items_and_normalized_shop(db_session, owned) -> None:
    user = await owned(EXTERNAL_ID)
    bill = await insert_pending_bill(db_session, user.id)
    processor = processor_for(db_session, receipt=receipt_for(EXTERNAL_ID))

    await processor.process_receipt(bill.id)

    await db_session.refresh(bill)
    assert bill.status == ProcessingStatus.COMPLETED
    assert bill.total_amount == RECEIPT_TOTAL
    shop = await db_session.get(Shop, bill.shop_id)
    assert shop is not None
    assert shop.name == normalized_shop_name(EXTERNAL_ID)
    assert shop.address == NORMALIZED_SHOP_ADDRESS
    items = list(
        await db_session.scalars(select(BillItem).where(BillItem.bill_id == bill.id))
    )
    assert [item.original_text for item in items] == [RECEIPT_ITEM]
