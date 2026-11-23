import json
import logging
import re
import time
from decimal import Decimal

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.ai.catalog_prompt import build_categorization_prompt, hits_for_categorization
from src.ai.confidence import (
    catalog_name_without_category,
    normalization_confidence,
)
from src.ai.schemas import NormalizedItem
from src.ai.usage import CallOutcome, ModelUsage
from src.categories.models import Category
from src.categories.schemas import CategoryResponse
from src.categories.services import CategoryService
from src.common.exceptions import ResourceNotFoundError
from src.config import settings
from src.ocr.schemas import OCRItem
from src.product_index_aliases.models import ProductIndexAlias
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.catalog import CatalogHit
from src.product_indexes.models import ProductIndex
from src.product_indexes.services import ProductIndexService

logger = logging.getLogger(__name__)


def _token_count(response: object) -> int | None:
    usage = getattr(response, "usage_metadata", None)
    total = getattr(usage, "total_token_count", None)
    if total is None:
        return None
    return int(total)


def _should_retry_gemini_error(exception: BaseException) -> bool:
    """
    Sprawdza, czy błąd Gemini powinien być retryowany.

    NIE retryujemy:
    - InvalidArgument (błędne żądanie)
    - PermissionDenied (brak uprawnień)

    Retryujemy:
    - ResourceExhausted (429 Too Many Requests)
    - ServiceUnavailable (503)
    - InternalServerError (500)
    - DeadlineExceeded (Timeout)
    """
    if isinstance(
        exception,
        (
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
            google_exceptions.InternalServerError,
            google_exceptions.DeadlineExceeded,
            google_exceptions.Aborted,
        ),
    ):
        logger.warning(f"Gemini API error (will retry): {str(exception)}")
        return True

    return False


