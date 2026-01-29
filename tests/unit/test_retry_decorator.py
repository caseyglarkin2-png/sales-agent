"""
Tests for the unified retry decorator.

Sprint 67: Connector Resilience - Retry & Backoff
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.connectors.retry import (
    with_retry,
    with_standard_retry,
    with_aggressive_retry,
    with_gentle_retry,
    RetryExhaustedError,
    DEFAULT_RETRYABLE_STATUSES,
    _add_jitter,
    _get_retry_after,
    _is_retryable_status,
)


class TestRetryDecorator:
    """Test the @with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        """Test that 429 errors trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=3, backoff_base=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = MagicMock(spec=httpx.Response)
                response.status_code = 429
                response.headers = {}
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=MagicMock(),
                    response=response
                )
            return "success"
        
        result = await flaky_func()
        
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third
    
    @pytest.mark.asyncio
    async def test_retries_on_500(self):
        """Test that 500 errors trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=3, backoff_base=0.01)
        async def server_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = MagicMock(spec=httpx.Response)
                response.status_code = 500
                response.headers = {}
                raise httpx.HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=response
                )
            return "recovered"
        
        result = await server_error_func()
        
        assert result == "recovered"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_400(self):
        """Test that 400 errors don't trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=3, backoff_base=0.01)
        async def bad_request_func():
            nonlocal call_count
            call_count += 1
            response = MagicMock(spec=httpx.Response)
            response.status_code = 400
            response.headers = {}
            raise httpx.HTTPStatusError(
                "Bad request",
                request=MagicMock(),
                response=response
            )
        
        with pytest.raises(httpx.HTTPStatusError):
            await bad_request_func()
        
        assert call_count == 1  # No retries for 400
    
    @pytest.mark.asyncio
    async def test_no_retry_on_401(self):
        """Test that 401 errors don't trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=3, backoff_base=0.01)
        async def unauthorized_func():
            nonlocal call_count
            call_count += 1
            response = MagicMock(spec=httpx.Response)
            response.status_code = 401
            response.headers = {}
            raise httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=response
            )
        
        with pytest.raises(httpx.HTTPStatusError):
            await unauthorized_func()
        
        assert call_count == 1  # No retries for 401
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Test that exhausted retries raise RetryExhaustedError."""
        call_count = 0
        
        @with_retry(max_retries=2, backoff_base=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            response = MagicMock(spec=httpx.Response)
            response.status_code = 503
            response.headers = {}
            raise httpx.HTTPStatusError(
                "Service unavailable",
                request=MagicMock(),
                response=response
            )
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_fails()
        
        assert call_count == 3  # Initial + 2 retries
        assert exc_info.value.attempts == 3
        assert exc_info.value.last_error is not None
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        delays = []
        
        @with_retry(max_retries=3, backoff_base=1.0, jitter=0)
        async def track_delays():
            response = MagicMock(spec=httpx.Response)
            response.status_code = 429
            response.headers = {}
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=MagicMock(),
                response=response
            )
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)
            
            with pytest.raises(RetryExhaustedError):
                await track_delays()
        
        # Verify exponential pattern: 1, 2, 4 (or close due to jitter)
        assert len(delays) == 3
        assert delays[0] <= 1.5  # ~1s with jitter
        assert delays[1] <= 3.0  # ~2s with jitter
        assert delays[2] <= 5.0  # ~4s with jitter
    
    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        """Test that Retry-After header is respected."""
        @with_retry(max_retries=1, backoff_base=1.0, jitter=0)
        async def rate_limited_with_header():
            response = MagicMock(spec=httpx.Response)
            response.status_code = 429
            response.headers = {"Retry-After": "5"}
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=MagicMock(),
                response=response
            )
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(RetryExhaustedError):
                await rate_limited_with_header()
            
            # Should use Retry-After value (5s) instead of backoff_base
            assert mock_sleep.call_count == 1
            called_delay = mock_sleep.call_args[0][0]
            assert 4.0 <= called_delay <= 6.0  # ~5s with jitter
    
    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self):
        """Test that connection errors trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=2, backoff_base=0.01)
        async def connection_fails_then_works():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return "connected"
        
        result = await connection_fails_then_works()
        
        assert result == "connected"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        """Test that timeout errors trigger retries."""
        call_count = 0
        
        @with_retry(max_retries=2, backoff_base=0.01)
        async def timeout_then_works():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return "completed"
        
        result = await timeout_then_works()
        
        assert result == "completed"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        retry_calls = []
        
        def track_retry(attempt, error, delay):
            retry_calls.append((attempt, type(error).__name__, delay))
        
        @with_retry(max_retries=2, backoff_base=0.01, on_retry=track_retry)
        async def fails_twice():
            if len(retry_calls) < 2:
                response = MagicMock(spec=httpx.Response)
                response.status_code = 502
                response.headers = {}
                raise httpx.HTTPStatusError(
                    "Bad gateway",
                    request=MagicMock(),
                    response=response
                )
            return "success"
        
        result = await fails_twice()
        
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0][0] == 1  # First retry
        assert retry_calls[1][0] == 2  # Second retry
        assert retry_calls[0][1] == "HTTPStatusError"


class TestConvenienceDecorators:
    """Test convenience retry decorators."""
    
    @pytest.mark.asyncio
    async def test_standard_retry(self):
        """Test @with_standard_retry uses default settings."""
        call_count = 0
        
        @with_standard_retry
        async def func():
            nonlocal call_count
            call_count += 1
            return "ok"
        
        result = await func()
        assert result == "ok"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_aggressive_retry_has_more_retries(self):
        """Test @with_aggressive_retry allows 5 retries."""
        call_count = 0
        
        @with_aggressive_retry
        async def fails_many_times():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise httpx.ConnectError("Network error")
            return "success after many tries"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await fails_many_times()
        
        assert result == "success after many tries"
        assert call_count == 5
    
    @pytest.mark.asyncio
    async def test_gentle_retry_limits_retries(self):
        """Test @with_gentle_retry only allows 2 retries."""
        call_count = 0
        
        @with_gentle_retry
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Network error")
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RetryExhaustedError):
                await always_fails()
        
        assert call_count == 3  # Initial + 2 retries


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_add_jitter_within_range(self):
        """Test that jitter is within expected range."""
        base_delay = 10.0
        jitter = 0.2  # ±20%
        
        # Run multiple times to verify randomness
        for _ in range(100):
            result = _add_jitter(base_delay, jitter)
            assert 8.0 <= result <= 12.0  # ±20% of 10
    
    def test_get_retry_after_from_header(self):
        """Test extraction of Retry-After header."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "30"}
        
        result = _get_retry_after(response=response, default=5.0)
        assert result == 30.0
    
    def test_get_retry_after_missing_header(self):
        """Test fallback when Retry-After is missing."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}
        
        result = _get_retry_after(response=response, default=5.0)
        assert result == 5.0
    
    def test_is_retryable_status(self):
        """Test status code classification."""
        retryable = DEFAULT_RETRYABLE_STATUSES
        
        assert _is_retryable_status(429, retryable) is True
        assert _is_retryable_status(500, retryable) is True
        assert _is_retryable_status(502, retryable) is True
        assert _is_retryable_status(503, retryable) is True
        assert _is_retryable_status(504, retryable) is True
        
        assert _is_retryable_status(200, retryable) is False
        assert _is_retryable_status(400, retryable) is False
        assert _is_retryable_status(401, retryable) is False
        assert _is_retryable_status(403, retryable) is False
        assert _is_retryable_status(404, retryable) is False
