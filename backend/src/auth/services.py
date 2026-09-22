import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import (
    InvalidTokenError,
    TokenAlreadyUsedError,
    TokenExpiredError,
)
from src.auth.jwt import create_access_token, create_refresh_token
from src.auth.models import MagicLink
from src.auth.schemas import MagicLinkCreate, MagicLinkUpdate
from src.common.exceptions import ResourceAlreadyExistsError, UserCreationError
from src.common.services import AppService
from src.config import settings
from src.users.models import User
from src.users.schemas import UserCreate
from src.users.services import UserService


class AuthService(AppService[MagicLink, MagicLinkCreate, MagicLinkUpdate]):
    """
    Authentication service handling magic link and JWT token operations.

    This service manages:
    - Magic link generation and verification
    - JWT token creation (access + refresh)
    - Token validation and expiration
    - CRUD operations for MagicLink (admin/debugging)

    Inherits from AppService to gain access to:
    - _ensure_exists() - check if related entity exists
    - _ensure_unique() - check uniqueness constraints
    - _is_foreign_key_violation() - detect FK violations
    - get_by_id() - get magic link by ID
    - get_all() - get paginated list of magic links
    """

    def __init__(self, session: AsyncSession):
        super().__init__(model=MagicLink, session=session)

    async def create_magic_link_for_user(
        self, user_id: int, redirect_url: str | None = None
    ) -> tuple[MagicLink, str]:
        """
        Create a magic link for passwordless authentication.

        Args:
            user_id: Internal user ID (must exist in database)
            redirect_url: Optional URL to redirect after authentication

        Returns:
            Tuple of (MagicLink model, full_magic_link_url)

        Raises:
            ResourceNotFoundError: If user with user_id doesn't exist
            IntegrityError: If database constraints are violated

        Flow:
            1. Check if user exists (using inherited _ensure_exists)
            2. Generate secure random token
            3. Create MagicLink record with expiration
            4. Persist to database with rollback on error
            5. Return link and URL
        """
        # User Existence Check (Referential Integrity check before DB hit)
        await self._ensure_exists(
            model=User, field=User.id, value=user_id, resource_name="User"
        )

        # Generate secure token (32 bytes = 64 hex characters)
        token = secrets.token_urlsafe(32)

        # Calculate expiration (using timezone-aware datetime)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
        )

        # Object Construction
        magic_link = MagicLink(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
            redirect_url=redirect_url,
            used=False,
        )

        # Persistence (Unit of Work)
        self.session.add(magic_link)

        try:
            await self.session.commit()
            await self.session.refresh(magic_link)
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        # Construct full URL
        # Ensure WEB_APP_URL has protocol (https:// for production, http:// for development)
        base_url = settings.WEB_APP_URL
        if not base_url.startswith(("http://", "https://")):
            # Default to https:// when the URL has no scheme.
            base_url = f"https://{base_url}"
        full_url = f"{base_url}/auth/verify?token={token}"

        return magic_link, full_url

    async def verify_magic_link(self, token: str) -> User:
        """
        Verify a magic link token and return authenticated user.

        Args:
            token: Magic link token to verify

        Returns:
            Authenticated User model

        Raises:
            InvalidTokenError: If token doesn't exist
            TokenExpiredError: If token is expired
            TokenAlreadyUsedError: If token was already used

        Flow:
            1. Find token in database
            2. Check if token is expired
            3. Check if token was already used
            4. Mark token as used
            5. Return user
        """
        # Find token
        stmt = select(MagicLink).where(MagicLink.token == token)
        result = await self.session.execute(stmt)
        magic_link = result.scalar_one_or_none()

        if not magic_link:
            raise InvalidTokenError()

        # Check expiration (using timezone-aware datetime)
        if magic_link.expires_at < datetime.now(UTC):
            raise TokenExpiredError(expires_at=magic_link.expires_at)

        # Check if already used
        if magic_link.used:
            raise TokenAlreadyUsedError(used_at=magic_link.used_at)

        # Mark as used (using timezone-aware datetime)
        magic_link.used = True
        magic_link.used_at = datetime.now(UTC)
        await self.session.commit()

        # Load and return user
        stmt = select(User).where(User.id == magic_link.user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one()

        return user

    def create_tokens_for_user(self, user: User) -> tuple[str, str]:
        """
        Create access and refresh JWT tokens for a user.

        Args:
            user: User model to create tokens for

        Returns:
            Tuple of (access_token, refresh_token)

        Note:
            Access token expires in 15 minutes (configurable)
            Refresh token expires in 7 days (configurable)
        """
        # Payload for both tokens
        token_data = {"sub": str(user.id)}

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return access_token, refresh_token

    async def create(self, data: MagicLinkCreate) -> MagicLink:
        """
        Create a magic link record (internal CRUD operation).

        This method is for direct database manipulation (admin/debugging).
        For normal authentication flow, use create_magic_link_for_user() instead.

        Args:
            data: MagicLinkCreate schema with all required fields

        Returns:
            Created MagicLink model

        Raises:
            ResourceNotFoundError: If user_id doesn't exist
            IntegrityError: If database constraints are violated
        """
        # User Existence Check
        await self._ensure_exists(
            model=User, field=User.id, value=data.user_id, resource_name="User"
        )

        # Object Construction
        magic_link = MagicLink(
            token=data.token,
            user_id=data.user_id,
            expires_at=data.expires_at,
            used=data.used,
            used_at=data.used_at,
            redirect_url=data.redirect_url,
        )

        # Persistence (Unit of Work)
        self.session.add(magic_link)

        try:
            await self.session.commit()
            await self.session.refresh(magic_link)
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        return magic_link

    async def update(self, magic_link_id: int, data: MagicLinkUpdate) -> MagicLink:
        """
        Update a magic link record (internal CRUD operation).

        This method is for direct database manipulation (admin/debugging).
        For normal verification flow, use verify_magic_link() instead.

        Args:
            magic_link_id: MagicLink ID to update
            data: MagicLinkUpdate schema with fields to update

        Returns:
            Updated MagicLink model

        Raises:
            ResourceNotFoundError: If magic_link_id doesn't exist
            IntegrityError: If database constraints are violated
        """
        magic_link = await self.get_by_id(magic_link_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return magic_link

        # User Existence Check (if user_id is being updated)
        if "user_id" in update_data and update_data["user_id"] != magic_link.user_id:
            await self._ensure_exists(
                model=User,
                field=User.id,
                value=update_data["user_id"],
                resource_name="User",
            )

        # Apply updates
        for key, value in update_data.items():
            setattr(magic_link, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(magic_link)
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        return magic_link

    async def delete(self, magic_link_id: int) -> None:
        """
        Delete a magic link record (internal CRUD operation).

        Args:
            magic_link_id: MagicLink ID to delete

        Raises:
            ResourceNotFoundError: If magic_link_id doesn't exist
        """
        magic_link = await self.get_by_id(magic_link_id)

        self.session.delete(magic_link)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        """
        Get user by Telegram user ID (external_id).

        This method is used by routes to map telegram_user_id to internal user_id.

        Args:
            telegram_user_id: Telegram user ID (external_id)

        Returns:
            User model or None if not found
        """
        stmt = select(User).where(User.external_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Get user by internal ID (used by get_current_user dependency).

        Note: This is a convenience wrapper. For MagicLink entities,
        use inherited get_by_id() method instead.

        Args:
            user_id: Internal user ID

        Returns:
            User model or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_user_by_telegram_id(self, telegram_user_id: int) -> User:
        """
        Get existing user by Telegram ID or create a new one.

        This method encapsulates the "get or create" pattern for Telegram users,
        eliminating code duplication across handlers. It handles user creation
        errors and translates them to domain exceptions.

        Args:
            telegram_user_id: Telegram user ID (external_id)

        Returns:
            User model (existing or newly created)

        Raises:
            UserCreationError: If user creation fails for reasons other than duplicate
            ResourceAlreadyExistsError: If user already exists (should not happen in normal flow)

        Note:
            This method follows the DRY principle by centralizing user creation logic
            that was previously duplicated in login_command and handle_receipt_image handlers.
        """
        # Try to get existing user
        user = await self.get_user_by_telegram_id(telegram_user_id)
        if user:
            return user

        # User doesn't exist, create new one
        user_service = UserService(self.session)
        try:
            user = await user_service.create(
                UserCreate(external_id=telegram_user_id, is_active=True)
            )
            return user
        except ResourceAlreadyExistsError:
            # Race condition: user was created between check and create
            # Retry getting the user
            user = await self.get_user_by_telegram_id(telegram_user_id)
            if user:
                return user
            # If still not found, re-raise the exception
            raise
        except Exception as e:
            # Wrap unexpected errors in UserCreationError
            # Note: ResourceAlreadyExistsError is already handled above
            raise UserCreationError(f"Nieoczekiwany błąd: {str(e)}") from e
