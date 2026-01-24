import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import Field, ConfigDict, model_validator

from src.common.schemas import AppBaseModel

logger = logging.getLogger(__name__)


class OCRItem(AppBaseModel):
    """Pojedyncza pozycja z paragonu (Intermediate Representation)"""
    name: str = Field(..., max_length=500, description="Nazwa produktu z paragonu")
    quantity: Decimal = Field(default=Decimal("1.0"), description="Ilość")
    unit_price: Optional[Decimal] = Field(None, description="Cena jednostkowa")
    total_price: Decimal = Field(..., description="Cena całkowita pozycji")
    category_suggestion: Optional[str] = Field(None, max_length=100, description="Sugerowana kategoria produktu (z LLM)")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Ocena pewności odczytu (0.0-1.0)")


class OCRReceiptData(AppBaseModel):
    """Dane paragonu wyekstrahowane przez LLM"""
    shop_name: Optional[str] = Field(None, max_length=200, description="Nazwa sklepu")
    shop_address: Optional[str] = Field(None, max_length=500, description="Adres sklepu")
    date: Optional[datetime] = Field(None, description="Data i czas zakupu")
    total_amount: Decimal = Field(..., description="Łączna kwota paragonu")
    items: List[OCRItem] = Field(default_factory=list, description="Lista pozycji")
    currency: str = Field(default="PLN", max_length=3, description="Waluta")
    requires_verification: bool = Field(default=False, description="Flaga wymaga weryfikacji")

    @model_validator(mode='after')
    def validate_total_amount(self) -> 'OCRReceiptData':
        """
        Dwupoziomowa walidacja sumy pozycji vs total_amount.
        
        Tolerancje:
        - > 5% różnicy: ustawia flagę requires_verification (TO_VERIFY status)
        - > 20% różnicy: rzuca błąd (prawdopodobnie poważny błąd OCR - ERROR status)
        
        Przyczyny rozbieżności < 20%:
        - Opakowania zwrotne / depozyty
        - Rabaty nie przypisane do pozycji  
        - Nieczytelna cena jednostkowa lub ilość pojedynczych pozycji
        - Błędy zaokrągleń
        
        Returns:
            OCRReceiptData with requires_verification flag set if needed
            
        Raises:
            ValueError: If difference > 20% (critical OCR error)
        """
        if not self.items:
            return self

        items_sum = sum(item.total_price for item in self.items)
        difference = abs(items_sum - self.total_amount)
        
        # Avoid division by zero
        if self.total_amount == 0:
            if difference > 0:
                raise ValueError("Total amount is 0, but items sum is not zero")
            return self
        
        # Calculate percentage difference
        percentage_diff = (difference / self.total_amount) * Decimal("100")

        # Level 1: Critical error (> 20%) - reject completely
        if percentage_diff > Decimal("20.0"):
            raise ValueError(
                f"Krytyczna rozbieżność w sumie! "
                f"Suma pozycji: {items_sum} PLN, "
                f"Total amount: {self.total_amount} PLN, "
                f"Różnica: {difference} PLN ({percentage_diff:.1f}%). "
                f"Prawdopodobnie poważny błąd OCR - paragon zostanie odrzucony."
            )
        
        # Level 2: Minor mismatch (5-20%) - flag for verification
        if percentage_diff > Decimal("5.0"):
            object.__setattr__(self, 'requires_verification', True)
            logger.warning(
                f"Total amount mismatch detected (requires verification). "
                f"Items sum: {items_sum} PLN, "
                f"Total amount: {self.total_amount} PLN, "
                f"Difference: {difference} PLN ({percentage_diff:.1f}%)"
            )

        return self


class OCRExtractResponse(AppBaseModel):
    """Odpowiedź endpointu OCR"""
    success: bool = Field(default=True, description="Status operacji")
    message: str = Field(default="Ekstrakcja zakończona pomyślnie", description="Komunikat dla użytkownika")
    data: OCRReceiptData = Field(..., description="Wyekstrahowane dane")
    raw_text: Optional[str] = Field(None, description="Surowy tekst z OCR (opcjonalnie, do debugowania)")
    execution_time: float = Field(..., description="Czas przetwarzania w sekundach")


# Strict Mode Schema dla LLM
class LLMReceiptItem(AppBaseModel):
    """Strict schema dla pojedynczej pozycji - używane w komunikacji z LLM"""
    model_config = ConfigDict(
        strict=True,  # Wymuszenie typów
        extra='forbid'  # Odrzucenie nieznanych pól
    )

    name: str
    quantity: float
    unit_price: Optional[float] = None
    total_price: float
    category_suggestion: Optional[str] = None
    confidence_score: float = 1.0


class LLMReceiptExtraction(AppBaseModel):
    """Strict schema dla całego paragonu - używane w komunikacji z LLM"""
    model_config = ConfigDict(
        strict=True,
        extra='forbid'
    )

    shop_name: Optional[str] = None
    shop_address: Optional[str] = None
    date: Optional[str] = None  # Date in ISO 8601 (preferred) or formats like DD/MM/YYYY HH:MM, DD.MM.YYYY HH:MM
    total_amount: float
    items: List[LLMReceiptItem]
    currency: str = "PLN"

