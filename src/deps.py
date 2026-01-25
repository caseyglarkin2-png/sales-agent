"""Dependency injection utilities for FastAPI."""
from typing import AsyncGenerator, Optional
from fastapi import Header

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for dependency injection."""
    async with get_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Get current user ID from header or return demo user.
    
    Ship Ship Ship: Authentication to be enhanced later.
    For now, allows testing without full auth system.
    """
    if x_user_id:
        return x_user_id
    
    # Default demo user for testing
    return "demo-user-123"
