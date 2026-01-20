"""Unit tests for database layer."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import async_session


@pytest.mark.asyncio
async def test_async_session_factory_works():
    """Test that async session factory is properly configured."""
    # This is a basic sanity check that session factory exists
    assert async_session is not None
    
    # Note: Full integration test would require actual database
    # This validates the factory is callable
    assert callable(async_session)
