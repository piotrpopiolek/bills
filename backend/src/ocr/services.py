import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import UploadFile
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from src.config import settings
from src.ocr.exceptions import (
    FileValidationError,
    ExtractionError,
    AIServiceError,
)
from src.ocr.schemas import (
    OCRReceiptData,
    OCRItem,
    LLMReceiptExtraction,
)

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


class OCRService:
    """
    Service for extracting structured data from receipt images using Gemini 1.5 Flash.
    """

    # Magic bytes dla obsługiwanych formatów obrazów
    ALLOWED_MAGIC_BYTES = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89\x50\x4e\x47': 'image/png',
        b'\x52\x49\x46\x46': 'image/webp',
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, model: genai.GenerativeModel):
        self.model = model

    async def extract_data(self, file: UploadFile) -> OCRReceiptData:
        """
        Główna metoda ekstrakcji danych z paragonu.
        
        Args:
            file: UploadFile z obrazem paragonu
            
        Returns:
            OCRReceiptData z wyekstrahowanymi danymi
            
        Raises:
            FileValidationError: Jeśli plik jest nieprawidłowy
            ExtractionError: Jeśli ekstrakcja się nie powiodła
            AIServiceError: Jeśli wystąpił błąd komunikacji z AI
        """
        logger.info("OCR extraction started", extra={"file_name": file.filename})

        # 1. Walidacja pliku
        mime_type = await self._validate_file(file)

        # 2. Przygotowanie obrazu (bytes)
        image_part = await self._prepare_image_part(file, mime_type)

        # Gemini przyjmuje listę [text_prompt, image_part]
        prompt_parts = self._build_prompt_parts(image_part)

        # 4. Wywołanie Gemini z retry
        try:
            llm_response = await self._call_gemini_with_retry(prompt_parts)
        except Exception as e:
            logger.error("Gemini API error", exc_info=True, extra={"error": str(e)})
            raise AIServiceError(f"Błąd komunikacji z Gemini API: {str(e)}") from e

        # 5. Parsowanie i walidacja odpowiedzi
        try:
            result = self._parse_response(llm_response)
            logger.info("Gemini response parsed successfully", extra={"response": result})
        except Exception as e:
            logger.error("Failed to parse Gemini response", exc_info=True, extra={"error": str(e)})
            raise ExtractionError(f"Nie udało się przetworzyć odpowiedzi z Gemini: {str(e)}") from e

        logger.info(
            "OCR extraction completed",
            extra={
                "items_count": len(result.items),
                "shop_name": result.shop_name,
            }
        )

        return result

    async def _validate_file(self, file: UploadFile) -> str:
        """
        Waliduje plik: magic bytes, rozmiar, MIME type.
        
        Returns:
            Wykryty typ MIME
            
        Raises:
            FileValidationError: Jeśli walidacja się nie powiedzie
        """
        # Sprawdzenie magic bytes
        file_bytes = await file.read()
        await file.seek(0)  # Reset dla dalszego przetwarzania

        if len(file_bytes) < 4:
            raise FileValidationError("Plik jest zbyt mały lub uszkodzony")

        magic_bytes = file_bytes[:4]
        mime_type = None
        for magic, mime in self.ALLOWED_MAGIC_BYTES.items():
            if magic_bytes.startswith(magic):
                mime_type = mime
                break

        if not mime_type:
            raise FileValidationError("Invalid file format. Allowed: JPEG, PNG, WEBP")

        # Sprawdzenie rozmiaru
        if len(file_bytes) > self.MAX_FILE_SIZE:
            raise FileValidationError(f"File too large. Max size: {self.MAX_FILE_SIZE / (1024 * 1024)}MB")

        return mime_type

    async def _prepare_image_part(self, file: UploadFile, mime_type: str) -> Dict[str, Any]:
        """
        Przygotowuje część obrazu dla Gemini.
        
        Args:
            file: UploadFile z obrazem
            mime_type: Typ MIME obrazu
            
        Returns:
            Słownik z danymi obrazu zgodny z API Gemini
        """
        file_bytes = await file.read()
        await file.seek(0)
        
        return {
            "mime_type": mime_type,
            "data": file_bytes
        }

    def _build_prompt_parts(self, image_part: Dict[str, Any]) -> List[Any]:
        """
        Konstruuje części promptu dla Gemini.
        """
        system_prompt = """You are an expert OCR system specialized in reading Polish retail receipts (paragony fiskalne).

Your task is to extract the following information:
1. Shop name and address in strict order: "Shop name, ul. Example Street 123, 00-000 Example City"
2. Purchase date and time: Extract the date and time exactly as shown on the receipt. 
   - Preferred format: ISO 8601 (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD HH:MM
   - Alternative formats accepted: DD/MM/YYYY HH:MM, DD.MM.YYYY HH:MM
   - If only date is available, use YYYY-MM-DD format
   - If date/time is not found or unclear, set to null
3. List of all purchased items with:
   - Product name (exactly as written on receipt)
   - Quantity (default 1.0 if not specified)
   - Unit price (if available)
   - Total price for the item
   - Suggested product category in Polish (e.g., "Nabiał", "Pieczywo", "Owoce", "Mięso", "Napoje")
   - Confidence score (0.0-1.0) based on text clarity
4. Total amount to pay
5. Currency (default PLN)

Rules:
- Extract data exactly as shown on the receipt
- If information is unclear, set confidence_score < 0.8
- If date/time is not found, set to null
- Category suggestions should be common Polish grocery categories
- Quantity and prices must be positive numbers
- Total amount must match or be close to sum of item prices
"""
        return [system_prompt, image_part]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_should_retry_gemini_error),
        reraise=True
    )
    async def _call_gemini_with_retry(self,parts: List[Any]) -> LLMReceiptExtraction:
        """
        Wywołuje Gemini API z automatycznym retry.
        """
        try:
            # FIX: Gemini API nie obsługuje pola "default" w schemacie JSON Schema,
            # które Pydantic generuje domyślnie. Musimy ręcznie wyczyścić schemat.
            schema = LLMReceiptExtraction.model_json_schema()
            self._sanitize_schema(schema)

            # Użycie response_schema w generation_config dla Structured Output
            response = await self.model.generate_content_async(
                parts,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema # Przekazujemy słownik, nie klasę
                )
            )

            if not response.text:
                raise AIServiceError("Gemini zwróciło pustą odpowiedź")

            # Parsowanie JSON response do Pydantic model
            # Gemini zwraca tekst JSON zgodny ze schematem
            parsed_data = json.loads(response.text)
            return LLMReceiptExtraction.model_validate(parsed_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {str(e)}", exc_info=True)
            raise AIServiceError(f"Nieprawidłowa odpowiedź JSON z Gemini API: {str(e)}") from e
        except Exception as e:
            # Tenacity obsłuży wyjątki z _should_retry_gemini_error, inne polecą wyżej
            raise

    def _sanitize_schema(self, schema: Dict[str, Any]) -> None:
        """
        Usuwa klucze 'default', 'title' i '$defs' ze schematu JSON Schema, 
        ponieważ API Gemini (Protobuf) ich nie obsługuje.
        Rozwija referencje ($ref) przez inlining definicji.
        Działa rekurencyjnie (mutuje słownik).
        """
        if isinstance(schema, dict):
            # Najpierw rozwiąż definicje ($defs), jeśli istnieją na najwyższym poziomie
            defs = schema.pop('$defs', {})
            if defs:
               self._resolve_refs(schema, defs)

            # Usuń nieobsługiwane klucze
            for key in ['default', 'title', 'additionalProperties', 'anyOf']:
                if key in schema:
                    del schema[key]
            
            # Rekurencja dla zagnieżdżonych struktur
            for value in schema.values():
                self._sanitize_schema(value)
        elif isinstance(schema, list):
            for item in schema:
                self._sanitize_schema(item)

    def _resolve_refs(self, schema: Any, defs: Dict[str, Any]) -> None:
        """
        Rekurencyjnie zamienia $ref na definicje z $defs (inlining).
        Gemini nie obsługuje $ref/$defs w JSON Schema.
        """
        if isinstance(schema, dict):
            if '$ref' in schema:
                ref_name = schema.pop('$ref').split('/')[-1]
                if ref_name in defs:
                    # Skopiuj definicję w miejsce referencji
                    schema.update(defs[ref_name])
                    # Kontynuuj rekurencyjne rozwiązywanie wewnątrz wklejonej definicji
                    self._resolve_refs(schema, defs)
            
            for key, value in schema.items():
                self._resolve_refs(value, defs)
        elif isinstance(schema, list):
            for item in schema:
                self._resolve_refs(item, defs)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parsuje datę z różnych formatów używanych przez LLM.
        
        Obsługiwane formaty:
        - ISO 8601: 2026-01-09T19:19:00, 2026-01-09T19:19:00Z, 2026-01-09T19:19:00+00:00
        - DD/MM/YYYY HH:MM: 09/01/2026 19:19
        - DD.MM.YYYY HH:MM: 09.01.2026 19:19
        - DD-MM-YYYY HH:MM: 09-01-2026 19:19
        - YYYY-MM-DD HH:MM: 2026-01-09 19:19
        
        Returns:
            datetime object lub None jeśli parsowanie się nie powiodło
        """
        if not date_str or not date_str.strip():
            return None
        
        date_str = date_str.strip()
        
        # Próba 1: ISO 8601 format (najczęstszy)
        try:
            # Obsługa 'Z' na końcu (UTC)
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass
        
        # Próba 2: DD/MM/YYYY HH:MM lub DD.MM.YYYY HH:MM lub DD-MM-YYYY HH:MM
        # Wzorzec: DD/MM/YYYY HH:MM lub DD.MM.YYYY HH:MM lub DD-MM-YYYY HH:MM
        patterns = [
            (r'(\d{2})[/.-](\d{2})[/.-](\d{4})\s+(\d{1,2}):(\d{2})', 'DD/MM/YYYY HH:MM'),
            (r'(\d{4})[/.-](\d{2})[/.-](\d{2})\s+(\d{1,2}):(\d{2})', 'YYYY-MM-DD HH:MM'),
        ]
        
        for pattern, format_name in patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    if format_name == 'DD/MM/YYYY HH:MM':
                        day, month, year, hour, minute = match.groups()
                    else:  # YYYY-MM-DD HH:MM
                        year, month, day, hour, minute = match.groups()
                    
                    return datetime(
                        year=int(year),
                        month=int(month),
                        day=int(day),
                        hour=int(hour),
                        minute=int(minute),
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse date with pattern {pattern}: {e}")
                    continue
        
        # Próba 3: Tylko data bez czasu (różne formaty)
        date_only_patterns = [
            (r'(\d{2})[/.-](\d{2})[/.-](\d{4})', 'DD/MM/YYYY'),
            (r'(\d{4})[/.-](\d{2})[/.-](\d{2})', 'YYYY-MM-DD'),
        ]
        
        for pattern, format_name in date_only_patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    if format_name == 'DD/MM/YYYY':
                        day, month, year = match.groups()
                    else:  # YYYY-MM-DD
                        year, month, day = match.groups()
                    
                    return datetime(
                        year=int(year),
                        month=int(month),
                        day=int(day),
                        hour=0,
                        minute=0,
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse date-only with pattern {pattern}: {e}")
                    continue
        
        logger.warning(f"Failed to parse date in any known format: {date_str}")
        return None

    def _parse_response(self, llm_response: LLMReceiptExtraction) -> OCRReceiptData:
        """
        Konwertuje LLMReceiptExtraction na OCRReceiptData.
        """
        # Konwersja float → Decimal dla wszystkich cen
        items = [
            OCRItem(
                name=item.name,
                quantity=Decimal(str(item.quantity)),
                unit_price=Decimal(str(item.unit_price)) if item.unit_price else None,
                total_price=Decimal(str(item.total_price)),
                category_suggestion=item.category_suggestion,
                confidence_score=item.confidence_score
            )
            for item in llm_response.items
        ]

        # Parsowanie daty z różnych formatów
        date = None
        if llm_response.date:
            date = self._parse_date(llm_response.date)
            if date is None:
                logger.warning(f"Failed to parse date from LLM response: {llm_response.date}")

        return OCRReceiptData(
            shop_name=llm_response.shop_name,
            shop_address=llm_response.shop_address,
            date=date,
            total_amount=Decimal(str(llm_response.total_amount)),
            items=items,
            currency=llm_response.currency
        )
