"""ClientHealthAgent - Monitor client health and relationship status.

Tracks client engagement, identifies at-risk accounts, and suggests
proactive interventions to maintain healthy client relationships.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Client health status."""
    THRIVING = "thriving"       # Highly engaged, expanding
    HEALTHY = "healthy"         # On track, no issues
    NEUTRAL = "neutral"         # Quiet, unclear
    AT_RISK = "at_risk"         # Warning signs
    CRITICAL = "critical"       # Immediate attention needed
    CHURNED = "churned"         # Lost client


class RiskFactor(str, Enum):
    """Types of risk factors."""
    LOW_ENGAGEMENT = "low_engagement"
    MISSED_MEETINGS = "missed_meetings"
    DELAYED_PAYMENTS = "delayed_payments"
    NEGATIVE_FEEDBACK = "negative_feedback"
    CHAMPION_LEFT = "champion_left"
    DELIVERABLE_ISSUES = "deliverable_issues"
    COMPETITOR_MENTIONED = "competitor_mentioned"
    SCOPE_CREEP = "scope_creep"
    CONTRACT_ENDING = "contract_ending"


class ClientHealthAgent(BaseAgent):
    """Monitors client health and identifies at-risk accounts.
    
    Features:
    - Health score calculation based on multiple signals
    - Risk factor identification
    - Proactive intervention suggestions
    - Trend tracking over time
    - Client engagement analytics
    
    Example:
        agent = ClientHealthAgent()
        result = await agent.execute({
            "action": "assess",
            "client_id": "client-123",
        })
    """

    # Health score weights
    SCORE_WEIGHTS = {
        "engagement_frequency": 0.20,      # How often they engage
        "response_time": 0.15,             # How fast they respond
        "meeting_attendance": 0.15,        # Do they show up
        "deliverable_feedback": 0.20,      # Positive feedback on work
        "payment_timeliness": 0.10,        # Pay on time
        "expansion_signals": 0.10,         # Asking about more services
        "relationship_depth": 0.10,        # Multiple contacts engaged
    }

    def __init__(self, hubspot_connector=None, gmail_connector=None):
        """Initialize with connectors."""
        super().__init__(
            name="Client Health Agent",
            description="Monitors client health and identifies at-risk accounts"
        )
        self.hubspot_connector = hubspot_connector
        self.gmail_connector = gmail_connector
        
        # In-memory storage (would be DB in production)
        self._client_health: Dict[str, Dict[str, Any]] = {}
        self._health_history: Dict[str, List[Dict[str, Any]]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "list")
        if action in ["assess", "update"]:
            return "client_id" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute client health action."""
        action = context.get("action", "list")
        
        if action == "assess":
            return await self._assess_health(context)
        elif action == "update":
            return await self._update_signals(context)
        elif action == "list":
            return await self._list_clients(context)
        elif action == "at_risk":
            return await self._get_at_risk(context)
        elif action == "trends":
            return await self._get_trends(context)
        elif action == "interventions":
            return await self._suggest_interventions(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _assess_health(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a full health assessment for a client."""
        client_id = context["client_id"]
        
        # Gather signals from various sources
        signals = await self._gather_signals(client_id, context)
        
        # Calculate component scores
        scores = self._calculate_component_scores(signals)
        
        # Calculate overall health score (0-100)
        overall_score = sum(
            scores.get(component, 50) * weight
            for component, weight in self.SCORE_WEIGHTS.items()
        )
        
        # Determine health status
        health_status = self._score_to_status(overall_score)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(signals, scores)
        
        # Build assessment
        assessment = {
            "client_id": client_id,
            "client_name": context.get("client_name", "Unknown"),
            "overall_score": round(overall_score, 1),
            "health_status": health_status,
            "component_scores": scores,
            "risk_factors": risk_factors,
            "signals": signals,
            "assessed_at": datetime.utcnow().isoformat(),
        }
        
        # Store for tracking
        self._client_health[client_id] = assessment
        
        # Add to history
        if client_id not in self._health_history:
            self._health_history[client_id] = []
        self._health_history[client_id].append({
            "score": overall_score,
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"Health assessment for {client_id}: {health_status} ({overall_score})")
        
        return {
            "status": "success",
            "assessment": assessment,
            "interventions": await self._suggest_interventions({"client_id": client_id}),
        }

    async def _gather_signals(self, client_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather health signals from various sources."""
        signals = {
            "last_contact_days": context.get("last_contact_days", 7),
            "meetings_scheduled": context.get("meetings_scheduled", 2),
            "meetings_attended": context.get("meetings_attended", 2),
            "emails_sent_30d": context.get("emails_sent_30d", 10),
            "emails_received_30d": context.get("emails_received_30d", 8),
            "avg_response_hours": context.get("avg_response_hours", 24),
            "deliverables_completed": context.get("deliverables_completed", 3),
            "deliverables_on_time": context.get("deliverables_on_time", 3),
            "positive_feedback_count": context.get("positive_feedback_count", 2),
            "negative_feedback_count": context.get("negative_feedback_count", 0),
            "invoices_paid_on_time": context.get("invoices_paid_on_time", True),
            "expansion_discussions": context.get("expansion_discussions", 0),
            "contacts_engaged": context.get("contacts_engaged", 2),
            "contract_end_days": context.get("contract_end_days", 180),
            "competitor_mentions": context.get("competitor_mentions", 0),
            "nps_score": context.get("nps_score"),  # Optional
        }
        
        # Enrich from HubSpot if available
        if self.hubspot_connector:
            try:
                # TODO: Pull real data from HubSpot
                pass
            except Exception as e:
                logger.warning(f"Could not enrich from HubSpot: {e}")
        
        return signals

    def _calculate_component_scores(self, signals: Dict[str, Any]) -> Dict[str, float]:
        """Calculate individual component scores."""
        scores = {}
        
        # Engagement frequency (based on contact recency and volume)
        last_contact = signals.get("last_contact_days", 30)
        if last_contact <= 3:
            scores["engagement_frequency"] = 100
        elif last_contact <= 7:
            scores["engagement_frequency"] = 80
        elif last_contact <= 14:
            scores["engagement_frequency"] = 60
        elif last_contact <= 30:
            scores["engagement_frequency"] = 40
        else:
            scores["engagement_frequency"] = 20
        
        # Response time
        avg_response = signals.get("avg_response_hours", 48)
        if avg_response <= 4:
            scores["response_time"] = 100
        elif avg_response <= 12:
            scores["response_time"] = 80
        elif avg_response <= 24:
            scores["response_time"] = 60
        elif avg_response <= 48:
            scores["response_time"] = 40
        else:
            scores["response_time"] = 20
        
        # Meeting attendance
        scheduled = signals.get("meetings_scheduled", 1)
        attended = signals.get("meetings_attended", 1)
        if scheduled > 0:
            scores["meeting_attendance"] = min(100, (attended / scheduled) * 100)
        else:
            scores["meeting_attendance"] = 50  # Neutral if no meetings
        
        # Deliverable feedback
        positive = signals.get("positive_feedback_count", 0)
        negative = signals.get("negative_feedback_count", 0)
        total = positive + negative
        if total > 0:
            scores["deliverable_feedback"] = (positive / total) * 100
        else:
            scores["deliverable_feedback"] = 50  # Neutral if no feedback
        
        # Payment timeliness
        scores["payment_timeliness"] = 100 if signals.get("invoices_paid_on_time", True) else 30
        
        # Expansion signals
        expansion = signals.get("expansion_discussions", 0)
        scores["expansion_signals"] = min(100, 50 + (expansion * 25))
        
        # Relationship depth
        contacts = signals.get("contacts_engaged", 1)
        if contacts >= 4:
            scores["relationship_depth"] = 100
        elif contacts >= 3:
            scores["relationship_depth"] = 80
        elif contacts >= 2:
            scores["relationship_depth"] = 60
        else:
            scores["relationship_depth"] = 40
        
        return scores

    def _score_to_status(self, score: float) -> str:
        """Convert numeric score to health status."""
        if score >= 85:
            return HealthStatus.THRIVING.value
        elif score >= 70:
            return HealthStatus.HEALTHY.value
        elif score >= 50:
            return HealthStatus.NEUTRAL.value
        elif score >= 30:
            return HealthStatus.AT_RISK.value
        else:
            return HealthStatus.CRITICAL.value

    def _identify_risk_factors(
        self, 
        signals: Dict[str, Any], 
        scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Identify specific risk factors."""
        risk_factors = []
        
        # Low engagement
        if signals.get("last_contact_days", 0) > 14:
            risk_factors.append({
                "factor": RiskFactor.LOW_ENGAGEMENT.value,
                "severity": "high" if signals["last_contact_days"] > 30 else "medium",
                "detail": f"No contact in {signals['last_contact_days']} days",
            })
        
        # Missed meetings
        scheduled = signals.get("meetings_scheduled", 0)
        attended = signals.get("meetings_attended", 0)
        if scheduled > 0 and attended < scheduled:
            missed = scheduled - attended
            risk_factors.append({
                "factor": RiskFactor.MISSED_MEETINGS.value,
                "severity": "high" if missed >= 2 else "medium",
                "detail": f"Missed {missed} of {scheduled} meetings",
            })
        
        # Negative feedback
        if signals.get("negative_feedback_count", 0) > 0:
            risk_factors.append({
                "factor": RiskFactor.NEGATIVE_FEEDBACK.value,
                "severity": "high" if signals["negative_feedback_count"] >= 2 else "medium",
                "detail": f"{signals['negative_feedback_count']} negative feedback instances",
            })
        
        # Payment issues
        if not signals.get("invoices_paid_on_time", True):
            risk_factors.append({
                "factor": RiskFactor.DELAYED_PAYMENTS.value,
                "severity": "medium",
                "detail": "Late payment on recent invoices",
            })
        
        # Competitor mentions
        if signals.get("competitor_mentions", 0) > 0:
            risk_factors.append({
                "factor": RiskFactor.COMPETITOR_MENTIONED.value,
                "severity": "high",
                "detail": f"Competitor mentioned {signals['competitor_mentions']} times",
            })
        
        # Contract ending soon
        if signals.get("contract_end_days", 365) < 60:
            risk_factors.append({
                "factor": RiskFactor.CONTRACT_ENDING.value,
                "severity": "high" if signals["contract_end_days"] < 30 else "medium",
                "detail": f"Contract ends in {signals['contract_end_days']} days",
            })
        
        return risk_factors

    async def _update_signals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update specific signals for a client."""
        client_id = context["client_id"]
        
        if client_id not in self._client_health:
            # Run initial assessment
            return await self._assess_health(context)
        
        # Update specific signals
        current = self._client_health[client_id]
        for key, value in context.items():
            if key in current.get("signals", {}):
                current["signals"][key] = value
        
        current["updated_at"] = datetime.utcnow().isoformat()
        
        # Re-assess with updated signals
        return await self._assess_health(context)

    async def _list_clients(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List all clients with health status."""
        status_filter = context.get("status")
        
        clients = list(self._client_health.values())
        
        if status_filter:
            clients = [c for c in clients if c["health_status"] == status_filter]
        
        # Sort by score ascending (worst first)
        clients = sorted(clients, key=lambda x: x["overall_score"])
        
        return {
            "status": "success",
            "count": len(clients),
            "clients": clients,
        }

    async def _get_at_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get all at-risk and critical clients."""
        at_risk = [
            c for c in self._client_health.values()
            if c["health_status"] in [HealthStatus.AT_RISK.value, HealthStatus.CRITICAL.value]
        ]
        
        # Sort by score ascending (worst first)
        at_risk = sorted(at_risk, key=lambda x: x["overall_score"])
        
        return {
            "status": "success",
            "count": len(at_risk),
            "clients": at_risk,
            "summary": {
                "critical": len([c for c in at_risk if c["health_status"] == "critical"]),
                "at_risk": len([c for c in at_risk if c["health_status"] == "at_risk"]),
            },
        }

    async def _get_trends(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get health trends for a client."""
        client_id = context.get("client_id")
        
        if client_id not in self._health_history:
            return {"status": "error", "error": f"No history for client: {client_id}"}
        
        history = self._health_history[client_id]
        
        # Calculate trend
        if len(history) >= 2:
            recent = history[-1]["score"]
            previous = history[-2]["score"]
            trend = "improving" if recent > previous else "declining" if recent < previous else "stable"
            change = recent - previous
        else:
            trend = "stable"
            change = 0
        
        return {
            "status": "success",
            "client_id": client_id,
            "current_score": history[-1]["score"] if history else None,
            "trend": trend,
            "change": round(change, 1),
            "history": history[-10:],  # Last 10 assessments
        }

    async def _suggest_interventions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest proactive interventions for a client."""
        client_id = context.get("client_id")
        
        if client_id not in self._client_health:
            return {"interventions": []}
        
        assessment = self._client_health[client_id]
        risk_factors = assessment.get("risk_factors", [])
        
        interventions = []
        
        for risk in risk_factors:
            factor = risk["factor"]
            
            if factor == RiskFactor.LOW_ENGAGEMENT.value:
                interventions.append({
                    "action": "schedule_checkin",
                    "priority": "high",
                    "description": "Schedule a casual check-in call to reconnect",
                    "suggested_message": "Hey! It's been a while - would love to catch up and hear how things are going. Coffee chat this week?",
                })
            
            elif factor == RiskFactor.MISSED_MEETINGS.value:
                interventions.append({
                    "action": "reschedule_meeting",
                    "priority": "high",
                    "description": "Reach out to reschedule missed meetings",
                    "suggested_message": "I noticed we've had trouble connecting recently. Want me to suggest some alternative times?",
                })
            
            elif factor == RiskFactor.NEGATIVE_FEEDBACK.value:
                interventions.append({
                    "action": "address_concerns",
                    "priority": "critical",
                    "description": "Schedule a call to address concerns directly",
                    "suggested_message": "I want to make sure we're fully aligned - can we hop on a quick call to discuss how things are going?",
                })
            
            elif factor == RiskFactor.CONTRACT_ENDING.value:
                interventions.append({
                    "action": "renewal_discussion",
                    "priority": "high",
                    "description": "Initiate renewal conversation",
                    "suggested_message": "With our engagement coming up for renewal, I'd love to discuss how we can continue adding value.",
                })
            
            elif factor == RiskFactor.COMPETITOR_MENTIONED.value:
                interventions.append({
                    "action": "competitive_defense",
                    "priority": "critical",
                    "description": "Proactively address competitive concerns",
                    "suggested_message": "I'd love to get your candid feedback on how we're doing - and discuss any areas where you feel we could improve.",
                })
        
        return {
            "client_id": client_id,
            "interventions": interventions,
        }
