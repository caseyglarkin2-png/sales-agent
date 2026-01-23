"""Rate limiting and quota management for operator mode."""
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import wraps
from fastapi import HTTPException

from src.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Enforce rate limits on email sending."""

    def __init__(
        self,
        max_emails_per_day: int = 20,
        max_emails_per_week: int = 2,
        max_emails_per_contact_per_week: int = 2,
    ):
        """Initialize rate limiter."""
        self.max_per_day = max_emails_per_day
        self.max_per_week = max_emails_per_week
        self.max_per_contact_per_week = max_emails_per_contact_per_week

        # Tracking: {key: [timestamps]}
        self.daily_sends: Dict[str, list] = {}
        self.weekly_sends: Dict[str, list] = {}
        self.contact_weekly_sends: Dict[str, list] = {}

        logger.info(
            f"Rate limiter initialized: {max_emails_per_day}/day, {max_emails_per_week}/week"
        )

    async def check_can_send(self, contact_email: str) -> tuple[bool, str]:
        """Check if email can be sent based on rate limits."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        # Check daily limit
        daily_key = f"day:{today}"
        self.daily_sends.setdefault(daily_key, [])
        if len(self.daily_sends[daily_key]) >= self.max_per_day:
            logger.warning(f"Daily limit reached for {today}")
            return False, f"Daily limit ({self.max_per_day}) reached"

        # Check weekly limit
        weekly_key = f"week:{week_start}"
        self.weekly_sends.setdefault(weekly_key, [])
        if len(self.weekly_sends[weekly_key]) >= self.max_per_week:
            logger.warning(f"Weekly limit reached for {week_start}")
            return False, f"Weekly limit ({self.max_per_week}) reached"

        # Check per-contact weekly limit
        contact_key = f"contact:{contact_email}:week:{week_start}"
        self.contact_weekly_sends.setdefault(contact_key, [])
        if len(self.contact_weekly_sends[contact_key]) >= self.max_per_contact_per_week:
            logger.warning(f"Contact limit reached for {contact_email}")
            return (
                False,
                f"Contact weekly limit ({self.max_per_contact_per_week}) reached",
            )

        return True, "OK"

    async def record_send(self, contact_email: str) -> None:
        """Record email send for rate limit tracking."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        daily_key = f"day:{today}"
        weekly_key = f"week:{week_start}"
        contact_key = f"contact:{contact_email}:week:{week_start}"

        self.daily_sends.setdefault(daily_key, []).append(now)
        self.weekly_sends.setdefault(weekly_key, []).append(now)
        self.contact_weekly_sends.setdefault(contact_key, []).append(now)

        logger.info(
            f"Send recorded: {contact_email}, daily={len(self.daily_sends[daily_key])}, "
            f"weekly={len(self.weekly_sends[weekly_key])}, contact_weekly={len(self.contact_weekly_sends[contact_key])}"
        )

    async def get_remaining_quota(self, contact_email: str) -> Dict[str, int]:
        """Get remaining quota for contact."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        daily_key = f"day:{today}"
        weekly_key = f"week:{week_start}"
        contact_key = f"contact:{contact_email}:week:{week_start}"

        return {
            "remaining_today": max(0, self.max_per_day - len(self.daily_sends.get(daily_key, []))),
            "remaining_this_week": max(0, self.max_per_week - len(self.weekly_sends.get(weekly_key, []))),
            "remaining_for_contact": max(
                0,
                self.max_per_contact_per_week
                - len(self.contact_weekly_sends.get(contact_key, [])),
            ),
        }


# Global rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        from src.config import get_settings
        settings = get_settings()
        _rate_limiter = RateLimiter(
            max_emails_per_day=settings.max_emails_per_day,
            max_emails_per_week=settings.max_emails_per_week,
        )
    return _rate_limiter


class EndpointRateLimiter:
    """Rate limit specific endpoints based on client IP or user ID."""

    def __init__(self):
        """Initialize endpoint rate limiter."""
        self.limits: Dict[str, list] = {}  # {key: [timestamps]}

    def check_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            max_requests: Max requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            (is_allowed, retry_after_seconds)
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        if key not in self.limits:
            self.limits[key] = []
        
        self.limits[key] = [t for t in self.limits[key] if t > cutoff]
        
        # Check limit
        if len(self.limits[key]) >= max_requests:
            # Calculate retry-after
            oldest = min(self.limits[key])
            retry_after = (oldest + timedelta(seconds=window_seconds) - now).total_seconds()
            return False, max(1, retry_after)
        
        # Add current request
        self.limits[key].append(now)
        return True, None

    def cleanup_old_keys(self, max_age_minutes: int = 60) -> None:
        """Remove old keys from memory."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        keys_to_remove = []
        
        for key, timestamps in self.limits.items():
            active_timestamps = [t for t in timestamps if t > cutoff]
            if not active_timestamps:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.limits[key]


# Global endpoint rate limiter
_endpoint_limiter: Optional[EndpointRateLimiter] = None


def get_endpoint_rate_limiter() -> EndpointRateLimiter:
    """Get or create global endpoint rate limiter."""
    global _endpoint_limiter
    if _endpoint_limiter is None:
        _endpoint_limiter = EndpointRateLimiter()
    return _endpoint_limiter


def rate_limit(max_requests: int, window_seconds: int):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        max_requests: Maximum requests allowed per client
        window_seconds: Time window in seconds
        
    Example:
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint(request: Request):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to find Request object in kwargs or args
            request = kwargs.get('http_request')
            
            if request is None:
                # Try to find it in args
                from fastapi import Request as FastAPIRequest
                for arg in args:
                    if isinstance(arg, FastAPIRequest):
                        request = arg
                        break
            
            # Apply rate limiting if we have a request
            if request:
                try:
                    client_ip = request.client.host if request.client else "unknown"
                    limiter = get_endpoint_rate_limiter()
                    allowed, retry_after = limiter.check_rate_limit(
                        key=f"{client_ip}:{func.__name__}",
                        max_requests=max_requests,
                        window_seconds=window_seconds,
                    )
                    
                    if not allowed:
                        logger.warning(
                            f"Rate limit exceeded for {client_ip} on {func.__name__}",
                            retry_after=retry_after,
                        )
                        raise HTTPException(
                            status_code=429,
                            detail="Too many requests",
                            headers={"Retry-After": str(int(retry_after))},
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Rate limiting error: {e}")
                    # Don't block requests on rate limiter errors
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
