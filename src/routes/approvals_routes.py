"""
Approval Routes - Approval API Endpoints
=========================================
RESTful API for approval workflow management.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.approvals import ApprovalService, get_approval_service


router = APIRouter(prefix="/approvals", tags=["Approvals"])


# Request/Response Models
class CreateChainRequest(BaseModel):
    name: str
    description: str
    approval_type: str
    approvers: list[dict[str, Any]] = []
    require_all: bool = True
    allow_self_approval: bool = False
    allow_parallel: bool = False
    escalation_enabled: bool = True
    escalation_hours: int = 24
    expiration_hours: int = 72


class UpdateChainRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    require_all: Optional[bool] = None
    escalation_hours: Optional[int] = None
    is_active: Optional[bool] = None


class CreateRuleRequest(BaseModel):
    name: str
    description: str
    approval_type: str
    chain_id: str
    conditions: dict[str, Any]
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class CreateRequestRequest(BaseModel):
    approval_type: str
    entity_type: str
    entity_id: str
    requester_id: str
    requester_name: str = ""
    title: str = ""
    description: str = ""
    amount: float = 0.0
    entity_data: dict[str, Any] = {}
    chain_id: Optional[str] = None
    context: dict[str, Any] = {}


class ActionRequest(BaseModel):
    approver_id: str
    comments: str = ""


class DelegateRequest(BaseModel):
    approver_id: str
    delegate_to: str
    reason: str = ""


class AddCommentRequest(BaseModel):
    user_id: str
    comment: str
    is_internal: bool = False


# Helper
def get_service() -> ApprovalService:
    return get_approval_service()


# Chain endpoints
@router.post("/chains")
async def create_chain(request: CreateChainRequest):
    """Create an approval chain."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    chain = await service.create_chain(
        name=request.name,
        description=request.description,
        approval_type=ApprovalType(request.approval_type),
        approvers=request.approvers,
        require_all=request.require_all,
        allow_self_approval=request.allow_self_approval,
        allow_parallel=request.allow_parallel,
        escalation_enabled=request.escalation_enabled,
        escalation_hours=request.escalation_hours,
        expiration_hours=request.expiration_hours,
    )
    
    return {"chain": chain}


@router.get("/chains")
async def list_chains(
    approval_type: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List approval chains."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    type_enum = ApprovalType(approval_type) if approval_type else None
    chains = await service.list_chains(approval_type=type_enum, active_only=active_only)
    
    return {"chains": chains, "count": len(chains)}


@router.get("/chains/{chain_id}")
async def get_chain(chain_id: str):
    """Get an approval chain."""
    service = get_service()
    chain = await service.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return {"chain": chain}


@router.put("/chains/{chain_id}")
async def update_chain(chain_id: str, request: UpdateChainRequest):
    """Update an approval chain."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    chain = await service.update_chain(chain_id, updates)
    
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return {"chain": chain}


@router.delete("/chains/{chain_id}")
async def delete_chain(chain_id: str):
    """Delete an approval chain."""
    service = get_service()
    success = await service.delete_chain(chain_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return {"deleted": True}


# Rule endpoints
@router.post("/rules")
async def create_rule(request: CreateRuleRequest):
    """Create an approval rule."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    rule = await service.create_rule(
        name=request.name,
        description=request.description,
        approval_type=ApprovalType(request.approval_type),
        chain_id=request.chain_id,
        conditions=request.conditions,
        priority=request.priority,
    )
    
    return {"rule": rule}


@router.get("/rules")
async def list_rules(
    approval_type: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List approval rules."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    type_enum = ApprovalType(approval_type) if approval_type else None
    rules = await service.list_rules(approval_type=type_enum, active_only=active_only)
    
    return {"rules": rules, "count": len(rules)}


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get an approval rule."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"rule": rule}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, request: UpdateRuleRequest):
    """Update an approval rule."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    rule = await service.update_rule(rule_id, updates)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"rule": rule}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an approval rule."""
    service = get_service()
    success = await service.delete_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"deleted": True}


