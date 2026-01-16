"""Authentication module for Arakis OAuth and JWT handling."""

from arakis.auth.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    UserNotFoundError,
)
from arakis.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from arakis.auth.schemas import TokenData, TokenResponse, UserInfo
from arakis.auth.service import AuthService

__all__ = [
    # JWT functions
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    # Schemas
    "TokenData",
    "TokenResponse",
    "UserInfo",
    # Service
    "AuthService",
    # Exceptions
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "UserNotFoundError",
]
