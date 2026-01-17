"""OAuth authentication endpoints."""

import json
import secrets
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.api.dependencies import get_current_user, get_db
from arakis.api.ratelimit import rate_limit
from arakis.api.schemas.auth import (
    LogoutRequest,
    MessageResponse,
    OAuthLoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
)
from arakis.auth.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    OAuthError,
    TokenExpiredError,
)
from arakis.auth.jwt import decode_refresh_token
from arakis.auth.providers.apple import AppleOAuthProvider
from arakis.auth.providers.google import GoogleOAuthProvider
from arakis.auth.service import AuthService
from arakis.config import get_settings
from arakis.database.models import User

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# In-memory state storage (use Redis in production)
_oauth_states: dict[str, dict] = {}


def _generate_state() -> str:
    """Generate a secure random state for CSRF protection."""
    return secrets.token_urlsafe(32)


def _store_state(state: str, data: dict | None = None) -> None:
    """Store OAuth state temporarily."""
    _oauth_states[state] = data or {}


def _validate_state(state: str) -> dict | None:
    """Validate and consume OAuth state."""
    return _oauth_states.pop(state, None)


# ============================================================
# Google OAuth
# ============================================================


@router.get("/google/login", response_model=OAuthLoginResponse)
@rate_limit(requests=10, window_seconds=300, error_message="Too many OAuth login attempts.")
async def google_login(request: Request, redirect_url: Optional[str] = None):
    """
    Initiate Google OAuth login.

    Returns authorization URL to redirect user to Google's login page.
    The optional redirect_url parameter specifies where to redirect after login.
    """
    settings = get_settings()

    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured",
        )

    state = _generate_state()
    _store_state(state, {"redirect_url": redirect_url})

    provider = GoogleOAuthProvider()
    auth_url = provider.get_authorization_url(state)

    return OAuthLoginResponse(authorization_url=auth_url, state=state)


@router.get("/google/callback")
@rate_limit(requests=10, window_seconds=60, error_message="Too many authentication attempts.")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Exchanges authorization code for tokens and creates/updates user.
    Redirects to frontend with tokens or error.
    """
    settings = get_settings()

    # Validate state
    state_data = _validate_state(state)
    if state_data is None:
        return _redirect_with_error("Invalid or expired state", settings)

    try:
        # Exchange code for user info
        provider = GoogleOAuthProvider()
        user_info = await provider.get_user_info(code)

        # Get or create user
        auth_service = AuthService(db)
        user = await auth_service.get_or_create_oauth_user(user_info)

        # Claim any trial workflows
        session_id = request.cookies.get("arakis_session")
        if session_id:
            await auth_service.claim_trial_workflows(user.id, session_id)

        # Create tokens
        device_info = request.headers.get("User-Agent", "Unknown")[:255]
        tokens = await auth_service.create_tokens(user, device_info)

        # Redirect to frontend with tokens
        # Pass original redirect_url as return_to for post-auth redirect
        return_to = state_data.get("redirect_url")
        return _redirect_with_tokens(tokens, return_to, settings)

    except OAuthError as e:
        return _redirect_with_error(str(e), settings)
    except Exception as e:
        return _redirect_with_error(f"Authentication failed: {str(e)}", settings)


# ============================================================
# Apple OAuth
# ============================================================


@router.get("/apple/login", response_model=OAuthLoginResponse)
@rate_limit(requests=10, window_seconds=300, error_message="Too many OAuth login attempts.")
async def apple_login(request: Request, redirect_url: Optional[str] = None):
    """
    Initiate Apple Sign In.

    Returns authorization URL to redirect user to Apple's login page.
    """
    settings = get_settings()

    if not settings.apple_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Apple OAuth is not configured",
        )

    state = _generate_state()
    _store_state(state, {"redirect_url": redirect_url})

    provider = AppleOAuthProvider()
    auth_url = provider.get_authorization_url(state)

    return OAuthLoginResponse(authorization_url=auth_url, state=state)


@router.post("/apple/callback")
@rate_limit(requests=10, window_seconds=60, error_message="Too many authentication attempts.")
async def apple_callback(
    request: Request,
    code: str = Form(...),
    state: str = Form(...),
    id_token: Optional[str] = Form(None),
    user: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Apple Sign In callback.

    Apple sends callback as POST with form data.
    The `user` field is only sent on first login and contains name/email.
    """
    settings = get_settings()

    # Validate state
    state_data = _validate_state(state)
    if state_data is None:
        return _redirect_with_error("Invalid or expired state", settings)

    try:
        # Parse user data if provided (only on first login)
        user_data = None
        if user:
            try:
                user_data = json.loads(user)
            except json.JSONDecodeError:
                pass

        # Exchange code for user info
        provider = AppleOAuthProvider()
        user_info = await provider.get_user_info(
            code=code,
            id_token=id_token,
            user_data=user_data,
        )

        # Get or create user
        auth_service = AuthService(db)
        db_user = await auth_service.get_or_create_oauth_user(user_info)

        # Claim any trial workflows
        session_id = request.cookies.get("arakis_session")
        if session_id:
            await auth_service.claim_trial_workflows(db_user.id, session_id)

        # Create tokens
        device_info = request.headers.get("User-Agent", "Unknown")[:255]
        tokens = await auth_service.create_tokens(db_user, device_info)

        # Redirect to frontend with tokens
        # Pass original redirect_url as return_to for post-auth redirect
        return_to = state_data.get("redirect_url")
        return _redirect_with_tokens(tokens, return_to, settings)

    except OAuthError as e:
        return _redirect_with_error(str(e), settings)
    except Exception as e:
        return _redirect_with_error(f"Authentication failed: {str(e)}", settings)


