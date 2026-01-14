"""FastAPI dependencies for database, authentication, etc."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.database.connection import AsyncSessionLocal

# Security scheme for JWT tokens (will be implemented later)
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Get current authenticated user from JWT token.

    For now, this is a placeholder that allows all requests.
    TODO: Implement proper JWT validation in Phase 2 (Authentication).

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            ...
    """
    # Placeholder - allow all requests for now
    # In production, validate JWT token and return user info
    if credentials is None:
        # For development, allow unauthenticated access
        return {"id": "anonymous", "email": "anonymous@example.com"}

    # TODO: Validate JWT token
    # token = credentials.credentials
    # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    # user_id = payload.get("sub")
    # return get_user_from_db(user_id)

    return {"id": "authenticated", "email": "user@example.com"}


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get current active user (not disabled).

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_active_user)):
            ...
    """
    # TODO: Check if user is active in database
    return current_user
