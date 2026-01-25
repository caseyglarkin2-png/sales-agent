"""Slack Connector - Ingest internal team communications.

Uses slack-sdk (async) to fetch channel history and user info.
The "Comms Trove" for Deep Research context.
"""
from typing import Any, Dict, List, Optional
import time
from datetime import datetime, timedelta

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


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

    async def get_health(self) -> Dict[str, Any]:
        """Check connection health."""
        if not self.client:
            return {"status": "disabled", "error": "Missing token"}
        
        try:
            await self.client.auth_test()
            return {"status": "healthy"}
        except SlackApiError as e:
            return {"status": "error", "error": str(e)}

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
