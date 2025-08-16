from typing import List, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import Bill, BillItem, ProcessingStatus
from src.bill.schemas import BillCreate, BillUpdate
from src.billitem.schemas import BillItemCreate


async def get_bill(session: AsyncSession, bill_id: int) -> Optional[Bill]:
    """Pobiera jeden rachunek po jego ID."""
    return await session.get(Bill, bill_id)

async def get_bills_by_user(session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Bill]:
    """Pobiera listę rachunków dla danego użytkownika."""
    statement = select(Bill).where(Bill.user_id == user_id).offset(skip).limit(limit)
    result = await session.execute(statement)
    return result.all()

async def create_bill(session: AsyncSession, bill_in: BillCreate) -> Bill:
    """Tworzy nowy wpis dla rachunku (bez pozycji)."""
    db_bill = Bill.model_validate(bill_in)
    db_bill.status = ProcessingStatus.PENDING
    session.add(db_bill)
    await session.commit()
    await session.refresh(db_bill)
    return db_bill

async def update_bill(session: AsyncSession, db_bill: Bill, bill_in: BillUpdate) -> Bill:
    """Aktualizuje dane rachunku."""
    bill_data = bill_in.model_dump(exclude_unset=True)
    for key, value in bill_data.items():
        setattr(db_bill, key, value)
    session.add(db_bill)
    await session.commit()
    await session.refresh(db_bill)
    return db_bill

async def add_items_to_bill(session: AsyncSession, db_bill: Bill, items_in: List[BillItemCreate]) -> Bill:
    """Dodaje listę pozycji do istniejącego rachunku."""
    for item_in in items_in:
        # Tworzy obiekt BillItem i od razu przypisuje mu bill_id
        db_item = BillItem.model_validate(item_in, update={"bill_id": db_bill.id})
        session.add(db_item)
    
    await session.commit()
    # Odświeżenie obiektu rachunku spowoduje załadowanie nowo dodanych pozycji
    await session.refresh(db_bill)
    return db_bill