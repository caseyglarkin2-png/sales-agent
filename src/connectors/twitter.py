"""Twitter/X Connector - Real-time social monitoring and engagement.

Uses Twitter API v2 for:
- Monitoring tweets from credible industry voices
- Tracking mentions and keywords
- Real-time trend detection
- Signal generation for CaseyOS command queue

API Docs: https://developer.twitter.com/en/docs/twitter-api
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import httpx

from src.logger import get_logger

logger = get_logger(__name__)


class TweetType(str, Enum):
    """Type of tweet for categorization."""
    MENTION = "mention"
    KEYWORD = "keyword"
    USER_TIMELINE = "user_timeline"
    TREND = "trend"


@dataclass
class Tweet:
    """Parsed tweet data."""
    id: str
    text: str
    author_id: str
    author_username: str
    author_name: str
    created_at: datetime
    tweet_type: TweetType
    metrics: Dict[str, int]  # likes, retweets, replies
    urls: List[str]
    hashtags: List[str]
    mentions: List[str]
    relevance_score: float  # Calculated based on engagement + source credibility


class TwitterConnector:
    """Connector for Twitter/X API v2.
    
    Required Environment Variables:
    - TWITTER_BEARER_TOKEN: OAuth 2.0 Bearer Token for API access
    - TWITTER_API_KEY: API Key (for user context operations)
    - TWITTER_API_SECRET: API Key Secret
    
    Rate Limits (Free tier):
    - 1,500 tweet lookups/month
    - 50 requests/15 min for search
    """
    
    BASE_URL = "https://api.twitter.com/2"
    
    # Credible voices to monitor (would be configurable)
    DEFAULT_MONITORED_ACCOUNTS = [
        "jason",       # Jason Lemkin (SaaS)
        "saborman",    # Gary Vee
        "aileenlee",   # Aileen Lee (Cowboy Ventures)
        "msuster",     # Mark Suster
        "benedictevans",  # Benedict Evans
        "hunterwalk",  # Hunter Walk
    ]
    
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            logger.warning("TWITTER_BEARER_TOKEN not configured - Twitter features disabled")
        
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        
        # Cache for user ID lookups
        self._user_cache: Dict[str, str] = {}
    
    @property
    def is_configured(self) -> bool:
        """Check if Twitter connector is properly configured."""
        return bool(self.bearer_token)
    
    async def search_recent_tweets(
        self,
        query: str,
        max_results: int = 10,
        since_hours: int = 24,
    ) -> List[Tweet]:
        """Search for recent tweets matching query.
        
        Args:
            query: Twitter search query (supports operators)
            max_results: Maximum tweets to return (10-100)
            since_hours: Look back this many hours
            
        Returns:
            List of parsed Tweet objects
        """
        if not self.is_configured:
            logger.warning("Twitter not configured, returning empty results")
            return []
        
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "start_time": since_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tweet.fields": "created_at,public_metrics,entities,author_id",
            "expansions": "author_id",
            "user.fields": "username,name,verified,public_metrics",
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/tweets/search/recent",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                
                tweets = self._parse_tweets(data, TweetType.KEYWORD)
                logger.info(f"Found {len(tweets)} tweets for query: {query[:50]}...")
                return tweets
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Twitter search error: {e.response.text}")
                return []
            except Exception as e:
                logger.error(f"Twitter search error: {e}")
                return []
    
    async def get_user_tweets(
        self,
        username: str,
        max_results: int = 10,
        since_hours: int = 24,
    ) -> List[Tweet]:
        """Get recent tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum tweets to return
            since_hours: Look back this many hours
            
        Returns:
            List of parsed Tweet objects
        """
        if not self.is_configured:
            return []
        
        # First, get user ID from username
        user_id = await self._get_user_id(username)
        if not user_id:
            return []
        
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        
        params = {
            "max_results": min(max_results, 100),
            "start_time": since_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tweet.fields": "created_at,public_metrics,entities",
            "exclude": "retweets,replies",  # Only original tweets
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/users/{user_id}/tweets",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                
                # Add user info to response for parsing
                data["includes"] = {"users": [{"id": user_id, "username": username, "name": username}]}
                
                tweets = self._parse_tweets(data, TweetType.USER_TIMELINE)
                return tweets
                
            except Exception as e:
                logger.error(f"Error getting tweets for @{username}: {e}")
                return []
    
    async def monitor_credible_voices(
        self,
        usernames: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        since_hours: int = 24,
    ) -> List[Tweet]:
        """Monitor tweets from credible industry voices.
        
        Args:
            usernames: List of usernames to monitor (uses defaults if None)
            keywords: Optional keywords to filter tweets
            since_hours: Look back this many hours
            
        Returns:
            List of relevant tweets sorted by relevance
        """
        if not self.is_configured:
            return []
        
        accounts = usernames or self.DEFAULT_MONITORED_ACCOUNTS
        all_tweets = []
        
        # Fetch tweets from each account
        for username in accounts:
            tweets = await self.get_user_tweets(username, max_results=20, since_hours=since_hours)
            all_tweets.extend(tweets)
            await asyncio.sleep(0.5)  # Rate limit protection
        
        # If keywords provided, filter tweets
        if keywords:
            keyword_lower = [k.lower() for k in keywords]
            all_tweets = [
                t for t in all_tweets
                if any(k in t.text.lower() for k in keyword_lower)
            ]
        
        # Sort by relevance score
        all_tweets.sort(key=lambda t: t.relevance_score, reverse=True)
        
        logger.info(f"Monitored {len(accounts)} accounts, found {len(all_tweets)} relevant tweets")
        return all_tweets
    
    async def track_keywords(
        self,
        keywords: List[str],
        exclude_retweets: bool = True,
        min_followers: int = 1000,
        since_hours: int = 24,
    ) -> List[Tweet]:
        """Track tweets containing specific keywords.
        
        Args:
            keywords: Keywords to track
            exclude_retweets: Whether to exclude retweets
            min_followers: Minimum follower count for authors
            since_hours: Look back this many hours
            
        Returns:
            List of matching tweets
        """
        if not self.is_configured:
            return []
        
        # Build query
        query_parts = [f'"{k}"' if " " in k else k for k in keywords]
        query = " OR ".join(query_parts)
        
        if exclude_retweets:
            query += " -is:retweet"
        
        # Add language filter for English
        query += " lang:en"
        
        tweets = await self.search_recent_tweets(query, max_results=50, since_hours=since_hours)
        
        # Filter by follower count would require additional API calls
        # For now, use engagement as proxy for credibility
        tweets = [t for t in tweets if t.metrics.get("like_count", 0) >= 5]
        
        return tweets
    
    async def get_trending_topics(
        self,
        woeid: int = 1  # 1 = Worldwide, 23424977 = US
    ) -> List[Dict[str, Any]]:
        """Get trending topics (requires elevated access).
        
        Note: This endpoint requires elevated API access.
        """
        if not self.is_configured:
            return []
        
        # Trends API requires v1.1 endpoint
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"https://api.twitter.com/1.1/trends/place.json",
                    headers=self.headers,
                    params={"id": woeid},
                )
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    trends = data[0].get("trends", [])
                    return [
                        {
                            "name": t.get("name"),
                            "url": t.get("url"),
                            "tweet_volume": t.get("tweet_volume"),
                        }
                        for t in trends[:20]
                    ]
                return []
                
            except Exception as e:
                logger.error(f"Error getting trends: {e}")
                return []
    
    async def _get_user_id(self, username: str) -> Optional[str]:
        """Get user ID from username."""
        if username in self._user_cache:
            return self._user_cache[username]
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/users/by/username/{username}",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                
                user_id = data.get("data", {}).get("id")
                if user_id:
                    self._user_cache[username] = user_id
                return user_id
                
            except Exception as e:
                logger.error(f"Error getting user ID for @{username}: {e}")
                return None
    
    def _parse_tweets(self, data: Dict[str, Any], tweet_type: TweetType) -> List[Tweet]:
        """Parse API response into Tweet objects."""
        tweets = []
        
        # Build user lookup
        users = {}
        for user in data.get("includes", {}).get("users", []):
            users[user.get("id")] = user
        
        for tweet_data in data.get("data", []):
            author_id = tweet_data.get("author_id", "")
            author = users.get(author_id, {})
            
            # Parse entities
            entities = tweet_data.get("entities", {})
            urls = [u.get("expanded_url", "") for u in entities.get("urls", [])]
            hashtags = [h.get("tag", "") for h in entities.get("hashtags", [])]
            mentions = [m.get("username", "") for m in entities.get("mentions", [])]
            
            # Parse metrics
            metrics = tweet_data.get("public_metrics", {})
            
            # Calculate relevance score
            relevance = self._calculate_relevance(metrics, author)
            
            # Parse timestamp
            created_str = tweet_data.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except:
                created_at = datetime.utcnow()
            
            tweet = Tweet(
                id=tweet_data.get("id", ""),
                text=tweet_data.get("text", ""),
                author_id=author_id,
                author_username=author.get("username", ""),
                author_name=author.get("name", ""),
                created_at=created_at,
                tweet_type=tweet_type,
                metrics={
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "quote_count": metrics.get("quote_count", 0),
                },
                urls=urls,
                hashtags=hashtags,
                mentions=mentions,
                relevance_score=relevance,
            )
            tweets.append(tweet)
        
        return tweets
    
    def _calculate_relevance(self, metrics: Dict, author: Dict) -> float:
        """Calculate tweet relevance score 0-1."""
        score = 0.0
        
        # Engagement metrics (0-0.5)
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        
        engagement = likes + (retweets * 2) + (replies * 1.5)
        if engagement > 1000:
            score += 0.5
        elif engagement > 100:
            score += 0.3
        elif engagement > 10:
            score += 0.1
        
        # Author credibility (0-0.5)
        author_metrics = author.get("public_metrics", {})
        followers = author_metrics.get("followers_count", 0)
        
        if followers > 100000:
            score += 0.5
        elif followers > 10000:
            score += 0.3
        elif followers > 1000:
            score += 0.1
        
        # Verified badge bonus
        if author.get("verified"):
            score += 0.1
        
        return min(score, 1.0)
    
    def to_signal(self, tweet: Tweet) -> Dict[str, Any]:
        """Convert a tweet to a CaseyOS signal."""
        return {
            "source": "twitter",
            "signal_type": f"tweet_{tweet.tweet_type.value}",
            "data": {
                "tweet_id": tweet.id,
                "text": tweet.text,
                "author_username": tweet.author_username,
                "author_name": tweet.author_name,
                "created_at": tweet.created_at.isoformat(),
                "metrics": tweet.metrics,
                "urls": tweet.urls,
                "hashtags": tweet.hashtags,
                "relevance_score": tweet.relevance_score,
            },
            "processed": False,
        }


# Singleton instance
_twitter_connector: Optional[TwitterConnector] = None


def get_twitter_connector() -> Optional[TwitterConnector]:
    """Get singleton Twitter connector."""
    global _twitter_connector
    if _twitter_connector is None:
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if bearer_token:
            _twitter_connector = TwitterConnector(bearer_token)
        else:
            logger.warning("TWITTER_BEARER_TOKEN not configured")
            return None
    return _twitter_connector
