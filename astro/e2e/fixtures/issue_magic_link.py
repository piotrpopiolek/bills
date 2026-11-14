"""Seed one magic link and one receipt for the Playwright read-only list.

Prints a single JSON object with the token. Does not call Telegram or OCR.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal

from src.auth.services import AuthService
from src.bills.models import Bill, ProcessingStatus
from tests.support import (
    create_test_engine,
    create_user,
    delete_owned_user,
    session_factory,
)

EXTERNAL_ID = 8_100_001_901


async def main() -> None:
    engine = create_test_engine()
    try:
        maker = session_factory(engine)
        async with maker() as session:
            if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
                await delete_owned_user(session, EXTERNAL_ID)
                return
            user = await create_user(session, EXTERNAL_ID)
            session.add(
                Bill(
                    user_id=user.id,
                    status=ProcessingStatus.COMPLETED,
                    total_amount=Decimal("12.50"),
                    bill_date=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
                )
            )
            await session.commit()
            _link, url = await AuthService(session).create_magic_link_for_user(user.id)
            token = url.split("token=", 1)[1]
            sys.stdout.write(json.dumps({"external_id": EXTERNAL_ID, "token": token}))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
