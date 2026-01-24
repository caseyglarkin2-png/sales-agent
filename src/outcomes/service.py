"""Outcome tracking service for closed-loop learning.

This service:
1. Records outcomes from actions taken
2. Links outcomes to queue items and signals
3. Updates queue item outcome field
4. Feeds impact scores into APS learning
5. Provides outcome analytics
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.outcomes import (
    OutcomeRecord, 
    OutcomeType, 
    OutcomeSource,
    get_impact_score
)
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)

# In-memory store for outcomes (use database in production)
_outcomes: Dict[str, OutcomeRecord] = {}
_outcomes_by_queue_item: Dict[str, List[str]] = defaultdict(list)
_outcomes_by_contact: Dict[str, List[str]] = defaultdict(list)


class OutcomeService:
    """Service for recording and querying outcomes.
    
    Outcomes close the loop between actions and results, enabling:
    - Tracking what works (reply rates, conversion rates)
    - Improving APS scoring based on historical success
    - Identifying patterns in successful engagements
    """
    
    def __init__(self):
        """Initialize outcome service."""
        logger.info("OutcomeService initialized")
    
    async def record_outcome(
        self,
        outcome_type: OutcomeType,
        source: OutcomeSource,
        queue_item_id: Optional[str] = None,
        action_id: Optional[str] = None,
        signal_id: Optional[str] = None,
        contact_email: Optional[str] = None,
        deal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> OutcomeRecord:
        """Record a new outcome.
        
        Args:
            outcome_type: Type of outcome (reply, meeting booked, etc.)
            source: Where outcome was detected (gmail, hubspot, etc.)
            queue_item_id: Optional queue item this relates to
            action_id: Optional action ID (idempotency key)
            signal_id: Optional signal that triggered original action
            contact_email: Contact involved
            deal_id: Deal involved (if any)
            context: Additional context
            confidence: Confidence in detection (0-1)
            
        Returns:
            The recorded outcome
        """
        impact_score = get_impact_score(outcome_type)
        
        outcome = OutcomeRecord(
            queue_item_id=queue_item_id,
            action_id=action_id,
            signal_id=signal_id,
            outcome_type=outcome_type,
            source=source,
            contact_email=contact_email,
            deal_id=deal_id,
            context=context or {},
            confidence=confidence,
            impact_score=impact_score * confidence  # Scale by confidence
        )
        
        # Store in memory
        _outcomes[outcome.id] = outcome
        
        if queue_item_id:
            _outcomes_by_queue_item[queue_item_id].append(outcome.id)
        
        if contact_email:
            _outcomes_by_contact[contact_email].append(outcome.id)
        
        # Log event for telemetry
        log_event("outcome_recorded", {
            "outcome_id": outcome.id,
            "outcome_type": outcome_type.value,
            "source": source.value,
            "queue_item_id": queue_item_id,
            "contact_email": contact_email,
            "impact_score": outcome.impact_score
        })
        
        logger.info(
            f"Outcome recorded: {outcome_type.value} for {contact_email or 'unknown'}",
            extra={
                "outcome_id": outcome.id,
                "queue_item_id": queue_item_id,
                "impact_score": outcome.impact_score
            }
        )
        
        return outcome
    
    async def get_outcome(self, outcome_id: str) -> Optional[OutcomeRecord]:
        """Get an outcome by ID."""
        return _outcomes.get(outcome_id)
    
    async def get_outcomes_for_queue_item(self, queue_item_id: str) -> List[OutcomeRecord]:
        """Get all outcomes for a queue item."""
        outcome_ids = _outcomes_by_queue_item.get(queue_item_id, [])
        return [_outcomes[oid] for oid in outcome_ids if oid in _outcomes]
    
    async def get_outcomes_for_contact(self, contact_email: str) -> List[OutcomeRecord]:
        """Get all outcomes for a contact."""
        outcome_ids = _outcomes_by_contact.get(contact_email, [])
        return [_outcomes[oid] for oid in outcome_ids if oid in _outcomes]
    
    async def get_recent_outcomes(
        self, 
        limit: int = 50,
        outcome_type: Optional[OutcomeType] = None,
        source: Optional[OutcomeSource] = None
    ) -> List[OutcomeRecord]:
        """Get recent outcomes with optional filtering."""
        outcomes = list(_outcomes.values())
        
        # Filter by type
        if outcome_type:
            outcomes = [o for o in outcomes if o.outcome_type == outcome_type]
        
        # Filter by source
        if source:
            outcomes = [o for o in outcomes if o.source == source]
        
        # Sort by detected_at descending
        outcomes.sort(key=lambda o: o.detected_at, reverse=True)
        
        return outcomes[:limit]
    
    async def get_outcome_stats(
        self,
        days: int = 7,
        contact_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get outcome statistics for a time period.
        
        Returns aggregated stats useful for:
        - Understanding engagement rates
        - Identifying what's working
        - Feeding into APS learning
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Filter outcomes
        if contact_email:
            outcome_ids = _outcomes_by_contact.get(contact_email, [])
            outcomes = [_outcomes[oid] for oid in outcome_ids if oid in _outcomes]
        else:
            outcomes = list(_outcomes.values())
        
        # Filter by time
        outcomes = [o for o in outcomes if o.detected_at >= cutoff]
        
        # Aggregate by type
        by_type = defaultdict(int)
        total_impact = 0.0
        positive_count = 0
        negative_count = 0
        
        for o in outcomes:
            by_type[o.outcome_type.value] += 1
            total_impact += o.impact_score
            if o.impact_score > 0:
                positive_count += 1
            elif o.impact_score < 0:
                negative_count += 1
        
        # Calculate rates
        total = len(outcomes)
        reply_count = by_type.get(OutcomeType.EMAIL_REPLIED.value, 0)
        meeting_count = by_type.get(OutcomeType.MEETING_BOOKED.value, 0) + by_type.get(OutcomeType.MEETING_HELD.value, 0)
        sent_count = by_type.get(OutcomeType.EMAIL_SENT.value, 0) or 1  # Avoid div by zero
        
        return {
            "period_days": days,
            "total_outcomes": total,
            "by_type": dict(by_type),
            "positive_outcomes": positive_count,
            "negative_outcomes": negative_count,
            "net_impact": total_impact,
            "avg_impact": total_impact / max(total, 1),
            "reply_rate": reply_count / sent_count if sent_count else 0,
            "meeting_rate": meeting_count / sent_count if sent_count else 0,
        }
    
    async def calculate_contact_score_adjustment(
        self, 
        contact_email: str
    ) -> float:
        """Calculate APS adjustment based on contact's outcome history.
        
        Returns a score modifier (-20 to +20) based on:
        - Recent outcomes with this contact
        - Pattern of engagement
        - Time decay (recent outcomes weight more)
        """
        outcomes = await self.get_outcomes_for_contact(contact_email)
        if not outcomes:
            return 0.0
        
        # Calculate weighted impact with time decay
        now = datetime.utcnow()
        total_weighted_impact = 0.0
        total_weight = 0.0
        
        for outcome in outcomes:
            # Time decay: outcomes from today = 1.0, 7 days ago = 0.5, 30 days = 0.1
            days_ago = (now - outcome.detected_at).days
            time_weight = max(0.1, 1.0 - (days_ago / 30))
            
            weighted_impact = outcome.impact_score * time_weight
            total_weighted_impact += weighted_impact
            total_weight += time_weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize and cap
        adjustment = total_weighted_impact / total_weight
        return max(-20.0, min(20.0, adjustment))


# Global service instance
_service: Optional[OutcomeService] = None


def get_outcome_service() -> OutcomeService:
    """Get or create the global OutcomeService instance."""
    global _service
    if _service is None:
        _service = OutcomeService()
    return _service
