"""Pydantic schemas for auth API endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""

    refresh_token: str


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    affiliation: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    total_workflows: int = 0
    total_cost: float = 0.0

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    """Request to update user profile."""

    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    affiliation: Optional[str] = Field(None, max_length=500)


class OAuthLoginResponse(BaseModel):
    """Response from OAuth login initiation."""

    authorization_url: str
    state: str


class AppleCallbackRequest(BaseModel):
    """Apple OAuth callback data (sent as form POST)."""

    code: str
    state: str
    id_token: Optional[str] = None
    user: Optional[str] = None  # JSON string with user data on first login


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True
