"""
SignalToRecommendationService - Converts signals to action recommendations.

This service provides a centralized mapping from signal types to action types,
ensuring consistent APS calculation and recommendation creation.
"""
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem, ActionRecommendation
from src.services.aps_calculator import calculate_aps
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ActionTypeMapping:
    """Mapping configuration for a signal type to action type."""
    
    action_type: str
    default_urgency: float
    default_effort: float
    default_strategic_value: float
    due_by_hours: int
    owner: str = "casey"


# Signal type to action type mappings
SIGNAL_ACTION_MAPPINGS: Dict[tuple[SignalSource, str], ActionTypeMapping] = {
    # Form submissions -> email follow-up (high urgency, low effort)
    (SignalSource.FORM, "form_submitted"): ActionTypeMapping(
        action_type="email_follow_up",
        default_urgency=0.9,
        default_effort=0.2,
        default_strategic_value=0.5,
        due_by_hours=2,
    ),
    
    # HubSpot deal created -> deal outreach
    (SignalSource.HUBSPOT, "deal_created"): ActionTypeMapping(
        action_type="deal_outreach",
        default_urgency=0.85,
        default_effort=0.3,
        default_strategic_value=0.7,
        due_by_hours=4,
    ),
    
    # HubSpot deal stage changed -> deal progression
    (SignalSource.HUBSPOT, "deal_stage_changed"): ActionTypeMapping(
        action_type="deal_progression",
        default_urgency=0.8,
        default_effort=0.4,
        default_strategic_value=0.8,
        due_by_hours=8,
    ),
    
    # Gmail reply received -> reply response
    (SignalSource.GMAIL, "reply_received"): ActionTypeMapping(
        action_type="reply_response",
        default_urgency=0.95,  # Very high - someone replied!
        default_effort=0.3,
        default_strategic_value=0.7,
        due_by_hours=1,  # Reply within 1 hour
    ),
    
    # Manual signals -> custom action
    (SignalSource.MANUAL, "task_created"): ActionTypeMapping(
        action_type="manual_task",
        default_urgency=0.5,
        default_effort=0.5,
        default_strategic_value=0.5,
        due_by_hours=24,
    ),
}


