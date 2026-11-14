"""The free monthly cap accepts the 100th receipt and rejects the 101st."""

from httpx import AsyncClient
from tests.support import access_token_for, bill_count

from src.bills.models import Bill, ProcessingStatus

EXTERNAL_ID = 8_100_001_201


async def test_hundredth_bill_is_accepted_and_hundred_first_is_rejected(
    api_client: AsyncClient,
    db_session,
    owned,
) -> None:
    user = await owned(EXTERNAL_ID)
    db_session.add_all(
        [Bill(user_id=user.id, status=ProcessingStatus.PENDING) for _ in range(99)]
    )
    await db_session.commit()
    assert await bill_count(db_session, user.id) == 99

    headers = {"Authorization": f"Bearer {access_token_for(db_session, user)}"}
    accepted = await api_client.post(
        "/api/bills/",
        headers=headers,
        json={"user_id": user.id},
    )

    assert accepted.status_code == 201
    assert await bill_count(db_session, user.id) == 100

    rejected = await api_client.post(
        "/api/bills/",
        headers=headers,
        json={"user_id": user.id},
    )

    assert rejected.status_code == 429
    assert await bill_count(db_session, user.id) == 100
