"""Circuit Breaker Pattern Implementation.

Prevents cascading failures by stopping calls to failing external services.
"""

from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from enum import Enum
import asyncio
from functools import wraps

from src.logger import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Failing, all requests blocked (fast fail)
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before entering HALF_OPEN
        success_threshold: Successes needed to close from HALF_OPEN
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout: float = 30.0,
    ):
        """Initialize circuit breaker."""
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        
        # Stats
        self.total_calls = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_rejections = 0
        
        logger.info(
            f"Circuit breaker '{name}' initialized",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            asyncio.TimeoutError: If function times out
        """
        self.total_calls += 1
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_recovery():
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                self.total_rejections += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service will be retried in {self._time_until_retry()} seconds."
                )
        
        # Attempt the call
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
            
            # Success
            self._on_success()
            return result
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Circuit breaker '{self.name}' timeout",
                timeout=self.timeout,
            )
            self._on_failure()
            raise
            
        except Exception as e:
            logger.error(
                f"Circuit breaker '{self.name}' failure",
                error=str(e),
            )
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.total_successes += 1
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # Close circuit if enough successes
            if self.success_count >= self.success_threshold:
                logger.info(
                    f"Circuit breaker '{self.name}' closing (service recovered)",
                    consecutive_successes=self.success_count,
                )
                self.state = CircuitState.CLOSED
                self.opened_at = None
    
    def _on_failure(self):
        """Handle failed call."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        # Open circuit if threshold exceeded
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}' opening (threshold exceeded)",
                    consecutive_failures=self.failure_count,
                    threshold=self.failure_threshold,
                )
                self.state = CircuitState.OPEN
                self.opened_at = datetime.utcnow()
        
        # Return to OPEN if HALF_OPEN test fails
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"Circuit breaker '{self.name}' returning to OPEN (recovery failed)"
            )
            self.state = CircuitState.OPEN
            self.opened_at = datetime.utcnow()
            self.success_count = 0
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.opened_at:
            return True
        
        elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _time_until_retry(self) -> float:
        """Get seconds until next retry attempt."""
        if not self.opened_at:
            return 0
        
        elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
        remaining = max(0, self.recovery_timeout - elapsed)
        return round(remaining, 1)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        success_rate = (
            (self.total_successes / self.total_calls * 100)
            if self.total_calls > 0
            else 0
        )
        
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_rejections": self.total_rejections,
            "success_rate": round(success_rate, 2),
            "consecutive_failures": self.failure_count,
            "consecutive_successes": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else None,
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None


# Global circuit breakers for external services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: float = 30.0,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker for a service.
    
    Args:
        name: Service name (e.g., "hubspot_api", "openai_api")
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before retry
        success_threshold: Successes to close
        timeout: Request timeout
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout,
        )
    
    return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: float = 30.0,
):
    """
    Decorator for circuit breaker pattern.
    
    Args:
        name: Service name
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
        success_threshold: Successes needed to close circuit
        timeout: Request timeout in seconds
        
    Example:
        @circuit_breaker("hubspot_api", failure_threshold=3, recovery_timeout=30)
        async def call_hubspot_api():
            # ... API call ...
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                timeout=timeout,
            )
            
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return {
        name: breaker.get_stats()
        for name, breaker in _circuit_breakers.items()
    }


def reset_all_circuit_breakers():
    """Reset all circuit breakers (admin function)."""
    for breaker in _circuit_breakers.values():
        breaker.reset()
    
    logger.info("All circuit breakers reset")
