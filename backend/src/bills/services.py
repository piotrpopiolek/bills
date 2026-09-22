from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.bill_items.models import BillItem
from src.bills.models import Bill
from src.bills.schemas import BillCreate, BillResponse, BillUpdate
from src.common.exceptions import BillAccessDeniedError, ResourceNotFoundError
from src.common.services import AppService
from src.shops.models import Shop
from src.storage.service import StorageService
from src.users.models import User


class BillService(AppService[Bill, BillCreate, BillUpdate]):
    def __init__(self, session: AsyncSession, storage_service: StorageService):
        super().__init__(model=Bill, session=session)
        self.storage_service = storage_service

    def _to_response(self, bill: Bill) -> BillResponse:
        """
        Convert Bill model to BillResponse schema with signed URL and shop name.

        This method encapsulates the logic for generating signed URLs
        and converting Bill models to BillResponse schemas, following
        the DRY principle to avoid code duplication.

        Args:
            bill: The Bill model instance to convert (shop relationship should be loaded via joinedload)

        Returns:
            BillResponse with image_signed_url and shop_name populated
        """
        image_signed_url = None
        if bill.image_url:
            image_signed_url = self.storage_service.get_signed_url(bill.image_url)

        # Extract shop name if shop relationship is loaded
        shop_name = None
        if bill.shop is not None:
            shop_name = bill.shop.name

        response = BillResponse.model_validate(bill, from_attributes=True)
        response.image_signed_url = image_signed_url
        response.shop_name = shop_name
        return response

    async def create(self, data: BillCreate) -> BillResponse:
        # User Existence Check (Referential Integrity check before DB hit)
        await self._ensure_exists(
            model=User, field=User.id, value=data.user_id, resource_name="User"
        )

        # Shop Existence Check (if provided)
        if data.shop_id:
            await self._ensure_exists(
                model=Shop, field=Shop.id, value=data.shop_id, resource_name="Shop"
            )

        # Object Construction
        new_bill = Bill(
            status=data.status,
            bill_date=data.bill_date,
            total_amount=data.total_amount,
            user_id=data.user_id,
            shop_id=data.shop_id,
            image_url=data.image_url,
            image_hash=data.image_hash,
            image_expires_at=data.image_expires_at,
            image_status=data.image_status,
            error_message=data.error_message,
        )

        # Persistence (Unit of Work)
        self.session.add(new_bill)

        try:
            await self.session.commit()
            # Reload bill with shop relationship for response using eager loading
            stmt = (
                select(Bill)
                .options(joinedload(Bill.shop))
                .where(Bill.id == new_bill.id)
            )
            result = await self.session.execute(stmt)
            new_bill = result.scalar_one()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        return self._to_response(new_bill)

    async def update(
        self, bill_id: int, data: BillUpdate, user_id: int
    ) -> BillResponse:
        """
        Update bill by ID with user ownership check.

        Args:
            bill_id: ID of the bill to update
            data: BillUpdate schema with fields to update
            user_id: ID of the user requesting the update (must own the bill)

        Returns:
            BillResponse with signed URL

        Raises:
            BillAccessDeniedError: If bill exists but doesn't belong to user_id
            ResourceNotFoundError: If bill doesn't exist
        """
        # Ownership check: get bill with shop relationship and verify it belongs to user_id
        stmt = select(Bill).options(joinedload(Bill.shop)).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ResourceNotFoundError("Bill", bill_id)

        if bill.user_id != user_id:
            raise BillAccessDeniedError(bill_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            # Even if no updates, return BillResponse with signed URL and shop_name
            return self._to_response(bill)

        # Prevent changing ownership via update (user_id should not be updatable)
        if "user_id" in update_data and update_data["user_id"] != bill.user_id:
            raise BillAccessDeniedError(bill_id)

        # Shop Existence Check (if shop_id is being updated)
        if "shop_id" in update_data and update_data["shop_id"] != bill.shop_id:
            new_shop_id = update_data["shop_id"]
            if new_shop_id is not None:
                await self._ensure_exists(
                    model=Shop, field=Shop.id, value=new_shop_id, resource_name="Shop"
                )

        # Apply updates
        for key, value in update_data.items():
            setattr(bill, key, value)

        try:
            await self.session.commit()
            # Reload bill with shop relationship for response using eager loading
            stmt = select(Bill).options(joinedload(Bill.shop)).where(Bill.id == bill.id)
            result = await self.session.execute(stmt)
            bill = result.scalar_one()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        return self._to_response(bill)

    async def get_by_id(self, bill_id: int) -> BillResponse:
        """
        Get bill by ID and generate signed URL for the image.
        Overrides base method to add image_signed_url to response.

        Note: This method does not check ownership. Use get_by_id_and_user()
        for user-isolated access.
        """
        bill = await super().get_by_id(bill_id)
        return self._to_response(bill)

    async def get_by_id_and_user(self, bill_id: int, user_id: int) -> BillResponse:
        """
        Get bill by ID for a specific user and generate signed URL for the image.
        Enforces user isolation by checking ownership.
        Uses eager loading (joinedload) to fetch shop relationship in one query.

        Args:
            bill_id: ID of the bill to retrieve
            user_id: ID of the user requesting the bill (must own the bill)

        Returns:
            BillResponse with signed URL and shop_name

        Raises:
            BillAccessDeniedError: If bill exists but doesn't belong to user_id
            ResourceNotFoundError: If bill doesn't exist
        """
        # Use eager loading to fetch shop relationship in one query (LEFT JOIN)
        stmt = select(Bill).options(joinedload(Bill.shop)).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ResourceNotFoundError("Bill", bill_id)

        if bill.user_id != user_id:
            raise BillAccessDeniedError(bill_id)

        return self._to_response(bill)

    async def get_all(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        """
        Get all bills for a specific user with pagination and generate signed URLs for images.
        Uses eager loading (joinedload) to fetch shop relationships efficiently (avoids N+1 queries).

        Args:
            user_id: ID of the user whose bills to retrieve (required for user isolation)
            skip: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Dictionary with paginated bills and signed URLs
        """
        # Count total bills for this user
        count_stmt = (
            select(func.count()).select_from(Bill).where(Bill.user_id == user_id)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch bills with eager loading of shop relationship (prevents N+1 queries)
        # Uses LEFT JOIN to load shop data in a single query
        stmt = (
            select(Bill)
            .options(joinedload(Bill.shop))
            .where(Bill.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Bill.id)
        )
        result = await self.session.execute(stmt)
        bills = result.scalars().all()

        # Generate signed URLs for each bill
        bills_with_urls = [self._to_response(bill) for bill in bills]

        return {"items": bills_with_urls, "total": total, "skip": skip, "limit": limit}

    async def delete(self, bill_id: int, user_id: int) -> None:
        """
        Delete bill by ID with user ownership check.

        Args:
            bill_id: ID of the bill to delete
            user_id: ID of the user requesting the deletion (must own the bill)

        Raises:
            BillAccessDeniedError: If bill exists but doesn't belong to user_id
            ResourceNotFoundError: If bill doesn't exist
        """
        # Ownership check: get bill and verify it belongs to user_id
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await self.session.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ResourceNotFoundError("Bill", bill_id)

        if bill.user_id != user_id:
            raise BillAccessDeniedError(bill_id)

        self.session.delete(bill)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_items_sum(self, bill_id: int) -> Decimal:
        """
        Calculate sum of all bill_items for given bill.
        Returns 0 if no items.
        """
        stmt = select(func.sum(BillItem.total_price)).where(BillItem.bill_id == bill_id)
        result = await self.session.execute(stmt)
        items_sum = result.scalar_one_or_none()

        return items_sum or Decimal("0.00")
