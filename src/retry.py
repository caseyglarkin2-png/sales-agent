"""Retry logic and error recovery for workflow execution."""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps

from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
)

# Specific configs for different operations
GMAIL_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=60.0,
)

HUBSPOT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
)

OPENAI_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=5.0,  # OpenAI rate limits need longer waits
    max_delay=120.0,
)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay."""
    delay = config.base_delay * (config.exponential_base ** attempt)
    return min(delay, config.max_delay)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    operation_name: str = "operation",
    **kwargs,
) -> T:
    """Execute an async function with retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: Retry configuration
        operation_name: Name for logging
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of func
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
            return result
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"{operation_name} failed after {config.max_retries + 1} attempts: {e}"
                )
    
    raise last_exception


def with_retry(
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    operation_name: Optional[str] = None,
):
    """Decorator to add retry logic to async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await retry_async(func, *args, config=config, operation_name=name, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = "half-open"
                    self.half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False
        
        if self.state == "half-open":
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record a successful call."""
        if self.state == "half-open":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
        else:
            self.failure_count = 0
    
    def record_failure(self, error: Exception):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == "half-open":
            self.state = "open"
            logger.warning(f"Circuit breaker opened again after failure in half-open: {error}")
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Global circuit breakers for external services
gmail_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=120.0)
hubspot_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
openai_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=300.0)


async def with_circuit_breaker(
    circuit: CircuitBreaker,
    func: Callable[..., T],
    *args,
    fallback: Optional[T] = None,
    **kwargs,
) -> T:
    """Execute function with circuit breaker protection.
    
    Args:
        circuit: Circuit breaker instance
        func: Async function to execute
        fallback: Value to return if circuit is open
        
    Returns:
        Result of func or fallback if circuit is open
    """
    if not circuit.can_execute():
        logger.warning(f"Circuit breaker is open, returning fallback")
        if fallback is not None:
            return fallback
        raise Exception("Circuit breaker is open")
    
    try:
        result = await func(*args, **kwargs)
        circuit.record_success()
        return result
    except Exception as e:
        circuit.record_failure(e)
        raise
