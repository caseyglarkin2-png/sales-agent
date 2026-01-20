"""Tests for rate limiting."""
import pytest

from src.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_initialization():
    """Test rate limiter initialization."""
    limiter = RateLimiter(max_emails_per_day=20, max_emails_per_week=2)
    assert limiter.max_per_day == 20
    assert limiter.max_per_week == 2


@pytest.mark.asyncio
async def test_rate_limiter_can_send():
    """Test checking if email can be sent."""
    limiter = RateLimiter(max_emails_per_day=2, max_emails_per_week=1)
    
    can_send, msg = await limiter.check_can_send("prospect@example.com")
    assert can_send is True
    assert msg == "OK"


@pytest.mark.asyncio
async def test_rate_limiter_daily_limit():
    """Test daily rate limit enforcement."""
    limiter = RateLimiter(max_emails_per_day=2, max_emails_per_week=10)
    
    # Send 2 emails (at limit)
    await limiter.record_send("prospect@example.com")
    await limiter.record_send("prospect2@example.com")
    
    # Try to send 3rd - should fail
    can_send, msg = await limiter.check_can_send("prospect3@example.com")
    assert can_send is False
    assert "Daily limit" in msg


@pytest.mark.asyncio
async def test_rate_limiter_weekly_limit():
    """Test weekly rate limit enforcement."""
    limiter = RateLimiter(max_emails_per_day=100, max_emails_per_week=1)
    
    can_send1, _ = await limiter.check_can_send("prospect@example.com")
    assert can_send1 is True
    await limiter.record_send("prospect@example.com")
    
    can_send2, msg = await limiter.check_can_send("prospect2@example.com")
    assert can_send2 is False
    assert "Weekly limit" in msg


@pytest.mark.asyncio
async def test_rate_limiter_get_quota():
    """Test getting remaining quota."""
    limiter = RateLimiter(max_emails_per_day=5, max_emails_per_week=3)
    
    await limiter.record_send("prospect@example.com")
    
    quota = await limiter.get_remaining_quota("prospect@example.com")
    assert quota["remaining_today"] == 4
    assert quota["remaining_this_week"] == 2
    assert quota["remaining_for_contact"] == 1
