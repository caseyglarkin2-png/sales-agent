"""
Commission Routes - Commission API Endpoints
=============================================
RESTful API for commission management.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.commissions import CommissionService, get_commission_service


router = APIRouter(prefix="/commissions", tags=["Commissions"])


# Request/Response Models
class CreatePlanRequest(BaseModel):
    name: str
    description: str
    plan_type: str = "percentage"
    base_rate: float = 0.0
    accelerator_threshold: float = 100.0
    accelerator_rate: float = 0.0
    payout_frequency: str = "monthly"
    trigger_event: str = "deal_won"
    clawback_enabled: bool = False
    clawback_period_days: int = 90
    user_ids: list[str] = []
    role_ids: list[str] = []


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_rate: Optional[float] = None
    accelerator_threshold: Optional[float] = None
    accelerator_rate: Optional[float] = None
    payout_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class AddTierRequest(BaseModel):
    min_amount: float
    max_amount: Optional[float] = None
    rate: float
    is_percentage_based: bool = True


class AddRuleRequest(BaseModel):
    name: str
    description: str
    condition: dict[str, Any]
    modifier_type: str  # multiplier, bonus, penalty
    modifier_value: float


class CalculateCommissionRequest(BaseModel):
    user_id: str
    deal_id: str
    deal_amount: float
    plan_id: Optional[str] = None
    quota_attainment: float = 0.0
    deal_metadata: Optional[dict[str, Any]] = None


class SplitCommissionRequest(BaseModel):
    splits: list[dict[str, Any]]  # [{user_id, percentage}]


class UpdateCommissionRequest(BaseModel):
    adjusted_amount: Optional[float] = None
    notes: Optional[str] = None


class CreatePayoutRequest(BaseModel):
    user_id: str
    period_start: datetime
    period_end: datetime


class ProcessPayoutRequest(BaseModel):
    payment_method: str
    payment_reference: str


# Helper
def get_service() -> CommissionService:
    return get_commission_service()


# Plan endpoints
@router.post("/plans")
async def create_plan(request: CreatePlanRequest):
    """Create a commission plan."""
    service = get_service()
    from src.commissions.commission_service import PlanType, PayoutFrequency, TriggerEvent
    
    plan = await service.create_plan(
        name=request.name,
        description=request.description,
        plan_type=PlanType(request.plan_type),
        base_rate=request.base_rate,
        accelerator_threshold=request.accelerator_threshold,
        accelerator_rate=request.accelerator_rate,
        payout_frequency=PayoutFrequency(request.payout_frequency),
        trigger_event=TriggerEvent(request.trigger_event),
        clawback_enabled=request.clawback_enabled,
        clawback_period_days=request.clawback_period_days,
        user_ids=request.user_ids,
        role_ids=request.role_ids,
    )
    
    return {"plan": plan}


@router.get("/plans")
async def list_plans(
    active_only: bool = Query(True),
    user_id: Optional[str] = Query(None)
):
    """List commission plans."""
    service = get_service()
    plans = await service.list_plans(active_only=active_only, user_id=user_id)
    return {"plans": plans, "count": len(plans)}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a commission plan."""
    service = get_service()
    plan = await service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"plan": plan}


@router.put("/plans/{plan_id}")
async def update_plan(plan_id: str, request: UpdatePlanRequest):
    """Update a commission plan."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    plan = await service.update_plan(plan_id, updates)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"plan": plan}


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a commission plan."""
    service = get_service()
    success = await service.delete_plan(plan_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"deleted": True}


# Tier endpoints
@router.post("/plans/{plan_id}/tiers")
async def add_tier(plan_id: str, request: AddTierRequest):
    """Add a tier to a plan."""
    service = get_service()
    tier = await service.add_tier(
        plan_id=plan_id,
        min_amount=request.min_amount,
        max_amount=request.max_amount,
        rate=request.rate,
        is_percentage_based=request.is_percentage_based,
    )
    
    if not tier:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"tier": tier}


@router.delete("/plans/{plan_id}/tiers/{tier_id}")
async def remove_tier(plan_id: str, tier_id: str):
    """Remove a tier from a plan."""
    service = get_service()
    success = await service.remove_tier(plan_id, tier_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Plan or tier not found")
    
    return {"deleted": True}


# Rule endpoints
@router.post("/plans/{plan_id}/rules")
async def add_rule(plan_id: str, request: AddRuleRequest):
    """Add a rule to a plan."""
    service = get_service()
    rule = await service.add_rule(
        plan_id=plan_id,
        name=request.name,
        description=request.description,
        condition=request.condition,
        modifier_type=request.modifier_type,
        modifier_value=request.modifier_value,
    )
    
    if not rule:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"rule": rule}


