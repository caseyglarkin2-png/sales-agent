"""Social/Twitter signal processor for CaseyOS command queue."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem
from src.services.signal_processors.base import SignalProcessor
from src.services.aps_calculator import calculate_aps
from src.logger import get_logger

logger = get_logger(__name__)


class SocialSignalProcessor(SignalProcessor):
    """
    Processes social media signals (Twitter/X) and creates actionable recommendations.
    
    Handles:
    - mention: Someone mentioned GTM-relevant topic in our feed
    - engagement: High-engagement post worth responding to
    - thought_leader: Post from a tracked thought leader
    - competitor_mention: Competitor mentioned in conversation
    """

    # Action type mappings for different social signal types
    ACTION_TYPES = {
        "mention": "social_engage",
        "engagement": "social_respond",
        "thought_leader": "thought_leader_engage",
        "competitor_mention": "competitive_intel",
    }

    # High-value keywords that increase priority
    HIGH_VALUE_KEYWORDS = [
        "looking for", "recommend", "anyone know",
        "help with", "pain point", "frustrated",
        "switching from", "alternative to",
        "budget for", "evaluating", "considering"
    ]

    @property
    def source_name(self) -> str:
        return "twitter"

    def can_handle(self, signal: Signal) -> bool:
        """Handle signals from Twitter/social source."""
        if signal.source != SignalSource.TWITTER:
            return False
        
        social_event_types = [
            "mention",
            "engagement", 
            "thought_leader",
            "competitor_mention",
            "gtm_opportunity",
            "tweet_relevant",
        ]
        return signal.event_type in social_event_types

    async def validate(self, signal: Signal) -> bool:
        """Validate social signal has required fields."""
        if not await super().validate(signal):
            return False
        
        payload = signal.payload
        
        # Must have tweet_id or equivalent
        if not payload.get("tweet_id") and not payload.get("post_id"):
            logger.warning(f"Signal {signal.id} missing tweet_id/post_id in payload")
            return False
        
        # Must have text content
        if not payload.get("text"):
            logger.warning(f"Signal {signal.id} missing text content")
            return False
        
        return True

    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process social signal and create engagement recommendation.
        
        Args:
            signal: Social/Twitter signal
            
        Returns:
            CommandQueueItem for engagement action, or None if invalid
        """
        if not self.can_handle(signal):
            return None
        
        if not await self.validate(signal):
            logger.warning(f"Invalid social signal {signal.id}, skipping")
            return None

        payload = signal.payload
        tweet_id = payload.get("tweet_id") or payload.get("post_id", "")
        author = payload.get("author", "")
        author_handle = payload.get("author_handle", "")
        text = payload.get("text", "")
        relevance_score = payload.get("relevance_score", 0.5)
        matching_keywords = payload.get("matching_keywords", [])
        engagement_count = payload.get("engagement_count", 0)
        is_thought_leader = payload.get("is_thought_leader", False)
        
        # Determine action type
        action_type = self._determine_action_type(signal.event_type, payload)
        
        # Calculate urgency based on recency and engagement
        urgency = self._calculate_urgency(payload)
        
        # Check for high-value keywords
        has_buying_signal = self._has_buying_signal(text)
        
        # Build context for the action
        action_context = {
            "tweet_id": tweet_id,
            "tweet_url": f"https://twitter.com/{author_handle}/status/{tweet_id}" if author_handle else "",
            "author": author,
            "author_handle": author_handle,
            "text": text[:500],  # Truncate long text
            "relevance_score": relevance_score,
            "matching_keywords": matching_keywords[:10],  # Top 10 keywords
            "engagement_count": engagement_count,
            "is_thought_leader": is_thought_leader,
            "has_buying_signal": has_buying_signal,
            "signal_id": signal.id,
            "source": "twitter_feed",
            "suggested_response": self._generate_response_hint(text, matching_keywords),
        }
        
        # Calculate APS
        strategic_value = 0.5
        if is_thought_leader:
            strategic_value = 0.9
        elif has_buying_signal:
            strategic_value = 0.8
        elif relevance_score > 0.7:
            strategic_value = 0.7
            
        aps_result = calculate_aps(
            action_type=action_type,
            context={
                "revenue_impact": 0.3 + (0.4 if has_buying_signal else 0),  # Social is lower revenue
                "urgency": urgency,
                "strategic_value": strategic_value,
                "effort": 0.2,  # Quick to engage on social
            }
        )
        
        # Social signals should be acted on quickly (24h)
        due_by = datetime.utcnow() + timedelta(hours=24)
        
        # Create the command queue item
        item = CommandQueueItem(
            id=str(uuid4()),
            priority_score=aps_result.score / 100.0,
            action_type=action_type,
            action_context=action_context,
            status="pending",
            owner="casey",
            due_by=due_by,
            recommendation_id=None,
            created_at=datetime.utcnow(),
        )
        
        logger.info(
            f"Created social recommendation for @{author_handle}: "
            f"{action_type} (APS: {aps_result.score}, keywords: {matching_keywords[:3]})"
        )
        
        return item

    def _determine_action_type(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Determine action type based on signal event type and content."""
        # Check for thought leader first
        if payload.get("is_thought_leader"):
            return "thought_leader_engage"
        
        # Check for competitor mentions
        text = payload.get("text", "").lower()
        competitor_keywords = ["competitor", "alternative", "switching", "vs", "compared"]
        if any(kw in text for kw in competitor_keywords):
            return "competitive_intel"
        
        # Use mapped action type or default
        return self.ACTION_TYPES.get(event_type, "social_engage")

    def _calculate_urgency(self, payload: Dict[str, Any]) -> float:
        """Calculate urgency based on engagement and recency."""
        urgency = 0.5  # Base urgency for social
        
        # High engagement = higher urgency
        engagement = payload.get("engagement_count", 0)
        if engagement > 100:
            urgency += 0.3
        elif engagement > 50:
            urgency += 0.2
        elif engagement > 10:
            urgency += 0.1
        
        # Thought leader posts are more urgent
        if payload.get("is_thought_leader"):
            urgency += 0.2
        
        # Cap at 1.0
        return min(urgency, 1.0)

    def _has_buying_signal(self, text: str) -> bool:
        """Check if text contains buying intent signals."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.HIGH_VALUE_KEYWORDS)

    def _generate_response_hint(self, text: str, keywords: list) -> str:
        """Generate a hint for responding to the tweet."""
        if not keywords:
            return "Engage authentically - add value to the conversation"
        
        # Map keywords to response types
        sales_keywords = {"sales", "crm", "pipeline", "revenue", "quota"}
        tech_keywords = {"automation", "ai", "integration", "api", "software"}
        problem_keywords = {"pain", "problem", "struggle", "challenge", "frustrated"}
        
        keyword_set = set(kw.lower() for kw in keywords)
        
        if keyword_set & problem_keywords:
            return "Empathize with the challenge - share a relevant insight or solution"
        elif keyword_set & sales_keywords:
            return "Share sales expertise - offer tactical advice or resource"
        elif keyword_set & tech_keywords:
            return "Technical engagement - share integration or automation insight"
        else:
            return "Add value to the conversation with relevant expertise"
