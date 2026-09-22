"""
Factory functions for Bill-related services.

Provides Dependency Injection pattern for Bill services,
allowing them to work both in FastAPI (with injected session) and Telegram handlers.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.services import BillItemService
from src.bills.services import BillService
from src.bills.verification_service import BillVerificationService
from src.product_candidates.services import ProductCandidateService
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.services import ProductIndexService
from src.product_learning.service import ProductLearningService
from src.telegram.context import _db_session, get_storage_service_for_telegram

logger = logging.getLogger(__name__)


async def get_bill_verification_service(
    session: AsyncSession | None = None,
) -> BillVerificationService:
    """
    Factory function for BillVerificationService with proper dependency injection.

    Works both in FastAPI (with injected session) and Telegram handlers.

    Args:
        session: Optional AsyncSession (jeśli None, używa session z context lub tworzy nową)

    Returns:
        BillVerificationService: Configured service instance
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
    bill_service = BillService(session, storage_service)
    bill_item_service = BillItemService(session)

    # ProductLearningService dependencies
    product_candidate_service = ProductCandidateService(session)
    product_index_service = ProductIndexService(session)
    alias_service = ProductIndexAliasService(session)

    product_learning_service = ProductLearningService(
        session=session,
        bill_item_service=bill_item_service,
        product_candidate_service=product_candidate_service,
        product_index_service=product_index_service,
        alias_service=alias_service,
    )

    return BillVerificationService(
        session=session,
        bill_service=bill_service,
        bill_item_service=bill_item_service,
        product_learning_service=product_learning_service,
    )
