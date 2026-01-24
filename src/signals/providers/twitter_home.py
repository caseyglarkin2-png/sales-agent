"""Twitter Home Timeline Signal Provider - Personal feed monitoring via OAuth.

Polls authenticated user's home timeline for GTM-relevant signals.
Requires OAuth 1.0a authentication via /auth/twitter/login.

This extends the base SocialSignalProvider to add personal feed access.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.signals.base import SignalProvider, Signal
from src.signals.providers.social_signal import SocialSignalType
from src.routes.twitter_oauth import get_user_tokens
from src.logger import get_logger
from src.config import get_settings

import httpx
import hmac
import hashlib
import base64
import time
import urllib.parse
import secrets
import os

logger = get_logger(__name__)
settings = get_settings()


# GTM-relevant keywords for filtering home timeline
GTM_KEYWORDS = [
    # Sales
    "sales", "selling", "close", "deal", "pipeline", "quota", "revenue",
    "prospect", "lead", "outbound", "cold email", "follow up",
    # CRM/Tools
    "CRM", "HubSpot", "Salesforce", "Outreach", "Apollo", "ZoomInfo",
    # Strategy
    "GTM", "go-to-market", "growth", "scale", "startup", "SaaS", "B2B",
    "PLG", "product-led", "sales-led",
    # Industry
    "AI", "automation", "workflow", "integration", "API",
    # Success
    "booked", "closed", "won", "landed", "signed", "launched",
]


@dataclass 
class HomeTimelineTweet:
    """Parsed tweet from home timeline."""
    id: str
    text: str
    author_id: str
    author_username: str
    author_name: str
    created_at: datetime
    metrics: Dict[str, int]
    relevance_score: float
    matching_keywords: List[str]


class TwitterHomeProvider(SignalProvider):
    """Polls authenticated user's home timeline for GTM signals.
    
    Requires:
    - User to complete OAuth at /auth/twitter/login
    - TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET set
    
    Signal Generation:
    - High engagement (>100 likes) + GTM keywords = HIGH priority
    - From followed accounts + relevant = MEDIUM priority
    - General matching = LOW priority
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        min_relevance: float = 0.3,
    ):
        self.user_id = user_id
        self.keywords = keywords or GTM_KEYWORDS
        self.min_relevance = min_relevance
        self._last_poll: Optional[datetime] = None
        self._last_tweet_id: Optional[str] = None
    
    @property
    def source_name(self) -> str:
        return "twitter_home"
    
    @property
    def is_available(self) -> bool:
        """Check if OAuth is configured and user is authenticated."""
        consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
        if not consumer_key:
            return False
        
        # Check if any users are authenticated
        if self.user_id:
            tokens = get_user_tokens(self.user_id)
            return tokens is not None
        
        return True  # Provider is available, just needs user auth
    
    def set_user(self, user_id: str):
        """Set the user ID for fetching home timeline."""
        self.user_id = user_id
    
    async def poll_signals(self, since: Optional[datetime] = None) -> List[Signal]:
        """Poll home timeline for new signals.
        
        Args:
            since: Only get signals after this timestamp
            
        Returns:
            List of Signal objects for GTM-relevant tweets
        """
        if not self.user_id:
            logger.warning("No user_id set for TwitterHomeProvider")
            return []
        
        tokens = get_user_tokens(self.user_id)
        if not tokens:
            logger.warning(f"No OAuth tokens for user {self.user_id}")
            return []
        
        signals = []
        
        try:
            # Fetch home timeline
            tweets = await self._fetch_home_timeline(tokens, count=50)
            
            for tweet in tweets:
                # Calculate relevance
                relevance, matching = self._calculate_relevance(tweet["text"])
                
                if relevance >= self.min_relevance:
                    # Convert to signal
                    signal = self._tweet_to_signal(tweet, relevance, matching)
                    signals.append(signal)
            
            self._last_poll = datetime.utcnow()
            logger.info(f"Polled home timeline: {len(tweets)} tweets, {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"Error polling home timeline: {e}")
        
        return signals
    
    async def _fetch_home_timeline(
        self,
        tokens: Dict[str, str],
        count: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch home timeline using OAuth 1.0a."""
        consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
        consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("TWITTER_API_SECRET")
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Twitter OAuth credentials not configured")
        
        # Build OAuth params
        oauth_params = self._generate_oauth_params(
            consumer_key=consumer_key,
            token=tokens["access_token"]
        )
        
        # API URL
        url = f"https://api.twitter.com/2/users/{self.user_id}/timelines/reverse_chronological"
        
        query_params = {
            "max_results": min(count, 100),
            "tweet.fields": "created_at,public_metrics,entities,author_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        
        # Add since_id if we have it
        if self._last_tweet_id:
            query_params["since_id"] = self._last_tweet_id
        
        # Generate signature with all params
        all_params = {**oauth_params, **query_params}
        signature = self._generate_signature(
            method="GET",
            url=url,
            params=all_params,
            consumer_secret=consumer_secret,
            token_secret=tokens["access_token_secret"]
        )
        oauth_params["oauth_signature"] = signature
        
        # Build header
        auth_header = self._build_auth_header(oauth_params)
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"Authorization": auth_header},
                params=query_params
            )
            response.raise_for_status()
            data = response.json()
        
        tweets = data.get("data", [])
        
        # Track last tweet ID for pagination
        if tweets:
            self._last_tweet_id = tweets[0].get("id")
        
        # Merge user info
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        for tweet in tweets:
            author = users.get(tweet.get("author_id"), {})
            tweet["author_username"] = author.get("username", "unknown")
            tweet["author_name"] = author.get("name", "Unknown")
        
        return tweets
    
    def _calculate_relevance(self, text: str) -> tuple[float, List[str]]:
        """Calculate relevance score based on keyword matches.
        
        Returns:
            (score, matching_keywords) tuple
        """
        text_lower = text.lower()
        matching = []
        
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                matching.append(keyword)
        
        if not matching:
            return 0.0, []
        
        # Base score from keyword count
        score = min(1.0, len(matching) * 0.2)
        
        # Boost for high-value keywords
        high_value = ["closed", "won", "booked", "revenue", "deal", "signed"]
        if any(kw.lower() in [m.lower() for m in matching] for kw in high_value):
            score = min(1.0, score + 0.3)
        
        return score, matching
    
    def _tweet_to_signal(
        self,
        tweet: Dict[str, Any],
        relevance: float,
        matching_keywords: List[str]
    ) -> Signal:
        """Convert a tweet to a Signal object."""
        metrics = tweet.get("public_metrics", {})
        
        # Calculate priority based on engagement + relevance
        engagement = (
            metrics.get("like_count", 0) +
            metrics.get("retweet_count", 0) * 2 +
            metrics.get("reply_count", 0)
        )
        
        if engagement > 100 and relevance > 0.5:
            priority = "high"
        elif engagement > 20 or relevance > 0.4:
            priority = "medium"
        else:
            priority = "low"
        
        return Signal(
            id=f"twitter_home_{tweet['id']}",
            source="twitter_home",
            signal_type=SocialSignalType.MARKET_TREND.value,
            data={
                "tweet_id": tweet["id"],
                "text": tweet.get("text", ""),
                "author_id": tweet.get("author_id"),
                "author_username": tweet.get("author_username", "unknown"),
                "author_name": tweet.get("author_name", "Unknown"),
                "metrics": metrics,
                "relevance_score": relevance,
                "matching_keywords": matching_keywords,
                "priority": priority,
                "url": f"https://twitter.com/{tweet.get('author_username')}/status/{tweet['id']}",
            },
        )
    
    def _generate_oauth_params(
        self,
        consumer_key: str,
        token: str
    ) -> Dict[str, str]:
        """Generate base OAuth 1.0a parameters."""
        return {
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": token,
            "oauth_version": "1.0",
        }
    
    def _generate_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
        consumer_secret: str,
        token_secret: str
    ) -> str:
        """Generate OAuth 1.0a signature."""
        sorted_params = sorted(params.items())
        param_string = urllib.parse.urlencode(sorted_params, safe="")
        
        signature_base = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe="")
        ])
        
        signing_key = "&".join([
            urllib.parse.quote(consumer_secret, safe=""),
            urllib.parse.quote(token_secret, safe="")
        ])
        
        signature = hmac.new(
            signing_key.encode(),
            signature_base.encode(),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def _build_auth_header(self, params: Dict[str, str]) -> str:
        """Build OAuth Authorization header."""
        auth_parts = [
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(params.items())
            if k.startswith("oauth_")
        ]
        return "OAuth " + ", ".join(auth_parts)


# Singleton instance
_home_provider: Optional[TwitterHomeProvider] = None


def get_twitter_home_provider() -> TwitterHomeProvider:
    """Get singleton TwitterHomeProvider instance."""
    global _home_provider
    if _home_provider is None:
        _home_provider = TwitterHomeProvider()
    return _home_provider
