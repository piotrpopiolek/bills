"""
Bills Processing Service.

Orchestrates the complete bill processing pipeline from file download to database storage.
"""
import logging
from io import BytesIO
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.bills.models import Bill, ProcessingStatus
from src.common.exceptions import ResourceNotFoundError
from src.bills.services import BillService
from src.bills.schemas import BillUpdate
from src.bill_items.models import BillItem, VerificationSource
from src.bill_items.services import BillItemService
from src.bill_items.schemas import BillItemCreate
from src.shops.services import ShopService
from src.storage.service import StorageService
from src.ocr.services import OCRService
from src.ocr.schemas import OCRReceiptData, OCRItem
from src.ai.service import AICategorizationService
from src.ai.schemas import NormalizedItem
from src.processing.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class BillsProcessorService:
    """
    Service orchestrating bill processing pipeline.

    Flow:
    1. Download file from Storage
    2. Call OCR Service
    3. Update Bill status → PROCESSING
    4. Get or create Shop
    5. Create BillItems
    6. Update Bill (total_amount, shop_id, status → COMPLETED)
    7. Handle errors (status → ERROR, error_message)
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_service: StorageService,
        ocr_service: OCRService,
        bill_service: BillService,
        bill_item_service: BillItemService,
        shop_service: ShopService,
        ai_service: AICategorizationService
    ):
        self.session = session
        self.storage_service = storage_service
        self.ocr_service = ocr_service
        self.bill_service = bill_service
        self.bill_item_service = bill_item_service
        self.shop_service = shop_service
        self.ai_service = ai_service

    async def process_receipt(self, bill_id: int) -> None:
        """
        Main method processing receipt from PENDING to COMPLETED/TO_VERIFY/ERROR.
        
        New flow:
        PENDING → PROCESSING → [TO_VERIFY] → COMPLETED
                         ↘ ERROR
        """
        logger.info(f"Starting receipt processing for bill_id={bill_id}")

        try:
            # Step 1: Get Bill and validate basic requirements
            bill = await self._get_bill(bill_id)

            # Quick check: jeśli już przetworzony, pomiń (early return)
            if bill.status == ProcessingStatus.COMPLETED:
                logger.info(f"Bill {bill_id} already processed (COMPLETED), skipping")
                return
            
            if bill.status == ProcessingStatus.TO_VERIFY:
                logger.info(f"Bill {bill_id} already processed (TO_VERIFY), skipping")
                return

            if not bill.image_url:
                await self._set_error(bill_id, "Bill has no image_url")
                return

            # Step 2: Atomowo przejmij lock (PENDING → PROCESSING)
            # KRYTYCZNE: To zapobiega race condition - jeśli wiele procesów próbuje
            # przetworzyć ten sam paragon równolegle, tylko jeden przejmie lock.
            if not await self._try_acquire_processing_lock(bill_id):
                # Inny proces już rozpoczął przetwarzanie - przerwij
                logger.info(f"Bill {bill_id} is already being processed by another process, skipping")
                return

            # Step 3: Download file from Storage
            file_content = await self._download_file(bill.image_url)

            # Step 4: Call OCR Service
            ocr_data = await self._extract_receipt_data(file_content, bill.image_url)

            # Step 5: Get or create Shop
            shop_id = await self._get_or_create_shop(
                ocr_data.shop_name,
                ocr_data.shop_address
            )

            # Step 6: AI Categorization & Normalization (POZA transakcją DB)
            # KRYTYCZNE: Wywołania Gemini API (w AI service) muszą być PRZED transakcjami DB
            # Serwis AI może używać własnych krótkich transakcji do odczytu (read-only),
            # ale nie powinien blokować połączenia czekając na Gemini.
            normalized_items = await self._normalize_items(
                ocr_data.items,
                shop_id=shop_id,
                shop_name=ocr_data.shop_name,
                user_id=bill.user_id
            )

            # Detailed logging of normalized items
            logger.info(
                f"AI normalization completed: {len(normalized_items)}/{len(ocr_data.items)} items normalized | "
                f"shop_id={shop_id}, shop_name={ocr_data.shop_name}"
            )
            
            # Log each normalized item in detail
            for idx, normalized_item in enumerate(normalized_items, start=1):
                unit_price_str = f"{normalized_item.unit_price:.2f}" if normalized_item.unit_price else "N/A"
                logger.info(
                    f"Normalized Item #{idx}: {normalized_item.original_text} → {normalized_item.normalized_name} | "
                    f"quantity={normalized_item.quantity}, unit_price={unit_price_str}, total_price={normalized_item.total_price:.2f} | "
                    f"category_id={normalized_item.category_id}, product_index_id={normalized_item.product_index_id} | "
                    f"confidence={normalized_item.confidence_score:.2f}, is_confident={normalized_item.is_confident}"
                )

            # # Step 7: Create BillItems
            # # Uwaga: BillItemService.create() wykonuje własny commit(), więc nie używamy session.begin()
            # # Most Koncepcyjny (PHP → Python): W Symfony/Laravel, Doctrine/Eloquent automatycznie
            # # zarządza transakcjami przez EntityManager/DB facade. W SQLAlchemy async, każdy serwis
            # # wykonuje własne commit(), co jest idiomatyczne dla async SQLAlchemy (connection pooling).
            await self._create_bill_items(bill_id, normalized_items)

            # Step 8: Determine final status based on validation
            # Sprawdzamy czy jakikolwiek item wymaga weryfikacji
            requires_verification = any(
                not item.is_confident or item.confidence_score < 0.8
                for item in normalized_items
            )
            
            final_status = (
                ProcessingStatus.TO_VERIFY 
                if requires_verification 
                else ProcessingStatus.COMPLETED
            )

            # Step 9: Update Bill with final data
            # Use date extracted from OCR if available, otherwise keep None
            await self._update_bill_completed(
                bill_id,
                total_amount=ocr_data.total_amount,
                shop_id=shop_id,
                bill_date=ocr_data.date,  # Use OCR date if extracted, None otherwise
                status=final_status
            )

            logger.info(
                f"Receipt processing finished for bill_id={bill_id}, status={final_status.value}",
                extra={
                    "status": final_status.value,
                    "requires_verification": ocr_data.requires_verification
                }
            )

        except Exception as e:
            logger.error(f"Error processing receipt bill_id={bill_id}: {e}", exc_info=True)
            # Try to save error state
            try:
                await self._set_error(bill_id, str(e))
            except Exception as inner_e:
                logger.critical(f"CRITICAL: Failed to save error status for bill {bill_id}: {inner_e}", exc_info=True)
            
            # Re-raise to let caller know something went wrong
            raise

    async def _get_bill(self, bill_id: int) -> Bill:
        """
        Get Bill model by ID, raise ResourceNotFoundError if not found.

        Używa bezpośredniego zapytania SQLAlchemy, ponieważ potrzebujemy modelu,
        a nie response schema (BillResponse).
        """
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ResourceNotFoundError("Bill", bill_id)

        return bill

    async def _download_file(self, image_url: str) -> bytes:
        """
        Download file from Storage.
        Propagates StorageService exceptions.
        """
        file_content = await self.storage_service.download_file(image_url)
        logger.debug(f"Downloaded file: {image_url} ({len(file_content)} bytes)")
        return file_content

    async def _extract_receipt_data(self, file_content: bytes, filename: str) -> OCRReceiptData:
        """
        Extract receipt data using OCR Service.
        Propagates OCRService exceptions.
        """
        file_obj = BytesIO(file_content)

        # Determine MIME type from filename
        mime_type = "image/jpeg"  # default
        if filename.endswith(".png"):
            mime_type = "image/png"
        elif filename.endswith(".webp"):
            mime_type = "image/webp"

        # Create UploadFile
        upload_file = UploadFile(
            file=file_obj,
            filename=filename,
            headers={"content-type": mime_type}
        )

        ocr_data = await self.ocr_service.extract_data(upload_file)
        
        return ocr_data

    async def _update_bill_status(self, bill_id: int, status: ProcessingStatus) -> None:
        """
        Update Bill status using BillService.
        """
        bill = await self._get_bill(bill_id)

        update_data = BillUpdate(status=status)

        try:
            await self.bill_service.update(bill_id, update_data, bill.user_id)
            logger.debug(f"Updated bill {bill_id} status to {status.value}")
        except Exception as e:
            logger.error(f"Failed to update bill status: {e}", exc_info=True)
            raise ProcessingError(f"Failed to update bill status: {str(e)}") from e

    async def _try_acquire_processing_lock(self, bill_id: int) -> bool:
        """
        Atomowo aktualizuje status z PENDING na PROCESSING.
        
        Zwraca True, jeśli udało się zaktualizować (lock acquired),
        False, jeśli status już nie był PENDING (inny proces rozpoczął przetwarzanie).
        
        Args:
            bill_id: ID paragonu do zablokowania
            
        Returns:
            bool: True jeśli lock został nabyty, False jeśli inny proces już rozpoczął przetwarzanie
        """
        stmt = (
            update(Bill)
            .where(Bill.id == bill_id)
            .where(Bill.status == ProcessingStatus.PENDING)
            .values(status=ProcessingStatus.PROCESSING)
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        rows_updated = result.rowcount
        
        if rows_updated > 0:
            logger.info(f"Acquired processing lock for bill_id={bill_id}")
            return True
        else:
            logger.warning(
                f"Could not acquire processing lock for bill_id={bill_id} - "
                f"status is not PENDING (likely already being processed by another process)"
            )
            return False

    async def _get_or_create_shop(
        self,
        shop_name: Optional[str],
        shop_address: Optional[str]
    ) -> Optional[int]:
        """Get or create Shop, return shop_id or None."""
        if not shop_name:
            logger.debug("No shop name in OCR data, skipping shop creation")
            return None

        try:
            shop = await self.shop_service.get_or_create_by_name(
                name=shop_name,
                address=shop_address
            )
            logger.info(f"Shop resolved: {shop.id} ({shop_name})")
            return shop.id
        except Exception as e:
            logger.error(f"Failed to get/create shop: {e}", exc_info=True)
            # Don't fail processing if shop creation fails
            # Just log and continue without shop_id
            logger.warning(f"Continuing without shop_id due to error: {e}")
            return None

    async def _normalize_items(
        self,
        ocr_items: List[OCRItem],
        shop_id: Optional[int] = None,
        shop_name: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[NormalizedItem]:
        """
        Normalizuje pozycje OCR używając AI Categorization Service.
        
        KRYTYCZNE: Ta metoda jest wywoływana POZA transakcją DB!
        - Wywołania Gemini API mogą trwać sekundy
        - Nie blokujemy połączenia DB podczas wywołań zewnętrznych API
        
        Most Koncepcyjny (PHP → Python):
        W Symfony/Laravel (synchroniczne) nie ma problemu z blokowaniem połączenia,
        bo każde żądanie ma dedykowane połączenie (FPM model).
        W async Pythonie połączenia są współdzielone (connection pool),
        więc długie operacje w transakcji mogą spowodować deadlock.
        
        Args:
            ocr_items: Lista pozycji z OCR
            shop_id: ID sklepu (dla kontekstu aliasów)
            shop_name: Nazwa sklepu (dla kontekstu AI Categorization)
            user_id: ID użytkownika (dla kontekstu aliasów)
            
        Returns:
            List[NormalizedItem]: Lista znormalizowanych pozycji gotowych do zapisu
        """
        normalized_items = []
        
        for ocr_item in ocr_items:
            try:
                normalized_item = await self.ai_service.normalize_item(
                    ocr_item=ocr_item,
                    shop_id=shop_id,
                    shop_name=shop_name,
                    user_id=user_id,
                    save_alias=True  # Uczenie się systemu - zapis aliasów
                )
                # Detailed logging of normalized item
                unit_price_str = f"{normalized_item.unit_price:.2f}" if normalized_item.unit_price else "N/A"
                logger.info(
                    f"AI normalize_item returned: original='{normalized_item.original_text}' → normalized='{normalized_item.normalized_name}' | "
                    f"quantity={normalized_item.quantity}, unit_price={unit_price_str}, total_price={normalized_item.total_price:.2f} | "
                    f"category_id={normalized_item.category_id}, product_index_id={normalized_item.product_index_id} | "
                    f"confidence={normalized_item.confidence_score:.2f}, is_confident={normalized_item.is_confident}"
                )
                normalized_items.append(normalized_item)
            except Exception as e:
                logger.error(
                    f"Failed to normalize item '{ocr_item.name}': {e}",
                    exc_info=True
                )
                # Continue with other items even if one fails
                # Fallback: użyj surowych danych z OCR (bez normalizacji)
                continue
        
        logger.info(f"Normalized {len(normalized_items)}/{len(ocr_items)} items")
        return normalized_items

    async def _create_bill_items(self, bill_id: int, items: List[NormalizedItem]) -> None:
        """
        Tworzy BillItems z znormalizowanych pozycji.
        
        Przyjmuje już znormalizowane i przeliczone obiekty NormalizedItem.
        Tylko mapuje na model DB (BillItemCreate) i zapisuje.
        
        Logika biznesowa (wyliczanie cen, walidacja) została przeniesiona do AI serwisu.
        
        Most Koncepcyjny (PHP → Python):
        W Symfony/Laravel używałbyś Data Transformer lub Mapper (np. Symfony Form Data Transformers).
        W Pythonie mamy prosty mapper jako metodę prywatną - idiomatyczne i czytelne.
        
        Args:
            bill_id: ID paragonu
            items: Lista znormalizowanych pozycji (NormalizedItem)
        """
        if not items:
            logger.warning(f"No normalized items for bill_id={bill_id}")
            return

        created_count = 0
        for normalized_item in items:
            try:
                # Mapowanie NormalizedItem -> BillItemCreate
                # NormalizedItem już ma przeliczone ceny i walidację
                bill_item_data = self._map_normalized_to_bill_item(
                    bill_id=bill_id,
                    normalized_item=normalized_item
                )

                await self.bill_item_service.create(bill_item_data)
                created_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to create bill_item for bill_id={bill_id}, "
                    f"item={normalized_item.original_text}: {e}",
                    exc_info=True
                )
                # Continue with other items even if one fails
                continue

        logger.info(f"Created {created_count}/{len(items)} bill_items for bill_id={bill_id}")

    def _map_normalized_to_bill_item(
        self,
        bill_id: int,
        normalized_item: NormalizedItem
    ) -> BillItemCreate:
        """
        Mapuje NormalizedItem na BillItemCreate.
        
        Logika biznesowa:
        - Items with negative prices always require verification (discounts/rebates)
        - Low confidence (< 0.8) also requires verification
        - NormalizedItem już ma przeliczone unit_price i total_price
        
        Args:
            bill_id: ID paragonu
            normalized_item: Znormalizowana pozycja z AI service
            
        Returns:
            BillItemCreate: Gotowy do zapisu w DB
        """
        # Items with negative prices always require verification
        has_negative_price = normalized_item.total_price < 0
        
        # Determine if item needs verification
        # - Negative prices always need verification
        # - Low confidence also requires verification
        needs_verification = (
            has_negative_price or 
            not normalized_item.is_confident or
            normalized_item.confidence_score < 0.8
        )

        # Log negative prices for monitoring
        if has_negative_price:
            logger.info(
                f"Item with negative price detected (will require verification) for bill_id={bill_id}: "
                f"{normalized_item.original_text} ({normalized_item.total_price} PLN)"
            )

        # Walidacja: quantity musi być > 0
        if normalized_item.quantity <= 0:
            raise ValueError(
                f"Invalid quantity for item {normalized_item.original_text}: "
                f"{normalized_item.quantity}"
            )

        # NormalizedItem już ma przeliczone ceny (unit_price, total_price)
        # Jeśli unit_price jest None, obliczamy z total_price / quantity
        unit_price = normalized_item.unit_price
        if unit_price is None or unit_price == 0:
            if normalized_item.quantity > 0:
                unit_price = normalized_item.total_price / normalized_item.quantity
            else:
                raise ValueError(
                    f"Cannot calculate unit_price for item {normalized_item.original_text}: "
                    f"quantity={normalized_item.quantity}, total_price={normalized_item.total_price}"
                )

        return BillItemCreate(
            bill_id=bill_id,
            quantity=normalized_item.quantity,
            unit_price=unit_price,
            total_price=normalized_item.total_price,
            original_text=normalized_item.original_text,
            confidence_score=Decimal(str(normalized_item.confidence_score)),
            is_verified=not needs_verification,  # False if negative price or low confidence
            verification_source=VerificationSource.AUTO,
            index_id=normalized_item.product_index_id,  # FK do ProductIndex (nullable)
            category_id=normalized_item.category_id  # FK do Category (nullable)
        )

    async def _update_bill_completed(
        self,
        bill_id: int,
        total_amount: Decimal,
        shop_id: Optional[int],
        bill_date: Optional[datetime],
        status: ProcessingStatus = ProcessingStatus.COMPLETED  # ← Now accepts TO_VERIFY too
    ) -> None:
        """Update Bill with final data and set status to COMPLETED or TO_VERIFY.
        
        bill_date: Date extracted from receipt via OCR (None if not extracted)
        """
        bill = await self._get_bill(bill_id)

        update_data = BillUpdate(
            status=status,
            total_amount=total_amount,
            shop_id=shop_id,
            bill_date=bill_date
        )

        try:
            await self.bill_service.update(bill_id, update_data, bill.user_id)
            logger.info(f"Bill {bill_id} marked as {status.value}")
        except Exception as e:
            logger.error(f"Failed to update bill as {status.value}: {e}", exc_info=True)
            raise ProcessingError(f"Failed to finalize bill: {str(e)}") from e

    async def _set_error(self, bill_id: int, error_message: str) -> None:
        """Set Bill status to ERROR and save error message."""
        bill = await self._get_bill(bill_id)

        # Truncate error message to fit database field
        max_error_length = 1000
        truncated_error = (
            error_message[:max_error_length]
            if len(error_message) > max_error_length
            else error_message
        )

        update_data = BillUpdate(
            status=ProcessingStatus.ERROR,
            error_message=truncated_error
        )

        try:
            await self.bill_service.update(bill_id, update_data, bill.user_id)
            logger.error(f"Bill {bill_id} marked as ERROR: {truncated_error}")
        except Exception as e:
            logger.critical(
                f"CRITICAL: Failed to set error status for bill {bill_id}: {e}",
                exc_info=True
            )
