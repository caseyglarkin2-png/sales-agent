"""Slack Connector - Ingest internal team communications.

Uses slack-sdk (async) to fetch channel history and user info.
The "Comms Trove" for Deep Research context.
Sprint 67: Added retry for rate limiting
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional, TypeVar
import time
from datetime import datetime, timedelta
from functools import wraps

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")


def with_slack_retry(
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for Slack API calls with rate limit handling.
    
    The Slack SDK has built-in rate limiting, but this adds additional
    resilience for transient failures.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except SlackApiError as e:
                    last_error = e
                    error_code = e.response.get("error", "")
                    
                    # Retryable errors
                    if error_code in ("ratelimited", "service_unavailable", "internal_error"):
                        if attempt < max_retries:
                            # Check for Retry-After header
                            retry_after = int(e.response.headers.get("Retry-After", backoff_base * (2 ** attempt)))
                            logger.warning(
                                f"Slack API error {error_code}, retry {attempt + 1}/{max_retries} "
                                f"in {retry_after}s"
                            )
                            await asyncio.sleep(retry_after)
                            continue
                    # Non-retryable, re-raise
                    raise
            raise last_error
        return wrapper
    return decorator


class SlackConnector:
    """Connector for Slack API using AsyncWebClient."""

    def __init__(self, token: Optional[str] = None):
        """Initialize Slack connector."""
        self.token = token or settings.slack_bot_token
        if not self.token:
            logger.warning("SLACK_BOT_TOKEN not found. SlackConnector disabled.")
            self.client = None
        else:
            self.client = AsyncWebClient(token=self.token)

    async def health_check(self) -> Dict[str, Any]:
        """Check Slack API connectivity and return health status.
        
        Uses auth.test for a lightweight connectivity check.
        
        Returns:
            Dict with status, latency_ms, bot_name, and optional error
        """
        import time
        
        start_time = time.time()
        
        if not self.client:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "bot_name": None,
                "error": "Slack client not configured (missing token)",
            }
        
        try:
            response = await self._health_check_with_retry()
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "bot_name": response.get("user"),
                "team": response.get("team"),
                "error": None,
            }
        except SlackApiError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Slack health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "bot_name": None,
                "error": str(e.response.get("error", str(e))),
            }

    # Keep deprecated alias for backward compatibility
    async def get_health(self) -> Dict[str, Any]:
        """Deprecated: Use health_check() instead."""
        return await self.health_check()

    @with_slack_retry(max_retries=2, backoff_base=1.0)
    async def _health_check_with_retry(self) -> Dict[str, Any]:
        """Health check with retry - returns auth test response."""
        return await self.client.auth_test()

    @with_slack_retry(max_retries=3, backoff_base=1.0)
    async def fetch_channel_history(
        self, 
        channel_id: str, 
        days: int = 30,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversation history from a channel.
        
        Args:
            channel_id: Slack Channel ID (C123456)
            days: Lookback window
            limit: Max messages
            
        Returns:
            List of message objects (cleaned)
        """
        if not self.client:
            logger.error("Slack client not initialized")
            return []

        logger.info(f"Fetching Slack history for {channel_id} ({days} days)")
        
        oldest = datetime.now() - timedelta(days=days)
        oldest_ts = str(time.mktime(oldest.timetuple()))
        
        try:
            messages = []
            cursor = None
            
            while True:
                response = await self.client.conversations_history(
                    channel=channel_id,
                    oldest=oldest_ts,
                    limit=min(limit - len(messages), 200),
                    cursor=cursor
                )
                
                batch = response.get("messages", [])
                
                # Enrich with user names (could optimize by caching users)
                for msg in batch:
                    # Filter out join messages, etc if needed
                    if msg.get("subtype") in ["channel_join", "channel_leave"]:
                        continue
                        
                    messages.append({
                        "ts": msg.get("ts"),
                        "user": msg.get("user"),  # User ID, resolve later if needed
                        "text": msg.get("text"),
                        "thread_ts": msg.get("thread_ts"),
                        "reply_count": msg.get("reply_count", 0)
                    })
                
                if len(messages) >= limit or not response.get("has_more"):
                    break
                    
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            logger.info(f"Retrieved {len(messages)} Slack messages from {channel_id}")
            return messages
            
        except SlackApiError as e:
            logger.error(f"Slack API Error: {e.response['error']}")
            return []

    @with_slack_retry(max_retries=3, backoff_base=1.0)
    async def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
        """List accessible channels."""
        if not self.client:
            return []
            
        try:
            response = await self.client.conversations_list(types=types, limit=100)
            channels = response.get("channels", [])
            return [
                {"id": c["id"], "name": c["name"], "num_members": c["num_members"]} 
                for c in channels
            ]
        except SlackApiError as e:
            logger.error(f"Failed to list channels: {e}")
            return []
