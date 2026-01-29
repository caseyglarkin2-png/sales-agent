"""Tests for resilience module."""
import pytest
import asyncio

from src.resilience import RetryConfig, retry_with_backoff, CircuitBreaker


def test_retry_config_delay_calculation():
    """Test retry config delay calculation."""
    config = RetryConfig(initial_delay=1.0, max_delay=60.0)
    
    delay_0 = config.get_delay(0)
    delay_1 = config.get_delay(1)
    delay_2 = config.get_delay(2)
    
    assert delay_0 == 1.0
    assert delay_1 == 2.0
    assert delay_2 == 4.0


@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    """Test retry with backoff on success."""
    call_count = 0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not yet")
        return "success"
    
    result = await retry_with_backoff(failing_func)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    """Test retry with backoff when retries exhausted."""
    config = RetryConfig(max_retries=2, initial_delay=0.01)
    
    async def always_fails():
        raise ValueError("Always fails")
    
    with pytest.raises(ValueError):
        await retry_with_backoff(always_fails, config=config)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test circuit breaker opens after threshold failures."""
    from src.resilience import CircuitBreakerOpenError
    
    breaker = CircuitBreaker(failure_threshold=2)
    
    async def failing_func():
        raise ValueError("Fail")
    
    # First call: opens circuit after threshold
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    
    assert breaker.failure_count == 1
    
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    
    assert breaker.failure_count == 2
    assert breaker.state == "open"
    
    # Third call: circuit is open
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing_func)
