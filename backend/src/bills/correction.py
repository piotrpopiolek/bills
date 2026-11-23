"""User edits on a receipt. A renamed product writes an alias; price and shop do not."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.ai.usage import ModelUsage
from src.bill_items.models import BillItem, VerificationSource
from src.bill_items.schemas import BillItemCreate, BillItemResponse, BillItemUpdate
from src.bill_items.services import BillItemService
from src.bills.models import Bill
from src.common.exceptions import BillAccessDeniedError, ResourceNotFoundError
from src.product_index_aliases.services import ProductIndexAliasService
from src.product_indexes.schemas import ProductIndexCreate
from src.product_indexes.services import ProductIndexService


def names_differ(left: str | None, right: str | None) -> bool:
    return (left or "").strip().casefold() != (right or "").strip().casefold()


def alias_for_rename(
    original_text: str | None, previous_name: str, new_name: str
) -> str | None:
    """The receipt wording that should point at the name the user chose."""
    if not names_differ(previous_name, new_name):
        return None
    raw = (original_text or previous_name).strip()
    if not raw or not names_differ(raw, new_name):
        return None
    return raw


def displayed_name(item: BillItem) -> str:
    if item.index is not None and item.index.name:
        return item.index.name
    return item.original_text or ""


class ReceiptCorrection:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.items = BillItemService(session)
        self.indexes = ProductIndexService(session, usage=ModelUsage(session))
        self.aliases = ProductIndexAliasService(session)

    async def save_item(
        self,
        *,
        bill_id: int,
        item_id: int,
        user_id: int,
        name: str | None,
        quantity: Decimal | None,
        unit_price: Decimal | None,
        total_price: Decimal | None,
    ) -> BillItemResponse:
        item = await self._owned_item(bill_id, item_id, user_id)
        update = BillItemUpdate(
            is_verified=True,
            verification_source=VerificationSource.USER,
        )
        if quantity is not None:
            update = update.model_copy(update={"quantity": quantity})
        if unit_price is not None:
            update = update.model_copy(update={"unit_price": unit_price})
        if total_price is not None:
            update = update.model_copy(update={"total_price": total_price})
        try:
            if name is not None and names_differ(displayed_name(item), name):
                index_id = await self._index_for_name(item, user_id, name.strip())
                update = update.model_copy(update={"index_id": index_id})
            saved = await self.items.update(item_id, update, user_id, commit=False)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return saved

    async def add_item(
        self,
        *,
        bill_id: int,
        user_id: int,
        name: str,
        quantity: Decimal,
        unit_price: Decimal,
        total_price: Decimal,
    ) -> BillItemResponse:
        await self._owned_bill(bill_id, user_id)
        cleaned = name.strip()
        try:
            product = await self.indexes.create_or_get_existing(
                ProductIndexCreate(name=cleaned, category_id=None),
                commit=False,
            )
            created = await self.items.create(
                BillItemCreate(
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    is_verified=True,
                    verification_source=VerificationSource.USER,
                    bill_id=bill_id,
                    index_id=product.id,
                    original_text=cleaned,
                ),
                commit=False,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return created

    async def delete_item(self, *, bill_id: int, item_id: int, user_id: int) -> None:
        item = await self._owned_item(bill_id, item_id, user_id)
        await self.session.delete(item)
        await self.session.commit()

    async def _index_for_name(self, item: BillItem, user_id: int, name: str) -> int:
        product = await self.indexes.create_or_get_existing(
            ProductIndexCreate(name=name, category_id=item.category_id),
            commit=False,
        )
        raw = alias_for_rename(item.original_text, displayed_name(item), name)
        if raw is not None:
            bill = await self._owned_bill(item.bill_id, user_id)
            await self.aliases.upsert_alias(
                raw_name=raw,
                index_id=product.id,
                shop_id=bill.shop_id,
                user_id=user_id,
                commit=False,
            )
        return product.id

    async def _owned_bill(self, bill_id: int, user_id: int) -> Bill:
        bill = await self.session.get(Bill, bill_id)
        if bill is None:
            raise ResourceNotFoundError("Bill", bill_id)
        if bill.user_id != user_id:
            raise BillAccessDeniedError(bill_id)
        return bill

    async def _owned_item(self, bill_id: int, item_id: int, user_id: int) -> BillItem:
        await self._owned_bill(bill_id, user_id)
        item = await self.session.scalar(
            select(BillItem)
            .options(joinedload(BillItem.index))
            .where(BillItem.id == item_id)
        )
        if item is None or item.bill_id != bill_id:
            raise ResourceNotFoundError("BillItem", item_id)
        return item
