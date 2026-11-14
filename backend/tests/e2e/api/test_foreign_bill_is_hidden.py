"""A second user cannot read or change someone else's receipt."""

from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from tests.support import access_token_for

from src.bill_items.models import BillItem, VerificationSource
from src.bills.models import Bill, ProcessingStatus

OWNER_EXTERNAL_ID = 8_100_001_401
OTHER_EXTERNAL_ID = 8_100_001_402
ITEM_TEXT = "MLEKO QA 8100001401"
ORIGINAL_TOTAL = Decimal("10.00")


async def test_other_user_cannot_read_or_change_the_bill(
    api_client: AsyncClient,
    db_session,
    owned,
) -> None:
    owner = await owned(OWNER_EXTERNAL_ID)
    other = await owned(OTHER_EXTERNAL_ID)
    bill = Bill(
        user_id=owner.id,
        status=ProcessingStatus.COMPLETED,
        total_amount=ORIGINAL_TOTAL,
        bill_date=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    db_session.add(
        BillItem(
            bill_id=bill.id,
            quantity=Decimal("1"),
            unit_price=ORIGINAL_TOTAL,
            total_price=ORIGINAL_TOTAL,
            original_text=ITEM_TEXT,
            is_verified=True,
            verification_source=VerificationSource.AUTO,
            confidence_score=Decimal("1.00"),
        )
    )
    await db_session.commit()

    owner_headers = {"Authorization": f"Bearer {access_token_for(db_session, owner)}"}
    other_headers = {"Authorization": f"Bearer {access_token_for(db_session, other)}"}

    own_items = await api_client.get(
        f"/api/bills/{bill.id}/items", headers=owner_headers
    )
    assert own_items.status_code == 200
    assert ITEM_TEXT in own_items.text

    foreign_list = await api_client.get("/api/bills", headers=other_headers)
    assert foreign_list.status_code == 200
    assert foreign_list.json()["items"] == []
    assert foreign_list.json()["total"] == 0

    foreign_bill = await api_client.get(f"/api/bills/{bill.id}", headers=other_headers)
    foreign_items = await api_client.get(
        f"/api/bills/{bill.id}/items", headers=other_headers
    )
    assert foreign_bill.status_code == 403
    assert foreign_items.status_code == 403
    assert ITEM_TEXT not in foreign_bill.text
    assert ITEM_TEXT not in foreign_items.text

    patched = await api_client.patch(
        f"/api/bills/{bill.id}",
        headers=other_headers,
        json={"error_message": "changed-by-other"},
    )
    assert patched.status_code == 403

    await db_session.refresh(bill)
    assert bill.error_message is None
    assert bill.total_amount == ORIGINAL_TOTAL
    assert bill.user_id == owner.id