# Commission endpoints
@router.post("/calculate")
async def calculate_commission(request: CalculateCommissionRequest):
    """Calculate commission for a deal."""
    service = get_service()
    commission = await service.calculate_commission(
        user_id=request.user_id,
        deal_id=request.deal_id,
        deal_amount=request.deal_amount,
        plan_id=request.plan_id,
        quota_attainment=request.quota_attainment,
        deal_metadata=request.deal_metadata,
    )
    
    if not commission:
        raise HTTPException(status_code=400, detail="No applicable plan found")
    
    return {"commission": commission}


@router.get("")
async def list_commissions(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000)
):
    """List commissions."""
    service = get_service()
    from src.commissions.commission_service import CommissionStatus
    
    status_enum = CommissionStatus(status) if status else None
    
    commissions = await service.list_commissions(
        user_id=user_id,
        status=status_enum,
        period_start=period_start,
        period_end=period_end,
        limit=limit,
    )
    
    return {"commissions": commissions, "count": len(commissions)}


@router.get("/{commission_id}")
async def get_commission(commission_id: str):
    """Get a commission."""
    service = get_service()
    commission = await service.get_commission(commission_id)
    
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    return {"commission": commission}


@router.put("/{commission_id}")
async def update_commission(commission_id: str, request: UpdateCommissionRequest):
    """Update a commission."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    commission = await service.update_commission(commission_id, updates)
    
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    return {"commission": commission}


# Split endpoint
@router.post("/{commission_id}/split")
async def split_commission(commission_id: str, request: SplitCommissionRequest):
    """Split a commission between users."""
    service = get_service()
    
    # Validate splits total 100%
    total = sum(s.get("percentage", 0) for s in request.splits)
    if abs(total - 100) > 0.01:
        raise HTTPException(status_code=400, detail="Splits must total 100%")
    
    commissions = await service.split_commission(commission_id, request.splits)
    
    if not commissions:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    return {"commissions": commissions, "count": len(commissions)}


# Status workflow endpoints
@router.post("/{commission_id}/approve")
async def approve_commission(commission_id: str, approver_id: str = Query(...)):
    """Approve a commission."""
    service = get_service()
    success = await service.approve_commission(commission_id, approver_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve commission")
    
    commission = await service.get_commission(commission_id)
    return {"commission": commission}


@router.post("/{commission_id}/hold")
async def hold_commission(commission_id: str, reason: str = Query(...)):
    """Put a commission on hold."""
    service = get_service()
    success = await service.hold_commission(commission_id, reason)
    
    if not success:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    commission = await service.get_commission(commission_id)
    return {"commission": commission}


@router.post("/{commission_id}/clawback")
async def clawback_commission(
    commission_id: str,
    reason: str = Query(...),
    amount: Optional[float] = Query(None)
):
    """Clawback a commission."""
    service = get_service()
    success = await service.clawback_commission(commission_id, reason, amount)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot clawback commission")
    
    commission = await service.get_commission(commission_id)
    return {"commission": commission}


# Payout endpoints
@router.post("/payouts")
async def create_payout(request: CreatePayoutRequest):
    """Create a payout for approved commissions."""
    service = get_service()
    payout = await service.create_payout(
        user_id=request.user_id,
        period_start=request.period_start,
        period_end=request.period_end,
    )
    return {"payout": payout}


@router.get("/payouts")
async def list_payouts(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List payouts."""
    service = get_service()
    payouts = await service.list_payouts(user_id=user_id, status=status)
    return {"payouts": payouts, "count": len(payouts)}


@router.get("/payouts/{payout_id}")
async def get_payout(payout_id: str):
    """Get a payout."""
    service = get_service()
    payout = await service.get_payout(payout_id)
    
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    return {"payout": payout}


@router.post("/payouts/{payout_id}/process")
async def process_payout(payout_id: str, request: ProcessPayoutRequest):
    """Process a payout."""
    service = get_service()
    success = await service.process_payout(
        payout_id=payout_id,
        payment_method=request.payment_method,
        payment_reference=request.payment_reference,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot process payout")
    
    payout = await service.get_payout(payout_id)
    return {"payout": payout}


# Analytics endpoints
@router.get("/analytics/summary/{user_id}")
async def get_commission_summary(
    user_id: str,
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None)
):
    """Get commission summary for a user."""
    service = get_service()
    summary = await service.get_commission_summary(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
    )
    return summary


@router.get("/analytics/leaderboard")
async def get_team_leaderboard(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    limit: int = Query(10, le=100)
):
    """Get team commission leaderboard."""
    service = get_service()
    leaderboard = await service.get_team_leaderboard(
        period_start=period_start,
        period_end=period_end,
        limit=limit,
    )
    return {"leaderboard": leaderboard}
