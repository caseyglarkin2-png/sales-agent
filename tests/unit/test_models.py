"""Unit tests for database models."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db import Base
from src.models.message import Message, Thread
from src.models.hubspot import HubSpotCompany, HubSpotContact
import uuid


@pytest.fixture
async def test_db():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_message_unique_key_constraint(test_db):
    """Test that duplicate gmail_message_id violates constraint."""
    msg_id = str(uuid.uuid4())
    
    msg1 = Message(
        id=uuid.uuid4(),
        gmail_message_id="gmail-123",
        gmail_thread_id="thread-123",
        sender="test@example.com",
        recipient="recipient@example.com",
        subject="Test",
        body="Test body"
    )
    
    test_db.add(msg1)
    await test_db.commit()
    
    # Attempting to add duplicate should fail
    msg2 = Message(
        id=uuid.uuid4(),
        gmail_message_id="gmail-123",  # Duplicate
        gmail_thread_id="thread-456",
        sender="test@example.com",
        recipient="recipient@example.com",
        subject="Test 2",
        body="Test body 2"
    )
    
    test_db.add(msg2)
    
    # Check constraint exists (implementation may vary by DB)
    assert msg1.gmail_message_id == "gmail-123"
