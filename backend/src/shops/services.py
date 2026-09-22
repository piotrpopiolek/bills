import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.exceptions import ResourceAlreadyExistsError
from src.common.services import AppService
from src.shops.models import Shop
from src.shops.normalization import normalize_shop_address, normalize_shop_name
from src.shops.schemas import ShopCreate, ShopUpdate

logger = logging.getLogger(__name__)


class ShopService(AppService[Shop, ShopCreate, ShopUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=Shop, session=session)

    async def update(self, shop_id: int, data: ShopUpdate) -> Shop:
        shop = await self.get_by_id(shop_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return shop

        # Uniqueness Check (if name or address is being updated)
        new_name = update_data.get("name", shop.name)
        new_address = update_data.get("address", shop.address)

        if "name" in update_data or "address" in update_data:
            if new_name != shop.name or new_address != shop.address:
                await self._ensure_unique_shop(
                    new_name, new_address, exclude_id=shop.id
                )

        # Apply updates
        for key, value in update_data.items():
            setattr(shop, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(shop)
        except IntegrityError as e:
            await self.session.rollback()
            # Check if it's a unique constraint violation
            if "uq_shops_name_address" in str(e.orig) or "23505" in str(e.orig):
                raise ResourceAlreadyExistsError(
                    "Shop", "name + address", f"{new_name} + {new_address or 'NULL'}"
                ) from e
            raise e

        return shop

    async def _find_by_name_and_address(
        self, name: str, address: str | None, exclude_id: int | None = None
    ) -> Shop | None:
        """
        Find shop by name and address.

        Args:
            name: Shop name (będzie znormalizowany przed wyszukiwaniem)
            address: Shop address (optional, będzie znormalizowany przed wyszukiwaniem)
            exclude_id: Optional shop ID to exclude from search

        Returns:
            Shop instance if found, None otherwise

        Note:
            Name i address są normalizowane przed wyszukiwaniem (defensive programming).
            Baza danych przechowuje znormalizowane wartości dzięki standaryzacji w schemas/services.
        """
        # Normalizacja dla bezpieczeństwa (defensive programming)
        # Zapewnia, że wyszukiwanie działa nawet jeśli dane nie były wcześniej znormalizowane
        normalized_name = normalize_shop_name(name)
        normalized_address = normalize_shop_address(address) if address else None

        stmt = select(Shop).where(
            Shop.name == normalized_name, Shop.address == normalized_address
        )

        if exclude_id is not None:
            stmt = stmt.where(Shop.id != exclude_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_by_name(
        self, name: str, address: str | None = None
    ) -> Shop:
        """
        Get existing shop by name and address, or create new one.

        Args:
            name: Shop name (required) - będzie znormalizowany przed wyszukiwaniem/tworzeniem
            address: Shop address (optional) - będzie znormalizowany przed wyszukiwaniem/tworzeniem

        Returns:
            Shop instance (existing or newly created)

        Note:
            Uses unique constraint on (name, address) to prevent duplicates.
            If shop with same name+address exists, returns existing.
            Otherwise creates new shop.
            Handles race conditions (concurrent creation) by retrying fetch on IntegrityError.

            STANDARYZACJA: Nazwa i adres są normalizowane przed zapisem do bazy danych,
            zgodnie z "złotym standardem" (lowercase, trim, bez przecinków, znormalizowane białe znaki).
        """
        # STANDARYZACJA przed wyszukiwaniem/tworzeniem
        normalized_name = normalize_shop_name(name)
        normalized_address = normalize_shop_address(address) if address else None

        # Walidacja: nazwa nie może być pusta po normalizacji
        if not normalized_name:
            raise ValueError("Shop name cannot be empty after normalization")

        # Try to find existing shop (używamy znormalizowanych wartości)
        existing_shop = await self._find_by_name_and_address(
            normalized_name, normalized_address
        )

        if existing_shop:
            logger.info(f"Found existing shop: {existing_shop.id} ({normalized_name})")
            return existing_shop

        # Create new shop (z znormalizowanymi wartościami)
        new_shop = Shop(name=normalized_name, address=normalized_address)
        self.session.add(new_shop)

        try:
            await self.session.commit()
            await self.session.refresh(new_shop)
            logger.info(f"Created new shop: {new_shop.id} ({normalized_name})")
            return new_shop
        except IntegrityError as e:
            await self.session.rollback()
            # Race condition: shop was created by another request
            # Retry: fetch existing shop (używamy znormalizowanych wartości)
            existing_shop = await self._find_by_name_and_address(
                normalized_name, normalized_address
            )
            if existing_shop:
                logger.info(
                    f"Shop created concurrently, returning existing: {existing_shop.id}"
                )
                return existing_shop
            raise e

    async def _ensure_unique_shop(
        self, name: str, address: str | None, exclude_id: int | None = None
    ) -> None:
        """
        Checks if a combination of name and address already exists.
        Used to prevent duplicate shops with the same name and address.
        Note: This is case-sensitive (not using LOWER) as per database constraint.
        """
        existing_shop = await self._find_by_name_and_address(name, address, exclude_id)
        if existing_shop:
            raise ResourceAlreadyExistsError(
                "Shop", "name + address", f"{name} + {address or 'NULL'}"
            )
