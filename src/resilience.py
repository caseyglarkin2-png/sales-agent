"""Retry logic and circuit breaker patterns."""
import asyncio
from typing import Any, Awaitable, Callable, Optional, TypeVar

from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and refusing requests."""
    pass


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """Initialize retry config."""
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> T:
    """Retry async function with exponential backoff."""
    if config is None:
        config = RetryConfig()

    last_error = None
    for attempt in range(config.max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < config.max_retries - 1:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s",
                    error=str(e),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {config.max_retries} attempts failed", error=str(e))

    raise last_error


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures.
    
    States:
    - closed: Normal operation, requests go through
    - open: Circuit tripped, requests fail fast without calling the service
    - half_open: Testing if service has recovered, allowing limited requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            name: Name for logging and identification
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def get_state(self) -> dict:
        """Return current circuit breaker state for monitoring."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }

    async def call(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' transitioning from open to half_open")
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.last_failure_time is None:
            return False
        elapsed = asyncio.get_event_loop().time() - self.last_failure_time
        return elapsed > self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        old_state = self.state
        self.failure_count = 0
        self.state = "closed"
        if old_state != "closed":
            logger.info(f"Circuit breaker '{self.name}' transitioned from {old_state} to closed")

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        if self.failure_count >= self.failure_threshold:
            old_state = self.state
            self.state = "open"
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures "
                f"(was: {old_state})"
            )
