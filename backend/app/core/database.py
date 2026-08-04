"""Async database session with connection pooling and health checks."""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.core.config import settings

# SQLAlchemy async engines support only AsyncAdaptedQueuePool (default)
# or NullPool. Sync-only pool classes like QueuePool are not allowed.
# Use NullPool only in tests to avoid cross-test connection leaks.
poolclass = NullPool if settings.ENVIRONMENT == "test" else None

engine_kwargs: dict = {
    "echo": settings.DATABASE_ECHO,
    "pool_pre_ping": True,  # verify connections before use
}
if settings.ENVIRONMENT == "test":
    engine_kwargs["poolclass"] = NullPool
else:
    # Production: use the asyncio-compatible default pool
    # (AsyncAdaptedQueuePool) with explicit sizing.
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_async_engine(settings.async_database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # manual flush for performance
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_ctx():
    """Context manager version for use outside FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health() -> dict:
    """Health check for the database connection."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "latency_ms": None}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