# ============================================================
# Token Management
# ============================================================


@router.post("/refresh", response_model=TokenResponse)
@rate_limit(requests=10, window_seconds=60, error_message="Too many token refresh attempts.")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    The old refresh token is invalidated.
    """
    try:
        # Decode refresh token
        payload = decode_refresh_token(body.refresh_token)
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidCredentialsError("Invalid refresh token")

        # Validate token is not revoked
        auth_service = AuthService(db)
        if not await auth_service.validate_refresh_token(body.refresh_token):
            raise InvalidCredentialsError("Refresh token has been revoked")

        # Create new tokens
        device_info = request.headers.get("User-Agent", "Unknown")[:255]
        tokens = await auth_service.refresh_tokens(
            user_id=user_id,
            old_token=body.refresh_token,
            device_info=device_info,
        )

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please sign in again.",
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", response_model=MessageResponse)
@rate_limit(requests=10, window_seconds=60, error_message="Too many logout attempts.")
async def logout(
    request: Request,
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout by revoking refresh token.

    The access token will remain valid until expiration.
    Client should discard it.
    """
    auth_service = AuthService(db)
    revoked = await auth_service.revoke_refresh_token(body.refresh_token)

    if revoked:
        return MessageResponse(message="Successfully logged out", success=True)
    else:
        return MessageResponse(message="Token already revoked or invalid", success=True)


# ============================================================
# User Profile
# ============================================================


@router.get("/me", response_model=UserProfileResponse)
@rate_limit(requests=30, window_seconds=60, error_message="Too many profile requests.")
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's profile.

    Requires valid access token.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return UserProfileResponse.model_validate(current_user)


# ============================================================
# Helper Functions
# ============================================================


def _redirect_with_tokens(tokens: TokenResponse, return_to: str | None, settings) -> RedirectResponse:
    """Create redirect response with tokens in URL fragment.

    Always redirects to /auth/success page which handles token extraction.
    The original redirect destination is passed as return_to query param.
    """
    token_params = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": str(tokens.expires_in),
    }

    # Always redirect to /auth/success - it's the only page with token extraction logic
    # Pass original destination as return_to query param
    success_path = settings.oauth_success_redirect
    if return_to and return_to != success_path:
        success_path = f"{success_path}?return_to={return_to}"

    # Use fragment (#) for tokens to avoid them being logged in server logs
    redirect_url = f"{settings.frontend_url}{success_path}#{urlencode(token_params)}"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # Clear trial session cookie after successful login
    response.delete_cookie("arakis_session")

    return response


def _redirect_with_error(error: str, settings) -> RedirectResponse:
    """Create redirect response with error."""
    params = {"error": error}
    redirect_url = f"{settings.frontend_url}{settings.oauth_error_redirect}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
