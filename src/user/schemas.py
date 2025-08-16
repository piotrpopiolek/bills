from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel

class UserBase(SQLModel):
    external_id: str
    is_active: bool = True

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    created_at: datetime

class UserUpdate(SQLModel):
    external_id: Optional[str] = None
    is_active: Optional[bool] = None