from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.deps import CurrentUser, get_session
from src.users.services import UserService

# In-memory store: {user_id: [timestamps]}
_ocr_rate_limit_store: dict[int, list[datetime]] = defaultdict(list)


async def check_monthly_bills_limit(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> None:
    """
    Dependency to check if the user has reached their monthly bills limit.
    Raises 429 Too Many Requests if the limit is exceeded.
    """
    user_service = UserService(session)
    stats = await user_service.get_user_usage_stats(user.id)

    if stats["remaining_bills"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Osiągnięto miesięczny limit {settings.MONTHLY_BILLS_LIMIT} paragonów. Limit zresetuje się w przyszłym miesiącu.",
        )


async def check_ocr_rate_limit(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> None:
    """
    Dependency to check OCR rate limit: 5 requests per minute per user.
    Raises 429 Too Many Requests if exceeded.

    Most Koncepcyjny (PHP → Python): W Symfony/Laravel używasz Rate Limiter jako service dependency.
    W FastAPI ten sam wzorzec realizujemy przez Depends(), co jest bardziej idiomatyczne niż dekoratory.

    NOTE: To rozwiązanie używa in-memory store (słownik z TTL) dla MVP.
    Dla produkcji multi-worker wymagany będzie Redis lub shared storage.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=1)

    # Usuń stare wpisy
    _ocr_rate_limit_store[user.id] = [
        ts for ts in _ocr_rate_limit_store[user.id] if ts > cutoff
    ]

    # Sprawdź limit
    if len(_ocr_rate_limit_store[user.id]) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 requests per minute.",
        )

    # Dodaj aktualny timestamp
    _ocr_rate_limit_store[user.id].append(now)
