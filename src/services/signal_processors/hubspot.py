"""HubSpot deal signal processor."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem
from src.services.signal_processors.base import SignalProcessor
from src.services.aps_calculator import calculate_aps
from src.logger import get_logger

logger = get_logger(__name__)


# Deal stage to urgency mapping
DEAL_STAGE_URGENCY = {
    "appointmentscheduled": 0.9,
    "qualifiedtobuy": 0.8,
    "presentationscheduled": 0.85,
    "decisionmakerboughtin": 0.9,
    "contractsent": 0.95,
    "closedwon": 0.3,  # Lower urgency - won already
    "closedlost": 0.1,  # Low urgency
}

# Action type mapping based on deal stage
DEAL_STAGE_ACTION = {
    "appointmentscheduled": "meeting_prep",
    "qualifiedtobuy": "email_follow_up",
    "presentationscheduled": "presentation_prep",
    "decisionmakerboughtin": "proposal_send",
    "contractsent": "contract_follow_up",
    "closedwon": "onboarding_kickoff",
    "closedlost": "win_loss_analysis",
}


class HubSpotDealSignalProcessor(SignalProcessor):
    """
    Processes HubSpot deal signals and creates appropriate recommendations.
    
    Handles:
    - deal_stage_changed: When a deal moves to a new stage
    - deal_created: New deal created
    - deal_amount_changed: Deal value updated
    """

    @property
    def source_name(self) -> str:
        return "hubspot"

    def can_handle(self, signal: Signal) -> bool:
        """Handle signals from HubSpot source with deal event types."""
        if signal.source != SignalSource.HUBSPOT:
            return False
        
        deal_event_types = [
            "deal_stage_changed",
            "deal_created",
            "deal_amount_changed",
        ]
        return signal.event_type in deal_event_types

    async def validate(self, signal: Signal) -> bool:
        """Validate deal signal has required fields."""
        if not await super().validate(signal):
            return False
        
        payload = signal.payload
        
        # Must have deal_id
        if not payload.get("deal_id"):
            logger.warning(f"Signal {signal.id} missing deal_id in payload")
            return False
        
        # Must have deal_name
        if not payload.get("deal_name"):
            logger.warning(f"Signal {signal.id} missing deal_name in payload")
            return False
        
        return True

    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process HubSpot deal signal and create appropriate recommendation.
        
        Args:
            signal: HubSpot deal signal
            
        Returns:
            CommandQueueItem for the recommended action, or None if invalid
        """
        if not self.can_handle(signal):
            return None
        
        if not await self.validate(signal):
            logger.warning(f"Invalid HubSpot deal signal {signal.id}, skipping")
            return None

        payload = signal.payload
        deal_id = payload.get("deal_id")
        deal_name = payload.get("deal_name", "Unknown Deal")
        deal_stage = payload.get("deal_stage", "").lower()
        deal_amount = payload.get("amount", 0)
        contact_email = payload.get("contact_email")
        company_name = payload.get("company_name", "Unknown Company")
        
        # Determine action type based on deal stage
        action_type = self._get_action_type(signal.event_type, deal_stage)
        
        # Calculate urgency based on deal stage
        urgency = DEAL_STAGE_URGENCY.get(deal_stage, 0.5)
        
        # Calculate revenue potential based on deal amount
        revenue_potential = self._calculate_revenue_potential(deal_amount)
        
        # Build context for the action
        action_context = {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "deal_stage": deal_stage,
            "deal_amount": deal_amount,
            "contact_email": contact_email,
            "company_name": company_name,
            "signal_id": signal.id,
            "event_type": signal.event_type,
            "source": "hubspot_deal",
        }
        
        # Calculate APS
        aps_result = calculate_aps(
            action_type=action_type,
            context={
                "revenue_impact": revenue_potential,  # Key expected by APS calculator
                "urgency": urgency,
                "strategic_value": self._calculate_strategic_value(deal_stage),
                "effort": 0.3,  # Medium effort (lower = easier = higher score)
            }
        )
        
        # Determine due_by based on event type and stage
        due_by = self._calculate_due_by(signal.event_type, deal_stage)
        
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
            f"Created recommendation for deal '{deal_name}' "
            f"(stage: {deal_stage}, action: {action_type}, APS: {aps_result.score})"
        )
        
        return item

    def _get_action_type(self, event_type: str, deal_stage: str) -> str:
        """Determine action type based on event and stage."""
        if event_type == "deal_created":
            return "deal_research"
        
        if event_type == "deal_amount_changed":
            return "deal_review"
        
        # deal_stage_changed - map to stage-specific action
        return DEAL_STAGE_ACTION.get(deal_stage, "deal_review")

    def _calculate_revenue_potential(self, amount: float) -> float:
        """Calculate revenue potential score (0-1) based on deal amount."""
        if amount <= 0:
            return 0.3  # Unknown amount - assume medium
        
        # Tiered scoring
        if amount >= 100000:
            return 1.0
        elif amount >= 50000:
            return 0.9
        elif amount >= 25000:
            return 0.8
        elif amount >= 10000:
            return 0.7
        elif amount >= 5000:
            return 0.6
        else:
            return 0.5

    def _calculate_strategic_value(self, deal_stage: str) -> float:
        """Calculate strategic value based on deal stage progression."""
        stage_progression = {
            "appointmentscheduled": 0.4,
            "qualifiedtobuy": 0.5,
            "presentationscheduled": 0.6,
            "decisionmakerboughtin": 0.8,
            "contractsent": 0.9,
            "closedwon": 1.0,
            "closedlost": 0.2,
        }
        return stage_progression.get(deal_stage, 0.5)

    def _calculate_due_by(self, event_type: str, deal_stage: str) -> datetime:
        """Calculate due_by based on urgency of the event."""
        now = datetime.utcnow()
        
        if event_type == "deal_created":
            return now + timedelta(hours=4)  # Research new deals within 4 hours
        
        # Stage-specific timing
        if deal_stage in ("contractsent", "decisionmakerboughtin"):
            return now + timedelta(hours=1)  # Hot deals - respond fast
        elif deal_stage in ("presentationscheduled", "qualifiedtobuy"):
            return now + timedelta(hours=4)
        elif deal_stage == "closedwon":
            return now + timedelta(hours=24)  # Onboarding can wait a bit
        else:
            return now + timedelta(hours=8)


