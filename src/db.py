"""SQLAlchemy async session factory and base model."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    connect_args={"timeout": 10},
)

# Create session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base for models
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection function for database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
