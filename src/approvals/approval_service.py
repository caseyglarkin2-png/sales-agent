"""
Approval Service - Approval Workflow Management
================================================
Handles approval chains, rules, and request processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ApprovalStatus(str, Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ApprovalType(str, Enum):
    """Type of item requiring approval."""
    DEAL = "deal"
    DISCOUNT = "discount"
    QUOTE = "quote"
    CONTRACT = "contract"
    EXPENSE = "expense"
    COMMISSION = "commission"
    REFUND = "refund"
    CUSTOM = "custom"


class EscalationType(str, Enum):
    """Escalation type."""
    TIMEOUT = "timeout"
    THRESHOLD = "threshold"
    MANUAL = "manual"


class ApproverType(str, Enum):
    """Approver type."""
    USER = "user"
    ROLE = "role"
    MANAGER = "manager"
    GROUP = "group"


@dataclass
class Approver:
    """An approver in a chain."""
    id: str
    approver_type: ApproverType
    approver_id: str  # User ID, Role ID, or 'manager'
    order: int = 1
    is_required: bool = True
    can_delegate: bool = False


@dataclass
class ApprovalChain:
    """An approval chain definition."""
    id: str
    name: str
    description: str
    approval_type: ApprovalType
    
    # Approvers
    approvers: list[Approver] = field(default_factory=list)
    
    # Settings
    require_all: bool = True  # All must approve vs any
    allow_self_approval: bool = False
    allow_parallel: bool = False  # Parallel vs sequential
    
    # Escalation
    escalation_enabled: bool = True
    escalation_hours: int = 24
    escalation_to: Optional[str] = None  # User/Role ID
    
    # Expiration
    expiration_hours: int = 72
    
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApprovalRule:
    """A rule that determines which chain to use."""
    id: str
    name: str
    description: str
    approval_type: ApprovalType
    chain_id: str
    
    # Conditions
    conditions: dict[str, Any] = field(default_factory=dict)
    # Example: {"amount": {"gt": 10000}, "region": "enterprise"}
    
    priority: int = 0  # Higher priority rules checked first
    is_active: bool = True
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApprovalStep:
    """A step in an approval request."""
    id: str
    approver_id: str
    approver_type: ApproverType
    order: int
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Action
    actioned_by: Optional[str] = None
    actioned_at: Optional[datetime] = None
    comments: str = ""
    
    # Delegation
    delegated_to: Optional[str] = None
    delegated_at: Optional[datetime] = None


@dataclass
class ApprovalRequest:
    """An approval request."""
    id: str
    approval_type: ApprovalType
    chain_id: str
    
    # The item being approved
    entity_type: str
    entity_id: str
    entity_data: dict[str, Any] = field(default_factory=dict)
    
    # Requester
    requester_id: str
    requester_name: str = ""
    
    # Request details
    title: str = ""
    description: str = ""
    amount: float = 0.0  # For financial approvals
    
    # Steps
    steps: list[ApprovalStep] = field(default_factory=list)
    current_step: int = 0
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Timestamps
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Escalation
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    
    # Outcome
    final_decision: Optional[str] = None
    final_comments: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApprovalComment:
    """A comment on an approval request."""
    id: str
    request_id: str
    user_id: str
    comment: str
    is_internal: bool = False  # Hidden from requester
    created_at: datetime = field(default_factory=datetime.utcnow)


class ApprovalService:
    """Service for approval workflow management."""
    
    def __init__(self):
        self.chains: dict[str, ApprovalChain] = {}
        self.rules: dict[str, ApprovalRule] = {}
        self.requests: dict[str, ApprovalRequest] = {}
        self.comments: dict[str, list[ApprovalComment]] = {}
        self._init_sample_data()
    
    def _init_sample_data(self) -> None:
        """Initialize sample chains and rules."""
        # Standard discount approval chain
        discount_chain = ApprovalChain(
            id="chain-discount",
            name="Discount Approval",
            description="Approval chain for discounts",
            approval_type=ApprovalType.DISCOUNT,
            approvers=[
                Approver(
                    id="approver-1",
                    approver_type=ApproverType.MANAGER,
                    approver_id="manager",
                    order=1,
                ),
            ],
            escalation_hours=24,
        )
        
        # Large deal approval chain
        deal_chain = ApprovalChain(
            id="chain-large-deal",
            name="Large Deal Approval",
            description="Approval for deals over $50K",
            approval_type=ApprovalType.DEAL,
            approvers=[
                Approver(
                    id="approver-1",
                    approver_type=ApproverType.MANAGER,
                    approver_id="manager",
                    order=1,
                ),
                Approver(
                    id="approver-2",
                    approver_type=ApproverType.ROLE,
                    approver_id="role-vp-sales",
                    order=2,
                ),
            ],
        )
        
        self.chains[discount_chain.id] = discount_chain
        self.chains[deal_chain.id] = deal_chain
        
        # Rules
        discount_rule = ApprovalRule(
            id="rule-discount-10",
            name="10%+ Discount",
            description="Discounts of 10% or more require approval",
            approval_type=ApprovalType.DISCOUNT,
            chain_id="chain-discount",
            conditions={"discount_percent": {"gte": 10}},
            priority=1,
        )
        
        deal_rule = ApprovalRule(
            id="rule-large-deal",
            name="Large Deal",
            description="Deals over $50K require approval",
            approval_type=ApprovalType.DEAL,
            chain_id="chain-large-deal",
            conditions={"amount": {"gt": 50000}},
            priority=1,
        )
        
        self.rules[discount_rule.id] = discount_rule
        self.rules[deal_rule.id] = deal_rule
    
    # Chain CRUD
    async def create_chain(
        self,
        name: str,
        description: str,
        approval_type: ApprovalType,
        approvers: list[dict[str, Any]] = None,
        **kwargs
    ) -> ApprovalChain:
        """Create an approval chain."""
        chain_id = str(uuid.uuid4())
        
        approver_list = []
        if approvers:
            for i, a in enumerate(approvers):
                approver_list.append(Approver(
                    id=str(uuid.uuid4()),
                    approver_type=ApproverType(a.get("type", "user")),
                    approver_id=a.get("id", ""),
                    order=a.get("order", i + 1),
                    is_required=a.get("required", True),
                    can_delegate=a.get("can_delegate", False),
                ))
        
        chain = ApprovalChain(
            id=chain_id,
            name=name,
            description=description,
            approval_type=approval_type,
            approvers=approver_list,
            **kwargs
        )
        
        self.chains[chain_id] = chain
        return chain
    
    async def get_chain(self, chain_id: str) -> Optional[ApprovalChain]:
        """Get a chain by ID."""
        return self.chains.get(chain_id)
    
    async def update_chain(
        self,
        chain_id: str,
        updates: dict[str, Any]
    ) -> Optional[ApprovalChain]:
        """Update a chain."""
        chain = self.chains.get(chain_id)
        if not chain:
            return None
        
        for key, value in updates.items():
            if hasattr(chain, key):
                setattr(chain, key, value)
        
        chain.updated_at = datetime.utcnow()
        return chain
    
    async def delete_chain(self, chain_id: str) -> bool:
        """Delete a chain."""
        if chain_id in self.chains:
            del self.chains[chain_id]
            return True
        return False
    
    async def list_chains(
        self,
        approval_type: Optional[ApprovalType] = None,
        active_only: bool = True
    ) -> list[ApprovalChain]:
        """List chains."""
        chains = list(self.chains.values())
        
        if approval_type:
            chains = [c for c in chains if c.approval_type == approval_type]
        if active_only:
            chains = [c for c in chains if c.is_active]
        
        chains.sort(key=lambda c: c.name)
        return chains
    
    # Rule CRUD
    async def create_rule(
        self,
        name: str,
        description: str,
        approval_type: ApprovalType,
        chain_id: str,
        conditions: dict[str, Any],
        priority: int = 0
    ) -> ApprovalRule:
        """Create an approval rule."""
        rule = ApprovalRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            approval_type=approval_type,
            chain_id=chain_id,
            conditions=conditions,
            priority=priority,
        )
        self.rules[rule.id] = rule
        return rule
    
    async def get_rule(self, rule_id: str) -> Optional[ApprovalRule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
    
    async def update_rule(
        self,
        rule_id: str,
        updates: dict[str, Any]
    ) -> Optional[ApprovalRule]:
        """Update a rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        return rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    async def list_rules(
        self,
        approval_type: Optional[ApprovalType] = None,
        active_only: bool = True
    ) -> list[ApprovalRule]:
        """List rules."""
        rules = list(self.rules.values())
        
        if approval_type:
            rules = [r for r in rules if r.approval_type == approval_type]
        if active_only:
            rules = [r for r in rules if r.is_active]
        
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules
    
    # Find applicable chain
    async def find_chain(
        self,
        approval_type: ApprovalType,
        context: dict[str, Any]
    ) -> Optional[ApprovalChain]:
        """Find the applicable chain based on rules."""
        rules = await self.list_rules(approval_type=approval_type)
        
        for rule in rules:
            if self._evaluate_conditions(rule.conditions, context):
                return self.chains.get(rule.chain_id)
        
        return None
    
    def _evaluate_conditions(
        self,
        conditions: dict[str, Any],
        context: dict[str, Any]
    ) -> bool:
        """Evaluate rule conditions."""
        for field, condition in conditions.items():
            value = context.get(field)
            
            if isinstance(condition, dict):
                for op, threshold in condition.items():
                    if op == "gt" and not (value and value > threshold):
                        return False
                    if op == "gte" and not (value and value >= threshold):
                        return False
                    if op == "lt" and not (value and value < threshold):
                        return False
                    if op == "lte" and not (value and value <= threshold):
                        return False
                    if op == "eq" and value != threshold:
                        return False
                    if op == "in" and value not in threshold:
                        return False
            else:
                if value != condition:
                    return False
        
        return True
    
    # Request management
    async def create_request(
        self,
        approval_type: ApprovalType,
        entity_type: str,
        entity_id: str,
        requester_id: str,
        requester_name: str = "",
        title: str = "",
        description: str = "",
        amount: float = 0.0,
        entity_data: dict[str, Any] = None,
        chain_id: Optional[str] = None,
        context: dict[str, Any] = None
    ) -> Optional[ApprovalRequest]:
        """Create an approval request."""
        # Find chain
        if chain_id:
            chain = self.chains.get(chain_id)
        else:
            chain = await self.find_chain(approval_type, context or {"amount": amount})
        
        if not chain:
            return None  # No approval required
        
        # Build steps from chain
        steps = []
        for approver in chain.approvers:
            steps.append(ApprovalStep(
                id=str(uuid.uuid4()),
                approver_id=approver.approver_id,
                approver_type=approver.approver_type,
                order=approver.order,
            ))
        
        # Calculate expiration
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=chain.expiration_hours)
        
        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            approval_type=approval_type,
            chain_id=chain.id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data or {},
            requester_id=requester_id,
            requester_name=requester_name,
            title=title,
            description=description,
            amount=amount,
            steps=steps,
            expires_at=expires_at,
        )
        
        self.requests[request.id] = request
        self.comments[request.id] = []
        
        return request
    
    async def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self.requests.get(request_id)
    
    async def list_requests(
        self,
        requester_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        approval_type: Optional[ApprovalType] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100
    ) -> list[ApprovalRequest]:
        """List requests."""
        requests = list(self.requests.values())
        
        if requester_id:
            requests = [r for r in requests if r.requester_id == requester_id]
        if approver_id:
            # Filter to requests where approver is in current step
            requests = [
                r for r in requests
                if r.status == ApprovalStatus.PENDING and
                r.current_step < len(r.steps) and
                r.steps[r.current_step].approver_id == approver_id
            ]
        if approval_type:
            requests = [r for r in requests if r.approval_type == approval_type]
        if status:
            requests = [r for r in requests if r.status == status]
        
        requests.sort(key=lambda r: r.submitted_at, reverse=True)
        return requests[:limit]
    
    async def get_pending_for_user(self, user_id: str) -> list[ApprovalRequest]:
        """Get pending requests where user is next approver."""
        pending = []
        
        for request in self.requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue
            if request.current_step >= len(request.steps):
                continue
            
            step = request.steps[request.current_step]
            if step.approver_id == user_id or step.delegated_to == user_id:
                pending.append(request)
        
        pending.sort(key=lambda r: r.submitted_at)
        return pending
    
    # Actions
    async def approve(
        self,
        request_id: str,
        approver_id: str,
        comments: str = ""
    ) -> bool:
        """Approve a request."""
        request = self.requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        if request.current_step >= len(request.steps):
            return False
        
        step = request.steps[request.current_step]
        
        # Verify approver
        if step.approver_id != approver_id and step.delegated_to != approver_id:
            return False
        
        # Record approval
        step.status = ApprovalStatus.APPROVED
        step.actioned_by = approver_id
        step.actioned_at = datetime.utcnow()
        step.comments = comments
        
        # Move to next step or complete
        request.current_step += 1
        
        if request.current_step >= len(request.steps):
            request.status = ApprovalStatus.APPROVED
            request.completed_at = datetime.utcnow()
            request.final_decision = "approved"
            request.final_comments = comments
        
        request.updated_at = datetime.utcnow()
        return True
    
    async def reject(
        self,
        request_id: str,
        approver_id: str,
        comments: str = ""
    ) -> bool:
        """Reject a request."""
        request = self.requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        if request.current_step >= len(request.steps):
            return False
        
        step = request.steps[request.current_step]
        
        if step.approver_id != approver_id and step.delegated_to != approver_id:
            return False
        
        # Record rejection
        step.status = ApprovalStatus.REJECTED
        step.actioned_by = approver_id
        step.actioned_at = datetime.utcnow()
        step.comments = comments
        
        # Complete request as rejected
        request.status = ApprovalStatus.REJECTED
        request.completed_at = datetime.utcnow()
        request.final_decision = "rejected"
        request.final_comments = comments
        request.updated_at = datetime.utcnow()
        
        return True
    
    async def delegate(
        self,
        request_id: str,
        approver_id: str,
        delegate_to: str,
        reason: str = ""
    ) -> bool:
        """Delegate approval to another user."""
        request = self.requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        if request.current_step >= len(request.steps):
            return False
        
        step = request.steps[request.current_step]
        
        if step.approver_id != approver_id:
            return False
        
        # Check if chain allows delegation
        chain = self.chains.get(request.chain_id)
        if chain:
            approver = next((a for a in chain.approvers if a.order == step.order), None)
            if approver and not approver.can_delegate:
                return False
        
        step.delegated_to = delegate_to
        step.delegated_at = datetime.utcnow()
        step.comments = f"Delegated to {delegate_to}: {reason}"
        request.updated_at = datetime.utcnow()
        
        return True
    
    async def escalate(
        self,
        request_id: str,
        reason: str
    ) -> bool:
        """Escalate a request."""
        request = self.requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.ESCALATED
        request.escalated = True
        request.escalated_at = datetime.utcnow()
        request.escalation_reason = reason
        request.updated_at = datetime.utcnow()
        
        return True
    
    async def withdraw(
        self,
        request_id: str,
        requester_id: str
    ) -> bool:
        """Withdraw a request."""
        request = self.requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        if request.requester_id != requester_id:
            return False
        
        request.status = ApprovalStatus.WITHDRAWN
        request.completed_at = datetime.utcnow()
        request.final_decision = "withdrawn"
        request.updated_at = datetime.utcnow()
        
        return True
    
    # Comments
    async def add_comment(
        self,
        request_id: str,
        user_id: str,
        comment: str,
        is_internal: bool = False
    ) -> Optional[ApprovalComment]:
        """Add a comment to a request."""
        if request_id not in self.requests:
            return None
        
        approval_comment = ApprovalComment(
            id=str(uuid.uuid4()),
            request_id=request_id,
            user_id=user_id,
            comment=comment,
            is_internal=is_internal,
        )
        
        self.comments[request_id].append(approval_comment)
        return approval_comment
    
    async def get_comments(
        self,
        request_id: str,
        include_internal: bool = False
    ) -> list[ApprovalComment]:
        """Get comments for a request."""
        comments = self.comments.get(request_id, [])
        
        if not include_internal:
            comments = [c for c in comments if not c.is_internal]
        
        return comments
    
    # Analytics
    async def get_analytics(
        self,
        approval_type: Optional[ApprovalType] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get approval analytics."""
        requests = list(self.requests.values())
        
        if approval_type:
            requests = [r for r in requests if r.approval_type == approval_type]
        if period_start:
            requests = [r for r in requests if r.submitted_at >= period_start]
        if period_end:
            requests = [r for r in requests if r.submitted_at <= period_end]
        
        total = len(requests)
        approved = len([r for r in requests if r.status == ApprovalStatus.APPROVED])
        rejected = len([r for r in requests if r.status == ApprovalStatus.REJECTED])
        pending = len([r for r in requests if r.status == ApprovalStatus.PENDING])
        
        # Average processing time
        completed = [r for r in requests if r.completed_at]
        avg_hours = 0
        if completed:
            total_hours = sum(
                (r.completed_at - r.submitted_at).total_seconds() / 3600
                for r in completed
            )
            avg_hours = total_hours / len(completed)
        
        return {
            "total_requests": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": approved / total if total > 0 else 0,
            "avg_processing_hours": round(avg_hours, 2),
            "by_type": self._group_by_type(requests),
        }
    
    def _group_by_type(self, requests: list[ApprovalRequest]) -> dict[str, int]:
        """Group requests by type."""
        by_type = {}
        for r in requests:
            key = r.approval_type.value
            by_type[key] = by_type.get(key, 0) + 1
        return by_type


# Singleton instance
_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    """Get approval service singleton."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service
