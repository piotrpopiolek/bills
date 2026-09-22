"""
Dependency Injection dla modułu AI Categorization Service.

Przykład użycia w endpoincie:
    @app.post("/normalize")
    async def normalize(
        ai_service: AICategorizationService = Depends(get_ai_service)
    ):
        result = await ai_service.normalize_item(...)
        return result
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.service import AICategorizationService
from src.categories.services import CategoryService
from src.deps import get_db  # Główna funkcja DI dla sesji DB
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.services import ProductIndexService


async def get_ai_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AICategorizationService]:
    """
    Fabryka Dependency Injection dla AICategorizationService.

    Args:
        session: Async sesja DB (wstrzyknięta przez FastAPI z get_db)

    Yields:
        AICategorizationService: Gotowy do użycia serwis AI
    """
    # Utworzenie zależności
    product_index_service = ProductIndexService(session)
    alias_service = ProductIndexAliasService(session)
    category_service = CategoryService(session)

    # Utworzenie głównego serwisu
    ai_service = AICategorizationService(
        session=session,
        product_index_service=product_index_service,
        alias_service=alias_service,
        category_service=category_service,
    )

    # Yield - przekazanie do endpointu
    yield ai_service

    # Teardown (opcjonalnie)
    # Tutaj moglibyście dodać cleanup logic (np. flush cache, close connections)
    # W naszym przypadku session jest zarządzana przez get_db, więc nic nie robimy