class AICategorizationService:
    """
    Serwis odpowiedzialny za kategoryzację i normalizację produktów z OCR.

    """

    def __init__(
        self,
        session: AsyncSession,
        product_index_service: ProductIndexService,
        alias_service: ProductIndexAliasService,
        category_service: CategoryService,
    ):
        """
        Inicjalizacja serwisu z wstrzyknięciem zależności.

        Args:
            session: SQLAlchemy async session (do ręcznych zapytań)
            product_index_service: Serwis do zarządzania produktami
            alias_service: Serwis do zarządzania aliasami
            category_service: Serwis do zarządzania kategoriami
        """
        self.session = session
        self.product_index_service = product_index_service
        self.alias_service = alias_service
        self.category_service = category_service
        self.usage = ModelUsage(session)

        genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
        self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)  # type: ignore[attr-defined]

    def _preprocess_text(self, raw_text: str) -> str:
        """
        Cleans text from OCR noise.
        1. Whitespace normalization (remove double spaces)
        2. Symbol removal (remove weird characters at ends, e.g., _, #)
        3. Decimal normalization (replace , with . in numbers)
        """
        if not raw_text:
            return ""

        # 1. Whitespace normalization
        text = " ".join(raw_text.split())

        # 2. Symbol removal (leading/trailing specific noise characters)
        # Removing common OCR artifacts from ends: _ # - * | \ /
        text = text.strip(" _#-*|\\/")

        # 3. Decimal normalization (replace , with . in numbers)
        # Regex to find comma between digits: (\d),(\d) -> \1.\2
        text = re.sub(r"(\d),(\d)", r"\1.\2", text)

        return text.strip()

    async def _find_by_alias(
        self, cleaned_text: str, shop_id: int | None = None, user_id: int | None = None
    ) -> ProductIndex | None:
        """
        Wyszukuje produkt w aliasach z priorytetyzacją (User+Shop -> Shop -> Global).

        Strategia (MVP - 3 zapytania):
        1. Próba User+Shop (jeśli oba dostępne) - najwyższy priorytet
        2. Próba Shop (jeśli dostępny) - średni priorytet
        3. Próba Global (user_id=NULL, shop_id=NULL) - najniższy priorytet

        Indeks: LOWER(raw_name) - wyszukiwanie case-insensitive

        Args:
            cleaned_text: Wyczyszczony tekst po pre-processingu
            shop_id: ID sklepu (opcjonalne)
            user_id: ID użytkownika (opcjonalne)

        Returns:
            ProductIndex jeśli znaleziono alias, None w przeciwnym razie
        """
        # Próba 1: User+Shop (najwyższy priorytet)
        if user_id and shop_id:
            stmt = (
                select(ProductIndex)
                .join(ProductIndexAlias, ProductIndex.id == ProductIndexAlias.index_id)
                .where(
                    func.lower(ProductIndexAlias.raw_name) == func.lower(cleaned_text),
                    ProductIndexAlias.user_id == user_id,
                    ProductIndexAlias.shop_id == shop_id,
                )
                .order_by(ProductIndexAlias.confirmations_count.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                return product

        # Próba 2: Shop (średni priorytet)
        if shop_id:
            stmt = (
                select(ProductIndex)
                .join(ProductIndexAlias, ProductIndex.id == ProductIndexAlias.index_id)
                .where(
                    func.lower(ProductIndexAlias.raw_name) == func.lower(cleaned_text),
                    ProductIndexAlias.shop_id == shop_id,
                    ProductIndexAlias.user_id.is_(None),
                )
                .order_by(ProductIndexAlias.confirmations_count.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                return product

        # Próba 3: Global (najniższy priorytet)
        stmt = (
            select(ProductIndex)
            .join(ProductIndexAlias, ProductIndex.id == ProductIndexAlias.index_id)
            .where(
                func.lower(ProductIndexAlias.raw_name) == func.lower(cleaned_text),
                ProductIndexAlias.user_id.is_(None),
                ProductIndexAlias.shop_id.is_(None),
            )
            .order_by(ProductIndexAlias.confirmations_count.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _fuzzy_search_product(
        self, cleaned_text: str, category_suggestion: str | None = None
    ) -> ProductIndex | None:
        """
        Wyszukuje produkt używając fuzzy search (PostgreSQL pg_trgm).

        Strategia [MVP]:
        1. Dynamiczny threshold: dla krótkich słów (<5 znaków) wyższy threshold (0.9)
        2. Bazowy threshold: 0.75 (zwiększony z 0.6 dla lepszej precyzji)
        3. Opcjonalnie: filtrowanie po kategorii (jeśli category_suggestion dostępna)

        Indeks: idx_product_indexes_name_trgm (GIN trigram)

        Args:
            cleaned_text: Wyczyszczony tekst po pre-processingu
            category_suggestion: Opcjonalna sugestia kategorii z OCR/LLM

        Returns:
            ProductIndex jeśli znaleziono match, None w przeciwnym razie
        """
        # Dynamiczny threshold dla krótkich słów
        word_length = len(cleaned_text)
        if word_length < settings.AI_MIN_WORD_LENGTH_STRICT:
            threshold = settings.AI_STRICT_THRESHOLD
        else:
            threshold = settings.AI_SIMILARITY_THRESHOLD

        # PostgreSQL similarity search with pg_trgm
        # Używamy similarity() zamiast operatora %, aby móc kontrolować threshold w query
        stmt = (
            select(
                ProductIndex,
                func.similarity(ProductIndex.name, cleaned_text).label("score"),
            )
            .where(func.similarity(ProductIndex.name, cleaned_text) >= threshold)
            .order_by(func.similarity(ProductIndex.name, cleaned_text).desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        return row[0] if row else None

    async def _find_by_vector(
        self, cleaned_text: str
    ) -> tuple[ProductIndex | None, list[CatalogHit]]:
        """Top-k cosine search. Hits stay available when the score is too low."""
        try:
            query = await self.product_index_service.embed_name(cleaned_text)
            rows = await self.product_index_service.nearest_catalog(
                query, top_k=settings.AI_VECTOR_TOP_K
            )
        except Exception as exc:
            logger.warning("Wyszukiwanie wektorowe nie doszło do skutku: %s", exc)
            return None, []
        hits = [hit for _, hit in rows]
        if not hits or hits[0].similarity < settings.AI_VECTOR_SIMILARITY_THRESHOLD:
            return None, hits
        return rows[0][0], hits

    async def _assign_category(
        self,
        product_index: ProductIndex | None,
        cleaned_text: str,
        category_suggestion: str | None = None,
        shop_name: str | None = None,
        catalog_hits: list[CatalogHit] | None = None,
        user_id: int | None = None,
    ) -> CategoryResponse:
        """
        Przypisuje kategorię do produktu.

        Priorytety:
        1. Jeśli product_index ma istniejącą kategorię, użyj jej.
        2. Jeśli nazwa jest z katalogu, a kategorii nie ma, użyj "Inne" bez modelu.
        3. W przeciwnym razie zapytaj Gemini.
        4. Gdy model nie wskaże kategorii, użyj "Inne".

        Args:
            product_index: ProductIndex znaleziony przez normalizację (lub None)
            cleaned_text: Wyczyszczony tekst produktu (dla AI Categorization)
            category_suggestion: Sugestia kategorii z OCR/LLM (opcjonalne)
            shop_name: Nazwa sklepu dla kontekstu AI (opcjonalne)

        Returns:
            CategoryResponse: Przypisana kategoria produktu

        Most Koncepcyjny (PHP -> Python):
        - W Symfony/Laravel mielibyście podobną logikę w Service Layer (np. OrderService::assignCategory).
        - W Pythonie używamy async/await dla operacji I/O (DB, API), co jest idiomatyczne dla FastAPI.
        """
        # Priorytet 1: Kategoria z ProductIndex
        if product_index and product_index.category_id:
            try:
                category = await self.category_service.get_by_id(
                    product_index.category_id
                )
                logger.debug(
                    f"Użyto kategorii z ProductIndex (ID: {product_index.id}, "
                    f"category_id: {product_index.category_id})"
                )
                return category
            except ResourceNotFoundError:
                logger.warning(
                    f"ProductIndex (ID: {product_index.id}) ma nieistniejące category_id: "
                    f"{product_index.category_id}. Przechodzę do AI Categorization."
                )

        if catalog_name_without_category(
            has_catalog_product=product_index is not None,
            category_id=product_index.category_id
            if product_index is not None
            else None,
        ):
            logger.info(
                "Katalog ma nazwę bez kategorii (ID: %s). Model generujący się nie woła.",
                product_index.id if product_index is not None else None,
            )
            return await self.category_service.get_fallback_category()

        available_categories = await self.category_service.get_all_categories()
        ai_category_id = await self._ai_categorize_product(
            cleaned_text=cleaned_text,
            category_suggestion=category_suggestion,
            shop_name=shop_name,
            available_categories=available_categories,
            catalog_hits=hits_for_categorization(
                product_index.name if product_index is not None else None,
                catalog_hits or [],
            ),
            user_id=user_id,
        )

        if ai_category_id:
            try:
                category = await self.category_service.get_by_id(ai_category_id)
                logger.info(
                    f"AI skategoryzowało produkt '{cleaned_text}' do kategorii ID: {ai_category_id}"
                )
                return category
            except ResourceNotFoundError:
                logger.warning(
                    f"AI zwróciło nieistniejące category_id={ai_category_id} dla produktu: "
                    f"{cleaned_text}. Używam fallback."
                )

        # Priorytet 3: Fallback
        fallback_category = await self.category_service.get_fallback_category()
        logger.debug(f"Użyto kategorii fallback 'Inne' dla produktu: {cleaned_text}")
        return fallback_category

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry_gemini_error),
        reraise=True,
    )
    async def _ai_categorize_product(
        self,
        cleaned_text: str,
        category_suggestion: str | None = None,
        shop_name: str | None = None,
        available_categories: list[Category] | None = None,
        catalog_hits: list[CatalogHit] | None = None,
        user_id: int | None = None,
    ) -> int | None:
        """
        Używa Gemini API do zaproponowania kategorii dla nieznanego produktu.

        KRYTYCZNE: Ta metoda NIE może być wywołana wewnątrz transakcji DB!
        - Wywołania zewnętrznych API (Gemini) mogą trwać sekundy
        - Trzymanie otwartej transakcji DB blokuje połączenie i może spowodować deadlock
        - Wywołaj TĘ METODĘ PRZED otwarciem transakcji session.begin()

        Args:
            cleaned_text: Wyczyszczony tekst produktu (np. "Mleko 3.2%")
            category_suggestion: Sugestia kategorii z OCR/LLM (opcjonalne)
            shop_name: Nazwa sklepu dla kontekstu (opcjonalne)
            available_categories: Lista dostępnych kategorii z DB (wymagane)

        Returns:
            category_id jeśli AI znalazło dopasowanie (confidence >= threshold)
            None jeśli AI nie jest pewne (wtedy użyj fallback)

        Proces:
        1. Przygotuj prompt z kontekstem (produkt, sugestia, sklep, lista kategorii)
        2. Wywołaj Gemini API z structured output (JSON schema)
        3. Waliduj odpowiedź (czy zaproponowana kategoria istnieje w DB)
        4. Sprawdź confidence score (threshold: 0.8)
        5. Zwróć category_id lub None
        """
        if not available_categories or len(available_categories) == 0:
            logger.warning("Brak dostępnych kategorii dla AI Categorization")
            return None

        prompt = build_categorization_prompt(
            cleaned_text=cleaned_text,
            category_suggestion=category_suggestion,
            shop_name=shop_name,
            hits=catalog_hits or [],
            category_names=[cat.name for cat in available_categories],
        )

        reserved_id: int | None = None
        if user_id is not None:
            reserved_id = await self.usage.try_reserve_generative(
                user_id=user_id, model=settings.GEMINI_MODEL
            )
            if reserved_id is None:
                logger.info(
                    "Dzienny limit modelu generującego wyczerpany dla użytkownika %s",
                    user_id,
                )
                return None

        started = time.perf_counter()
        outcome: CallOutcome = "rejected"
        tokens: int | None = None
        invoked = False
        try:
            invoked = True
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(  # type: ignore[attr-defined]
                    response_mime_type="application/json",
                    temperature=settings.AI_CATEGORIZATION_TEMPERATURE,
                ),
            )
            tokens = _token_count(response)
            text = getattr(response, "text", None)
            if not text:
                logger.warning("Gemini zwróciło pustą odpowiedź dla kategoryzacji")
                return None

            parsed_data = json.loads(text)
            category_name = parsed_data.get("category_name")
            confidence = parsed_data.get("confidence", 0.0)
            reasoning = parsed_data.get("reasoning", "")

            if confidence < settings.AI_CATEGORIZATION_CONFIDENCE_THRESHOLD:
                outcome = "to_verify"
                logger.info(
                    f"AI confidence za niska ({confidence}) dla produktu: {cleaned_text}"
                )
                return None

            if not category_name:
                logger.info(f"AI nie zaproponowało kategorii dla: {cleaned_text}")
                return None

            for cat in available_categories:
                if cat.name.lower() == category_name.lower():
                    outcome = "accepted"
                    logger.info(
                        f"AI zaproponowało kategorię: {category_name} "
                        f"(confidence: {confidence}, reasoning: {reasoning})"
                    )
                    return cat.id

            outcome = "to_verify"
            logger.warning(
                f"AI zaproponowało nieistniejącą kategorię: {category_name} "
                f"dla produktu: {cleaned_text}"
            )
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Nieprawidłowa odpowiedź JSON z Gemini: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Błąd wywołania Gemini API: {str(e)}", exc_info=True)
            return None
        finally:
            if reserved_id is not None or invoked:
                try:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    if reserved_id is not None:
                        await self.usage.finish_generative(
                            reserved_id,
                            tokens=tokens,
                            latency_ms=latency_ms,
                            outcome=outcome,
                        )
                    else:
                        await self.usage.record_generative(
                            user_id=user_id,
                            model=settings.GEMINI_MODEL,
                            tokens=tokens,
                            latency_ms=latency_ms,
                            outcome=outcome,
                        )
                except Exception:
                    logger.exception("Nie zapisano wywołania modelu")

    async def normalize_item(
        self,
        ocr_item: OCRItem,
        shop_id: int | None = None,
        shop_name: str | None = None,
        user_id: int | None = None,
        save_alias: bool = True,
    ) -> NormalizedItem:
        """
        Główna metoda normalizacji produktu z OCR.

        Workflow (zgodnie z planem, sekcja 4.4):
        1. Pre-processing tekstu (Step 0)
        2. Normalizacja nazwy (Step 1: aliasy, Step 2: fuzzy search) - zwraca ProductIndex lub None
        3. Przypisanie kategorii (sekcja 4) - wywołanie _assign_category() jako osobny proces

        WAŻNE: Normalizacja nazwy produktu jest oddzielona od wyboru kategorii.
        Algorytm normalizacji skupia się wyłącznie na znalezieniu odpowiedniego ProductIndex
        na podstawie nazwy produktu z OCR. Wybór kategorii następuje osobno (patrz sekcja 4).

        Args:
            ocr_item: Pozycja z OCR (surowe dane)
            shop_id: ID sklepu (dla kontekstu aliasów)
            shop_name: Nazwa sklepu (dla kontekstu AI Categorization)
            user_id: ID użytkownika (dla kontekstu aliasów)
            save_alias: Czy zapisać alias po normalizacji (domyślnie True)

        Returns:
            NormalizedItem: Znormalizowana pozycja gotowa do zapisu jako BillItem

        Raises:
            CategorizationError: W przypadku krytycznego błędu kategoryzacji
        """
        # Step 0: Pre-processing
        cleaned_text = self._preprocess_text(ocr_item.name)

        if not cleaned_text:
            # Pusty tekst po czyszczeniu - fallback
            # Używamy oryginalnej nazwy z OCR jako normalized_name
            fallback_category = await self.category_service.get_fallback_category()
            return NormalizedItem(
                original_text=ocr_item.name,
                normalized_name=ocr_item.name,  # Pozostawiamy nazwę z OCR
                quantity=ocr_item.quantity,
                unit_price=ocr_item.unit_price or Decimal("0.0"),
                total_price=ocr_item.total_price,
                category_id=fallback_category.id,
                product_index_id=None,
                confidence_score=0.0,
                is_confident=False,
            )

        # Step 1: Wyszukiwanie w aliasach (priorytet: User+Shop -> Shop -> Global)
        product_index = await self._find_by_alias(cleaned_text, shop_id, user_id)
        found_by_alias = product_index is not None

        # Step 2: top-k po wektorze. Powyżej progu bierzemy nazwę z katalogu.
        catalog_hits: list[CatalogHit] = []
        if product_index is None:
            product_index, catalog_hits = await self._find_by_vector(cleaned_text)

        # Step 3: Fuzzy search, gdy alias i wektor nie wystarczyły.
        if product_index is None:
            product_index = await self._fuzzy_search_product(
                cleaned_text,
                ocr_item.category_suggestion,
            )

        if product_index and save_alias and not found_by_alias:
            try:
                await self.alias_service.upsert_alias(
                    raw_name=cleaned_text,
                    index_id=product_index.id,
                    shop_id=shop_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.error(f"Błąd zapisu aliasu: {str(e)}")

        # Kategoryzacja (osobny proces) - zgodnie z planem sekcja 4
        # KRYTYCZNE: Ta operacja jest POZA transakcją DB (wywołania API mogą trwać sekundy)
        category = await self._assign_category(
            product_index=product_index,
            cleaned_text=cleaned_text,
            category_suggestion=ocr_item.category_suggestion,
            shop_name=shop_name,
            catalog_hits=catalog_hits,
            user_id=user_id,
        )

        fallback_category = await self.category_service.get_fallback_category()
        confidence_score, is_confident = normalization_confidence(
            product_category_id=(
                product_index.category_id if product_index is not None else None
            ),
            assigned_category_id=category.id,
            fallback_category_id=fallback_category.id,
            ocr_confidence=ocr_item.confidence_score,
        )

        # Efekt normalizacji: znalezienie nazwy produktu lub pozostanie nazwy odczytanej przez OCR
        # Jeśli produkt znaleziony → użyj nazwy z ProductIndex
        # Jeśli produkt nieznany → użyj wyczyszczonej nazwy z OCR (cleaned_text)
        normalized_name = product_index.name if product_index else cleaned_text

        return NormalizedItem(
            original_text=ocr_item.name,
            normalized_name=normalized_name,
            quantity=ocr_item.quantity,
            unit_price=ocr_item.unit_price or Decimal("0.0"),
            total_price=ocr_item.total_price,
            category_id=category.id,
            product_index_id=product_index.id if product_index else None,
            confidence_score=confidence_score,
            is_confident=is_confident,
        )
