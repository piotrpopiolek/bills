"""
Product Learning Service - zarządzanie uczeniem się produktów z weryfikacji użytkowników.

Most Koncepcyjny (PHP → Python):
W Symfony/Laravel używałbyś Event Subscriber lub Command Handler (Symfony Messenger) do obsługi
zdarzeń weryfikacji. W FastAPI mamy serwis jako warstwę domenową - idiomatyczne podejście
w Pythonie, gdzie logika biznesowa jest w serwisach, a nie w kontrolerach.
"""

import logging
import re
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.models import BillItem, VerificationSource
from src.bill_items.schemas import BillItemUpdate
from src.bill_items.services import BillItemService
from src.bills.models import Bill
from src.config import settings
from src.product_candidates.models import ProductCandidate
from src.product_candidates.schemas import (
    ProductCandidateCreate,
    ProductCandidateUpdate,
)
from src.product_candidates.services import ProductCandidateService
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.models import ProductIndex
from src.product_indexes.schemas import ProductIndexCreate
from src.product_indexes.services import ProductIndexService

logger = logging.getLogger(__name__)


class ProductLearningService:
    """
    Serwis odpowiedzialny za uczenie się produktów z weryfikacji użytkowników.

    Implementuje workflow zgodnie z planem:
    1. Weryfikacja BillItem przez użytkownika
    2. Zarządzanie ProductCandidate (grupowanie, liczenie potwierdzeń)
    3. Tworzenie ProductIndex po osiągnięciu progu
    4. Aktualizacja powiązanych BillItems i tworzenie aliasów
    """

    def __init__(
        self,
        session: AsyncSession,
        bill_item_service: BillItemService,
        product_candidate_service: ProductCandidateService,
        product_index_service: ProductIndexService,
        alias_service: ProductIndexAliasService,
    ):
        """
        Inicjalizacja serwisu z wstrzyknięciem zależności.

        Most Koncepcyjny (PHP → Python):
        W Symfony/Laravel używałbyś Dependency Injection przez konstruktor (autowiring).
        W FastAPI używamy jawnego wstrzykiwania zależności - bardziej deklaratywne i czytelne.

        Args:
            session: SQLAlchemy async session
            bill_item_service: Serwis do zarządzania BillItems
            product_candidate_service: Serwis do zarządzania ProductCandidates
            product_index_service: Serwis do zarządzania ProductIndexes
            alias_service: Serwis do zarządzania aliasami
        """
        self.session = session
        self.bill_item_service = bill_item_service
        self.product_candidate_service = product_candidate_service
        self.product_index_service = product_index_service
        self.alias_service = alias_service

    def _preprocess_text_for_grouping(self, text: str) -> str:
        """
        Preprocessuje tekst dla potrzeb grupowania w ProductCandidate.

        Most Koncepcyjny (PHP → Python):
        W PHP używałbyś strtolower(), trim(), preg_replace().
        W Pythonie używamy metod stringowych i re - bardziej idiomatyczne.

        Args:
            text: Surowy tekst do przetworzenia

        Returns:
            str: Znormalizowany tekst
        """
        if not text:
            return ""

        # 1. Normalizacja whitespace
        text = " ".join(text.split())

        # 2. Usunięcie znaków specjalnych z końców (OCR artifacts)
        text = text.strip(" _#-*|\\/")

        # 3. Normalizacja przecinków w liczbach
        text = re.sub(r"(\d),(\d)", r"\1.\2", text)

        # 4. Lowercase dla porównań
        text = text.lower()

        return text.strip()

    async def _find_or_create_product_candidate(
        self, edited_original_text: str, category_id: int | None
    ) -> ProductCandidate:
        """
        Znajduje lub tworzy ProductCandidate dla zedytowanego tekstu.

        Strategia:
        1. Normalizuje edited_original_text do normalized_grouped_name
        2. Wykonuje fuzzy search w product_candidates na representative_name
        3. Jeśli znaleziono (similarity >= FUZZY_MATCH_GROUPING_THRESHOLD), zwraca istniejący
        4. Jeśli nie znaleziono, tworzy nowy ProductCandidate
        5. Zwiększa user_confirmations i aktualizuje category_id

        Most Koncepcyjny (PHP → Python):
        W Doctrine używałbyś DQL z similarity() lub natywnego SQL.
        W SQLAlchemy używamy func.similarity() - idiomatyczne dla PostgreSQL.

        Args:
            edited_original_text: Zaktualizowany tekst z weryfikacji użytkownika
            category_id: ID kategorii (opcjonalne)

        Returns:
            ProductCandidate: Znaleziony lub utworzony kandydat
        """
        # Normalizacja tekstu
        normalized_name = self._preprocess_text_for_grouping(edited_original_text)

        if not normalized_name:
            raise ValueError("Normalized name cannot be empty")

        # Fuzzy search w product_candidates (tylko pending)
        threshold = settings.FUZZY_MATCH_GROUPING_THRESHOLD
        stmt = (
            select(
                ProductCandidate,
                func.similarity(
                    func.lower(ProductCandidate.representative_name), normalized_name
                ).label("score"),
            )
            .where(
                ProductCandidate.status == "pending",
                func.similarity(
                    func.lower(ProductCandidate.representative_name), normalized_name
                )
                >= threshold,
            )
            .order_by(
                func.similarity(
                    func.lower(ProductCandidate.representative_name), normalized_name
                ).desc()
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if row:
            # Znaleziono istniejący kandydat
            candidate = row[0]
            # Zwiększ licznik potwierdzeń
            candidate.user_confirmations += 1
            # Aktualizuj category_id (jeśli podane i różne)
            if category_id is not None and candidate.category_id != category_id:
                candidate.category_id = category_id

            try:
                await self.session.commit()
                await self.session.refresh(candidate)
            except Exception as e:
                await self.session.rollback()
                logger.error(
                    f"Failed to update ProductCandidate {candidate.id}: {e}",
                    exc_info=True,
                )
                raise

            return candidate

        # Utwórz nowy kandydat
        candidate_data = ProductCandidateCreate(
            representative_name=edited_original_text,  # Używamy oryginalnego tekstu, nie znormalizowanego
            user_confirmations=1,
            category_id=category_id,
            status="pending",
        )

        candidate = await self.product_candidate_service.create(candidate_data)
        logger.info(
            f"Created new ProductCandidate {candidate.id} for '{edited_original_text}'"
        )

        return candidate

    async def _create_product_index_from_candidate(
        self, candidate: ProductCandidate
    ) -> ProductIndex:
        """
        Tworzy ProductIndex z ProductCandidate po osiągnięciu progu.

        Strategia:
        1. Znajduje wszystkie zweryfikowane BillItems powiązane z kandydatem (fuzzy match)
        2. Wyznacza najczęściej występującą original_text jako ProductIndex.name
        3. Wyznacza najczęściej występującą category_id jako ProductIndex.category_id
        4. Tworzy ProductIndex (lub zwraca istniejący jeśli duplikat)
        5. Tworzy aliasy dla wszystkich unikalnych original_text

        Most Koncepcyjny (PHP → Python):
        W Doctrine używałbyś DQL z GROUP BY i COUNT().
        W SQLAlchemy używamy func.count() i group_by() - idiomatyczne dla ORM.

        Args:
            candidate: ProductCandidate, który osiągnął próg

        Returns:
            ProductIndex: Utworzony lub istniejący ProductIndex
        """
        # Znajdź wszystkie powiązane BillItems
        bill_items = (
            await self.bill_item_service.find_unindexed_verified_items_for_candidate(
                candidate_representative_name=candidate.representative_name,
                candidate_category_id=candidate.category_id,
                fuzzy_threshold=settings.FUZZY_MATCH_GROUPING_THRESHOLD,
            )
        )

        if not bill_items:
            logger.warning(
                f"No verified BillItems found for ProductCandidate {candidate.id}. "
                "This should not happen if threshold was reached."
            )
            raise ValueError(
                f"No verified BillItems found for candidate {candidate.id}"
            )

        # Agregacja: najczęściej występująca original_text i category_id
        original_texts = [bi.original_text for bi in bill_items if bi.original_text]
        category_ids = [bi.category_id for bi in bill_items if bi.category_id]

        if not original_texts:
            raise ValueError(
                f"No original_text found in BillItems for candidate {candidate.id}"
            )

        # Najczęściej występująca nazwa
        text_counter = Counter(original_texts)
        most_common_text = text_counter.most_common(1)[0][0]

        # Najczęściej występująca kategoria (jeśli są kategorie)
        most_common_category_id = None
        if category_ids:
            category_counter = Counter(category_ids)
            most_common_category_id = category_counter.most_common(1)[0][0]

        # Utwórz lub pobierz istniejący ProductIndex
        product_index_data = ProductIndexCreate(
            name=most_common_text, category_id=most_common_category_id
        )

        product_index = await self.product_index_service.create_or_get_existing(
            product_index_data
        )
        logger.info(
            f"Created/retrieved ProductIndex {product_index.id} "
            f"('{product_index.name}') from candidate {candidate.id}"
        )

        # Utwórz aliasy dla wszystkich unikalnych original_text
        unique_texts = set(original_texts)
        for text in unique_texts:
            if text:  # Skip empty strings
                try:
                    # Pobierz shop_id i user_id z pierwszego BillItem z tym tekstem
                    # (dla kontekstu aliasu)
                    sample_bill_item = next(
                        bi for bi in bill_items if bi.original_text == text
                    )
                    await self.alias_service.upsert_alias(
                        raw_name=text,
                        index_id=product_index.id,
                        shop_id=(
                            sample_bill_item.bill.shop_id
                            if sample_bill_item.bill
                            else None
                        ),
                        user_id=(
                            sample_bill_item.bill.user_id
                            if sample_bill_item.bill
                            else None
                        ),
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create alias for '{text}' -> ProductIndex {product_index.id}: {e}",
                        exc_info=True,
                    )
                    # Continue with other aliases even if one fails
                    continue

        return product_index

    async def _update_bill_items_with_new_product_index(
        self, candidate: ProductCandidate, product_index: ProductIndex
    ) -> int:
        """
        Aktualizuje wszystkie powiązane BillItems nowym ProductIndex.

        Strategia:
        1. Znajduje wszystkie BillItems fuzzy matchujące kandydata
        2. Masowo aktualizuje ich index_id
        3. Tworzy aliasy dla każdego zaktualizowanego BillItem

        Most Koncepcyjny (PHP → Python):
        W Doctrine używałbyś QueryBuilder z WHERE IN i executeUpdate().
        W SQLAlchemy używamy bulk_update_index_id() - bardziej idiomatyczne dla bulk operations.

        Args:
            candidate: ProductCandidate, z którego utworzono ProductIndex
            product_index: Utworzony ProductIndex

        Returns:
            int: Liczba zaktualizowanych BillItems
        """
        # Znajdź wszystkie powiązane BillItems
        bill_items = (
            await self.bill_item_service.find_unindexed_verified_items_for_candidate(
                candidate_representative_name=candidate.representative_name,
                candidate_category_id=candidate.category_id,
                fuzzy_threshold=settings.FUZZY_MATCH_GROUPING_THRESHOLD,
            )
        )

        if not bill_items:
            return 0

        # Masowa aktualizacja index_id
        bill_item_ids = [bi.id for bi in bill_items]
        updated_count = await self.bill_item_service.bulk_update_index_id(
            bill_item_ids=bill_item_ids, new_product_index_id=product_index.id
        )

        logger.info(
            f"Updated {updated_count} BillItems with ProductIndex {product_index.id} "
            f"from candidate {candidate.id}"
        )

        return updated_count

    async def handle_user_bill_item_verification(
        self,
        bill_item_id: int,
        user_id: int,
        edited_original_text: str,
        edited_category_id: int | None,
    ) -> tuple[BillItem, ProductIndex | None]:
        """
        Główna metoda obsługująca weryfikację BillItem przez użytkownika.

        Implementuje pełny workflow zgodnie z planem:
        1. Aktualizacja BillItem (original_text, category_id, is_verified, verification_source)
        2. Sprawdzenie istniejącego ProductIndex (fuzzy search)
        3. Zarządzanie ProductCandidate (znajdź lub utwórz, zwiększ licznik)
        4. Sprawdzenie progu akceptacji
        5. Tworzenie ProductIndex (jeśli próg osiągnięty)
        6. Aktualizacja BillItems i tworzenie aliasów

        Most Koncepcyjny (PHP → Python):
        W Symfony używałbyś Command Handler (Symfony Messenger) lub Event Subscriber.
        W FastAPI mamy serwis jako orchestrator - idiomatyczne podejście w Pythonie.

        Args:
            bill_item_id: ID BillItem do weryfikacji
            user_id: ID użytkownika weryfikującego (do sprawdzenia ownership)
            edited_original_text: Zaktualizowany tekst produktu
            edited_category_id: Zaktualizowana kategoria (opcjonalne)

        Returns:
            Tuple[BillItem, Optional[ProductIndex]]: Zaktualizowany BillItem i opcjonalnie utworzony ProductIndex

        Raises:
            ResourceNotFoundError: Jeśli BillItem nie istnieje
            BillAccessDeniedError: Jeśli BillItem nie należy do użytkownika
        """
        # Step 1: Aktualizacja BillItem
        update_data = BillItemUpdate(
            original_text=edited_original_text,
            category_id=edited_category_id,
            is_verified=True,
            verification_source=VerificationSource.USER,
        )

        bill_item = await self.bill_item_service.update(
            bill_item_id=bill_item_id, data=update_data, user_id=user_id
        )

        logger.info(f"Updated BillItem {bill_item_id} with user verification")

        # Step 2: Sprawdź istniejący ProductIndex (fuzzy search)
        normalized_text = self._preprocess_text_for_grouping(edited_original_text)
        existing_product_index = await self.product_index_service.fuzzy_search(
            search_text=normalized_text, threshold=settings.AI_SIMILARITY_THRESHOLD
        )

        if existing_product_index:
            # Znaleziono istniejący ProductIndex - zaktualizuj BillItem i utwórz alias
            bill_item.index_id = existing_product_index.id
            await self.session.commit()
            await self.session.refresh(bill_item)

            # Utwórz alias dla tego tekstu
            try:
                # Pobierz shop_id z Bill
                stmt = select(Bill).where(Bill.id == bill_item.bill_id)
                result = await self.session.execute(stmt)
                bill = result.scalar_one_or_none()

                await self.alias_service.upsert_alias(
                    raw_name=edited_original_text,
                    index_id=existing_product_index.id,
                    shop_id=bill.shop_id if bill else None,
                    user_id=user_id,
                )
            except Exception as e:
                logger.error(
                    f"Failed to create alias for BillItem {bill_item_id}: {e}",
                    exc_info=True,
                )

            logger.info(
                f"BillItem {bill_item_id} linked to existing ProductIndex {existing_product_index.id}"
            )
            return bill_item, None

        # Step 3: Zarządzanie ProductCandidate
        candidate = await self._find_or_create_product_candidate(
            edited_original_text=edited_original_text, category_id=edited_category_id
        )

        # Step 4: Sprawdź próg akceptacji
        if candidate.user_confirmations >= settings.PRODUCT_INDEX_ACCEPTANCE_THRESHOLD:
            # Step 5: Utwórz ProductIndex
            product_index = await self._create_product_index_from_candidate(candidate)

            # Step 6: Zaktualizuj BillItems
            updated_count = await self._update_bill_items_with_new_product_index(
                candidate=candidate, product_index=product_index
            )

            # Step 7: Zaktualizuj ProductCandidate
            candidate_update = ProductCandidateUpdate(
                status="approved", product_index_id=product_index.id
            )
            await self.product_candidate_service.update(
                product_candidate_id=candidate.id, data=candidate_update
            )

            logger.info(
                f"ProductCandidate {candidate.id} approved and converted to ProductIndex {product_index.id}. "
                f"Updated {updated_count} BillItems."
            )

            return bill_item, product_index
        else:
            logger.info(
                f"ProductCandidate {candidate.id} has {candidate.user_confirmations} confirmations "
                f"(threshold: {settings.PRODUCT_INDEX_ACCEPTANCE_THRESHOLD}). Waiting for more."
            )
            return bill_item, None
