"""HubSpot API Client with Rate Limiting and Caching.

Sprint 3 - Production-ready HubSpot integration.

HubSpot Rate Limits:
- Private Apps: 100 requests per 10 seconds (burst)
- Daily: 150,000 requests per day
- We use a token bucket to stay under limits.
"""
import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Generic
from functools import wraps

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# Rate Limiter (Token Bucket Algorithm)
# =============================================================================

class TokenBucket:
    """Token bucket rate limiter for HubSpot API.
    
    HubSpot allows 100 requests per 10 seconds for private apps.
    We use 90/10s (9/s) to have headroom.
    """
    
    def __init__(
        self, 
        tokens_per_second: float = 9.0,  # 90 per 10 sec 
        max_tokens: float = 90.0,        # Burst capacity
    ):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: float = 1.0) -> float:
        """Acquire tokens, waiting if necessary.
        
        Returns the time waited in seconds.
        """
        async with self._lock:
            now = time.monotonic()
            
            # Refill tokens based on time elapsed
            elapsed = now - self.last_update
            self.tokens = min(
                self.max_tokens,
                self.tokens + (elapsed * self.tokens_per_second)
            )
            self.last_update = now
            
            wait_time = 0.0
            if self.tokens < tokens:
                # Calculate wait time
                deficit = tokens - self.tokens
                wait_time = deficit / self.tokens_per_second
                await asyncio.sleep(wait_time)
                self.tokens = tokens  # Will be consumed immediately
            
            self.tokens -= tokens
            return wait_time


# =============================================================================
# Cache Layer
# =============================================================================

