"""Database package."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings
from src.db.workflow_db import WorkflowDB, get_workflow_db, close_workflow_db
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


# Base class for SQLAlchemy models (used by Alembic)
class Base(DeclarativeBase):
    pass


class SafeJSON(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


settings = get_settings()

# Primary async engine/session factory (used by health checks and new features)
_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)
_async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session bound to the primary engine."""
    async with _async_session_factory() as session:
        yield session


# Alias for better naming (Sprint 22 standard)
get_session = async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        yield session


# Alias for backwards compatibility
SessionLocal = _async_session_factory


__all__ = ["WorkflowDB", "get_workflow_db", "close_workflow_db", "async_session", "get_session", "get_db", "Base", "SessionLocal", "SafeJSON"]
