"""FastAPI dependencies for database, authentication, etc."""

from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.database.connection import AsyncSessionLocal
from arakis.database.models import User

# Security scheme for JWT tokens - auto_error=False allows anonymous access
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.

    Returns None if no token provided (for trial/anonymous access).
    Returns User if valid token provided.
    Raises 401 if token is invalid or expired.

    Usage:
        @app.get("/endpoint")
        async def endpoint(user: User | None = Depends(get_current_user)):
            if user is None:
                # Anonymous/trial access
            else:
                # Authenticated access
    """
    if credentials is None:
        return None

    from arakis.auth.exceptions import InvalidCredentialsError, TokenExpiredError
    from arakis.auth.jwt import decode_access_token

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Get current active user (requires authentication).

    Raises 401 if not authenticated.

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            # Only authenticated users reach here
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
