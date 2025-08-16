from typing import Optional
from decimal import Decimal
from datetime import datetime
from sqlmodel import SQLModel
from src.index.schemas import IndexReadWithCategory

class BillItemBase(SQLModel):
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    original_text: Optional[str] = None
    confidence_score: Optional[float] = None
    index_id: Optional[int] = None

class BillItemCreate(BillItemBase):
    pass

class BillItemRead(BillItemBase):
    id: int
    created_at: datetime

# Zagnieżdżony schemat odczytu z dołączonym indeksem i jego kategorią
class BillItemReadWithDetails(BillItemRead):
    index: Optional[IndexReadWithCategory] = None