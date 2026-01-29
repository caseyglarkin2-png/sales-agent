"""
Unified retry utilities for connectors.

Provides a decorator for async functions with exponential backoff retry logic.
Consolidates patterns from gmail.py and grok.py.
"""

import asyncio
import functools
import random
from typing import Any, Callable, Optional, Set, TypeVar, Union
import httpx
from googleapiclient.errors import HttpError as GoogleHttpError

from src.logger import get_logger

logger = get_logger(__name__)

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])

# Default retryable HTTP status codes
DEFAULT_RETRYABLE_STATUSES: Set[int] = {429, 500, 502, 503, 504}

# Default configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds
DEFAULT_MAX_BACKOFF = 32.0  # seconds
DEFAULT_JITTER = 0.2  # ±20% jitter


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def _add_jitter(delay: float, jitter: float = DEFAULT_JITTER) -> float:
    """Add random jitter to delay to prevent thundering herd."""
    jitter_range = delay * jitter
    return delay + random.uniform(-jitter_range, jitter_range)


def _get_retry_after(
    response: Optional[httpx.Response] = None,
    google_error: Optional[GoogleHttpError] = None,
    default: float = DEFAULT_BACKOFF_BASE
) -> float:
    """Extract Retry-After value from response headers."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                # Could be HTTP date format, fall back to default
                pass
    return default


def _is_retryable_status(status_code: int, retryable_statuses: Set[int]) -> bool:
    """Check if HTTP status code is retryable."""
    return status_code in retryable_statuses


def _extract_status_code(error: Exception) -> Optional[int]:
    """Extract HTTP status code from various exception types."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code
    if isinstance(error, GoogleHttpError):
        return error.resp.status
    return None


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    max_backoff: float = DEFAULT_MAX_BACKOFF,
    retryable_statuses: Set[int] = DEFAULT_RETRYABLE_STATUSES,
    jitter: float = DEFAULT_JITTER,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator for async functions with exponential backoff retry.
    
    Supports both httpx and Google API client errors.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_base: Initial backoff delay in seconds (default: 1.0)
        max_backoff: Maximum backoff delay in seconds (default: 32.0)
        retryable_statuses: Set of HTTP status codes to retry (default: {429, 500, 502, 503, 504})
        jitter: Jitter factor for randomizing delays (default: 0.2 = ±20%)
        on_retry: Optional callback called on each retry with (attempt, error, delay)
    
    Returns:
        Decorated async function with retry logic
        
    Raises:
        RetryExhaustedError: When all retries are exhausted
        Original exception: For non-retryable errors
        
    Example:
        @with_retry(max_retries=3, backoff_base=1.0)
        async def fetch_data():
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None
            backoff = backoff_base
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)
                    
                except (httpx.HTTPStatusError, GoogleHttpError) as e:
                    status_code = _extract_status_code(e)
                    
                    if status_code and _is_retryable_status(status_code, retryable_statuses):
                        last_error = e
                        
                        if attempt >= max_retries:
                            # Exhausted all retries
                            break
                        
                        # Calculate delay with Retry-After header support
                        if isinstance(e, httpx.HTTPStatusError):
                            delay = _get_retry_after(response=e.response, default=backoff)
                        else:
                            delay = backoff
                        
                        # Add jitter
                        delay = _add_jitter(delay, jitter)
                        delay = min(delay, max_backoff)
                        
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            status_code=status_code,
                            delay_seconds=round(delay, 2),
                            error=str(e)[:200]
                        )
                        
                        if on_retry:
                            on_retry(attempt + 1, e, delay)
                        
                        await asyncio.sleep(delay)
                        backoff = min(backoff * 2, max_backoff)  # Exponential backoff
                        continue
                    else:
                        # Non-retryable error, re-raise immediately
                        logger.error(
                            "non_retryable_error",
                            function=func.__name__,
                            status_code=status_code,
                            error=str(e)[:200]
                        )
                        raise
                        
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    # Network errors are retryable
                    last_error = e
                    
                    if attempt >= max_retries:
                        break
                    
                    delay = _add_jitter(backoff, jitter)
                    delay = min(delay, max_backoff)
                    
                    logger.warning(
                        "retry_network_error",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error_type=type(e).__name__,
                        delay_seconds=round(delay, 2)
                    )
                    
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    
                    await asyncio.sleep(delay)
                    backoff = min(backoff * 2, max_backoff)
                    continue
            
            # All retries exhausted
            raise RetryExhaustedError(
                f"Retry exhausted after {max_retries + 1} attempts for {func.__name__}",
                attempts=max_retries + 1,
                last_error=last_error
            )
        
        return wrapper  # type: ignore
    
    return decorator


# Convenience decorators with common configurations
def with_standard_retry(func: F) -> F:
    """Standard retry decorator with default settings."""
    return with_retry()(func)


def with_aggressive_retry(func: F) -> F:
    """Aggressive retry for critical operations (5 retries, longer backoff)."""
    return with_retry(max_retries=5, backoff_base=2.0, max_backoff=60.0)(func)


def with_gentle_retry(func: F) -> F:
    """Gentle retry for non-critical operations (2 retries, short backoff)."""
    return with_retry(max_retries=2, backoff_base=0.5, max_backoff=4.0)(func)
