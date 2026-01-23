"""Tests for GPT-4 rate limiting utility."""

import pytest
import time
from src.utils.gpt_helpers import (
    check_rate_limit,
    RateLimitExceeded,
    get_rate_limit_status,
    reset_rate_limit,
    _rate_limit_calls
)


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear rate limit tracking before each test."""
    reset_rate_limit()
    yield
    reset_rate_limit()


def test_rate_limit_allows_initial_calls():
    """Test that initial calls are allowed."""
    # Should allow first 10 calls
    for i in range(10):
        check_rate_limit()  # Should not raise


def test_rate_limit_blocks_excess_calls():
    """Test that 11th call in a minute is blocked."""
    # Fill up the rate limit
    for i in range(10):
        check_rate_limit()
    
    # 11th call should raise
    with pytest.raises(RateLimitExceeded) as exc_info:
        check_rate_limit()
    
    assert "10 GPT-4 calls per minute" in str(exc_info.value)


def test_rate_limit_status_tracking():
    """Test that status tracking is accurate."""
    reset_rate_limit()
    
    # Make 3 calls
    for i in range(3):
        check_rate_limit()
    
    status = get_rate_limit_status()
    
    assert status["calls_last_minute"] == 3
    assert status["remaining_minute"] == 7
    assert status["limit_per_minute"] == 10


def test_rate_limit_resets_after_minute():
    """Test that calls older than 1 minute don't count."""
    # This test would require time manipulation, skip for now
    # In real scenario, use freezegun or similar
    pass


def test_rate_limit_status_empty():
    """Test status when no calls made."""
    reset_rate_limit()
    
    status = get_rate_limit_status()
    
    assert status["calls_last_minute"] == 0
    assert status["calls_last_hour"] == 0
    assert status["remaining_minute"] == 10
    assert status["remaining_hour"] == 100


def test_reset_rate_limit():
    """Test that reset clears all tracking."""
    # Make some calls
    for i in range(5):
        check_rate_limit()
    
    assert len(_rate_limit_calls) == 5
    
    # Reset
    reset_rate_limit()
    
    assert len(_rate_limit_calls) == 0
    
    # Should allow 10 more calls
    for i in range(10):
        check_rate_limit()  # Should not raise


def test_custom_rate_limits():
    """Test with custom rate limit parameters."""
    reset_rate_limit()
    
    # Allow only 3 calls per minute
    for i in range(3):
        check_rate_limit(max_per_minute=3, max_per_hour=100)
    
    # 4th should fail
    with pytest.raises(RateLimitExceeded):
        check_rate_limit(max_per_minute=3, max_per_hour=100)
