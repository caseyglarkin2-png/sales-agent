"""Social Signal Provider - Real-time social monitoring for CaseyOS signals.

Monitors:
- Twitter/X for industry trends and influencer activity
- LinkedIn (via webhooks/manual) for prospect engagement
- Generates signals for the command queue based on social activity
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.signals.base import SignalProvider, Signal
from src.connectors.twitter import get_twitter_connector, Tweet
from src.logger import get_logger

logger = get_logger(__name__)


class SocialSignalType(str, Enum):
    """Types of social signals."""
    INFLUENCER_MENTION = "influencer_mention"      # Credible voice mentioned relevant topic
    TREND_SPIKE = "trend_spike"                     # Topic trending
    PROSPECT_ENGAGEMENT = "prospect_engagement"     # Prospect engaged with our content
    COMPETITOR_MENTION = "competitor_mention"       # Competitor mentioned
    INDUSTRY_NEWS = "industry_news"                 # Breaking industry news
    MARKET_TREND = "market_trend"                   # Market trend detected


@dataclass
class SocialAlert:
    """An alert from social monitoring."""
    signal_type: SocialSignalType
    source: str  # "twitter", "linkedin"
    title: str
    summary: str
    author: str
    author_followers: int
    relevance_score: float
    url: Optional[str]
    raw_data: Dict[str, Any]
    created_at: datetime


class SocialSignalProvider(SignalProvider):
    """Provides signals from social media monitoring.
    
    Monitoring Rules:
    1. Influencer tweets about relevant topics → High priority signal
    2. Keywords spiking in conversation → Trend alert
    3. Competitor mentions with negative sentiment → Opportunity signal
    4. Industry news from credible sources → Awareness signal
    
    Signal Priority:
    - Influencer with >100k followers + relevant topic = HIGH
    - Trending topic + our keywords = MEDIUM
    - General industry chatter = LOW
    """
    
    # Keywords to monitor (would be configurable per user)
    DEFAULT_KEYWORDS = [
        "sales automation",
        "revenue operations",
        "GTM strategy",
        "sales enablement",
        "CRM",
        "sales intelligence",
        "account-based",
        "pipeline",
    ]
    
    # Competitor names to track
    DEFAULT_COMPETITORS = [
        "Outreach",
        "Salesloft",
        "Apollo",
        "ZoomInfo",
        "Gong",
        "Clari",
        "6sense",
    ]
    
    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
        monitored_accounts: Optional[List[str]] = None,
    ):
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.competitors = competitors or self.DEFAULT_COMPETITORS
        self.monitored_accounts = monitored_accounts or []
        self.twitter = get_twitter_connector()
        self._last_poll = None
    
    @property
    def source_name(self) -> str:
        return "social"
    
    @property
    def is_available(self) -> bool:
        """Check if any social connectors are available."""
        return self.twitter is not None and self.twitter.is_configured
    
    async def poll_signals(self, since: Optional[datetime] = None) -> List[Signal]:
        """Poll for new social signals.
        
        Args:
            since: Only get signals after this timestamp
            
        Returns:
            List of Signal objects ready for ingestion
        """
        if not self.is_available:
            logger.warning("No social connectors available")
            return []
        
        signals = []
        since_hours = 24
        
        if since:
            delta = datetime.utcnow() - since
            since_hours = max(1, int(delta.total_seconds() / 3600))
        
        # 1. Monitor credible voices for relevant content
        if self.twitter:
            influencer_signals = await self._poll_influencer_tweets(since_hours)
            signals.extend(influencer_signals)
        
        # 2. Track keyword mentions
        if self.twitter and self.keywords:
            keyword_signals = await self._poll_keyword_mentions(since_hours)
            signals.extend(keyword_signals)
        
        # 3. Track competitor mentions
        if self.twitter and self.competitors:
            competitor_signals = await self._poll_competitor_mentions(since_hours)
            signals.extend(competitor_signals)
        
        self._last_poll = datetime.utcnow()
        logger.info(f"Polled social signals: {len(signals)} found")
        
        # Sort by relevance
        signals.sort(key=lambda s: s.data.get("relevance_score", 0), reverse=True)
        
        return signals
    
    async def _poll_influencer_tweets(self, since_hours: int) -> List[Signal]:
        """Get tweets from monitored influencers."""
        signals = []
        
        try:
            tweets = await self.twitter.monitor_credible_voices(
                usernames=self.monitored_accounts or None,
                keywords=self.keywords,
                since_hours=since_hours,
            )
            
            for tweet in tweets:
                if tweet.relevance_score >= 0.5:  # Only high-relevance tweets
                    signal = self._tweet_to_signal(tweet, SocialSignalType.INFLUENCER_MENTION)
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error polling influencer tweets: {e}")
        
        return signals
    
    async def _poll_keyword_mentions(self, since_hours: int) -> List[Signal]:
        """Get tweets mentioning our keywords."""
        signals = []
        
        try:
            tweets = await self.twitter.track_keywords(
                keywords=self.keywords[:5],  # Limit to top 5 keywords
                min_followers=5000,
                since_hours=since_hours,
            )
            
            for tweet in tweets:
                if tweet.relevance_score >= 0.3:
                    signal = self._tweet_to_signal(tweet, SocialSignalType.MARKET_TREND)
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error polling keyword mentions: {e}")
        
        return signals
    
    async def _poll_competitor_mentions(self, since_hours: int) -> List[Signal]:
        """Get tweets mentioning competitors."""
        signals = []
        
        try:
            # Build competitor query
            query_parts = [f'"{c}"' for c in self.competitors[:3]]  # Top 3 competitors
            
            tweets = await self.twitter.search_recent_tweets(
                query=" OR ".join(query_parts) + " -is:retweet lang:en",
                max_results=20,
                since_hours=since_hours,
            )
            
            for tweet in tweets:
                # Check for negative sentiment (simple keyword check)
                negative_words = ["bad", "terrible", "hate", "awful", "worst", "issue", "problem", "frustrated"]
                has_negative = any(w in tweet.text.lower() for w in negative_words)
                
                if has_negative and tweet.relevance_score >= 0.2:
                    signal = self._tweet_to_signal(tweet, SocialSignalType.COMPETITOR_MENTION)
                    signal.data["sentiment"] = "negative"
                    signal.data["opportunity"] = True
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error polling competitor mentions: {e}")
        
        return signals
    
    def _tweet_to_signal(self, tweet: Tweet, signal_type: SocialSignalType) -> Signal:
        """Convert a Tweet to a Signal."""
        # Determine priority based on relevance and type
        if tweet.relevance_score >= 0.7 and signal_type == SocialSignalType.INFLUENCER_MENTION:
            priority = "high"
        elif tweet.relevance_score >= 0.5:
            priority = "medium"
        else:
            priority = "low"
        
        return Signal(
            source="twitter",
            signal_type=signal_type.value,
            data={
                "tweet_id": tweet.id,
                "text": tweet.text,
                "author": tweet.author_username,
                "author_name": tweet.author_name,
                "author_followers": tweet.metrics.get("follower_count", 0),
                "engagement": sum(tweet.metrics.values()),
                "relevance_score": tweet.relevance_score,
                "hashtags": tweet.hashtags,
                "urls": tweet.urls,
                "created_at": tweet.created_at.isoformat(),
                "priority": priority,
                "url": f"https://twitter.com/{tweet.author_username}/status/{tweet.id}",
            },
            processed=False,
        )
    
    def generate_alert(self, signal: Signal) -> Optional[SocialAlert]:
        """Convert a signal to a user-facing alert."""
        if signal.source != "twitter":
            return None
        
        data = signal.data
        signal_type = SocialSignalType(signal.signal_type)
        
        # Build title based on type
        if signal_type == SocialSignalType.INFLUENCER_MENTION:
            title = f"@{data['author']} tweeted about relevant topic"
        elif signal_type == SocialSignalType.COMPETITOR_MENTION:
            title = f"Competitor mention (negative sentiment)"
        elif signal_type == SocialSignalType.MARKET_TREND:
            title = f"Market trend: {data['hashtags'][0] if data['hashtags'] else 'relevant topic'}"
        else:
            title = f"Social activity detected"
        
        return SocialAlert(
            signal_type=signal_type,
            source="twitter",
            title=title,
            summary=data["text"][:200],
            author=f"@{data['author']}",
            author_followers=data.get("author_followers", 0),
            relevance_score=data["relevance_score"],
            url=data.get("url"),
            raw_data=data,
            created_at=datetime.fromisoformat(data["created_at"]),
        )


# Singleton
_social_signal_provider: Optional[SocialSignalProvider] = None


def get_social_signal_provider() -> SocialSignalProvider:
    """Get singleton social signal provider."""
    global _social_signal_provider
    if _social_signal_provider is None:
        _social_signal_provider = SocialSignalProvider()
    return _social_signal_provider
