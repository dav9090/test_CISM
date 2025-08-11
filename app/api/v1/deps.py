"""Dependencies for API endpoints."""

from collections.abc import AsyncGenerator

from app.db.session import AsyncSession, AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session
