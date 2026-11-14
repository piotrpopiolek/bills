"""Two spellings of one shop address resolve to a single shop row."""

from sqlalchemy import select
from tests.support import (
    insert_pending_bill,
    normalized_shop_name,
    processor_for,
    quoted_shop_name,
    receipt_for,
)

from src.shops.models import Shop

EXTERNAL_ID = 8_100_001_501


async def test_same_shop_different_spelling_does_not_create_a_second_row(
    db_session, owned
) -> None:
    user = await owned(EXTERNAL_ID)
    first = await insert_pending_bill(db_session, user.id)
    second = await insert_pending_bill(db_session, user.id)
    quoted = processor_for(
        db_session,
        receipt=receipt_for(EXTERNAL_ID, shop_name=quoted_shop_name(EXTERNAL_ID)),
    )
    plain = processor_for(
        db_session,
        receipt=receipt_for(EXTERNAL_ID, shop_name=normalized_shop_name(EXTERNAL_ID)),
    )

    await quoted.process_receipt(first.id)
    await plain.process_receipt(second.id)

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.shop_id is not None
    assert first.shop_id == second.shop_id
    rows = list(
        await db_session.scalars(
            select(Shop).where(Shop.name == normalized_shop_name(EXTERNAL_ID))
        )
    )
    assert len(rows) == 1
    assert rows[0].id == first.shop_id
