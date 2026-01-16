"""JWT token creation and validation utilities."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from arakis.auth.exceptions import InvalidCredentialsError, TokenExpiredError
from arakis.config import get_settings


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's unique ID
        email: The user's email address
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    Create a JWT refresh token.

    Args:
        user_id: The user's unique ID
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (encoded JWT token string, token hash for DB storage)
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(timezone.utc) + expires_delta

    # Generate a unique token ID
    token_id = secrets.token_urlsafe(32)

    payload = {
        "sub": user_id,
        "jti": token_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    # Create hash for DB storage
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return token, token_hash


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.

    Args:
        token: The JWT token string

    Returns:
        Decoded token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidCredentialsError: If the token is invalid
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "access":
            raise InvalidCredentialsError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Access token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidCredentialsError(f"Invalid token: {str(e)}")


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.

    Args:
        token: The JWT token string

    Returns:
        Decoded token payload

    Raises:
        TokenExpiredError: If the token has expired
        InvalidCredentialsError: If the token is invalid
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "refresh":
            raise InvalidCredentialsError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Refresh token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidCredentialsError(f"Invalid token: {str(e)}")


def hash_token(token: str) -> str:
    """Create a SHA256 hash of a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()
