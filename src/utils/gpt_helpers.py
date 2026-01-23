"""Helper utilities for GPT-4 API calls with rate limiting.

Prevents API cost explosion by limiting calls per minute/hour.
"""

import time
import logging
from collections import deque
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Rate limit tracking (in-memory, per-process)
# Using deque for efficient FIFO operations
_rate_limit_calls: deque = deque(maxlen=1000)

# Configuration
_rate_limit_config = {
    "max_calls_per_minute": 10,
    "max_calls_per_hour": 100
}


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


def check_rate_limit(max_per_minute: int = 10, max_per_hour: int = 100) -> None:
    """Check if rate limit is exceeded, raise exception if so.
    
    Args:
        max_per_minute: Maximum calls allowed per minute
        max_per_hour: Maximum calls allowed per hour
        
    Raises:
        RateLimitExceeded: If rate limit threshold exceeded
    """
    now = time.time()
    
    # Calculate time windows
    minute_ago = now - 60
    hour_ago = now - 3600
    
    # Count recent calls
    recent_minute = [t for t in _rate_limit_calls if t > minute_ago]
    recent_hour = [t for t in _rate_limit_calls if t > hour_ago]
    
    # Check limits
    if len(recent_minute) >= max_per_minute:
        logger.warning(f"Rate limit exceeded: {len(recent_minute)} calls in last minute")
        raise RateLimitExceeded(
            f"Exceeded {max_per_minute} GPT-4 calls per minute. "
            f"Current: {len(recent_minute)}"
        )
    
    if len(recent_hour) >= max_per_hour:
        logger.warning(f"Rate limit exceeded: {len(recent_hour)} calls in last hour")
        raise RateLimitExceeded(
            f"Exceeded {max_per_hour} GPT-4 calls per hour. "
            f"Current: {len(recent_hour)}"
        )
    
    # Record this call
    _rate_limit_calls.append(now)
    logger.debug(f"Rate limit check passed. Calls in last minute: {len(recent_minute) + 1}")


def rate_limited_gpt4(func: Callable) -> Callable:
    """Decorator to enforce rate limiting on GPT-4 API calls.
    
    Usage:
        @rate_limited_gpt4
        async def my_gpt4_call():
            return await client.chat.completions.create(...)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        check_rate_limit(
            max_per_minute=_rate_limit_config["max_calls_per_minute"],
            max_per_hour=_rate_limit_config["max_calls_per_hour"]
        )
        return await func(*args, **kwargs)
    
    return wrapper


def get_rate_limit_status() -> dict:
    """Get current rate limit status for monitoring.
    
    Returns:
        dict: Status with calls in last minute/hour and remaining quota
    """
    now = time.time()
    minute_ago = now - 60
    hour_ago = now - 3600
    
    recent_minute = len([t for t in _rate_limit_calls if t > minute_ago])
    recent_hour = len([t for t in _rate_limit_calls if t > hour_ago])
    
    return {
        "calls_last_minute": recent_minute,
        "calls_last_hour": recent_hour,
        "limit_per_minute": _rate_limit_config["max_calls_per_minute"],
        "limit_per_hour": _rate_limit_config["max_calls_per_hour"],
        "remaining_minute": max(0, _rate_limit_config["max_calls_per_minute"] - recent_minute),
        "remaining_hour": max(0, _rate_limit_config["max_calls_per_hour"] - recent_hour),
        "total_calls": len(_rate_limit_calls)
    }


def reset_rate_limit() -> None:
    """Reset rate limit tracking. Use for testing only."""
    _rate_limit_calls.clear()
    logger.info("Rate limit tracking reset")
