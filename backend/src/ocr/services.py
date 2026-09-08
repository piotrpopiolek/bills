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

from src.ai.ollama_client import OllamaClient
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


def _should_retry_ollama_error(exception: Exception) -> bool:
    import httpx
    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        logger.warning(f"Ollama error (will retry): {str(exception)}")
        return True
    if isinstance(exception, httpx.HTTPStatusError) and exception.response.status_code >= 500:
        return True
    return False


RECEIPT_OCR_PROMPT = """You are an expert OCR system specialized in reading Polish retail receipts (paragony fiskalne).

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
- Return ONLY valid JSON matching the requested schema
"""


class OCRService:
    """
    Service for extracting structured data from receipt images.
    Supports Gemini (cloud) and Ollama (local vision models).
    """

    ALLOWED_MAGIC_BYTES = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89\x50\x4e\x47': 'image/png',
        b'\x52\x49\x46\x46': 'image/webp',
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(
        self,
        model: Optional[genai.GenerativeModel] = None,
        ollama_client: Optional[OllamaClient] = None,
        provider: Optional[str] = None,
    ):
        self.provider = (provider or settings.OCR_PROVIDER).lower()
        self.model = model
        self.ollama_client = ollama_client or OllamaClient(
            timeout=float(settings.OLLAMA_TIMEOUT)
        )

        if self.provider == "gemini" and self.model is None:
            if not settings.GEMINI_API_KEY:
                raise AIServiceError("GEMINI_API_KEY is required when OCR_PROVIDER=gemini")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def extract_data(self, file: UploadFile) -> OCRReceiptData:
        logger.info(
            "OCR extraction started",
            extra={"file_name": file.filename, "provider": self.provider},
        )

        mime_type = await self._validate_file(file)
        image_part = await self._prepare_image_part(file, mime_type)

        try:
            if self.provider == "ollama":
                llm_response = await self._call_ollama_with_retry(image_part)
            else:
                prompt_parts = self._build_prompt_parts(image_part)
                llm_response = await self._call_gemini_with_retry(prompt_parts)
        except AIServiceError:
            raise
        except Exception as e:
            logger.error("OCR LLM error", exc_info=True, extra={"error": str(e)})
            raise AIServiceError(f"Błąd komunikacji z OCR LLM ({self.provider}): {str(e)}") from e

        try:
            result = self._parse_response(llm_response)
            logger.info("OCR response parsed successfully", extra={"response": result})
        except Exception as e:
            logger.error("Failed to parse OCR response", exc_info=True, extra={"error": str(e)})
            raise ExtractionError(f"Nie udało się przetworzyć odpowiedzi OCR: {str(e)}") from e

        logger.info(
            "OCR extraction completed",
            extra={
                "items_count": len(result.items),
                "shop_name": result.shop_name,
                "provider": self.provider,
            }
        )
        return result

    async def _validate_file(self, file: UploadFile) -> str:
        file_bytes = await file.read()
        await file.seek(0)

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

        if len(file_bytes) > self.MAX_FILE_SIZE:
            raise FileValidationError(f"File too large. Max size: {self.MAX_FILE_SIZE / (1024 * 1024)}MB")

        return mime_type

    async def _prepare_image_part(self, file: UploadFile, mime_type: str) -> Dict[str, Any]:
        file_bytes = await file.read()
        await file.seek(0)
        return {
            "mime_type": mime_type,
            "data": file_bytes
        }

    def _build_prompt_parts(self, image_part: Dict[str, Any]) -> List[Any]:
        return [RECEIPT_OCR_PROMPT, image_part]

    def _llm_json_schema(self) -> Dict[str, Any]:
        schema = LLMReceiptExtraction.model_json_schema()
        self._sanitize_schema(schema)
        return schema

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_should_retry_gemini_error),
        reraise=True
    )
    async def _call_gemini_with_retry(self, parts: List[Any]) -> LLMReceiptExtraction:
        try:
            schema = self._llm_json_schema()
            response = await self.model.generate_content_async(
                parts,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )

            if not response.text:
                raise AIServiceError("Gemini zwróciło pustą odpowiedź")

            parsed_data = json.loads(response.text)
            return LLMReceiptExtraction.model_validate(parsed_data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {str(e)}", exc_info=True)
            raise AIServiceError(f"Nieprawidłowa odpowiedź JSON z Gemini API: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception(_should_retry_ollama_error),
        reraise=True
    )
    async def _call_ollama_with_retry(self, image_part: Dict[str, Any]) -> LLMReceiptExtraction:
        schema = self._llm_json_schema()
        prompt = (
            f"{RECEIPT_OCR_PROMPT}\n\n"
            "Respond with a single JSON object matching this schema:\n"
            f"{json.dumps(schema)}"
        )
        # Prefer simple "json" for vision models — full JSON Schema often crashes older Ollama builds
        try:
            parsed_data = await self.ollama_client.chat_json(
                model=settings.OLLAMA_VISION_MODEL,
                prompt=prompt,
                images=[image_part["data"]],
                format_schema="json",
                temperature=0.1,
            )
            return LLMReceiptExtraction.model_validate(parsed_data)
        except json.JSONDecodeError as e:
            raise AIServiceError(f"Nieprawidłowa odpowiedź JSON z Ollama: {str(e)}") from e
        except Exception as e:
            if _should_retry_ollama_error(e):
                raise
            raise AIServiceError(f"Błąd Ollama OCR: {str(e)}") from e

    def _sanitize_schema(self, schema: Dict[str, Any]) -> None:
        if isinstance(schema, dict):
            defs = schema.pop('$defs', {})
            if defs:
               self._resolve_refs(schema, defs)

            for key in ['default', 'title', 'additionalProperties', 'anyOf']:
                if key in schema:
                    del schema[key]
            
            for value in schema.values():
                self._sanitize_schema(value)
        elif isinstance(schema, list):
            for item in schema:
                self._sanitize_schema(item)

    def _resolve_refs(self, schema: Any, defs: Dict[str, Any]) -> None:
        if isinstance(schema, dict):
            if '$ref' in schema:
                ref_name = schema.pop('$ref').split('/')[-1]
                if ref_name in defs:
                    schema.update(defs[ref_name])
                    self._resolve_refs(schema, defs)
            
            for key, value in schema.items():
                self._resolve_refs(value, defs)
        elif isinstance(schema, list):
            for item in schema:
                self._resolve_refs(item, defs)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str or not date_str.strip():
            return None
        
        date_str = date_str.strip()
        
        try:
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass
        
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
                    else:
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
                    else:
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
