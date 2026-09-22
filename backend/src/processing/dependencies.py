"""
Factory functions for Bills Processing Pipeline dependencies.

Provides Dependency Injection pattern for BillsProcessorService,
allowing it to work both in FastAPI (with injected session) and Telegram handlers.
"""

import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.service import AICategorizationService
from src.bill_items.services import BillItemService
from src.bills.services import BillService
from src.categories.services import CategoryService
from src.ocr.routes import get_ocr_service
from src.processing.service import BillsProcessorService
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.services import ProductIndexService
from src.shops.services import ShopService
from src.telegram.context import _db_session, get_storage_service_for_telegram

logger = logging.getLogger(__name__)


async def get_bills_processor_service(
    session: AsyncSession | None = None,
) -> BillsProcessorService:
    """
    Factory function for BillsProcessorService.

    Works both in FastAPI (with injected session) and Telegram handlers.
    Używa Dependency Injection pattern zgodnie z architekturą projektu.

    Args:
        session: Optional AsyncSession (jeśli None, używa session z context lub tworzy nową)

    Returns:
        BillsProcessorService: Configured service instance

    Note:
        W kontekście Telegram, session powinien być już dostępny z `async with get_or_create_session() as session:`
        W FastAPI, session jest wstrzykiwany przez Depends(get_session).

        Most Koncepcyjny (Mentoring): W Symfony/Laravel, kontenery DI automatycznie rozwiązują zależności.
        W FastAPI, Depends() działa podobnie, ale jest bardziej deklaratywne - zależności są jawne
        na poziomie funkcji endpointu. To pozwala FastAPI zarządzać cyklem życia (np. session per-request)
        automatycznie. W kontekście Telegram (poza FastAPI), używamy ContextVar do przechowywania
        session w kontekście asynchronicznym, co jest idiomatycznym rozwiązaniem w Pythonie.
    """
    # Resolve session: use provided, or from context (Telegram), or create new (fallback)
    if session is None:
        # Try to get session from context (Telegram handlers)
        session = _db_session.get()
        if session is None:
            # Fallback: create new session (should not happen in normal flow)
            from src.db.main import AsyncSessionLocal

            logger.warning(
                "No session provided and no session in context, creating new session. "
                "Ensure this is intended (e.g. tests)."
            )
            session = AsyncSessionLocal()

    # Get dependencies via factory functions (DI pattern)
    storage_service = get_storage_service_for_telegram()
    ocr_service = await get_ocr_service()
    bill_service = BillService(session, storage_service)
    bill_item_service = BillItemService(session)
    shop_service = ShopService(session)

    # AI Categorization Service dependencies
    product_index_service = ProductIndexService(session)
    alias_service = ProductIndexAliasService(session)
    category_service = CategoryService(session)

    ai_service = AICategorizationService(
        session=session,
        product_index_service=product_index_service,
        alias_service=alias_service,
        category_service=category_service,
    )

    return BillsProcessorService(
        session=session,
        storage_service=storage_service,
        ocr_service=ocr_service,
        bill_service=bill_service,
        bill_item_service=bill_item_service,
        shop_service=shop_service,
        ai_service=ai_service,
    )


# Type alias dla FastAPI dependencies (jeśli używane w routes)
BillsProcessorServiceDependency = Annotated[
    BillsProcessorService, Depends(get_bills_processor_service)
]
