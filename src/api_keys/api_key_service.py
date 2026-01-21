"""
API Key Service - API Key Management
=====================================
Generate and manage API keys for external integrations.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class APIKeyPermission(str, Enum):
    """API key permission scopes."""
    # Read permissions
    READ_CONTACTS = "read:contacts"
    READ_COMPANIES = "read:companies"
    READ_DEALS = "read:deals"
    READ_EMAILS = "read:emails"
    READ_CAMPAIGNS = "read:campaigns"
    READ_REPORTS = "read:reports"
    READ_ALL = "read:all"
    
    # Write permissions
    WRITE_CONTACTS = "write:contacts"
    WRITE_COMPANIES = "write:companies"
    WRITE_DEALS = "write:deals"
    WRITE_EMAILS = "write:emails"
    WRITE_CAMPAIGNS = "write:campaigns"
    WRITE_ALL = "write:all"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_INTEGRATIONS = "admin:integrations"
    ADMIN_ALL = "admin:all"
    
    # Full access
    FULL_ACCESS = "full:access"


class APIKeyStatus(str, Enum):
    """API key status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class APIKeyUsage:
    """API key usage statistics."""
    total_requests: int = 0
    requests_today: int = 0
    requests_this_month: int = 0
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    last_used_endpoint: Optional[str] = None


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000


@dataclass
class APIKey:
    """API key entity."""
    id: str
    name: str
    key_prefix: str  # First 8 chars of key (for display)
    key_hash: str    # Hashed full key (for verification)
    permissions: list[APIKeyPermission]
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    
    # Rate limiting
    rate_limit: RateLimit = field(default_factory=RateLimit)
    
    # Usage tracking
    usage: APIKeyUsage = field(default_factory=APIKeyUsage)
    
    # Restrictions
    allowed_ips: Optional[list[str]] = None
    allowed_origins: Optional[list[str]] = None
    
    # Metadata
    description: Optional[str] = None
    created_by: Optional[str] = None
    organization_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


@dataclass
class APIKeyValidation:
    """Result of API key validation."""
    is_valid: bool
    api_key: Optional[APIKey] = None
    error: Optional[str] = None


