"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from arakis.config import get_settings

settings = get_settings()

# Async engine for API (PostgreSQL with asyncpg)
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before using
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync engine for migrations (Alembic)
# Replace asyncpg with psycopg2 for sync operations
sync_database_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(
    sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
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


async def init_db():
    """Initialize database (create all tables). For development only."""
    from arakis.database.models import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections. Call on application shutdown."""
    await async_engine.dispose()
