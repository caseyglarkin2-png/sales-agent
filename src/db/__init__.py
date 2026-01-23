"""Database package."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.db.workflow_db import WorkflowDB, get_workflow_db, close_workflow_db


# Base class for SQLAlchemy models (used by Alembic)
class Base(DeclarativeBase):
    pass

# Placeholder async_session for backward compatibility
# Real database connection is handled by WorkflowDB using asyncpg
_engine = None
_async_session_factory = None


@asynccontextmanager
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a mock async session for backward compatibility.
    
    Note: For workflow operations, use get_workflow_db() instead.
    """
    # This is a placeholder - real DB ops use WorkflowDB
    import os
    database_url = os.environ.get("DATABASE_URL", "")
    
    if database_url and database_url.startswith("postgres"):
        # Convert to async URL format
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(async_url, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session
    else:
        # Mock session for testing
        yield None  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        yield session


# Alias for backward compatibility with GDPR module
SessionLocal = async_sessionmaker


__all__ = ["WorkflowDB", "get_workflow_db", "close_workflow_db", "async_session", "get_db", "Base", "SessionLocal"]
