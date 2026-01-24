"""Market Trend Monitor Agent - Tracks market trends from credible sources.

Responsibilities:
- Monitor tweets from industry thought leaders
- Detect trending topics relevant to GTM/sales
- Generate actionable insights from social signals
- Create command queue items for trend-based opportunities
- Use Grok AI for real-time market intelligence analysis
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.agents.base import BaseAgent
from src.connectors.twitter import get_twitter_connector, Tweet
from src.connectors.grok import get_grok, GrokConnector
from src.signals.providers.social_signal import get_social_signal_provider, SocialSignalType
from src.logger import get_logger

logger = get_logger(__name__)


class TrendCategory(str, Enum):
    """Categories of market trends."""
    TECHNOLOGY = "technology"
    MARKET_SHIFT = "market_shift"
    COMPETITOR = "competitor"
    INDUSTRY_NEWS = "industry_news"
    CUSTOMER_SENTIMENT = "customer_sentiment"
    FUNDING = "funding"
    HIRING = "hiring"


@dataclass
class TrendInsight:
    """An actionable insight from market trend analysis."""
    category: TrendCategory
    title: str
    summary: str
    sources: List[str]  # Tweet IDs or URLs
    relevance_score: float
    actionable: bool
    suggested_action: Optional[str]
    related_accounts: List[str]  # Prospect accounts this might affect
    created_at: datetime


class MarketTrendMonitorAgent(BaseAgent):
    """Monitors market trends and generates actionable insights.
    
    Monitoring Sources:
    1. Twitter thought leaders (investors, analysts, executives)
    2. Keyword tracking for industry terms
    3. Competitor mention analysis
    4. Funding/hiring announcements
    
    Insight Generation:
    - Detect topic clusters from multiple tweets
    - Score by engagement + source credibility
    - Generate suggested actions (outreach timing, talking points)
    - Link to relevant prospect accounts
    """
    
    # Industry thought leaders to monitor
    DEFAULT_THOUGHT_LEADERS = [
        # SaaS / Sales
        "jasonlk",          # Jason Lemkin - SaaStr
        "saborman",         # Gary Vaynerchuk
        "dharmesh",         # Dharmesh Shah - HubSpot
        "paborenstein",     # Peter Aborenstein
        "mariepokora",      # Sales thought leader
        
        # VCs / Investors
        "msuster",          # Mark Suster
        "hunterwalk",       # Hunter Walk
        "aileenlee",        # Aileen Lee
        "baboris",          # Boris Wertz
        "davemcclure",      # Dave McClure
        
        # Tech / Product
        "benedictevans",    # Benedict Evans
        "benthompson",      # Ben Thompson
        "kevinrose",        # Kevin Rose
    ]
    
    # Keywords indicating market trends
    TREND_KEYWORDS = [
        # Market conditions
        "market shift", "economic downturn", "growth opportunity",
        "market expansion", "consolidation",
        
        # Sales/GTM
        "sales automation", "revenue operations", "GTM strategy",
        "pipeline", "churn", "net retention", "expansion revenue",
        
        # Technology
        "AI sales", "GPT", "automation", "integration",
        
        # Funding/M&A
        "raised funding", "acquisition", "IPO", "layoffs",
    ]
    
    def __init__(self, connectors: Dict[str, Any] = None):
        super().__init__(
            name="MarketTrendMonitorAgent",
            description="Monitors market trends and generates actionable insights with Grok AI"
        )
        self.twitter = get_twitter_connector()
        self.social_provider = get_social_signal_provider()
        self.grok = get_grok()
        self.connectors = connectors or {}
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input based on action."""
        return True  # Most actions don't require specific input
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trend monitoring based on action."""
        action = context.get("action", "get_trends")
        
        if action == "get_trends":
            # Get current market trends
            since_hours = context.get("since_hours", 24)
            categories = context.get("categories")
            
            insights = await self._get_market_trends(since_hours, categories)
            
            return {
                "status": "success",
                "insights": [self._insight_to_dict(i) for i in insights],
                "total": len(insights),
                "since_hours": since_hours,
            }
        
        elif action == "monitor_topic":
            # Deep dive on a specific topic
            topic = context.get("topic")
            if not topic:
                return {"status": "error", "error": "topic required"}
            
            insights = await self._monitor_topic(topic)
            
            return {
                "status": "success",
                "topic": topic,
                "insights": [self._insight_to_dict(i) for i in insights],
            }
        
        elif action == "get_competitor_intel":
            # Get competitor-related insights
            competitors = context.get("competitors", [])
            
            insights = await self._get_competitor_intel(competitors)
            
            return {
                "status": "success",
                "insights": [self._insight_to_dict(i) for i in insights],
            }
        
        elif action == "get_funding_news":
            # Get funding/M&A news
            insights = await self._get_funding_news()
            
            return {
                "status": "success",
                "insights": [self._insight_to_dict(i) for i in insights],
            }
        
        elif action == "generate_talking_points":
            # Generate talking points from recent trends
            account = context.get("account")  # Optional: focus on specific account
            
            talking_points = await self._generate_talking_points(account)
            
            return {
                "status": "success",
                "talking_points": talking_points,
            }
        
        elif action == "configure_monitoring":
            # Configure what to monitor
            thought_leaders = context.get("thought_leaders")
            keywords = context.get("keywords")
            competitors = context.get("competitors")
            
            return {
                "status": "success",
                "configured": {
                    "thought_leaders": thought_leaders or self.DEFAULT_THOUGHT_LEADERS,
                    "keywords": keywords or self.TREND_KEYWORDS,
                    "competitors": competitors or [],
                },
            }
        
        elif action == "grok_market_intel":
            # Use Grok for real-time market intelligence
            topic = context.get("topic", "B2B sales automation")
            industry = context.get("industry", "SaaS")
            
            intel = await self._grok_market_intel(topic, industry)
            
            return {
                "status": "success",
                "topic": topic,
                "industry": industry,
                "intel": intel,
                "powered_by": "grok",
            }
        
        elif action == "grok_competitive_analysis":
            # Use Grok for competitive analysis
            company = context.get("company")
            if not company:
                return {"status": "error", "error": "company required"}
            
            competitors = context.get("competitors", [])
            analysis = await self._grok_competitive_analysis(company, competitors)
            
            return {
                "status": "success",
                "company": company,
                "analysis": analysis,
                "powered_by": "grok",
            }
        
        elif action == "grok_summarize_signals":
            # Use Grok to summarize social signals
            signals = context.get("signals", [])
            focus_topics = context.get("focus_topics", ["sales", "GTM"])
            
            summary = await self._grok_summarize_signals(signals, focus_topics)
            
            return {
                "status": "success",
                "summary": summary,
                "signal_count": len(signals),
                "powered_by": "grok",
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    async def _get_market_trends(
        self, 
        since_hours: int = 24,
        categories: Optional[List[str]] = None
    ) -> List[TrendInsight]:
        """Get market trends from the last N hours."""
        insights = []
        
        if not self.twitter or not self.twitter.is_configured:
            logger.warning("Twitter not configured, cannot get market trends")
            return insights
        
        # Get tweets from thought leaders
        tweets = await self.twitter.monitor_credible_voices(
            usernames=self.DEFAULT_THOUGHT_LEADERS,
            keywords=self.TREND_KEYWORDS,
            since_hours=since_hours,
        )
        
        # Cluster tweets by topic
        topic_clusters = self._cluster_tweets(tweets)
        
        # Convert clusters to insights
        for topic, cluster_tweets in topic_clusters.items():
            category = self._categorize_topic(topic)
            
            if categories and category.value not in categories:
                continue
            
            # Calculate aggregate relevance
            relevance = sum(t.relevance_score for t in cluster_tweets) / len(cluster_tweets)
            
            insight = TrendInsight(
                category=category,
                title=f"Trend: {topic}",
                summary=self._summarize_tweets(cluster_tweets),
                sources=[f"https://twitter.com/{t.author_username}/status/{t.id}" for t in cluster_tweets[:3]],
                relevance_score=relevance,
                actionable=relevance >= 0.5,
                suggested_action=self._suggest_action(category, topic, cluster_tweets),
                related_accounts=[],  # Would match against prospect list
                created_at=datetime.utcnow(),
            )
            insights.append(insight)
        
        # Sort by relevance
        insights.sort(key=lambda i: i.relevance_score, reverse=True)
        
        return insights
    
    async def _monitor_topic(self, topic: str) -> List[TrendInsight]:
        """Deep dive on a specific topic."""
        insights = []
        
        if not self.twitter:
            return insights
        
        # Search for topic
        tweets = await self.twitter.track_keywords(
            keywords=[topic],
            min_followers=1000,
            since_hours=48,
        )
        
        if not tweets:
            return insights
        
        # Create insight from tweets
        category = self._categorize_topic(topic)
        relevance = sum(t.relevance_score for t in tweets) / len(tweets)
        
        insight = TrendInsight(
            category=category,
            title=f"Topic Analysis: {topic}",
            summary=self._summarize_tweets(tweets),
            sources=[f"https://twitter.com/{t.author_username}/status/{t.id}" for t in tweets[:5]],
            relevance_score=relevance,
            actionable=True,
            suggested_action=f"Consider incorporating '{topic}' into outreach messaging",
            related_accounts=[],
            created_at=datetime.utcnow(),
        )
        insights.append(insight)
        
        return insights
    
    async def _get_competitor_intel(self, competitors: List[str]) -> List[TrendInsight]:
        """Get insights about competitors."""
        insights = []
        
        if not self.twitter or not competitors:
            return insights
        
        for competitor in competitors[:5]:  # Limit to 5
            tweets = await self.twitter.search_recent_tweets(
                query=f'"{competitor}" -is:retweet lang:en',
                max_results=20,
                since_hours=72,
            )
            
            if tweets:
                # Analyze sentiment (simple)
                negative_tweets = [t for t in tweets if self._has_negative_sentiment(t.text)]
                positive_tweets = [t for t in tweets if self._has_positive_sentiment(t.text)]
                
                summary_parts = [f"{len(tweets)} mentions of {competitor}"]
                if negative_tweets:
                    summary_parts.append(f"{len(negative_tweets)} negative")
                if positive_tweets:
                    summary_parts.append(f"{len(positive_tweets)} positive")
                
                insight = TrendInsight(
                    category=TrendCategory.COMPETITOR,
                    title=f"Competitor Intel: {competitor}",
                    summary=". ".join(summary_parts),
                    sources=[f"https://twitter.com/{t.author_username}/status/{t.id}" for t in tweets[:3]],
                    relevance_score=0.7 if negative_tweets else 0.4,
                    actionable=len(negative_tweets) > 0,
                    suggested_action=f"Negative sentiment around {competitor} - opportunity to reach out to frustrated users" if negative_tweets else None,
                    related_accounts=[],
                    created_at=datetime.utcnow(),
                )
                insights.append(insight)
        
        return insights
    
    async def _get_funding_news(self) -> List[TrendInsight]:
        """Get funding and M&A news."""
        insights = []
        
        if not self.twitter:
            return insights
        
        keywords = ["raised funding", "series A", "series B", "acquisition", "acquired by"]
        
        tweets = await self.twitter.track_keywords(
            keywords=keywords,
            min_followers=5000,
            since_hours=72,
        )
        
        for tweet in tweets[:10]:
            insight = TrendInsight(
                category=TrendCategory.FUNDING,
                title=f"Funding News: @{tweet.author_username}",
                summary=tweet.text[:200],
                sources=[f"https://twitter.com/{tweet.author_username}/status/{tweet.id}"],
                relevance_score=tweet.relevance_score,
                actionable=True,
                suggested_action="Companies with new funding often expand - good time for outreach",
                related_accounts=[],
                created_at=tweet.created_at,
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_talking_points(self, account: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate talking points from recent trends."""
        talking_points = []
        
        # Get recent trends
        insights = await self._get_market_trends(since_hours=48)
        
        for insight in insights[:5]:  # Top 5 trends
            talking_points.append({
                "topic": insight.title,
                "talking_point": f"I noticed there's been buzz around {insight.title.replace('Trend: ', '')}. {insight.summary[:100]}...",
                "source": insight.sources[0] if insight.sources else None,
                "use_case": "opening line" if insight.relevance_score > 0.6 else "supporting point",
            })
        
        return talking_points
    
    def _cluster_tweets(self, tweets: List[Tweet]) -> Dict[str, List[Tweet]]:
        """Cluster tweets by topic using simple keyword extraction."""
        clusters = {}
        
        for tweet in tweets:
            # Use hashtags as primary clustering
            for hashtag in tweet.hashtags:
                if hashtag not in clusters:
                    clusters[hashtag] = []
                clusters[hashtag].append(tweet)
            
            # Also cluster by matched keywords
            for keyword in self.TREND_KEYWORDS:
                if keyword.lower() in tweet.text.lower():
                    key = keyword.replace(" ", "_")
                    if key not in clusters:
                        clusters[key] = []
                    clusters[key].append(tweet)
        
        # Filter to clusters with 2+ tweets
        return {k: v for k, v in clusters.items() if len(v) >= 2}
    
    def _categorize_topic(self, topic: str) -> TrendCategory:
        """Categorize a topic into a trend category."""
        topic_lower = topic.lower()
        
        if any(k in topic_lower for k in ["ai", "gpt", "automation", "tech"]):
            return TrendCategory.TECHNOLOGY
        elif any(k in topic_lower for k in ["funding", "raised", "series", "ipo"]):
            return TrendCategory.FUNDING
        elif any(k in topic_lower for k in ["hiring", "layoff", "job"]):
            return TrendCategory.HIRING
        elif any(k in topic_lower for k in ["market", "growth", "downturn", "recession"]):
            return TrendCategory.MARKET_SHIFT
        else:
            return TrendCategory.INDUSTRY_NEWS
    
    def _summarize_tweets(self, tweets: List[Tweet]) -> str:
        """Generate a summary from multiple tweets."""
        if not tweets:
            return ""
        
        # Simple: use the highest-engagement tweet
        top_tweet = max(tweets, key=lambda t: sum(t.metrics.values()))
        return f"@{top_tweet.author_username}: {top_tweet.text[:150]}..."
    
    def _suggest_action(
        self, 
        category: TrendCategory, 
        topic: str, 
        tweets: List[Tweet]
    ) -> Optional[str]:
        """Suggest an action based on the trend."""
        if category == TrendCategory.TECHNOLOGY:
            return f"Update messaging to reference {topic} - it's trending in your market"
        elif category == TrendCategory.COMPETITOR:
            return f"Competitive opportunity: {topic} is generating discussion"
        elif category == TrendCategory.FUNDING:
            return "Companies with new funding are expanding - prioritize outreach"
        elif category == TrendCategory.MARKET_SHIFT:
            return f"Market shift detected: adjust positioning around {topic}"
        else:
            return f"Stay informed: {topic} is being discussed by thought leaders"
    
    def _has_negative_sentiment(self, text: str) -> bool:
        """Simple negative sentiment detection."""
        negative_words = ["bad", "terrible", "hate", "awful", "worst", "issue", 
                         "problem", "frustrated", "disappointing", "broken"]
        return any(w in text.lower() for w in negative_words)
    
    def _has_positive_sentiment(self, text: str) -> bool:
        """Simple positive sentiment detection."""
        positive_words = ["great", "love", "amazing", "best", "awesome", 
                         "excellent", "fantastic", "impressed", "recommend"]
        return any(w in text.lower() for w in positive_words)
    
    def _insight_to_dict(self, insight: TrendInsight) -> Dict[str, Any]:
        """Convert insight to dict."""
        return {
            "category": insight.category.value,
            "title": insight.title,
            "summary": insight.summary,
            "sources": insight.sources,
            "relevance_score": round(insight.relevance_score, 2),
            "actionable": insight.actionable,
            "suggested_action": insight.suggested_action,
            "related_accounts": insight.related_accounts,
            "created_at": insight.created_at.isoformat(),
        }

    # ==================== GROK AI METHODS ====================
    
    async def _grok_market_intel(self, topic: str, industry: str) -> Dict[str, Any]:
        """Use Grok for real-time market intelligence on a topic."""
        if not self.grok or not self.grok.is_configured:
            logger.warning("Grok not configured, returning basic intel")
            return {
                "summary": f"Market intel for {topic} in {industry}",
                "trends": [],
                "opportunities": [],
                "risks": [],
                "powered_by": "fallback",
            }
        
        try:
            # Use Grok's market intel capabilities
            result = await self.grok.analyze_market_intel(
                topic=topic,
                context={"industry": industry}
            )
            
            logger.info(f"Grok market intel retrieved for {topic}", extra={
                "topic": topic,
                "industry": industry,
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Grok market intel failed: {e}", exc_info=True)
            return {
                "summary": f"Unable to analyze {topic}",
                "error": str(e),
                "powered_by": "error",
            }
    
    async def _grok_competitive_analysis(
        self, 
        company: str, 
        competitors: List[str]
    ) -> Dict[str, Any]:
        """Use Grok for competitive analysis."""
        if not self.grok or not self.grok.is_configured:
            logger.warning("Grok not configured for competitive analysis")
            return {
                "company": company,
                "competitors": competitors,
                "analysis": "Grok not configured",
                "powered_by": "fallback",
            }
        
        try:
            # Use Grok's competitive insights
            result = await self.grok.get_competitive_insights(
                company=company,
                industry="",  # Let Grok infer
                competitors=competitors[:5]  # Limit to 5
            )
            
            logger.info(f"Grok competitive analysis for {company}", extra={
                "company": company,
                "competitor_count": len(competitors),
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Grok competitive analysis failed: {e}", exc_info=True)
            return {
                "company": company,
                "error": str(e),
                "powered_by": "error",
            }
    
    async def _grok_summarize_signals(
        self, 
        signals: List[Dict[str, Any]], 
        focus_topics: List[str]
    ) -> Dict[str, Any]:
        """Use Grok to summarize social signals."""
        if not self.grok or not self.grok.is_configured:
            logger.warning("Grok not configured for signal summarization")
            return {
                "summary": f"Received {len(signals)} signals",
                "key_themes": focus_topics,
                "powered_by": "fallback",
            }
        
        try:
            # Use Grok's summarization
            result = await self.grok.summarize_social_signals(
                signals=signals,
                focus_topics=focus_topics
            )
            
            logger.info(f"Grok summarized {len(signals)} signals", extra={
                "signal_count": len(signals),
                "focus_topics": focus_topics,
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Grok signal summarization failed: {e}", exc_info=True)
            return {
                "summary": f"Unable to summarize {len(signals)} signals",
                "error": str(e),
                "powered_by": "error",
            }