# Request endpoints
@router.post("/requests")
async def create_request(request: CreateRequestRequest):
    """Create an approval request."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    approval_request = await service.create_request(
        approval_type=ApprovalType(request.approval_type),
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        requester_id=request.requester_id,
        requester_name=request.requester_name,
        title=request.title,
        description=request.description,
        amount=request.amount,
        entity_data=request.entity_data,
        chain_id=request.chain_id,
        context=request.context,
    )
    
    if not approval_request:
        return {"message": "No approval required", "required": False}
    
    return {"request": approval_request, "required": True}


@router.get("/requests")
async def list_requests(
    requester_id: Optional[str] = Query(None),
    approver_id: Optional[str] = Query(None),
    approval_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """List approval requests."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType, ApprovalStatus
    
    type_enum = ApprovalType(approval_type) if approval_type else None
    status_enum = ApprovalStatus(status) if status else None
    
    requests = await service.list_requests(
        requester_id=requester_id,
        approver_id=approver_id,
        approval_type=type_enum,
        status=status_enum,
        limit=limit,
    )
    
    return {"requests": requests, "count": len(requests)}


@router.get("/requests/pending/{user_id}")
async def get_pending_for_user(user_id: str):
    """Get pending requests for a user."""
    service = get_service()
    requests = await service.get_pending_for_user(user_id)
    
    return {"requests": requests, "count": len(requests)}


@router.get("/requests/{request_id}")
async def get_request(request_id: str):
    """Get an approval request."""
    service = get_service()
    request = await service.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {"request": request}


# Action endpoints
@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str, request: ActionRequest):
    """Approve a request."""
    service = get_service()
    success = await service.approve(
        request_id=request_id,
        approver_id=request.approver_id,
        comments=request.comments,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve request")
    
    approval_request = await service.get_request(request_id)
    return {"request": approval_request}


@router.post("/requests/{request_id}/reject")
async def reject_request(request_id: str, request: ActionRequest):
    """Reject a request."""
    service = get_service()
    success = await service.reject(
        request_id=request_id,
        approver_id=request.approver_id,
        comments=request.comments,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot reject request")
    
    approval_request = await service.get_request(request_id)
    return {"request": approval_request}


@router.post("/requests/{request_id}/delegate")
async def delegate_request(request_id: str, request: DelegateRequest):
    """Delegate a request."""
    service = get_service()
    success = await service.delegate(
        request_id=request_id,
        approver_id=request.approver_id,
        delegate_to=request.delegate_to,
        reason=request.reason,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delegate request")
    
    approval_request = await service.get_request(request_id)
    return {"request": approval_request}


@router.post("/requests/{request_id}/escalate")
async def escalate_request(request_id: str, reason: str = Query(...)):
    """Escalate a request."""
    service = get_service()
    success = await service.escalate(request_id, reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot escalate request")
    
    approval_request = await service.get_request(request_id)
    return {"request": approval_request}


@router.post("/requests/{request_id}/withdraw")
async def withdraw_request(request_id: str, requester_id: str = Query(...)):
    """Withdraw a request."""
    service = get_service()
    success = await service.withdraw(request_id, requester_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot withdraw request")
    
    approval_request = await service.get_request(request_id)
    return {"request": approval_request}


# Comments
@router.post("/requests/{request_id}/comments")
async def add_comment(request_id: str, request: AddCommentRequest):
    """Add a comment to a request."""
    service = get_service()
    comment = await service.add_comment(
        request_id=request_id,
        user_id=request.user_id,
        comment=request.comment,
        is_internal=request.is_internal,
    )
    
    if not comment:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {"comment": comment}


@router.get("/requests/{request_id}/comments")
async def get_comments(
    request_id: str,
    include_internal: bool = Query(False)
):
    """Get comments for a request."""
    service = get_service()
    comments = await service.get_comments(request_id, include_internal)
    
    return {"comments": comments, "count": len(comments)}


# Analytics
@router.get("/analytics")
async def get_analytics(
    approval_type: Optional[str] = Query(None),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None)
):
    """Get approval analytics."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    type_enum = ApprovalType(approval_type) if approval_type else None
    analytics = await service.get_analytics(
        approval_type=type_enum,
        period_start=period_start,
        period_end=period_end,
    )
    
    return analytics


# Check if approval is required
@router.post("/check")
async def check_approval_required(
    approval_type: str = Query(...),
    context: dict[str, Any] = {}
):
    """Check if approval is required."""
    service = get_service()
    from src.approvals.approval_service import ApprovalType
    
    chain = await service.find_chain(ApprovalType(approval_type), context)
    
    return {
        "required": chain is not None,
        "chain_id": chain.id if chain else None,
        "chain_name": chain.name if chain else None,
    }