@dataclass
class CacheEntry(Generic[T]):
    """A cached value with expiry."""
    value: T
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class HubSpotCache:
    """In-memory cache for HubSpot responses.
    
    TTL values are tuned for signal detection:
    - Contacts/Deals change frequently → short TTL
    - Pipelines rarely change → long TTL
    """
    
    # TTL in seconds by data type
    TTL = {
        "contacts": 300,      # 5 minutes
        "deals": 300,         # 5 minutes
        "companies": 600,     # 10 minutes
        "pipelines": 3600,    # 1 hour
        "emails": 120,        # 2 minutes (for activity detection)
        "engagements": 120,   # 2 minutes
    }
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0}
    
    def _make_key(self, data_type: str, params: Dict[str, Any]) -> str:
        """Generate cache key from type and params."""
        param_str = hashlib.md5(str(sorted(params.items())).encode()).hexdigest()[:8]
        return f"{data_type}:{param_str}"
    
    async def get(self, data_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached value if exists and not expired."""
        key = self._make_key(data_type, params)
        
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                self.stats["hits"] += 1
                return entry.value
            
            # Remove expired entry
            if entry and entry.is_expired:
                del self._cache[key]
            
            self.stats["misses"] += 1
            return None
    
    async def set(self, data_type: str, params: Dict[str, Any], value: Any) -> None:
        """Cache a value with appropriate TTL."""
        key = self._make_key(data_type, params)
        ttl = self.TTL.get(data_type, 300)  # Default 5 min
        
        async with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl
            )
    
    async def invalidate(self, data_type: Optional[str] = None) -> int:
        """Invalidate cache entries. Returns count invalidated."""
        async with self._lock:
            if data_type is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            
            # Invalidate by prefix
            prefix = f"{data_type}:"
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        async with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired:
                del self._cache[key]
            return len(expired)


# =============================================================================
# Response Models
# =============================================================================

class HubSpotContact(BaseModel):
    """Contact from HubSpot."""
    id: str
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    jobtitle: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_contacted: Optional[datetime] = None
    properties: Dict[str, Any] = {}
    
    @property
    def full_name(self) -> str:
        parts = [self.firstname, self.lastname]
        return " ".join(p for p in parts if p) or self.email or "Unknown"


class HubSpotDeal(BaseModel):
    """Deal from HubSpot."""
    id: str
    dealname: str
    amount: Optional[float] = None
    dealstage: str = ""
    pipeline: str = ""
    closedate: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    days_in_stage: int = 0
    properties: Dict[str, Any] = {}
    
    @property
    def is_stalled(self) -> bool:
        """Deal is stalled if no update in 7+ days."""
        if not self.updated_at:
            return False
        return (datetime.utcnow() - self.updated_at).days >= 7


class HubSpotCompany(BaseModel):
    """Company from HubSpot."""
    id: str
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = {}


class HubSpotEmail(BaseModel):
    """Email engagement from HubSpot."""
    id: str
    subject: Optional[str] = None
    from_email: Optional[str] = None
    to_email: Optional[str] = None
    status: Optional[str] = None  # "SENT", "OPENED", "CLICKED"
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None


class HubSpotMeeting(BaseModel):
    """Meeting from HubSpot."""
    id: str
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    contact_ids: List[str] = []
    deal_id: Optional[str] = None
    outcome: Optional[str] = None


class PipelineStage(BaseModel):
    """Pipeline stage from HubSpot."""
    id: str
    label: str
    display_order: int
    probability: Optional[float] = None


# =============================================================================
# HubSpot Client
# =============================================================================

class HubSpotClient:
    """Production-ready HubSpot API client.
    
    Features:
    - Token bucket rate limiting (respects 100/10s limit)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Clean typed responses
    
    Usage:
        client = HubSpotClient(api_key=os.getenv("HUBSPOT_API_KEY"))
        contacts = await client.get_contacts(limit=50)
        await client.close()
    """
    
    BASE_URL = "https://api.hubapi.com"
    
    def __init__(
        self, 
        api_key: str,
        enable_cache: bool = True,
        cache: Optional[HubSpotCache] = None,
        rate_limiter: Optional[TokenBucket] = None,
    ):
        self.api_key = api_key
        self.cache = cache or HubSpotCache() if enable_cache else None
        self.rate_limiter = rate_limiter or TokenBucket()
        
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        
        # Stats for monitoring
        self.stats = {
            "requests": 0,
            "rate_limit_waits": 0,
            "retries": 0,
            "errors": 0,
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make a rate-limited request with retry logic."""
        
        # Wait for rate limit token
        wait_time = await self.rate_limiter.acquire()
        if wait_time > 0:
            self.stats["rate_limit_waits"] += 1
            logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        last_error = None
        backoff = 1.0
        
        for attempt in range(max_retries):
            try:
                self.stats["requests"] += 1
                
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json,
                )
                
                # Handle rate limit response (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    logger.warning(f"HubSpot rate limited, sleeping {retry_after}s")
                    await asyncio.sleep(retry_after)
                    self.stats["retries"] += 1
                    backoff = min(backoff * 2, 30)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    # Server error, retry with backoff
                    logger.warning(f"HubSpot server error {e.response.status_code}, retry {attempt + 1}")
                    await asyncio.sleep(backoff)
                    self.stats["retries"] += 1
                    backoff = min(backoff * 2, 30)
                    continue
                else:
                    # Client error (4xx), don't retry
                    self.stats["errors"] += 1
                    raise
                    
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"HubSpot request error: {e}, retry {attempt + 1}")
                await asyncio.sleep(backoff)
                self.stats["retries"] += 1
                backoff = min(backoff * 2, 30)
        
        # All retries exhausted
        self.stats["errors"] += 1
        raise last_error or Exception("Request failed after retries")
    
    # =========================================================================
    # Contacts
    # =========================================================================
    
    async def get_contacts(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[List[str]] = None,
    ) -> List[HubSpotContact]:
        """Get contacts from HubSpot."""
        
        if properties is None:
            properties = [
                "email", "firstname", "lastname", "company", "phone",
                "jobtitle", "createdate", "lastmodifieddate", 
                "notes_last_contacted", "hs_lead_status"
            ]
        
        params = {
            "limit": limit,
            "properties": ",".join(properties),
        }
        if after:
            params["after"] = after
        
        # Check cache
        if self.cache:
            cached = await self.cache.get("contacts", params)
            if cached is not None:
                return cached
        
        data = await self._request("GET", "/crm/v3/objects/contacts", params=params)
        
        contacts = []
        for result in data.get("results", []):
            props = result.get("properties", {})
            contact = HubSpotContact(
                id=result["id"],
                email=props.get("email"),
                firstname=props.get("firstname"),
                lastname=props.get("lastname"),
                company=props.get("company"),
                phone=props.get("phone"),
                jobtitle=props.get("jobtitle"),
                created_at=self._parse_datetime(props.get("createdate")),
                updated_at=self._parse_datetime(props.get("lastmodifieddate")),
                last_contacted=self._parse_datetime(props.get("notes_last_contacted")),
                properties=props,
            )
            contacts.append(contact)
        
        # Cache result
        if self.cache:
            await self.cache.set("contacts", params, contacts)
        
        return contacts
    
    # =========================================================================
    # Deals
    # =========================================================================
    
    async def get_deals(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        pipeline: Optional[str] = None,
    ) -> List[HubSpotDeal]:
        """Get deals from HubSpot."""
        
        properties = [
            "dealname", "amount", "dealstage", "pipeline",
            "closedate", "createdate", "hs_lastmodifieddate",
            "days_to_close", "hs_deal_stage_probability"
        ]
        
        params = {
            "limit": limit,
            "properties": ",".join(properties),
        }
        if after:
            params["after"] = after
        
        # Check cache
        if self.cache:
            cached = await self.cache.get("deals", params)
            if cached is not None:
                return cached
        
        data = await self._request("GET", "/crm/v3/objects/deals", params=params)
        
        deals = []
        for result in data.get("results", []):
            props = result.get("properties", {})
            
            # Parse amount
            amount_str = props.get("amount")
            amount = float(amount_str) if amount_str else None
            
            # Calculate days in stage
            updated = self._parse_datetime(props.get("hs_lastmodifieddate"))
            days_in_stage = (datetime.utcnow() - updated).days if updated else 0
            
            deal = HubSpotDeal(
                id=result["id"],
                dealname=props.get("dealname", "Untitled Deal"),
                amount=amount,
                dealstage=props.get("dealstage", ""),
                pipeline=props.get("pipeline", ""),
                closedate=self._parse_datetime(props.get("closedate")),
                created_at=self._parse_datetime(props.get("createdate")),
                updated_at=updated,
                days_in_stage=days_in_stage,
                properties=props,
            )
            
            # Filter by pipeline if specified
            if pipeline and deal.pipeline != pipeline:
                continue
                
            deals.append(deal)
        
        # Cache result
        if self.cache:
            await self.cache.set("deals", params, deals)
        
        return deals
    
    # =========================================================================
    # Companies
    # =========================================================================
    
    async def get_companies(
        self,
        limit: int = 100,
        after: Optional[str] = None,
    ) -> List[HubSpotCompany]:
        """Get companies from HubSpot."""
        
        properties = [
            "name", "domain", "industry",
            "createdate", "hs_lastmodifieddate"
        ]
        
        params = {
            "limit": limit,
            "properties": ",".join(properties),
        }
        if after:
            params["after"] = after
        
        # Check cache
        if self.cache:
            cached = await self.cache.get("companies", params)
            if cached is not None:
                return cached
        
        data = await self._request("GET", "/crm/v3/objects/companies", params=params)
        
        companies = []
        for result in data.get("results", []):
            props = result.get("properties", {})
            company = HubSpotCompany(
                id=result["id"],
                name=props.get("name", "Unknown"),
                domain=props.get("domain"),
                industry=props.get("industry"),
                created_at=self._parse_datetime(props.get("createdate")),
                updated_at=self._parse_datetime(props.get("hs_lastmodifieddate")),
                properties=props,
            )
            companies.append(company)
        
        # Cache result
        if self.cache:
            await self.cache.set("companies", params, companies)
        
        return companies
    
    # =========================================================================
    # Emails (Engagements)
    # =========================================================================
    
    async def get_recent_emails(
        self,
        limit: int = 50,
        since_days: int = 7,
    ) -> List[HubSpotEmail]:
        """Get recent email engagements."""
        
        # Use search API with date filter
        since = datetime.utcnow() - timedelta(days=since_days)
        
        search_body = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "hs_timestamp",
                    "operator": "GTE",
                    "value": int(since.timestamp() * 1000)
                }]
            }],
            "sorts": [{"propertyName": "hs_timestamp", "direction": "DESCENDING"}],
            "limit": limit,
        }
        
        data = await self._request(
            "POST", 
            "/crm/v3/objects/emails/search",
            json=search_body
        )
        
        emails = []
        for result in data.get("results", []):
            props = result.get("properties", {})
            email = HubSpotEmail(
                id=result["id"],
                subject=props.get("hs_email_subject"),
                from_email=props.get("hs_email_from_email"),
                to_email=props.get("hs_email_to_email"),
                status=props.get("hs_email_status"),
                sent_at=self._parse_datetime(props.get("hs_timestamp")),
            )
            emails.append(email)
        
        return emails
    
    # =========================================================================
    # Pipelines
    # =========================================================================
    
    async def get_deal_pipelines(self) -> List[Dict[str, Any]]:
        """Get deal pipelines with stages."""
        
        # Check cache (pipelines rarely change)
        if self.cache:
            cached = await self.cache.get("pipelines", {})
            if cached is not None:
                return cached
        
        data = await self._request("GET", "/crm/v3/pipelines/deals")
        
        pipelines = data.get("results", [])
        
        # Cache result
        if self.cache:
            await self.cache.set("pipelines", {}, pipelines)
        
        return pipelines
    
    # =========================================================================
    # Associations
    # =========================================================================
    
    async def get_deal_contacts(self, deal_id: str) -> List[str]:
        """Get contact IDs associated with a deal."""
        data = await self._request(
            "GET",
            f"/crm/v4/objects/deals/{deal_id}/associations/contacts"
        )
        return [r["toObjectId"] for r in data.get("results", [])]
    
    async def get_contact_deals(self, contact_id: str) -> List[str]:
        """Get deal IDs associated with a contact."""
        data = await self._request(
            "GET",
            f"/crm/v4/objects/contacts/{contact_id}/associations/deals"
        )
        return [r["toObjectId"] for r in data.get("results", [])]
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """Test the HubSpot API connection."""
        try:
            await self._request("GET", "/crm/v3/objects/contacts", params={"limit": 1})
            return True
        except Exception as e:
            logger.error(f"HubSpot connection test failed: {e}")
            return False
    
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse HubSpot datetime string to Python datetime."""
        if not value:
            return None
        try:
            # HubSpot uses ISO format or Unix millis
            if value.isdigit():
                return datetime.fromtimestamp(int(value) / 1000)
            return datetime.fromisoformat(value.replace("Z", "+00:00").replace("+00:00", ""))
        except (ValueError, TypeError):
            return None


# =============================================================================
# Factory Function
# =============================================================================

def get_hubspot_client() -> HubSpotClient:
    """Get configured HubSpot client from environment."""
    api_key = os.environ.get("HUBSPOT_API_KEY")
    if not api_key:
        raise ValueError("HUBSPOT_API_KEY environment variable not set")
    
    return HubSpotClient(api_key=api_key)
