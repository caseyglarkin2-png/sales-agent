"""
OAuth2 token management and refresh for Google APIs.

Handles:
- Token storage in database (encrypted at rest)
- Automatic token refresh before expiry
- Token revocation detection
- Multi-user token management
"""
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as GoogleCredentials
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from src.db import Base
from src.logger import get_logger

logger = get_logger(__name__)


class OAuthToken(Base):
    """
    Encrypted OAuth tokens for external services.
    
    Stores tokens with encryption at rest for security.
    """
    __tablename__ = "oauth_tokens"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    service = Column(String(50), nullable=False, index=True)  # gmail, hubspot, drive
    
    # Encrypted token data
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_data_encrypted = Column(Text, nullable=True, comment="Full token JSON encrypted")
    
    # Token metadata
    scopes = Column(Text, nullable=True, comment="Space-separated scopes")
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    last_refreshed_at = Column(DateTime, nullable=True)


class TokenEncryption:
    """
    Encrypt/decrypt OAuth tokens at rest.
    
    Uses Fernet (symmetric encryption) with key from environment.
    """
    
    def __init__(self):
        """Initialize with encryption key from environment."""
        # Get or generate encryption key
        key_b64 = os.environ.get("OAUTH_ENCRYPTION_KEY")
        
        if not key_b64:
            logger.warning(
                "OAUTH_ENCRYPTION_KEY not set - generating temporary key. "
                "Set OAUTH_ENCRYPTION_KEY in production!"
            )
            key_b64 = Fernet.generate_key().decode()
        
        self.fernet = Fernet(key_b64.encode() if isinstance(key_b64, str) else key_b64)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        encrypted_bytes = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_bytes).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()


# Global encryption instance
_encryption = TokenEncryption()


class TokenManager:
    """
    Manage OAuth tokens with automatic refresh.
    
    Features:
    - Store tokens encrypted in database
    - Refresh tokens before expiry
    - Detect and handle revocation
    - Multi-user support
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize token manager."""
        self.db = db
        self.encryption = _encryption
    
    async def store_token(
        self,
        user_id: UUID,
        service: str,
        credentials: GoogleCredentials
    ) -> OAuthToken:
        """
        Store OAuth token (encrypted).
        
        Args:
            user_id: User ID
            service: Service name (gmail, drive, etc.)
            credentials: Google OAuth credentials object
        
        Returns:
            Created OAuthToken record
        """
        # Serialize full token data
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        token_json = json.dumps(token_data)
        
        # Encrypt sensitive fields
        access_token_enc = self.encryption.encrypt(credentials.token)
        refresh_token_enc = (
            self.encryption.encrypt(credentials.refresh_token)
            if credentials.refresh_token else None
        )
        token_data_enc = self.encryption.encrypt(token_json)
        
        # Check if token exists for this user/service
        query = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.access_token_encrypted = access_token_enc
            existing.refresh_token_encrypted = refresh_token_enc
            existing.token_data_encrypted = token_data_enc
            existing.scopes = " ".join(credentials.scopes) if credentials.scopes else None
            existing.expires_at = credentials.expiry
            existing.revoked = False
            existing.last_refreshed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            logger.info(f"Updated {service} token for user {user_id}")
            return existing
        
        else:
            # Create new
            token = OAuthToken(
                user_id=user_id,
                service=service,
                access_token_encrypted=access_token_enc,
                refresh_token_encrypted=refresh_token_enc,
                token_data_encrypted=token_data_enc,
                scopes=" ".join(credentials.scopes) if credentials.scopes else None,
                expires_at=credentials.expiry,
                revoked=False
            )
            
            self.db.add(token)
            await self.db.commit()
            await self.db.refresh(token)
            
            logger.info(f"Stored new {service} token for user {user_id}")
            return token
    
    async def get_token(
        self,
        user_id: UUID,
        service: str,
        auto_refresh: bool = True
    ) -> Optional[GoogleCredentials]:
        """
        Get OAuth token (decrypted), with optional auto-refresh.
        
        Args:
            user_id: User ID
            service: Service name
            auto_refresh: Automatically refresh if expired
        
        Returns:
            Google OAuth credentials or None if not found
        """
        query = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service,
            OAuthToken.revoked == False
        )
        result = await self.db.execute(query)
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            logger.warning(f"No {service} token found for user {user_id}")
            return None
        
        # Decrypt token data
        token_json = self.encryption.decrypt(token_record.token_data_encrypted)
        token_data = json.loads(token_json)
        
        # Reconstruct credentials
        credentials = GoogleCredentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes")
        )
        
        # Check if expired and refresh if needed
        if auto_refresh and credentials.expired:
            logger.info(f"{service} token expired, refreshing...")
            
            try:
                credentials.refresh(Request())
                
                # Store refreshed token
                await self.store_token(user_id, service, credentials)
                
                logger.info(f"Successfully refreshed {service} token for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to refresh {service} token: {e}")
                # Mark as revoked
                token_record.revoked = True
                await self.db.commit()
                return None
        
        return credentials
    
    async def revoke_token(self, user_id: UUID, service: str):
        """Mark token as revoked."""
        query = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.service == service
        )
        result = await self.db.execute(query)
        token_record = result.scalar_one_or_none()
        
        if token_record:
            token_record.revoked = True
            await self.db.commit()
            logger.info(f"Revoked {service} token for user {user_id}")
    
    async def get_expiring_tokens(self, hours_before: int = 1) -> list[OAuthToken]:
        """
        Get tokens expiring soon (for proactive refresh).
        
        Args:
            hours_before: Hours before expiry to consider "expiring soon"
        
        Returns:
            List of expiring token records
        """
        threshold = datetime.utcnow() + timedelta(hours=hours_before)
        
        query = select(OAuthToken).where(
            OAuthToken.expires_at < threshold,
            OAuthToken.revoked == False,
            OAuthToken.refresh_token_encrypted.isnot(None)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()


async def refresh_expiring_tokens_task(db: AsyncSession):
    """
    Background task to refresh tokens expiring soon.
    
    Should be run periodically (e.g., every 30 minutes via Celery Beat).
    """
    manager = TokenManager(db)
    expiring = await manager.get_expiring_tokens(hours_before=1)
    
    logger.info(f"Found {len(expiring)} tokens expiring within 1 hour")
    
    for token_record in expiring:
        try:
            # Trigger refresh by getting with auto_refresh=True
            await manager.get_token(
                token_record.user_id,
                token_record.service,
                auto_refresh=True
            )
        except Exception as e:
            logger.error(
                f"Failed to refresh {token_record.service} token "
                f"for user {token_record.user_id}: {e}"
            )
    
    logger.info(f"Completed token refresh task")
