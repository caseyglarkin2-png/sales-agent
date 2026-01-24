"""Outcome detection from external sources.

Detects outcomes automatically from:
- Gmail (reply detection)
- HubSpot (deal stage changes)
- Calendar (meeting outcomes)
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.outcomes import OutcomeRecord, OutcomeType, OutcomeSource
from src.outcomes.service import get_outcome_service
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


class OutcomeDetector:
    """Detects outcomes from external data sources.
    
    Works with:
    - Gmail: Detects replies to sent emails
    - HubSpot: Detects deal stage changes
    - Calendar: Detects meeting outcomes (held/no-show)
    """
    
    def __init__(self):
        """Initialize detector."""
        self.outcome_service = get_outcome_service()
    
    async def detect_gmail_reply(
        self,
        thread_id: str,
        from_email: str,
        to_email: str,
        subject: str,
        received_at: datetime,
        queue_item_id: Optional[str] = None,
        action_id: Optional[str] = None
    ) -> OutcomeRecord:
        """Detect and record a Gmail reply outcome.
        
        Called when we detect a reply in a thread we initiated.
        """
        # Analyze reply sentiment (simplified - could use LLM)
        outcome_type = OutcomeType.EMAIL_REPLIED
        
        context = {
            "thread_id": thread_id,
            "from_email": from_email,
            "to_email": to_email,
            "subject": subject,
            "received_at": received_at.isoformat()
        }
        
        outcome = await self.outcome_service.record_outcome(
            outcome_type=outcome_type,
            source=OutcomeSource.GMAIL,
            queue_item_id=queue_item_id,
            action_id=action_id,
            contact_email=from_email,
            context=context
        )
        
        logger.info(f"Gmail reply detected from {from_email}")
        return outcome
    
    async def detect_hubspot_deal_change(
        self,
        deal_id: str,
        old_stage: str,
        new_stage: str,
        deal_name: str,
        contact_email: Optional[str] = None,
        queue_item_id: Optional[str] = None
    ) -> OutcomeRecord:
        """Detect and record a HubSpot deal stage change.
        
        Determines if it's advancement, regression, or win/loss.
        """
        # Determine outcome type based on stage change
        # This is simplified - should map actual HubSpot stage order
        won_stages = ["closedwon", "closed won", "won"]
        lost_stages = ["closedlost", "closed lost", "lost"]
        
        new_stage_lower = new_stage.lower()
        old_stage_lower = old_stage.lower()
        
        if new_stage_lower in won_stages:
            outcome_type = OutcomeType.DEAL_WON
        elif new_stage_lower in lost_stages:
            outcome_type = OutcomeType.DEAL_LOST
        elif new_stage_lower > old_stage_lower:  # Simplified comparison
            outcome_type = OutcomeType.DEAL_STAGE_ADVANCED
        else:
            outcome_type = OutcomeType.DEAL_STAGE_REGRESSED
        
        context = {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "old_stage": old_stage,
            "new_stage": new_stage
        }
        
        outcome = await self.outcome_service.record_outcome(
            outcome_type=outcome_type,
            source=OutcomeSource.HUBSPOT,
            queue_item_id=queue_item_id,
            contact_email=contact_email,
            deal_id=deal_id,
            context=context
        )
        
        logger.info(f"HubSpot deal change: {deal_name} {old_stage} -> {new_stage}")
        return outcome
    
    async def detect_meeting_outcome(
        self,
        meeting_id: str,
        contact_email: str,
        scheduled_time: datetime,
        actual_outcome: str,  # "held", "no_show", "rescheduled", "cancelled"
        queue_item_id: Optional[str] = None
    ) -> OutcomeRecord:
        """Detect and record a meeting outcome."""
        outcome_map = {
            "held": OutcomeType.MEETING_HELD,
            "no_show": OutcomeType.MEETING_NO_SHOW,
            "rescheduled": OutcomeType.MEETING_RESCHEDULED,
            "booked": OutcomeType.MEETING_BOOKED,
        }
        
        outcome_type = outcome_map.get(actual_outcome.lower(), OutcomeType.MEETING_HELD)
        
        context = {
            "meeting_id": meeting_id,
            "scheduled_time": scheduled_time.isoformat(),
            "actual_outcome": actual_outcome
        }
        
        outcome = await self.outcome_service.record_outcome(
            outcome_type=outcome_type,
            source=OutcomeSource.CALENDAR,
            queue_item_id=queue_item_id,
            contact_email=contact_email,
            context=context
        )
        
        logger.info(f"Meeting outcome: {actual_outcome} with {contact_email}")
        return outcome
    
    async def detect_email_engagement(
        self,
        email_id: str,
        contact_email: str,
        event_type: str,  # "open", "click", "bounce", "unsubscribe"
        queue_item_id: Optional[str] = None
    ) -> OutcomeRecord:
        """Detect email engagement events (opens, clicks, etc.)."""
        event_map = {
            "open": OutcomeType.EMAIL_OPENED,
            "click": OutcomeType.EMAIL_CLICKED,
            "bounce": OutcomeType.EMAIL_BOUNCED,
            "unsubscribe": OutcomeType.EMAIL_UNSUBSCRIBED,
            "sent": OutcomeType.EMAIL_SENT,
        }
        
        outcome_type = event_map.get(event_type.lower(), OutcomeType.EMAIL_SENT)
        
        context = {
            "email_id": email_id,
            "event_type": event_type
        }
        
        outcome = await self.outcome_service.record_outcome(
            outcome_type=outcome_type,
            source=OutcomeSource.GMAIL,
            queue_item_id=queue_item_id,
            contact_email=contact_email,
            context=context
        )
        
        logger.info(f"Email engagement: {event_type} from {contact_email}")
        return outcome


# Global detector instance
_detector: Optional[OutcomeDetector] = None


def get_outcome_detector() -> OutcomeDetector:
    """Get or create the global OutcomeDetector instance."""
    global _detector
    if _detector is None:
        _detector = OutcomeDetector()
    return _detector
