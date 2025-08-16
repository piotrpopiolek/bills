from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel
from decimal import Decimal
from typing import List
from src.user.schemas import UserRead
from src.shop.schemas import ShopRead
from src.billitem.schemas import BillItemReadWithDetails

class BillBase(SQLModel):
    bill_date: datetime
    total_amount: Optional[Decimal] = None
    image_url: Optional[str] = None
    shop_id: Optional[int] = None

class BillCreate(BillBase):
    # Przy tworzeniu rachunku od razu przypisujemy go do użytkownika
    user_id: int

class BillRead(BillBase):
    id: int
    status: str # Zaciągnięte z enuma ProcessingStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_id: int

class BillUpdate(SQLModel):
    bill_date: Optional[datetime] = None
    total_amount: Optional[Decimal] = None
    image_url: Optional[str] = None
    shop_id: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None

# Główny, zagnieżdżony schemat do odczytu całego rachunku
class BillReadWithDetails(BillRead):
    user: UserRead
    shop: Optional[ShopRead] = None
    items: List[BillItemReadWithDetails] = []

# Dodatkowe schematy do zagnieżdżania w innych modelach (aby uniknąć cyklicznych zależności)
class UserReadWithBills(UserRead):
    bills: List[BillRead] = []

class ShopReadWithBills(ShopRead):
    bills: List[BillRead] = []