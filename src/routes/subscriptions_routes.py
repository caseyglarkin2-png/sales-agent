"""
Subscription Routes - Subscription API Endpoints
=================================================
RESTful API for subscription and recurring revenue management.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.subscriptions import SubscriptionService, get_subscription_service


router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# Request/Response Models
class CreatePlanRequest(BaseModel):
    name: str
    description: str
    price: float
    currency: str = "USD"
    billing_period: str = "monthly"
    setup_fee: float = 0.0
    trial_days: int = 0
    is_featured: bool = False
    sort_order: int = 0


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class CreateSubscriptionRequest(BaseModel):
    account_id: str
    plan_id: str
    quantity: int = 1
    start_date: Optional[datetime] = None
    trial: bool = False
    owner_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    discount_percent: float = 0.0


class UpdateSubscriptionRequest(BaseModel):
    notes: Optional[str] = None
    auto_renew: Optional[bool] = None
    payment_method_id: Optional[str] = None


class UpgradeRequest(BaseModel):
    new_plan_id: str
    prorate: bool = True


class DowngradeRequest(BaseModel):
    new_plan_id: str
    at_period_end: bool = True


class QuantityChangeRequest(BaseModel):
    new_quantity: int
    prorate: bool = True


class CancelRequest(BaseModel):
    reason: str = ""
    at_period_end: bool = True


class PauseRequest(BaseModel):
    resume_date: Optional[datetime] = None


# Helper
def get_service() -> SubscriptionService:
    return get_subscription_service()


# Plan endpoints
@router.post("/plans")
async def create_plan(request: CreatePlanRequest):
    """Create a subscription plan."""
    service = get_service()
    from src.subscriptions.subscription_service import BillingPeriod
    
    plan = await service.create_plan(
        name=request.name,
        description=request.description,
        price=request.price,
        currency=request.currency,
        billing_period=BillingPeriod(request.billing_period),
        setup_fee=request.setup_fee,
        trial_days=request.trial_days,
        is_featured=request.is_featured,
        sort_order=request.sort_order,
    )
    
    return {"plan": plan}


@router.get("/plans")
async def list_plans(
    active_only: bool = Query(True),
    billing_period: Optional[str] = Query(None)
):
    """List subscription plans."""
    service = get_service()
    from src.subscriptions.subscription_service import BillingPeriod
    
    period_enum = BillingPeriod(billing_period) if billing_period else None
    plans = await service.list_plans(active_only=active_only, billing_period=period_enum)
    
    return {"plans": plans, "count": len(plans)}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a subscription plan."""
    service = get_service()
    plan = await service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"plan": plan}


@router.put("/plans/{plan_id}")
async def update_plan(plan_id: str, request: UpdatePlanRequest):
    """Update a subscription plan."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    plan = await service.update_plan(plan_id, updates)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"plan": plan}


# Subscription endpoints
@router.post("")
async def create_subscription(request: CreateSubscriptionRequest):
    """Create a subscription."""
    service = get_service()
    
    subscription = await service.create_subscription(
        account_id=request.account_id,
        plan_id=request.plan_id,
        quantity=request.quantity,
        start_date=request.start_date,
        trial=request.trial,
        owner_id=request.owner_id,
        payment_method_id=request.payment_method_id,
        discount_percent=request.discount_percent,
    )
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    return {"subscription": subscription}


@router.get("")
async def list_subscriptions(
    account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """List subscriptions."""
    service = get_service()
    from src.subscriptions.subscription_service import SubscriptionStatus
    
    status_enum = SubscriptionStatus(status) if status else None
    
    subscriptions = await service.list_subscriptions(
        account_id=account_id,
        status=status_enum,
        plan_id=plan_id,
        owner_id=owner_id,
        limit=limit,
    )
    
    return {"subscriptions": subscriptions, "count": len(subscriptions)}


@router.get("/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Get a subscription."""
    service = get_service()
    subscription = await service.get_subscription(subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"subscription": subscription}


@router.put("/{subscription_id}")
async def update_subscription(subscription_id: str, request: UpdateSubscriptionRequest):
    """Update a subscription."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    subscription = await service.update_subscription(subscription_id, updates)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"subscription": subscription}


# Subscription actions
@router.post("/{subscription_id}/upgrade")
async def upgrade_subscription(subscription_id: str, request: UpgradeRequest):
    """Upgrade a subscription."""
    service = get_service()
    subscription = await service.upgrade(
        subscription_id=subscription_id,
        new_plan_id=request.new_plan_id,
        prorate=request.prorate,
    )
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Cannot upgrade subscription")
    
    return {"subscription": subscription}


@router.post("/{subscription_id}/downgrade")
async def downgrade_subscription(subscription_id: str, request: DowngradeRequest):
    """Downgrade a subscription."""
    service = get_service()
    subscription = await service.downgrade(
        subscription_id=subscription_id,
        new_plan_id=request.new_plan_id,
        at_period_end=request.at_period_end,
    )
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Cannot downgrade subscription")
    
    return {"subscription": subscription}


@router.post("/{subscription_id}/quantity")
async def change_quantity(subscription_id: str, request: QuantityChangeRequest):
    """Change subscription quantity."""
    service = get_service()
    subscription = await service.change_quantity(
        subscription_id=subscription_id,
        new_quantity=request.new_quantity,
        prorate=request.prorate,
    )
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Cannot change quantity")
    
    return {"subscription": subscription}


@router.post("/{subscription_id}/cancel")
async def cancel_subscription(subscription_id: str, request: CancelRequest):
    """Cancel a subscription."""
    service = get_service()
    success = await service.cancel(
        subscription_id=subscription_id,
        reason=request.reason,
        at_period_end=request.at_period_end,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel subscription")
    
    subscription = await service.get_subscription(subscription_id)
    return {"subscription": subscription}


@router.post("/{subscription_id}/pause")
async def pause_subscription(subscription_id: str, request: PauseRequest):
    """Pause a subscription."""
    service = get_service()
    success = await service.pause(
        subscription_id=subscription_id,
        resume_date=request.resume_date,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause subscription")
    
    subscription = await service.get_subscription(subscription_id)
    return {"subscription": subscription}


@router.post("/{subscription_id}/resume")
async def resume_subscription(subscription_id: str):
    """Resume a paused subscription."""
    service = get_service()
    success = await service.resume(subscription_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume subscription")
    
    subscription = await service.get_subscription(subscription_id)
    return {"subscription": subscription}


@router.post("/{subscription_id}/renew")
async def renew_subscription(subscription_id: str):
    """Renew a subscription."""
    service = get_service()
    subscription = await service.renew(subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Cannot renew subscription")
    
    return {"subscription": subscription}


# Changes
@router.get("/{subscription_id}/changes")
async def get_changes(subscription_id: str):
    """Get subscription changes."""
    service = get_service()
    
    subscription = await service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    changes = await service.get_changes(subscription_id)
    return {"changes": changes, "count": len(changes)}


# Analytics
@router.get("/analytics/mrr")
async def get_mrr_summary():
    """Get MRR summary."""
    service = get_service()
    summary = await service.get_mrr_summary()
    return summary


@router.get("/analytics/churn")
async def get_churn_metrics(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None)
):
    """Get churn metrics."""
    service = get_service()
    metrics = await service.get_churn_metrics(
        period_start=period_start,
        period_end=period_end,
    )
    return metrics
