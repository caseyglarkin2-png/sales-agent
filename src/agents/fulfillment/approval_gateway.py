"""ApprovalGatewayAgent - Manage multi-stakeholder approvals.

Routes deliverables through approval workflows, tracks sign-offs,
and escalates when approvals stall.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ApprovalType(str, Enum):
    """Types of approvals."""
    DELIVERABLE = "deliverable"
    PROPOSAL = "proposal"
    CONTRACT = "contract"
    BUDGET = "budget"
    CREATIVE = "creative"
    STRATEGY = "strategy"


class ApprovalGatewayAgent(BaseAgent):
    """Manages multi-stakeholder approval workflows.
    
    Features:
    - Multi-stakeholder approval routing
    - Sequential or parallel approval flows
    - Automatic escalation on stalled approvals
    - Audit trail of all decisions
    - Reminder scheduling
    
    Example:
        agent = ApprovalGatewayAgent()
        result = await agent.execute({
            "action": "create",
            "item_id": "del-123",
            "item_type": "deliverable",
            "approvers": ["john@client.com", "jane@client.com"],
            "workflow": "sequential",  # or "parallel"
            "deadline_days": 3,
        })
    """

    # Escalation settings
    ESCALATION_THRESHOLDS = {
        "reminder_after_hours": 24,
        "escalate_after_hours": 72,
        "expire_after_hours": 168,  # 7 days
    }

    def __init__(self, gmail_connector=None, hubspot_connector=None):
        """Initialize with connectors."""
        super().__init__(
            name="Approval Gateway Agent",
            description="Manages multi-stakeholder approval workflows"
        )
        self.gmail_connector = gmail_connector
        self.hubspot_connector = hubspot_connector
        
        # In-memory storage (would be DB in production)
        self._approval_requests: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "list")
        if action == "create":
            return all(k in context for k in ["item_id", "approvers"])
        elif action in ["approve", "reject"]:
            return "request_id" in context and "approver" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approval workflow action."""
        action = context.get("action", "list")
        
        if action == "create":
            return await self._create_request(context)
        elif action == "approve":
            return await self._record_approval(context)
        elif action == "reject":
            return await self._record_rejection(context)
        elif action == "list":
            return await self._list_requests(context)
        elif action == "status":
            return await self._get_status(context)
        elif action == "escalate":
            return await self._escalate(context)
        elif action == "check_stalled":
            return await self._check_stalled()
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _create_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new approval request."""
        request_id = f"apr-{datetime.utcnow().timestamp()}"
        
        approvers = context["approvers"]
        workflow = context.get("workflow", "parallel")  # sequential or parallel
        deadline_days = context.get("deadline_days", 3)
        
        # Build approver statuses
        approver_statuses = []
        for i, approver in enumerate(approvers):
            approver_statuses.append({
                "email": approver,
                "status": ApprovalStatus.PENDING.value,
                "order": i if workflow == "sequential" else 0,
                "can_approve": (i == 0) if workflow == "sequential" else True,
                "decided_at": None,
                "comments": None,
            })
        
        request = {
            "id": request_id,
            "item_id": context["item_id"],
            "item_type": context.get("item_type", ApprovalType.DELIVERABLE.value),
            "item_title": context.get("item_title", "Untitled"),
            "workflow": workflow,
            "approvers": approver_statuses,
            "overall_status": ApprovalStatus.PENDING.value,
            "deadline": (datetime.utcnow() + timedelta(days=deadline_days)).isoformat(),
            "created_by": context.get("created_by", "system"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "audit_log": [
                {
                    "action": "created",
                    "actor": context.get("created_by", "system"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
        }
        
        self._approval_requests[request_id] = request
        
        # Send initial approval request emails
        await self._send_approval_requests(request)
        
        logger.info(f"Created approval request: {request_id} for {context['item_id']}")
        
        return {
            "status": "success",
            "request": request,
            "message": f"Approval request sent to {len(approvers)} approvers",
        }

    async def _record_approval(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record an approval from an approver."""
        request_id = context["request_id"]
        approver_email = context["approver"]
        
        if request_id not in self._approval_requests:
            return {"status": "error", "error": f"Request not found: {request_id}"}
        
        request = self._approval_requests[request_id]
        
        # Find and update the approver
        approver_found = False
        for approver in request["approvers"]:
            if approver["email"] == approver_email:
                if not approver["can_approve"]:
                    return {"status": "error", "error": "Not your turn to approve (sequential workflow)"}
                
                approver["status"] = ApprovalStatus.APPROVED.value
                approver["decided_at"] = datetime.utcnow().isoformat()
                approver["comments"] = context.get("comments")
                approver_found = True
                break
        
        if not approver_found:
            return {"status": "error", "error": f"Approver not found: {approver_email}"}
        
        # Update audit log
        request["audit_log"].append({
            "action": "approved",
            "actor": approver_email,
            "timestamp": datetime.utcnow().isoformat(),
            "comments": context.get("comments"),
        })
        
        # Check if all approved / enable next approver
        request = self._update_workflow_state(request)
        request["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Approval recorded: {request_id} by {approver_email}")
        
        return {
            "status": "success",
            "request": request,
            "overall_status": request["overall_status"],
            "message": f"Approval recorded from {approver_email}",
        }

    async def _record_rejection(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record a rejection from an approver."""
        request_id = context["request_id"]
        approver_email = context["approver"]
        
        if request_id not in self._approval_requests:
            return {"status": "error", "error": f"Request not found: {request_id}"}
        
        request = self._approval_requests[request_id]
        
        # Find and update the approver
        for approver in request["approvers"]:
            if approver["email"] == approver_email:
                approver["status"] = context.get("status", ApprovalStatus.REJECTED.value)
                approver["decided_at"] = datetime.utcnow().isoformat()
                approver["comments"] = context.get("comments", "No reason provided")
                break
        
        # Rejection typically stops the whole workflow
        request["overall_status"] = ApprovalStatus.REJECTED.value
        
        request["audit_log"].append({
            "action": "rejected",
            "actor": approver_email,
            "timestamp": datetime.utcnow().isoformat(),
            "comments": context.get("comments"),
        })
        
        request["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Rejection recorded: {request_id} by {approver_email}")
        
        return {
            "status": "success",
            "request": request,
            "overall_status": request["overall_status"],
            "message": f"Rejection recorded from {approver_email}",
        }

    async def _list_requests(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List approval requests."""
        item_id = context.get("item_id")
        status = context.get("status")
        approver = context.get("approver")
        
        requests = list(self._approval_requests.values())
        
        if item_id:
            requests = [r for r in requests if r["item_id"] == item_id]
        if status:
            requests = [r for r in requests if r["overall_status"] == status]
        if approver:
            requests = [
                r for r in requests 
                if any(a["email"] == approver for a in r["approvers"])
            ]
        
        return {
            "status": "success",
            "count": len(requests),
            "requests": requests,
        }

    async def _get_status(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed status of an approval request."""
        request_id = context.get("request_id")
        
        if request_id not in self._approval_requests:
            return {"status": "error", "error": f"Request not found: {request_id}"}
        
        request = self._approval_requests[request_id]
        
        # Calculate progress
        total = len(request["approvers"])
        approved = sum(1 for a in request["approvers"] if a["status"] == "approved")
        pending = sum(1 for a in request["approvers"] if a["status"] == "pending")
        
        return {
            "status": "success",
            "request": request,
            "progress": {
                "total_approvers": total,
                "approved": approved,
                "pending": pending,
                "percent_complete": (approved / total * 100) if total > 0 else 0,
            },
        }

    async def _escalate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate a stalled approval request."""
        request_id = context.get("request_id")
        escalate_to = context.get("escalate_to")
        
        if request_id not in self._approval_requests:
            return {"status": "error", "error": f"Request not found: {request_id}"}
        
        request = self._approval_requests[request_id]
        request["overall_status"] = ApprovalStatus.ESCALATED.value
        
        request["audit_log"].append({
            "action": "escalated",
            "actor": context.get("actor", "system"),
            "timestamp": datetime.utcnow().isoformat(),
            "escalated_to": escalate_to,
            "reason": context.get("reason", "Approval deadline exceeded"),
        })
        
        # TODO: Send escalation email
        
        logger.info(f"Escalated approval request: {request_id} to {escalate_to}")
        
        return {
            "status": "success",
            "request": request,
            "message": f"Escalated to {escalate_to}",
        }

    async def _check_stalled(self) -> Dict[str, Any]:
        """Check for stalled approvals that need reminders or escalation."""
        now = datetime.utcnow()
        stalled = []
        needs_reminder = []
        needs_escalation = []
        
        for request in self._approval_requests.values():
            if request["overall_status"] != ApprovalStatus.PENDING.value:
                continue
            
            created = datetime.fromisoformat(request["created_at"].replace("Z", "+00:00"))
            hours_elapsed = (now - created).total_seconds() / 3600
            
            if hours_elapsed >= self.ESCALATION_THRESHOLDS["escalate_after_hours"]:
                needs_escalation.append(request)
            elif hours_elapsed >= self.ESCALATION_THRESHOLDS["reminder_after_hours"]:
                needs_reminder.append(request)
        
        return {
            "status": "success",
            "needs_reminder": len(needs_reminder),
            "needs_escalation": len(needs_escalation),
            "reminder_requests": [r["id"] for r in needs_reminder],
            "escalation_requests": [r["id"] for r in needs_escalation],
        }

    def _update_workflow_state(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow state after an approval."""
        all_approved = all(a["status"] == "approved" for a in request["approvers"])
        any_rejected = any(a["status"] in ["rejected", "changes_requested"] for a in request["approvers"])
        
        if all_approved:
            request["overall_status"] = ApprovalStatus.APPROVED.value
        elif any_rejected:
            request["overall_status"] = ApprovalStatus.REJECTED.value
        else:
            # For sequential workflow, enable next approver
            if request["workflow"] == "sequential":
                for i, approver in enumerate(request["approvers"]):
                    if approver["status"] == "pending":
                        approver["can_approve"] = True
                        break
        
        return request

    async def _send_approval_requests(self, request: Dict[str, Any]) -> None:
        """Send approval request emails to approvers."""
        if not self.gmail_connector:
            logger.info("Gmail connector not available, skipping email notifications")
            return
        
        for approver in request["approvers"]:
            if approver["can_approve"]:
                # TODO: Send email using gmail connector
                logger.info(f"Would send approval request to {approver['email']}")
