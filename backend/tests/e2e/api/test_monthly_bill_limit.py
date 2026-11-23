"""The free monthly cap counts receipts OCR kept, and rejects the next one."""

from httpx import AsyncClient
from tests.support import access_token_for, bill_count

from src.bills.models import Bill, ProcessingStatus

EXTERNAL_ID = 8_100_001_201


async def test_hundredth_finished_receipt_blocks_another_create(
    api_client: AsyncClient,
    db_session,
    owned,
) -> None:
    user = await owned(EXTERNAL_ID)
    db_session.add_all(
        [Bill(user_id=user.id, status=ProcessingStatus.COMPLETED) for _ in range(99)]
    )
    db_session.add(Bill(user_id=user.id, status=ProcessingStatus.PENDING))
    await db_session.commit()
    assert await bill_count(db_session, user.id) == 99

    headers = {"Authorization": f"Bearer {access_token_for(db_session, user)}"}
    accepted = await api_client.post(
        "/api/bills/",
        headers=headers,
        json={"user_id": user.id},
    )

    assert accepted.status_code == 201
    assert await bill_count(db_session, user.id) == 99

    db_session.add(Bill(user_id=user.id, status=ProcessingStatus.COMPLETED))
    await db_session.commit()
    assert await bill_count(db_session, user.id) == 100

    rejected = await api_client.post(
        "/api/bills/",
        headers=headers,
        json={"user_id": user.id},
    )

    assert rejected.status_code == 429
    assert await bill_count(db_session, user.id) == 100
