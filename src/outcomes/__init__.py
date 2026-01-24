"""Outcome types and data structures for closed-loop learning.

Outcomes represent the results of actions taken from the Command Queue.
They feed back into APS scoring to improve future recommendations.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class OutcomeType(str, Enum):
    """Types of outcomes we track."""
    # Email outcomes
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    EMAIL_UNSUBSCRIBED = "email_unsubscribed"
    
    # Meeting outcomes
    MEETING_BOOKED = "meeting_booked"
    MEETING_HELD = "meeting_held"
    MEETING_NO_SHOW = "meeting_no_show"
    MEETING_RESCHEDULED = "meeting_rescheduled"
    
    # Deal outcomes
    DEAL_CREATED = "deal_created"
    DEAL_STAGE_ADVANCED = "deal_stage_advanced"
    DEAL_STAGE_REGRESSED = "deal_stage_regressed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    
    # Task outcomes
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    
    # General
    POSITIVE_RESPONSE = "positive_response"
    NEGATIVE_RESPONSE = "negative_response"
    NO_RESPONSE = "no_response"


class OutcomeSource(str, Enum):
    """Where the outcome was detected from."""
    GMAIL = "gmail"
    HUBSPOT = "hubspot"
    CALENDAR = "calendar"
    MANUAL = "manual"
    SYSTEM = "system"


class OutcomeRecord(BaseModel):
    """Record of an outcome linked to a queue item or action.
    
    Attributes:
        id: Unique outcome ID
        queue_item_id: The command queue item this outcome relates to
        action_id: The action execution ID (from idempotency key)
        outcome_type: Type of outcome (reply, meeting booked, etc.)
        source: Where the outcome was detected
        detected_at: When the outcome was detected
        context: Additional context about the outcome
        confidence: How confident we are (0-1) that this is correct
        impact_score: Impact on APS adjustment (-10 to +10)
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    queue_item_id: Optional[str] = None
    action_id: Optional[str] = None
    signal_id: Optional[str] = None
    
    outcome_type: OutcomeType
    source: OutcomeSource
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    contact_email: Optional[str] = None
    deal_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Scoring
    confidence: float = 1.0  # 0-1
    impact_score: float = 0.0  # -10 to +10, affects APS learning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "queue_item_id": self.queue_item_id,
            "action_id": self.action_id,
            "signal_id": self.signal_id,
            "outcome_type": self.outcome_type.value,
            "source": self.source.value,
            "detected_at": self.detected_at.isoformat(),
            "contact_email": self.contact_email,
            "deal_id": self.deal_id,
            "context": self.context,
            "confidence": self.confidence,
            "impact_score": self.impact_score,
        }


# Impact scores for different outcome types (for APS learning)
OUTCOME_IMPACT_SCORES = {
    # Positive outcomes (increase APS for similar actions)
    OutcomeType.EMAIL_REPLIED: 8.0,
    OutcomeType.MEETING_BOOKED: 10.0,
    OutcomeType.MEETING_HELD: 9.0,
    OutcomeType.DEAL_CREATED: 10.0,
    OutcomeType.DEAL_STAGE_ADVANCED: 7.0,
    OutcomeType.DEAL_WON: 10.0,
    OutcomeType.POSITIVE_RESPONSE: 6.0,
    OutcomeType.EMAIL_OPENED: 2.0,
    OutcomeType.EMAIL_CLICKED: 4.0,
    OutcomeType.TASK_COMPLETED: 3.0,
    
    # Neutral outcomes
    OutcomeType.EMAIL_SENT: 0.0,
    OutcomeType.MEETING_RESCHEDULED: 1.0,
    OutcomeType.NO_RESPONSE: -1.0,
    
    # Negative outcomes (decrease APS for similar actions)
    OutcomeType.EMAIL_BOUNCED: -5.0,
    OutcomeType.EMAIL_UNSUBSCRIBED: -8.0,
    OutcomeType.MEETING_NO_SHOW: -4.0,
    OutcomeType.DEAL_STAGE_REGRESSED: -5.0,
    OutcomeType.DEAL_LOST: -7.0,
    OutcomeType.NEGATIVE_RESPONSE: -6.0,
    OutcomeType.TASK_OVERDUE: -2.0,
}


def get_impact_score(outcome_type: OutcomeType) -> float:
    """Get the default impact score for an outcome type."""
    return OUTCOME_IMPACT_SCORES.get(outcome_type, 0.0)
