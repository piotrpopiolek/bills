"""Postgres helpers for integration and e2e. Unit tests do not import this."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.schemas import NormalizedItem
from src.auth.models import MagicLink
from src.auth.services import AuthService
from src.bill_items.models import BillItem
from src.bill_items.services import BillItemService
from src.bills.models import Bill, ProcessingStatus
from src.bills.services import BillService
from src.ocr.schemas import OCRReceiptData
from src.processing.service import BillsProcessorService
from src.shops.models import Shop
from src.shops.services import ShopService
from src.users.models import User
from src.users.services import UserService

RAW_SHOP_ADDRESS = "UL. Akacjowa 1, 62-023 Gądki; ul. Inna 9, 00-001 Warszawa"
NORMALIZED_SHOP_ADDRESS = "ul. akacjowa 1 62-023 gądki"
RECEIPT_TOTAL = Decimal("12.50")
RECEIPT_ITEM = "MLEKO 3.2%"


def normalized_shop_name(external_id: int) -> str:
    return f"sklep qa {external_id} s.a."


def quoted_shop_name(external_id: int) -> str:
    return f'"SKLEP QA {external_id}" S.A.'


async def delete_shop_by_name(session: AsyncSession, name: str) -> None:
    shops = list(await session.scalars(select(Shop).where(Shop.name == name)))
    for shop in shops:
        referenced = await session.scalar(
            select(func.count()).select_from(Bill).where(Bill.shop_id == shop.id)
        )
        if referenced:
            continue
        await session.delete(shop)
    await session.commit()


async def delete_owned_user(session: AsyncSession, external_id: int) -> None:
    """Delete one test user. Bills, items, and magic links go with the user."""
    await session.execute(delete(User).where(User.external_id == external_id))
    await session.commit()
    await delete_shop_by_name(session, normalized_shop_name(external_id))


async def create_user(session: AsyncSession, external_id: int) -> User:
    await delete_owned_user(session, external_id)
    user = User(external_id=external_id, is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def bill_count(session: AsyncSession, user_id: int) -> int:
    stats = await UserService(session).get_user_usage_stats(user_id)
    return int(stats["bills_this_month"])


async def line_item_count(session: AsyncSession, bill_id: int) -> int:
    count = await session.scalar(
        select(func.count()).select_from(BillItem).where(BillItem.bill_id == bill_id)
    )
    return int(count or 0)


async def insert_magic_link(
    session: AsyncSession,
    *,
    user_id: int,
    token: str,
    expires_at: datetime,
    used: bool = False,
) -> MagicLink:
    await session.execute(delete(MagicLink).where(MagicLink.token == token))
    await session.commit()
    link = MagicLink(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
        used=used,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


def access_token_for(session: AsyncSession, user: User) -> str:
    access_token, _refresh_token = AuthService(session).create_tokens_for_user(user)
    return access_token


async def insert_pending_bill(session: AsyncSession, user_id: int) -> Bill:
    bill = Bill(
        user_id=user_id,
        status=ProcessingStatus.PENDING,
        image_url=f"bills/qa/{user_id}.jpg",
    )
    session.add(bill)
    await session.commit()
    await session.refresh(bill)
    return bill


def processor_for(
    session: AsyncSession,
    *,
    receipt: OCRReceiptData | None = None,
    ocr_error: Exception | None = None,
) -> BillsProcessorService:
    """Real bill, shop, and item services. OCR and the model are stand-ins."""
    ocr = AsyncMock()
    if ocr_error is not None:
        ocr.extract_data = AsyncMock(side_effect=ocr_error)
    else:
        ocr.extract_data = AsyncMock(return_value=receipt)

    async def normalize_item(
        ocr_item,
        shop_id=None,
        shop_name=None,
        user_id=None,
        save_alias=True,
    ) -> NormalizedItem:
        unit_price = (
            ocr_item.unit_price
            if ocr_item.unit_price is not None
            else ocr_item.total_price
        )
        return NormalizedItem(
            original_text=ocr_item.name,
            normalized_name=ocr_item.name.lower(),
            quantity=ocr_item.quantity,
            unit_price=unit_price,
            total_price=ocr_item.total_price,
            category_id=None,
            product_index_id=None,
            confidence_score=1.0,
            is_confident=True,
        )

    ai = AsyncMock()
    ai.normalize_item = AsyncMock(side_effect=normalize_item)
    storage = MagicMock()
    storage.download_file = AsyncMock(return_value=b"receipt-image")
    storage.get_signed_url = MagicMock(return_value="http://localhost/signed")
    return BillsProcessorService(
        session=session,
        storage_service=storage,
        ocr_service=ocr,
        bill_service=BillService(session, storage),
        bill_item_service=BillItemService(session),
        shop_service=ShopService(session),
        ai_service=ai,
    )


def receipt_for(external_id: int, *, shop_name: str | None = None) -> OCRReceiptData:
    from src.ocr.schemas import OCRItem

    return OCRReceiptData(
        shop_name=shop_name if shop_name is not None else quoted_shop_name(external_id),
        shop_address=RAW_SHOP_ADDRESS,
        date=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        total_amount=RECEIPT_TOTAL,
        items=[
            OCRItem(
                name=RECEIPT_ITEM,
                quantity=Decimal("1"),
                unit_price=RECEIPT_TOTAL,
                total_price=RECEIPT_TOTAL,
                confidence_score=1.0,
            )
        ],
    )
