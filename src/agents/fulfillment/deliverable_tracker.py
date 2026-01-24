"""DeliverableTrackerAgent - Track client deliverables and milestones.

Monitors deliverable status, sends reminders, and flags at-risk items.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class DeliverableStatus(str, Enum):
    """Status of a deliverable."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DELIVERED = "delivered"
    ON_HOLD = "on_hold"
    AT_RISK = "at_risk"


class DeliverableType(str, Enum):
    """Types of deliverables."""
    REPORT = "report"
    PRESENTATION = "presentation"
    ANALYSIS = "analysis"
    STRATEGY = "strategy"
    CREATIVE = "creative"
    IMPLEMENTATION = "implementation"
    TRAINING = "training"
    DOCUMENTATION = "documentation"


class DeliverableTrackerAgent(BaseAgent):
    """Tracks client deliverables and project milestones.
    
    Features:
    - Deliverable creation and status tracking
    - Automatic risk flagging (approaching deadlines)
    - Progress reporting
    - Dependency tracking
    - Client-facing status updates
    
    Example:
        agent = DeliverableTrackerAgent()
        result = await agent.execute({
            "action": "create",
            "client_id": "client-123",
            "title": "Q4 Strategy Presentation",
            "type": "presentation",
            "due_date": "2026-02-01",
            "owner": "casey",
        })
    """

    # Risk thresholds (days before deadline)
    RISK_THRESHOLDS = {
        "critical": 1,  # 1 day or less = critical
        "high": 3,      # 3 days or less = high risk
        "medium": 7,    # 7 days or less = medium risk
    }

    def __init__(self, hubspot_connector=None, db_session=None):
        """Initialize with connectors."""
        super().__init__(
            name="Deliverable Tracker Agent",
            description="Tracks client deliverables and project milestones"
        )
        self.hubspot_connector = hubspot_connector
        self.db_session = db_session
        
        # In-memory storage (would be DB in production)
        self._deliverables: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "list")
        if action == "create":
            return all(k in context for k in ["title", "client_id", "due_date"])
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deliverable tracking action."""
        action = context.get("action", "list")
        
        if action == "create":
            return await self._create_deliverable(context)
        elif action == "update":
            return await self._update_deliverable(context)
        elif action == "list":
            return await self._list_deliverables(context)
        elif action == "at_risk":
            return await self._get_at_risk(context)
        elif action == "report":
            return await self._generate_report(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _create_deliverable(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new deliverable."""
        deliverable_id = f"del-{datetime.utcnow().timestamp()}"
        
        due_date = context["due_date"]
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        
        deliverable = {
            "id": deliverable_id,
            "client_id": context["client_id"],
            "client_name": context.get("client_name", "Unknown Client"),
            "title": context["title"],
            "description": context.get("description", ""),
            "type": context.get("type", DeliverableType.REPORT.value),
            "status": context.get("status", DeliverableStatus.NOT_STARTED.value),
            "owner": context.get("owner", "unassigned"),
            "due_date": due_date.isoformat() if isinstance(due_date, datetime) else due_date,
            "progress_percent": context.get("progress_percent", 0),
            "dependencies": context.get("dependencies", []),
            "blockers": context.get("blockers", []),
            "notes": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Calculate risk level
        deliverable["risk_level"] = self._calculate_risk(deliverable)
        
        self._deliverables[deliverable_id] = deliverable
        
        # Create HubSpot task if connector available
        if self.hubspot_connector:
            try:
                await self._create_hubspot_task(deliverable)
            except Exception as e:
                logger.warning(f"Could not create HubSpot task: {e}")
        
        logger.info(f"Created deliverable: {deliverable_id} - {deliverable['title']}")
        
        return {
            "status": "success",
            "deliverable": deliverable,
            "message": f"Deliverable created: {deliverable['title']}",
        }

    async def _update_deliverable(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing deliverable."""
        deliverable_id = context.get("deliverable_id")
        
        if deliverable_id not in self._deliverables:
            return {"status": "error", "error": f"Deliverable not found: {deliverable_id}"}
        
        deliverable = self._deliverables[deliverable_id]
        
        # Update fields
        for field in ["status", "progress_percent", "owner", "due_date", "blockers"]:
            if field in context:
                deliverable[field] = context[field]
        
        # Add note if provided
        if "note" in context:
            deliverable["notes"].append({
                "text": context["note"],
                "author": context.get("author", "system"),
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        deliverable["updated_at"] = datetime.utcnow().isoformat()
        deliverable["risk_level"] = self._calculate_risk(deliverable)
        
        logger.info(f"Updated deliverable: {deliverable_id}")
        
        return {
            "status": "success",
            "deliverable": deliverable,
        }

    async def _list_deliverables(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List deliverables with optional filters."""
        client_id = context.get("client_id")
        status = context.get("status")
        owner = context.get("owner")
        
        deliverables = list(self._deliverables.values())
        
        if client_id:
            deliverables = [d for d in deliverables if d["client_id"] == client_id]
        if status:
            deliverables = [d for d in deliverables if d["status"] == status]
        if owner:
            deliverables = [d for d in deliverables if d["owner"] == owner]
        
        # Sort by due date
        deliverables = sorted(deliverables, key=lambda x: x["due_date"])
        
        return {
            "status": "success",
            "count": len(deliverables),
            "deliverables": deliverables,
        }

    async def _get_at_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get all at-risk deliverables."""
        at_risk = []
        
        for deliverable in self._deliverables.values():
            risk = self._calculate_risk(deliverable)
            if risk in ["critical", "high", "medium"]:
                deliverable["risk_level"] = risk
                at_risk.append(deliverable)
        
        # Sort by risk level then due date
        risk_order = {"critical": 0, "high": 1, "medium": 2}
        at_risk = sorted(
            at_risk,
            key=lambda x: (risk_order.get(x["risk_level"], 3), x["due_date"])
        )
        
        return {
            "status": "success",
            "count": len(at_risk),
            "at_risk_deliverables": at_risk,
            "summary": {
                "critical": len([d for d in at_risk if d["risk_level"] == "critical"]),
                "high": len([d for d in at_risk if d["risk_level"] == "high"]),
                "medium": len([d for d in at_risk if d["risk_level"] == "medium"]),
            },
        }

    async def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a client or portfolio report."""
        client_id = context.get("client_id")
        
        deliverables = list(self._deliverables.values())
        if client_id:
            deliverables = [d for d in deliverables if d["client_id"] == client_id]
        
        # Calculate stats
        total = len(deliverables)
        by_status = {}
        for d in deliverables:
            status = d["status"]
            by_status[status] = by_status.get(status, 0) + 1
        
        completed = sum(1 for d in deliverables if d["status"] in ["approved", "delivered"])
        on_track = sum(1 for d in deliverables if d["risk_level"] == "low" and d["status"] not in ["approved", "delivered"])
        at_risk = sum(1 for d in deliverables if d["risk_level"] in ["critical", "high", "medium"])
        
        return {
            "status": "success",
            "report": {
                "client_id": client_id,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_deliverables": total,
                    "completed": completed,
                    "on_track": on_track,
                    "at_risk": at_risk,
                    "completion_rate": (completed / total * 100) if total > 0 else 0,
                },
                "by_status": by_status,
                "upcoming": [
                    d for d in sorted(deliverables, key=lambda x: x["due_date"])
                    if d["status"] not in ["approved", "delivered"]
                ][:5],
            },
        }

    def _calculate_risk(self, deliverable: Dict[str, Any]) -> str:
        """Calculate risk level based on due date and progress."""
        if deliverable["status"] in ["approved", "delivered"]:
            return "none"
        
        due_date = deliverable["due_date"]
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        
        days_until_due = (due_date - datetime.utcnow()).days
        progress = deliverable.get("progress_percent", 0)
        
        # Adjust for progress (if behind schedule, increase risk)
        expected_progress = max(0, 100 - (days_until_due * 10))  # Rough estimate
        behind = progress < expected_progress
        
        if days_until_due <= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif days_until_due <= self.RISK_THRESHOLDS["high"] or (behind and days_until_due <= 5):
            return "high"
        elif days_until_due <= self.RISK_THRESHOLDS["medium"] or behind:
            return "medium"
        else:
            return "low"

    async def _create_hubspot_task(self, deliverable: Dict[str, Any]) -> None:
        """Create a corresponding HubSpot task."""
        if not self.hubspot_connector:
            return
        
        task = {
            "subject": f"[Deliverable] {deliverable['title']}",
            "body": f"Deliverable: {deliverable['description']}\nDue: {deliverable['due_date']}",
            "due_date": deliverable["due_date"],
            "priority": "high" if deliverable["risk_level"] in ["critical", "high"] else "medium",
        }
        
        await self.hubspot_connector.create_task(
            contact_id=deliverable.get("client_id"),
            task_data=task,
        )