class SignalToRecommendationService:
    """
    Service for converting signals to action recommendations.
    
    This provides a consistent interface for:
    - Mapping signal types to action types
    - Calculating APS scores
    - Creating CommandQueueItem and ActionRecommendation instances
    """
    
    def __init__(self, mappings: Optional[Dict] = None):
        """
        Initialize the service.
        
        Args:
            mappings: Optional custom mappings (for testing)
        """
        self.mappings = mappings or SIGNAL_ACTION_MAPPINGS
    
    def get_action_type(self, signal: Signal) -> Optional[str]:
        """
        Get the action type for a signal.
        
        Args:
            signal: The signal to map
            
        Returns:
            Action type string, or None if no mapping exists
        """
        key = (signal.source, signal.event_type)
        mapping = self.mappings.get(key)
        return mapping.action_type if mapping else None
    
    def get_mapping(self, signal: Signal) -> Optional[ActionTypeMapping]:
        """
        Get the full mapping configuration for a signal.
        
        Args:
            signal: The signal to map
            
        Returns:
            ActionTypeMapping or None if no mapping exists
        """
        key = (signal.source, signal.event_type)
        return self.mappings.get(key)
    
    def extract_revenue_impact(self, signal: Signal) -> float:
        """
        Extract revenue impact from signal payload.
        
        Different signal types store revenue info in different fields.
        """
        payload = signal.payload
        
        # HubSpot deals have amount
        if signal.source == SignalSource.HUBSPOT:
            amount = payload.get("deal_amount") or payload.get("amount", 0)
            if amount:
                # Normalize to 0-1 scale (assume $100k = 1.0)
                return min(1.0, float(amount) / 100000)
        
        # Form submissions might have revenue potential
        if "revenue_impact" in payload:
            return float(payload["revenue_impact"])
        if "revenue_potential" in payload:
            return float(payload["revenue_potential"])
        
        # Default based on signal source
        defaults = {
            SignalSource.FORM: 0.5,
            SignalSource.HUBSPOT: 0.7,
            SignalSource.GMAIL: 0.6,
            SignalSource.MANUAL: 0.4,
        }
        return defaults.get(signal.source, 0.5)
    
    def extract_contact_info(self, signal: Signal) -> Dict[str, Any]:
        """Extract contact information from signal payload."""
        payload = signal.payload
        
        # Extract company with fallbacks
        company = (
            payload.get("company") or 
            payload.get("company_name")
        )
        if not company and payload.get("deal_name"):
            # Try to extract from deal name (e.g., "Acme Corp - Enterprise")
            company = payload.get("deal_name", "").split(" - ")[0]
        if not company:
            company = "Unknown Company"
        
        return {
            "email": (
                payload.get("email") or 
                payload.get("contact_email") or 
                payload.get("from_email") or
                ""
            ),
            "name": (
                payload.get("name") or 
                payload.get("contact_name") or 
                payload.get("sender_name") or
                "Unknown"
            ),
            "company": company,
        }
    
    def convert(
        self,
        signal: Signal,
        override_urgency: Optional[float] = None,
        override_effort: Optional[float] = None,
        override_revenue: Optional[float] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[CommandQueueItem]:
        """
        Convert a signal to a CommandQueueItem recommendation.
        
        Args:
            signal: The signal to convert
            override_urgency: Optional urgency override (0-1)
            override_effort: Optional effort override (0-1)
            override_revenue: Optional revenue impact override (0-1)
            additional_context: Additional context to merge into action_context
            
        Returns:
            CommandQueueItem if mapping exists, None otherwise
        """
        mapping = self.get_mapping(signal)
        if not mapping:
            logger.debug(
                f"No mapping for signal {signal.id} "
                f"(source={signal.source}, event_type={signal.event_type})"
            )
            return None
        
        # Extract values
        revenue_impact = override_revenue or self.extract_revenue_impact(signal)
        urgency = override_urgency or mapping.default_urgency
        effort = override_effort or mapping.default_effort
        strategic_value = mapping.default_strategic_value
        
        # Calculate APS
        aps_result = calculate_aps(
            action_type=mapping.action_type,
            context={
                "revenue_impact": revenue_impact,
                "urgency": urgency,
                "strategic_value": strategic_value,
                "effort": effort,
            }
        )
        
        # Build action context
        contact_info = self.extract_contact_info(signal)
        action_context = {
            "signal_id": signal.id,
            "signal_source": signal.source.value,
            "signal_event_type": signal.event_type,
            "lead_email": contact_info["email"],
            "lead_name": contact_info["name"],
            "lead_company": contact_info["company"],
            "signal_payload": signal.payload,
            "aps_components": {
                "revenue_impact": revenue_impact,
                "urgency": urgency,
                "effort": effort,
                "strategic_value": strategic_value,
            },
        }
        
        # Merge additional context
        if additional_context:
            action_context.update(additional_context)
        
        # Calculate due_by
        due_by = datetime.utcnow() + timedelta(hours=mapping.due_by_hours)
        
        # Create the command queue item
        item = CommandQueueItem(
            id=str(uuid4()),
            priority_score=aps_result.score / 100.0,
            action_type=mapping.action_type,
            action_context=action_context,
            status="pending",
            owner=mapping.owner,
            due_by=due_by,
            recommendation_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        logger.info(
            f"Converted signal to recommendation",
            signal_id=signal.id,
            action_type=mapping.action_type,
            aps_score=aps_result.score,
            due_by=due_by.isoformat(),
        )
        
        return item
    
    def convert_with_recommendation(
        self,
        signal: Signal,
        **kwargs,
    ) -> Optional[tuple[CommandQueueItem, ActionRecommendation]]:
        """
        Convert a signal to both CommandQueueItem and ActionRecommendation.
        
        Returns:
            Tuple of (CommandQueueItem, ActionRecommendation) or None
        """
        item = self.convert(signal, **kwargs)
        if not item:
            return None
        
        # Extract APS components from action_context
        aps_components = item.action_context.get("aps_components", {})
        
        # Create the recommendation with full metadata
        recommendation = ActionRecommendation(
            id=str(uuid4()),
            aps_score=item.priority_score * 100,  # Store as 0-100
            reasoning=self._generate_reasoning(signal, item),
            revenue_impact=aps_components.get("revenue_impact", 0.0),
            urgency_score=aps_components.get("urgency", 0.0),
            effort_score=aps_components.get("effort", 0.0),
            strategic_score=aps_components.get("strategic_value", 0.0),
            recommendation_metadata={
                "signal_id": signal.id,
                "signal_source": signal.source.value,
                "signal_event_type": signal.event_type,
            },
            generated_at=datetime.utcnow(),
        )
        
        # Link item to recommendation
        item.recommendation_id = recommendation.id
        
        return item, recommendation
    
    def _generate_reasoning(self, signal: Signal, item: CommandQueueItem) -> str:
        """Generate human-readable reasoning for the recommendation."""
        contact = self.extract_contact_info(signal)
        aps_components = item.action_context.get("aps_components", {})
        
        reasons = []
        
        # Revenue reasoning
        revenue = aps_components.get("revenue_impact", 0)
        if revenue >= 0.8:
            reasons.append("High revenue potential")
        elif revenue >= 0.5:
            reasons.append("Moderate revenue opportunity")
        
        # Urgency reasoning
        urgency = aps_components.get("urgency", 0)
        if urgency >= 0.9:
            reasons.append("Time-sensitive - respond immediately")
        elif urgency >= 0.7:
            reasons.append("Urgent - respond today")
        
        # Source-specific reasoning
        if signal.source == SignalSource.FORM:
            reasons.append(f"{contact['name']} just submitted a form")
        elif signal.source == SignalSource.HUBSPOT:
            if signal.event_type == "deal_created":
                reasons.append("New deal created in HubSpot")
            elif signal.event_type == "deal_stage_changed":
                reasons.append("Deal progressed to new stage")
        elif signal.source == SignalSource.GMAIL:
            reasons.append(f"Reply received from {contact['name']}")
        
        return " | ".join(reasons) if reasons else f"Action required for {contact['name']}"
    
    @classmethod
    def get_supported_signal_types(cls) -> list[tuple[str, str]]:
        """Get list of supported (source, event_type) combinations."""
        return [
            (source.value, event_type)
            for (source, event_type) in SIGNAL_ACTION_MAPPINGS.keys()
        ]
    
    @classmethod
    def get_action_types(cls) -> list[str]:
        """Get list of all supported action types."""
        return list(set(
            mapping.action_type 
            for mapping in SIGNAL_ACTION_MAPPINGS.values()
        ))
