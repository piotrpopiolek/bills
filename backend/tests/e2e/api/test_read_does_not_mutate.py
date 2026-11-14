"""Reading bills and reports does not create a receipt or call OCR."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from tests.support import access_token_for, bill_count

from src.bills.models import Bill, ProcessingStatus

EXTERNAL_ID = 8_100_001_301
BILL_DATE = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
REPORT_DAY = "2026-01-15"
REPORT_MONTH = "2026-01"


async def test_get_bills_and_reports_do_not_create_a_receipt(
    api_client: AsyncClient,
    db_session,
    owned,
) -> None:
    user = await owned(EXTERNAL_ID)
    bill = Bill(
        user_id=user.id,
        status=ProcessingStatus.COMPLETED,
        total_amount=Decimal("12.50"),
        bill_date=BILL_DATE,
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    before = await bill_count(db_session, user.id)
    headers = {"Authorization": f"Bearer {access_token_for(db_session, user)}"}

    with patch(
        "src.ocr.services.OCRService.extract_data", new_callable=AsyncMock
    ) as extract_data:
        bills = await api_client.get("/api/bills", headers=headers)
        daily = await api_client.get(
            "/api/reports/daily",
            headers=headers,
            params={"date": REPORT_DAY},
        )
        monthly = await api_client.get(
            "/api/reports/monthly",
            headers=headers,
            params={"month": REPORT_MONTH},
        )
        extract_data.assert_not_called()

    assert bills.status_code == 200
    body = bills.json()
    assert body["total"] == 1
    assert [row["id"] for row in body["items"]] == [bill.id]
    assert daily.status_code == 200
    assert monthly.status_code == 200
    assert await bill_count(db_session, user.id) == before

    await db_session.refresh(bill)
    assert bill.status == ProcessingStatus.COMPLETED
    assert bill.total_amount == Decimal("12.50")
