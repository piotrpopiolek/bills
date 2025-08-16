from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from src.category.schemas import CategoryRead

class IndexBase(SQLModel):
    name: str
    synonyms: Optional[Dict[str, Any]] = None
    category_id: Optional[int] = None

class IndexCreate(IndexBase):
    pass

class IndexRead(IndexBase):
    id: int
    created_at: datetime
    updated_at: datetime

class IndexUpdate(SQLModel):
    name: Optional[str] = None
    synonyms: Optional[Dict[str, Any]] = None
    category_id: Optional[int] = None

# Zagnieżdżony schemat odczytu z dołączoną kategorią
class IndexReadWithCategory(IndexRead):
    category: Optional[CategoryRead] = None