"""
Enhanced rate limiting and quota management.

Provides:
- Token bucket algorithm for API rate limiting
- Redis-backed distributed rate limiting
- Per-service quota tracking (Gmail, HubSpot, etc.)
- User/tenant-level quotas
- Graceful degradation under quota pressure
"""
import time
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitService(str, Enum):
    """Services with rate limits."""
    GMAIL = "gmail"
    HUBSPOT = "hubspot"
    OPENAI = "openai"
    DRIVE = "drive"
    CALENDAR = "calendar"


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, service: str, reset_at: float):
        self.service = service
        self.reset_at = reset_at
        self.retry_after = max(0, int(reset_at - time.time()))
        super().__init__(f"Rate limit exceeded for {service}. Retry after {self.retry_after}s")


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter with Redis backend.
    
    Allows burst traffic up to bucket capacity, then enforces steady rate.
    """
    
    # Rate limits per service (tokens per minute)
    SERVICE_LIMITS = {
        RateLimitService.GMAIL: {
            "capacity": 100,  # Burst capacity
            "refill_rate": 60,  # Tokens per minute (1/second)
        },
        RateLimitService.HUBSPOT: {
            "capacity": 150,  # HubSpot allows 150 req/10sec
            "refill_rate": 600,  # 10 per second average
        },
        RateLimitService.OPENAI: {
            "capacity": 60,  # OpenAI tier-dependent
            "refill_rate": 60,  # 1 per second
        },
        RateLimitService.DRIVE: {
            "capacity": 100,
            "refill_rate": 100,
        },
        RateLimitService.CALENDAR: {
            "capacity": 50,
            "refill_rate": 50,
        },
    }
    
    def __init__(self, redis_client = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client for distributed tracking
        """
        self.redis = redis_client
        self.local_cache = {}  # Fallback for when Redis unavailable
    
    def _get_key(self, service: RateLimitService, user_id: Optional[str] = None) -> str:
        """Generate Redis key for rate limit tracking."""
        if user_id:
            return f"ratelimit:{service.value}:user:{user_id}"
        return f"ratelimit:{service.value}:global"
    
    async def check_limit(
        self,
        service: RateLimitService,
        cost: int = 1,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            service: Service being called
            cost: Token cost (default 1, can be higher for expensive operations)
            user_id: Optional user ID for per-user limits
        
        Returns:
            True if allowed, False if rate limited
        
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        config = self.SERVICE_LIMITS.get(service)
        if not config:
            # No limit configured, allow
            return True
        
        key = self._get_key(service, user_id)
        now = time.time()
        
        if self.redis:
            # Redis-backed distributed rate limiting
            return await self._check_redis(key, config, cost, now)
        else:
            # Local fallback
            return self._check_local(key, config, cost, now)
    
    async def _check_redis(self, key: str, config: Dict, cost: int, now: float) -> bool:
        """Check rate limit using Redis."""
        try:
            # Get current state
            state = await self.redis.hgetall(key)
            
            if not state:
                # Initialize bucket
                tokens = config["capacity"] - cost
                await self.redis.hset(key, mapping={
                    "tokens": str(tokens),
                    "last_refill": str(now)
                })
                await self.redis.expire(key, 3600)  # Expire after 1 hour
                return True
            
            # Calculate refill
            tokens = float(state.get(b"tokens", 0))
            last_refill = float(state.get(b"last_refill", now))
            time_passed = now - last_refill
            
            # Refill tokens based on time passed
            refill_amount = (time_passed / 60.0) * config["refill_rate"]
            tokens = min(config["capacity"], tokens + refill_amount)
            
            # Check if enough tokens
            if tokens >= cost:
                tokens -= cost
                await self.redis.hset(key, mapping={
                    "tokens": str(tokens),
                    "last_refill": str(now)
                })
                return True
            else:
                # Calculate when enough tokens will be available
                needed = cost - tokens
                seconds_until_available = (needed / config["refill_rate"]) * 60
                reset_at = now + seconds_until_available
                
                raise RateLimitExceeded(key.split(":")[1], reset_at)
                
        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}, falling back to local")
            return self._check_local(key, config, cost, now)
    
    def _check_local(self, key: str, config: Dict, cost: int, now: float) -> bool:
        """Check rate limit using local memory (fallback)."""
        if key not in self.local_cache:
            self.local_cache[key] = {
                "tokens": config["capacity"] - cost,
                "last_refill": now
            }
            return True
        
        state = self.local_cache[key]
        time_passed = now - state["last_refill"]
        
        # Refill tokens
        refill_amount = (time_passed / 60.0) * config["refill_rate"]
        state["tokens"] = min(config["capacity"], state["tokens"] + refill_amount)
        state["last_refill"] = now
        
        # Check tokens
        if state["tokens"] >= cost:
            state["tokens"] -= cost
            return True
        else:
            needed = cost - state["tokens"]
            seconds_until_available = (needed / config["refill_rate"]) * 60
            reset_at = now + seconds_until_available
            
            raise RateLimitExceeded(key.split(":")[1], reset_at)
    
    async def get_quota_status(
        self,
        service: RateLimitService,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Get current quota status.
        
        Returns:
            {
                "tokens_available": float,
                "capacity": int,
                "refill_rate": int,
                "utilization": float (0.0-1.0),
                "reset_at": float (timestamp)
            }
        """
        config = self.SERVICE_LIMITS.get(service)
        if not config:
            return {"error": "No limit configured"}
        
        key = self._get_key(service, user_id)
        now = time.time()
        
        try:
            if self.redis:
                state = await self.redis.hgetall(key)
                if not state:
                    return {
                        "tokens_available": config["capacity"],
                        "capacity": config["capacity"],
                        "refill_rate": config["refill_rate"],
                        "utilization": 0.0,
                        "reset_at": now
                    }
                
                tokens = float(state.get(b"tokens", config["capacity"]))
                last_refill = float(state.get(b"last_refill", now))
            else:
                state = self.local_cache.get(key, {
                    "tokens": config["capacity"],
                    "last_refill": now
                })
                tokens = state["tokens"]
                last_refill = state["last_refill"]
            
            # Apply refill
            time_passed = now - last_refill
            refill_amount = (time_passed / 60.0) * config["refill_rate"]
            tokens = min(config["capacity"], tokens + refill_amount)
            
            utilization = 1.0 - (tokens / config["capacity"])
            
            return {
                "tokens_available": tokens,
                "capacity": config["capacity"],
                "refill_rate": config["refill_rate"],
                "utilization": utilization,
                "reset_at": now + ((config["capacity"] - tokens) / config["refill_rate"]) * 60
            }
            
        except Exception as e:
            logger.error(f"Failed to get quota status: {e}")
            return {"error": str(e)}


class QuotaManager:
    """
    Manage user/tenant quotas (daily/weekly/monthly limits).
    
    Different from rate limiting - quotas are absolute caps over time periods.
    """
    
    def __init__(self, redis_client = None):
        """Initialize quota manager."""
        self.redis = redis_client
        self.local_cache = {}
    
    async def check_quota(
        self,
        user_id: str,
        quota_type: str,
        limit: int,
        period: str = "daily"
    ) -> bool:
        """
        Check if user is within quota.
        
        Args:
            user_id: User/tenant ID
            quota_type: Type of quota (emails_sent, api_calls, etc.)
            limit: Maximum allowed in period
            period: daily, weekly, monthly
        
        Returns:
            True if within quota
        """
        key = f"quota:{period}:{quota_type}:{user_id}"
        now = datetime.utcnow()
        
        # Determine period boundaries
        if period == "daily":
            period_key = now.strftime("%Y-%m-%d")
            ttl = 86400  # 24 hours
        elif period == "weekly":
            period_key = now.strftime("%Y-W%W")
            ttl = 604800  # 7 days
        elif period == "monthly":
            period_key = now.strftime("%Y-%m")
            ttl = 2592000  # 30 days
        else:
            raise ValueError(f"Invalid period: {period}")
        
        full_key = f"{key}:{period_key}"
        
        try:
            if self.redis:
                # Increment counter
                count = await self.redis.incr(full_key)
                if count == 1:
                    await self.redis.expire(full_key, ttl)
                
                return count <= limit
            else:
                # Local fallback
                if full_key not in self.local_cache:
                    self.local_cache[full_key] = {"count": 0, "expires": now + timedelta(seconds=ttl)}
                
                # Check expiry
                if self.local_cache[full_key]["expires"] < now:
                    self.local_cache[full_key] = {"count": 0, "expires": now + timedelta(seconds=ttl)}
                
                self.local_cache[full_key]["count"] += 1
                return self.local_cache[full_key]["count"] <= limit
                
        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            return True  # Fail open
    
    async def get_usage(
        self,
        user_id: str,
        quota_type: str,
        period: str = "daily"
    ) -> Dict:
        """
        Get current quota usage.
        
        Returns:
            {
                "used": int,
                "limit": int (if known),
                "remaining": int,
                "period": str,
                "resets_at": datetime
            }
        """
        # This would typically fetch limit from database/config
        # For now, return usage only
        key = f"quota:{period}:{quota_type}:{user_id}"
        now = datetime.utcnow()
        
        if period == "daily":
            period_key = now.strftime("%Y-%m-%d")
            resets_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        elif period == "weekly":
            period_key = now.strftime("%Y-W%W")
            resets_at = now + timedelta(days=(7 - now.weekday()))
        else:
            period_key = now.strftime("%Y-%m")
            resets_at = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        full_key = f"{key}:{period_key}"
        
        try:
            if self.redis:
                used = int(await self.redis.get(full_key) or 0)
            else:
                cache_data = self.local_cache.get(full_key, {"count": 0})
                used = cache_data["count"]
            
            return {
                "used": used,
                "period": period,
                "period_key": period_key,
                "resets_at": resets_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return {"error": str(e)}