class APIKeyService:
    """Service for API key management."""
    
    def __init__(self):
        self.api_keys: dict[str, APIKey] = {}
        self._key_prefix_to_id: dict[str, str] = {}  # For quick lookup
        self._create_sample_keys()
    
    def _create_sample_keys(self):
        """Create sample API keys for demo."""
        # Note: In production, we'd never store or return the actual key
        sample = APIKey(
            id="key_1",
            name="Production API Key",
            key_prefix="sk_prod_",
            key_hash=self._hash_key("sk_prod_sample123456"),
            permissions=[APIKeyPermission.READ_ALL, APIKeyPermission.WRITE_CONTACTS],
            description="Main production API key",
            created_by="admin",
            rate_limit=RateLimit(requests_per_minute=100, requests_per_hour=2000),
            usage=APIKeyUsage(
                total_requests=15420,
                requests_today=342,
                requests_this_month=8654,
                last_used_at=datetime.utcnow() - timedelta(minutes=5)
            )
        )
        
        self.api_keys[sample.id] = sample
        self._key_prefix_to_id[sample.key_prefix] = sample.id
    
    def _generate_key(self, prefix: str = "sk_live_") -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}{random_part}"
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _get_prefix(self, key: str) -> str:
        """Get the prefix portion of a key."""
        # Return first 8 characters as prefix
        return key[:8] if len(key) >= 8 else key
    
    async def create_api_key(
        self,
        name: str,
        permissions: list[APIKeyPermission],
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit: Optional[RateLimit] = None,
        allowed_ips: Optional[list[str]] = None,
        allowed_origins: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        organization_id: Optional[str] = None,
        prefix: str = "sk_live_"
    ) -> tuple[APIKey, str]:
        """Create a new API key. Returns the key object and the raw key (shown only once)."""
        key_id = f"key_{uuid4().hex[:12]}"
        raw_key = self._generate_key(prefix)
        key_prefix = self._get_prefix(raw_key)
        key_hash = self._hash_key(raw_key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            id=key_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=permissions,
            description=description,
            expires_at=expires_at,
            rate_limit=rate_limit or RateLimit(),
            allowed_ips=allowed_ips,
            allowed_origins=allowed_origins,
            created_by=created_by,
            organization_id=organization_id
        )
        
        self.api_keys[key_id] = api_key
        self._key_prefix_to_id[key_prefix] = key_id
        
        logger.info(f"Created API key: {name} ({key_id})")
        
        # Return both the key object and the raw key
        # The raw key is only returned once and should be stored securely by the user
        return api_key, raw_key
    
    async def validate_key(
        self,
        raw_key: str,
        required_permissions: Optional[list[APIKeyPermission]] = None,
        client_ip: Optional[str] = None,
        origin: Optional[str] = None
    ) -> APIKeyValidation:
        """Validate an API key and check permissions."""
        key_hash = self._hash_key(raw_key)
        
        # Find the key
        api_key = None
        for key in self.api_keys.values():
            if key.key_hash == key_hash:
                api_key = key
                break
        
        if not api_key:
            return APIKeyValidation(is_valid=False, error="Invalid API key")
        
        # Check status
        if api_key.status == APIKeyStatus.REVOKED:
            return APIKeyValidation(is_valid=False, error="API key has been revoked")
        
        if api_key.status == APIKeyStatus.EXPIRED:
            return APIKeyValidation(is_valid=False, error="API key has expired")
        
        # Check expiration
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            api_key.status = APIKeyStatus.EXPIRED
            return APIKeyValidation(is_valid=False, error="API key has expired")
        
        # Check IP whitelist
        if api_key.allowed_ips and client_ip:
            if client_ip not in api_key.allowed_ips:
                return APIKeyValidation(is_valid=False, error="IP address not allowed")
        
        # Check origin whitelist
        if api_key.allowed_origins and origin:
            if origin not in api_key.allowed_origins:
                return APIKeyValidation(is_valid=False, error="Origin not allowed")
        
        # Check permissions
        if required_permissions:
            has_full_access = APIKeyPermission.FULL_ACCESS in api_key.permissions
            
            if not has_full_access:
                for perm in required_permissions:
                    # Check for specific permission or wildcard
                    category = perm.value.split(":")[0]
                    wildcard_perm = f"{category}:all"
                    
                    has_perm = (
                        perm in api_key.permissions or
                        any(p.value == wildcard_perm for p in api_key.permissions)
                    )
                    
                    if not has_perm:
                        return APIKeyValidation(
                            is_valid=False,
                            error=f"Missing permission: {perm.value}"
                        )
        
        return APIKeyValidation(is_valid=True, api_key=api_key)
    
    async def record_usage(
        self,
        key_id: str,
        client_ip: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """Record API key usage."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return
        
        api_key.usage.total_requests += 1
        api_key.usage.requests_today += 1
        api_key.usage.requests_this_month += 1
        api_key.usage.last_used_at = datetime.utcnow()
        api_key.usage.last_used_ip = client_ip
        api_key.usage.last_used_endpoint = endpoint
    
    async def check_rate_limit(self, key_id: str) -> dict:
        """Check if API key is within rate limits."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return {"allowed": False, "error": "Key not found"}
        
        # Simplified rate limit check (in production, use Redis or similar)
        is_limited = api_key.usage.requests_today > api_key.rate_limit.requests_per_day
        
        return {
            "allowed": not is_limited,
            "requests_today": api_key.usage.requests_today,
            "daily_limit": api_key.rate_limit.requests_per_day,
            "remaining": max(0, api_key.rate_limit.requests_per_day - api_key.usage.requests_today)
        }
    
    async def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        return self.api_keys.get(key_id)
    
    async def list_api_keys(
        self,
        status: Optional[APIKeyStatus] = None,
        created_by: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> list[APIKey]:
        """List API keys with filters."""
        results = list(self.api_keys.values())
        
        if status:
            results = [k for k in results if k.status == status]
        
        if created_by:
            results = [k for k in results if k.created_by == created_by]
        
        if organization_id:
            results = [k for k in results if k.organization_id == organization_id]
        
        # Sort by created_at descending
        results.sort(key=lambda k: k.created_at, reverse=True)
        
        return results
    
    async def update_api_key(
        self,
        key_id: str,
        updates: dict[str, Any]
    ) -> Optional[APIKey]:
        """Update an API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return None
        
        allowed_fields = [
            "name", "description", "permissions", "rate_limit",
            "allowed_ips", "allowed_origins", "expires_at"
        ]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(api_key, key, value)
        
        logger.info(f"Updated API key: {key_id}")
        
        return api_key
    
    async def revoke_api_key(
        self,
        key_id: str,
        revoked_by: Optional[str] = None
    ) -> bool:
        """Revoke an API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        api_key.status = APIKeyStatus.REVOKED
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by = revoked_by
        
        logger.info(f"Revoked API key: {key_id}")
        
        return True
    
    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        # Remove from lookup
        if api_key.key_prefix in self._key_prefix_to_id:
            del self._key_prefix_to_id[api_key.key_prefix]
        
        del self.api_keys[key_id]
        
        logger.info(f"Deleted API key: {key_id}")
        
        return True
    
    async def rotate_api_key(
        self,
        key_id: str,
        rotated_by: Optional[str] = None
    ) -> Optional[tuple[APIKey, str]]:
        """Rotate an API key (create new, revoke old)."""
        old_key = self.api_keys.get(key_id)
        if not old_key:
            return None
        
        # Create new key with same settings
        new_key, raw_key = await self.create_api_key(
            name=old_key.name,
            permissions=old_key.permissions,
            description=old_key.description,
            rate_limit=old_key.rate_limit,
            allowed_ips=old_key.allowed_ips,
            allowed_origins=old_key.allowed_origins,
            created_by=rotated_by or old_key.created_by,
            organization_id=old_key.organization_id
        )
        
        # Revoke old key
        await self.revoke_api_key(key_id, revoked_by=rotated_by)
        
        logger.info(f"Rotated API key: {key_id} -> {new_key.id}")
        
        return new_key, raw_key
    
    async def get_usage_stats(
        self,
        key_id: Optional[str] = None
    ) -> dict:
        """Get usage statistics for API keys."""
        if key_id:
            api_key = self.api_keys.get(key_id)
            if not api_key:
                return {}
            
            return {
                "key_id": key_id,
                "name": api_key.name,
                "total_requests": api_key.usage.total_requests,
                "requests_today": api_key.usage.requests_today,
                "requests_this_month": api_key.usage.requests_this_month,
                "last_used_at": api_key.usage.last_used_at.isoformat() if api_key.usage.last_used_at else None,
                "rate_limit": {
                    "per_minute": api_key.rate_limit.requests_per_minute,
                    "per_hour": api_key.rate_limit.requests_per_hour,
                    "per_day": api_key.rate_limit.requests_per_day
                }
            }
        
        # Aggregate stats
        total_requests = sum(k.usage.total_requests for k in self.api_keys.values())
        active_keys = len([k for k in self.api_keys.values() if k.status == APIKeyStatus.ACTIVE])
        
        return {
            "total_api_keys": len(self.api_keys),
            "active_keys": active_keys,
            "revoked_keys": len([k for k in self.api_keys.values() if k.status == APIKeyStatus.REVOKED]),
            "total_requests_all_keys": total_requests,
            "top_keys_by_usage": sorted(
                [
                    {"key_id": k.id, "name": k.name, "total_requests": k.usage.total_requests}
                    for k in self.api_keys.values()
                ],
                key=lambda x: x["total_requests"],
                reverse=True
            )[:10]
        }


# Global service instance
_api_key_service: Optional[APIKeyService] = None


def get_api_key_service() -> APIKeyService:
    """Get or create the API key service singleton."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service
