"""Pydantic schemas for authentication."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Data extracted from a JWT token."""

    user_id: str
    email: str
    exp: datetime


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""

    refresh_token: str


class UserInfo(BaseModel):
    """User information from OAuth provider."""

    id: str
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str  # "google" or "apple"


class UserResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    full_name: Optional[str] = None
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
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "auth_provider": "google",
                "email_verified": True,
                "is_active": True,
                "created_at": "2026-01-15T10:00:00Z",
                "last_login": "2026-01-15T14:30:00Z",
                "total_workflows": 5,
                "total_cost": 25.50,
            }
        }


class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""

    state: str
    redirect_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
