"""Form submission signal processor."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem
from src.services.signal_processors.base import SignalProcessor
from src.services.aps_calculator import calculate_aps
from src.logger import get_logger

logger = get_logger(__name__)


class FormSubmissionSignalProcessor(SignalProcessor):
    """
    Processes form submission signals and creates follow-up recommendations.
    
    Form submissions typically generate an 'email_follow_up' action type
    with high urgency (lead is hot).
    """

    @property
    def source_name(self) -> str:
        return "form"

    def can_handle(self, signal: Signal) -> bool:
        """Handle signals from form source with form_submitted event."""
        return (
            signal.source == SignalSource.FORM
            and signal.event_type == "form_submitted"
        )

    async def validate(self, signal: Signal) -> bool:
        """Validate form submission has required fields."""
        if not await super().validate(signal):
            return False
        
        payload = signal.payload
        # Must have at least an email
        if not payload.get("email"):
            logger.warning(f"Signal {signal.id} missing email in payload")
            return False
        
        return True

    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process form submission and create email follow-up recommendation.
        
        Args:
            signal: Form submission signal
            
        Returns:
            CommandQueueItem for email follow-up, or None if invalid
        """
        if not self.can_handle(signal):
            return None
        
        if not await self.validate(signal):
            logger.warning(f"Invalid form signal {signal.id}, skipping")
            return None

        payload = signal.payload
        email = payload.get("email", "")
        name = payload.get("name", "Unknown")
        company = payload.get("company", "Unknown Company")
        
        # Build context for the action
        action_context = {
            "lead_email": email,
            "lead_name": name,
            "lead_company": company,
            "signal_id": signal.id,
            "form_data": payload,
            "source": "form_submission",
        }
        
        # Calculate APS - form submissions are typically high urgency
        aps_result = calculate_aps(
            action_type="email_follow_up",
            context={
                "revenue_potential": payload.get("revenue_potential", 0.6),
                "urgency": 0.9,  # Hot lead - just submitted form
                "strategic_value": payload.get("strategic_value", 0.5),
                "effort_required": 0.2,  # Low effort - template email
            }
        )
        
        # Create the command queue item
        item = CommandQueueItem(
            id=str(uuid4()),
            priority_score=aps_result.score / 100.0,
            action_type="email_follow_up",
            action_context=action_context,
            status="pending",
            owner="casey",
            due_by=datetime.utcnow() + timedelta(hours=2),  # Respond within 2 hours
            recommendation_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        logger.info(
            f"Created email_follow_up recommendation for {email} "
            f"(APS: {aps_result.score}, signal: {signal.id})"
        )
        
        return item
