"""
Bill Verification Service - zarządzanie procesem weryfikacji pozycji z rachunku.

Most Koncepcyjny (PHP → Python):
W Symfony/Laravel używałbyś Command Handler lub Event Subscriber do obsługi
weryfikacji. W FastAPI mamy serwis jako orchestrator - idiomatyczne podejście
w Pythonie, gdzie logika biznesowa jest w serwisach.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.models import BillItem
from src.bill_items.services import BillItemService
from src.bills.models import Bill, ProcessingStatus
from src.bills.schemas import BillUpdate
from src.bills.services import BillService
from src.common.exceptions import BillAccessDeniedError, ResourceNotFoundError
from src.product_learning.service import ProductLearningService

logger = logging.getLogger(__name__)


class BillVerificationService:
    """
    Serwis zarządzający procesem weryfikacji pozycji z rachunku.

    Implementuje workflow:
    1. Pobieranie pozycji wymagających weryfikacji
    2. Weryfikacja pojedynczych pozycji
    3. Sprawdzanie czy wszystkie pozycje zostały zweryfikowane
    4. Finalizacja weryfikacji (aktualizacja statusu Bill na COMPLETED)
    """

    def __init__(
        self,
        session: AsyncSession,
        bill_service: BillService,
        bill_item_service: BillItemService,
        product_learning_service: ProductLearningService,
    ):
        """
        Inicjalizacja serwisu z wstrzyknięciem zależności.

        Args:
            session: SQLAlchemy async session
            bill_service: Serwis do zarządzania Bill
            bill_item_service: Serwis do zarządzania BillItems
            product_learning_service: Serwis do uczenia się produktów z weryfikacji
        """
        self.session = session
        self.bill_service = bill_service
        self.bill_item_service = bill_item_service
        self.product_learning_service = product_learning_service

    async def _verify_bill_ownership(self, bill_id: int, user_id: int) -> Bill:
        """
        Sprawdza ownership rachunku i zwraca obiekt Bill.

        Args:
            bill_id: ID rachunku
            user_id: ID użytkownika

        Returns:
            Bill: Obiekt rachunku

        Raises:
            ResourceNotFoundError: Jeśli rachunek nie istnieje
            BillAccessDeniedError: Jeśli rachunek nie należy do użytkownika
        """
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ResourceNotFoundError("Bill", bill_id)

        if bill.user_id != user_id:
            raise BillAccessDeniedError(bill_id)

        return bill

    async def get_unverified_items(self, bill_id: int, user_id: int) -> list[BillItem]:
        """
        Pobiera wszystkie pozycje wymagające weryfikacji dla danego rachunku.
        Filtruje tylko pozycje z is_verified=False.

        Args:
            bill_id: ID rachunku
            user_id: ID użytkownika (do weryfikacji ownership)

        Returns:
            List[BillItem]: Lista pozycji wymagających weryfikacji

        Raises:
            ResourceNotFoundError: Jeśli rachunek nie istnieje
            BillAccessDeniedError: Jeśli rachunek nie należy do użytkownika
        """
        # Weryfikacja ownership
        await self._verify_bill_ownership(bill_id, user_id)

        # Pobierz pozycje wymagające weryfikacji
        stmt = (
            select(BillItem)
            .where(BillItem.bill_id == bill_id, BillItem.is_verified.is_(False))
            .order_by(BillItem.id)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        logger.info(
            f"Found {len(items)} unverified items for bill_id={bill_id}, user_id={user_id}"
        )

        return items

    async def get_next_unverified_item(
        self, bill_id: int, user_id: int, exclude_item_ids: list[int] | None = None
    ) -> BillItem | None:
        """
        Pobiera następną pozycję wymagającą weryfikacji.

        Args:
            bill_id: ID rachunku
            user_id: ID użytkownika
            exclude_item_ids: Lista ID pozycji do pominięcia (opcjonalne)

        Returns:
            Optional[BillItem]: Następna pozycja wymagająca weryfikacji lub None
        """
        # Weryfikacja ownership
        await self._verify_bill_ownership(bill_id, user_id)

        # Pobierz pozycje wymagające weryfikacji
        stmt = select(BillItem).where(
            BillItem.bill_id == bill_id, BillItem.is_verified.is_(False)
        )

        # Wyklucz już przetworzone pozycje
        if exclude_item_ids:
            stmt = stmt.where(~BillItem.id.in_(exclude_item_ids))

        stmt = stmt.order_by(BillItem.id).limit(1)

        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()

        return item

    async def verify_item(
        self,
        bill_item_id: int,
        user_id: int,
        edited_text: str | None = None,
        edited_category_id: int | None = None,
    ) -> BillItem:
        """
        Weryfikuje pozycję (używa ProductLearningService.handle_user_bill_item_verification).

        Args:
            bill_item_id: ID pozycji do weryfikacji
            user_id: ID użytkownika weryfikującego
            edited_text: Opcjonalny zedytowany tekst pozycji
            edited_category_id: Opcjonalna zedytowana kategoria

        Returns:
            BillItem: Zaktualizowana pozycja

        Raises:
            ResourceNotFoundError: Jeśli pozycja nie istnieje
            BillAccessDeniedError: Jeśli pozycja nie należy do użytkownika
        """
        # Pobierz pozycję i sprawdź ownership
        bill_item = await self.bill_item_service.get_by_id(bill_item_id)

        # Sprawdź ownership przez Bill
        await self._verify_bill_ownership(bill_item.bill_id, user_id)

        # Jeśli nie podano edytowanego tekstu, użyj oryginalnego
        if edited_text is None:
            edited_text = bill_item.original_text or ""

        # Jeśli nie podano kategorii, użyj istniejącej
        if edited_category_id is None:
            edited_category_id = bill_item.category_id

        # Użyj ProductLearningService do weryfikacji (automatycznie tworzy aliasy i ProductIndex)
        verified_item, product_index = (
            await self.product_learning_service.handle_user_bill_item_verification(
                bill_item_id=bill_item_id,
                user_id=user_id,
                edited_original_text=edited_text,
                edited_category_id=edited_category_id,
            )
        )

        logger.info(
            f"Verified bill_item_id={bill_item_id} for user_id={user_id}. "
            f"ProductIndex created: {product_index is not None}"
        )

        return verified_item

    async def skip_item(self, bill_item_id: int, user_id: int) -> BillItem:
        """
        Pomija pozycję (nie weryfikuje, tylko zwraca dla informacji).

        Args:
            bill_item_id: ID pozycji do pominięcia
            user_id: ID użytkownika

        Returns:
            BillItem: Pozycja (bez zmian)

        Raises:
            ResourceNotFoundError: Jeśli pozycja nie istnieje
            BillAccessDeniedError: Jeśli pozycja nie należy do użytkownika
        """
        # Pobierz pozycję i sprawdź ownership
        bill_item = await self.bill_item_service.get_by_id(bill_item_id)

        # Sprawdź ownership przez Bill
        await self._verify_bill_ownership(bill_item.bill_id, user_id)

        logger.info(f"Skipped bill_item_id={bill_item_id} for user_id={user_id}")

        return bill_item

    async def check_all_items_verified(self, bill_id: int, user_id: int) -> bool:
        """
        Sprawdza czy wszystkie pozycje wymagające weryfikacji zostały zweryfikowane.

        Args:
            bill_id: ID rachunku
            user_id: ID użytkownika

        Returns:
            bool: True jeśli wszystkie pozycje zweryfikowane, False w przeciwnym razie
        """
        # Weryfikacja ownership
        await self._verify_bill_ownership(bill_id, user_id)

        # Sprawdź czy są jeszcze niezweryfikowane pozycje
        stmt = select(func.count(BillItem.id)).where(
            BillItem.bill_id == bill_id, BillItem.is_verified.is_(False)
        )
        result = await self.session.execute(stmt)
        unverified_count = result.scalar() or 0

        all_verified = unverified_count == 0

        logger.info(
            f"Verification status for bill_id={bill_id}: "
            f"{'all verified' if all_verified else f'{unverified_count} items remaining'}"
        )

        return all_verified

    async def finalize_verification(self, bill_id: int, user_id: int) -> Bill:
        """
        Finalizuje weryfikację - aktualizuje status Bill na COMPLETED.

        Args:
            bill_id: ID rachunku
            user_id: ID użytkownika

        Returns:
            Bill: Zaktualizowany rachunek

        Raises:
            ResourceNotFoundError: Jeśli rachunek nie istnieje
            BillAccessDeniedError: Jeśli rachunek nie należy do użytkownika
            ValueError: Jeśli nie wszystkie pozycje zostały zweryfikowane
        """
        # Weryfikacja ownership
        await self._verify_bill_ownership(bill_id, user_id)

        # Sprawdź czy wszystkie pozycje zostały zweryfikowane
        if not await self.check_all_items_verified(bill_id, user_id):
            raise ValueError(
                f"Cannot finalize verification for bill_id={bill_id}: "
                "not all items have been verified"
            )

        # Aktualizuj status na COMPLETED
        update_data = BillUpdate(status=ProcessingStatus.COMPLETED)
        await self.bill_service.update(
            bill_id=bill_id, data=update_data, user_id=user_id
        )

        # Pobierz zaktualizowany obiekt Bill (nie Response)
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        updated_bill = result.scalar_one()

        logger.info(
            f"Finalized verification for bill_id={bill_id}, user_id={user_id}. "
            f"Status updated to COMPLETED"
        )

        return updated_bill
