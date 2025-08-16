from typing import Optional
from sqlmodel import SQLModel

class ShopBase(SQLModel):
    name: str
    address: Optional[str] = None

class ShopCreate(ShopBase):
    pass

class ShopRead(ShopBase):
    id: int

class ShopUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None