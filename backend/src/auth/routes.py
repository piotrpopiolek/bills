from typing import Annotated

from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError
from src.auth.jwt import verify_refresh_token
from src.auth.schemas import (
    TokenResponse,
    TokenRefreshRequest,
    UserResponse,
    MagicLinkInternalResponse,
    MagicLinkListResponse,
    MagicLinkUpdate
)
from src.auth.services import AuthService
from src.db.main import get_session
from src.deps import CurrentUser

router = APIRouter()

async def get_auth_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AuthService:
    """Dependency to inject AuthService with database session."""
    return AuthService(session)

ServiceDependency = Annotated[AuthService, Depends(get_auth_service)]

# Login URLs are created only inside the Telegram /login handler
# (AuthService.create_magic_link_for_user). Do not expose an HTTP endpoint
# that accepts telegram_user_id and returns the URL — that is account takeover.

@router.get("/verify", response_model=TokenResponse, status_code=status.HTTP_200_OK, summary="Verify magic link and authenticate user",
    description="""
    Verify a magic link token and return JWT tokens for authentication.
    
    **Flow:**
    1. User clicks magic link from Telegram (GET request from browser)
    2. Frontend extracts token from URL query parameter
    3. System verifies token and marks it as used
    4. Returns access token (15 min) and refresh token (7 days)
    
    **Security:**
    - Token can only be used once
    - Expired tokens are rejected
    - JWT tokens are signed with HS256
    
    **Note:**
    - This is a GET endpoint (not POST) because user clicks link in browser
    - GET is semantically correct for token verification (read operation)
    - State modification (marking token as used) happens in service layer
    """
)
async def verify_magic_link(service: ServiceDependency, token: str = Query(..., description="Magic link token from URL")) -> TokenResponse:
    """
    Verify magic link token and return JWT tokens.
    
    Args:
        token: Magic link token (query parameter)
        service: AuthService dependency
        
    Returns:
        TokenResponse with access_token, refresh_token, and user info
        
    Raises:
        400: Invalid or malformed token
        401: Token expired or already used
    """
    # Verify token and get user
    user = await service.verify_magic_link(token)
    
    # Create JWT tokens
    access_token, refresh_token = service.create_tokens_for_user(user)
    
    # Build response
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            external_id=user.external_id,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK, summary="Refresh access token",
    description="""
    Refresh an expired access token using a valid refresh token.
    
    **Flow:**
    1. Client detects access token is expired (or about to expire)
    2. Client sends refresh token to this endpoint
    3. System validates refresh token and extracts user_id
    4. System generates new access and refresh tokens
    5. Client stores new tokens and continues operation
    
    **Security:**
    - Refresh token must be valid and not expired
    - Refresh token is validated to be of type 'refresh' (not 'access')
    - User must still exist and be active
    - New refresh token is issued (token rotation)
    
    **Token Lifetimes:**
    - Access token: 15 minutes (configurable)
    - Refresh token: 7 days (configurable)
    """
)
async def refresh_tokens(data: TokenRefreshRequest, service: ServiceDependency) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        data: Request containing refresh_token
        service: AuthService dependency
        
    Returns:
        TokenResponse with new access_token, refresh_token, and user info
        
    Raises:
        401: Invalid, expired, or wrong type of token
        404: User not found (user was deleted)
    """
    # Verify refresh token and extract user_id
    try:
        user_id = verify_refresh_token(data.refresh_token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user from database
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create new tokens (token rotation)
    access_token, refresh_token = service.create_tokens_for_user(user)
    
    # Build response
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            external_id=user.external_id,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )

# --- ADMIN/DEBUGGING ENDPOINTS FOR MAGIC LINK CRUD ---

@router.get("/admin/magic-links", response_model=MagicLinkListResponse, status_code=status.HTTP_200_OK, summary="List all magic links (Admin)", description="Get paginated list of all magic links. For admin/debugging purposes only.", tags=["admin"])
async def get_magic_links(user: CurrentUser, service: ServiceDependency, skip: int = Query(0, ge=0, description="Number of items to skip"), limit: int = Query(100, ge=1, le=100, description="Max number of items to return")) -> MagicLinkListResponse:
    """
    List all magic links with pagination.
    Requires authentication.
    
    Args:
        user: Current authenticated user (from JWT token)
        service: AuthService dependency
        skip: Number of items to skip
        limit: Max number of items to return
        
    Returns:
        MagicLinkListResponse with paginated results
    """
    return await service.get_all(skip=skip, limit=limit)

@router.get("/admin/magic-links/{magic_link_id}", response_model=MagicLinkInternalResponse, status_code=status.HTTP_200_OK, summary="Get magic link by ID (Admin)", description="Get detailed information about a specific magic link. For admin/debugging purposes only.", tags=["admin"])
async def get_magic_link(magic_link_id: int, user: CurrentUser, service: ServiceDependency) -> MagicLinkInternalResponse:
    """
    Get magic link by ID.
    Requires authentication.
    
    Args:
        magic_link_id: MagicLink ID
        user: Current authenticated user (from JWT token)
        service: AuthService dependency
        
    Returns:
        MagicLinkInternalResponse with full record
        
    Raises:
        404: Magic link not found
    """
    return await service.get_by_id(magic_link_id)

@router.patch("/admin/magic-links/{magic_link_id}", response_model=MagicLinkInternalResponse, status_code=status.HTTP_200_OK, summary="Update magic link (Admin)", description="Update magic link fields. For admin/debugging purposes only.", tags=["admin"])
async def update_magic_link(magic_link_id: int, data: MagicLinkUpdate, user: CurrentUser, service: ServiceDependency):
    """
    Update magic link record.
    Requires authentication.
    
    Args:
        magic_link_id: MagicLink ID to update
        data: Fields to update
        user: Current authenticated user (from JWT token)
        service: AuthService dependency
        
    Returns:
        MagicLinkInternalResponse with updated record
        
    Raises:
        404: Magic link not found
    """
    return await service.update(magic_link_id, data)

@router.delete("/admin/magic-links/{magic_link_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete magic link (Admin)", description="Delete a magic link record. For admin/debugging purposes only.", tags=["admin"])
async def delete_magic_link(magic_link_id: int, user: CurrentUser, service: ServiceDependency) -> None:
    """
    Delete magic link record.
    Requires authentication.
    
    Args:
        magic_link_id: MagicLink ID to delete
        user: Current authenticated user (from JWT token)
        service: AuthService dependency
        
    Raises:
        404: Magic link not found
    """
    await service.delete(magic_link_id)
    return None

