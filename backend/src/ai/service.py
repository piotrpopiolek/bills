import re
import json
import logging
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from src.config import settings
from src.ai.schemas import NormalizedItem
from src.ai.exceptions import CategorizationError
from src.common.exceptions import ResourceNotFoundError
from src.ocr.schemas import OCRItem
from src.product_indexes.models import ProductIndex
from src.product_index_aliases.models import ProductIndexAlias
from src.product_indexes.services import ProductIndexService
from src.product_index_aliases.services import ProductIndexAliasService
from src.categories.services import CategoryService
from src.categories.models import Category

logger = logging.getLogger(__name__)


def _should_retry_gemini_error(exception: Exception) -> bool:
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
    if isinstance(exception, (
        google_exceptions.ResourceExhausted,
        google_exceptions.ServiceUnavailable,
        google_exceptions.InternalServerError,
        google_exceptions.DeadlineExceeded,
        google_exceptions.Aborted,
    )):
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
        category_service: CategoryService
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
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)

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
        text = re.sub(r'(\d),(\d)', r'\1.\2', text)

        return text.strip()

    async def _find_by_alias(
        self,
        cleaned_text: str,
        shop_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Optional[ProductIndex]:
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
                    ProductIndexAlias.shop_id == shop_id
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
                    ProductIndexAlias.user_id.is_(None)
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
                ProductIndexAlias.shop_id.is_(None)
            )
            .order_by(ProductIndexAlias.confirmations_count.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _fuzzy_search_product(
        self,
        cleaned_text: str,
        category_suggestion: Optional[str] = None
    ) -> Optional[ProductIndex]:
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
                func.similarity(ProductIndex.name, cleaned_text).label('score')
            )
            .where(func.similarity(ProductIndex.name, cleaned_text) >= threshold)
            .order_by(func.similarity(ProductIndex.name, cleaned_text).desc())
            .limit(1)
        )
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        return row[0] if row else None

    async def _assign_category(
        self,
        product_index: Optional[ProductIndex],
        cleaned_text: str,
        category_suggestion: Optional[str] = None,
        shop_name: Optional[str] = None
    ) -> Category:
        """
        Przypisuje kategorię do produktu.
        
        Priorytety (zgodnie z planem, sekcja 4.2):
        1. Jeśli product_index ma category_id → użyj tej kategorii
        2. Jeśli product_index jest None → użyj AI Categorization (Gemini API)
        3. W przeciwnym razie → użyj "Inne"
        
        Args:
            product_index: ProductIndex znaleziony przez normalizację (lub None)
            cleaned_text: Wyczyszczony tekst produktu (dla AI Categorization)
            category_suggestion: Sugestia kategorii z OCR/LLM (opcjonalne)
            shop_name: Nazwa sklepu dla kontekstu AI (opcjonalne)
            
        Returns:
            Category: Przypisana kategoria produktu
            
        Most Koncepcyjny (PHP -> Python):
        - W Symfony/Laravel mielibyście podobną logikę w Service Layer (np. OrderService::assignCategory).
        - W Pythonie używamy async/await dla operacji I/O (DB, API), co jest idiomatyczne dla FastAPI.
        """
        # Priorytet 1: Kategoria z ProductIndex
        if product_index and product_index.category_id:
            try:
                category = await self.category_service.get_by_id(product_index.category_id)
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
                # Fallback do AI Categorization jeśli kategoria nie istnieje
        
        # Priorytet 2: AI Categorization (gdy produkt nieznany)
        if not product_index:
            available_categories = await self.category_service.get_all_categories()
            ai_category_id = await self._ai_categorize_product(
                cleaned_text=cleaned_text,
                category_suggestion=category_suggestion,
                shop_name=shop_name,
                available_categories=available_categories
            )
            
            if ai_category_id:
                # Walidacja: sprawdź czy kategoria rzeczywiście istnieje w DB
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
        reraise=True
    )
    async def _ai_categorize_product(
        self,
        cleaned_text: str,
        category_suggestion: Optional[str] = None,
        shop_name: Optional[str] = None,
        available_categories: Optional[list[Category]] = None
    ) -> Optional[int]:
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

        # Przygotowanie promptu
        categories_list = "\n".join([f"- {cat.name}" for cat in available_categories])

        prompt = f"""Jesteś ekspertem w kategoryzacji produktów ze sklepów.

Produkt: {cleaned_text}
Sugerowana kategoria (z OCR): {category_suggestion or "brak"}
Sklep: {shop_name or "nieznany"}

Dostępne kategorie:
{categories_list}

Zadanie:
1. Wybierz NAJLEPSZĄ kategorię z listy dostępnych kategorii dla tego produktu.
2. Jeśli żadna kategoria nie pasuje idealnie, zwróć null (nie wymyślaj nowych kategorii).
3. Oceń swoją pewność (confidence) w przedziale 0.0-1.0.

Zwróć odpowiedź w formacie JSON:
{{
    "category_name": "Nazwa kategorii z listy lub null",
    "confidence": 0.95,
    "reasoning": "Krótkie uzasadnienie wyboru"
}}"""

        try:
            
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=settings.AI_CATEGORIZATION_TEMPERATURE,
                )
            )

            if not response.text:
                logger.warning("Gemini zwróciło pustą odpowiedź dla kategoryzacji")
                return None

            # Parsowanie JSON response
            parsed_data = json.loads(response.text)
            category_name = parsed_data.get("category_name")
            confidence = parsed_data.get("confidence", 0.0)
            reasoning = parsed_data.get("reasoning", "")

            # Walidacja confidence threshold
            if confidence < settings.AI_CATEGORIZATION_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"AI confidence za niska ({confidence}) dla produktu: {cleaned_text}"
                )
                return None

            # Walidacja: czy kategoria nie jest null
            if not category_name:
                logger.info(f"AI nie zaproponowało kategorii dla: {cleaned_text}")
                return None

            # Znajdź kategorię w dostępnych kategoriach (case-insensitive)
            for cat in available_categories:
                if cat.name.lower() == category_name.lower():
                    logger.info(
                        f"AI zaproponowało kategorię: {category_name} "
                        f"(confidence: {confidence}, reasoning: {reasoning})"
                    )
                    return cat.id

            # Kategoria nie znaleziona w liście (AI zaproponowało coś spoza listy)
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
            return None  # Fallback do kategorii "Inne"

    async def normalize_item(
        self,
        ocr_item: OCRItem,
        shop_id: Optional[int] = None,
        shop_name: Optional[str] = None,
        user_id: Optional[int] = None,
        save_alias: bool = True
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
                is_confident=False
            )

        # Step 1: Wyszukiwanie w aliasach (priorytet: User+Shop -> Shop -> Global)
        product_index = await self._find_by_alias(cleaned_text, shop_id, user_id)
        
        # Step 2: Fuzzy Search (jeśli alias nie znaleziony)
        if not product_index:
            product_index = await self._fuzzy_search_product(
                cleaned_text,
                ocr_item.category_suggestion  # Opcjonalne filtrowanie
            )
            
            # Zapis aliasu po znalezieniu przez fuzzy search (uczenie się systemu)
            if product_index and save_alias:
                try:
                    await self.alias_service.upsert_alias(
                        raw_name=cleaned_text,
                        index_id=product_index.id,
                        shop_id=shop_id,
                        user_id=user_id
                    )
                except Exception as e:
                    # Log error, ale nie przerywaj procesu
                    # (alias nie jest krytyczny dla normalizacji)
                    logger.error(f"Błąd zapisu aliasu: {str(e)}")

        # Kategoryzacja (osobny proces) - zgodnie z planem sekcja 4
        # KRYTYCZNE: Ta operacja jest POZA transakcją DB (wywołania API mogą trwać sekundy)
        category = await self._assign_category(
            product_index=product_index,
            cleaned_text=cleaned_text,
            category_suggestion=ocr_item.category_suggestion,
            shop_name=shop_name
        )

        # Oblicz confidence score na podstawie wyniku normalizacji
        fallback_category = await self.category_service.get_fallback_category()
        is_fallback = category.id == fallback_category.id
        
        if product_index:
            # Produkt znaleziony w słowniku (alias lub fuzzy search)
            confidence_score = 1.0
            is_confident = True
        else:
            # Produkt nieznany - użyto AI Categorization lub fallback
            if is_fallback:
                confidence_score = ocr_item.confidence_score * 0.5  # Unknown product penalty
                is_confident = False
            else:
                confidence_score = ocr_item.confidence_score * 0.7  # AI match penalty
                is_confident = True

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
            is_confident=is_confident
        )