def create_deal_signals_from_api_response(
    deals: List[Dict[str, Any]],
    last_checked: Optional[datetime] = None
) -> List[Signal]:
    """
    Create Signal objects from HubSpot API deal response.
    
    Compares deal updated_at with last_checked to only create signals
    for recently changed deals.
    
    Args:
        deals: List of deal dicts from HubSpot API
        last_checked: Timestamp of last poll (only create signals for newer updates)
        
    Returns:
        List of Signal objects to process
    """
    signals = []
    
    for deal in deals:
        deal_id = deal.get("id")
        props = deal.get("properties", deal)
        
        updated_at_str = props.get("updated_at") or props.get("hs_lastmodifieddate")
        if updated_at_str and last_checked:
            try:
                # Parse ISO format
                if isinstance(updated_at_str, str):
                    updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    if updated_at.replace(tzinfo=None) <= last_checked:
                        continue  # Skip - not updated since last check
            except ValueError:
                pass  # Parse error - include signal anyway
        
        # Determine event type
        event_type = "deal_stage_changed"  # Default - could enhance with history comparison
        
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type=event_type,
            source_id=f"deal-{deal_id}",
            payload={
                "deal_id": deal_id,
                "deal_name": props.get("dealname", "Unknown"),
                "deal_stage": props.get("dealstage", ""),
                "amount": float(props.get("amount", 0) or 0),
                "pipeline": props.get("pipeline", ""),
                "close_date": props.get("closedate"),
                "company_name": props.get("company_name", ""),
                "contact_email": props.get("contact_email", ""),
            },
            created_at=datetime.utcnow(),
        )
        signals.append(signal)
    
    logger.info(f"Created {len(signals)} signals from {len(deals)} deals")
    return signals
