"""Tests for auth module."""
import pytest

from src.oauth_manager_legacy import OAuth2Manager


@pytest.mark.asyncio
async def test_oauth2_store_and_retrieve():
    """Test storing and retrieving OAuth2 credentials."""
    manager = OAuth2Manager()
    creds = {"access_token": "token123", "refresh_token": "refresh123"}
    
    await manager.store_credentials("user1", "google", creds)
    retrieved = await manager.get_credentials("user1", "google")
    
    assert retrieved == creds


@pytest.mark.asyncio
async def test_oauth2_revoke():
    """Test revoking OAuth2 credentials."""
    manager = OAuth2Manager()
    creds = {"access_token": "token123"}
    
    await manager.store_credentials("user1", "google", creds)
    assert await manager.get_credentials("user1", "google") is not None
    
    revoked = await manager.revoke_credentials("user1", "google")
    assert revoked is True
    assert await manager.get_credentials("user1", "google") is None
