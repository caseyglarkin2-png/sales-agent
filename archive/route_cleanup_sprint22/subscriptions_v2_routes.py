"""
Subscription Management Routes - Recurring revenue and subscription lifecycle
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/subscriptions-v2", tags=["Subscription Management V2"])


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class ChangeType(str, Enum):
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    ADDON = "addon"
    CANCELLATION = "cancellation"
    RENEWAL = "renewal"
    PAUSE = "pause"
    RESUME = "resume"


class ChurnReason(str, Enum):
    PRICE = "price"
    FEATURES = "features"
    COMPETITOR = "competitor"
    BUDGET_CUT = "budget_cut"
    COMPANY_CLOSED = "company_closed"
    NOT_USING = "not_using"
    BAD_EXPERIENCE = "bad_experience"
    MERGED = "merged"
    OTHER = "other"


class SubscriptionCreate(BaseModel):
    account_id: str
    account_name: str
    plan_id: str
    plan_name: str
    billing_interval: BillingInterval
    mrr: float
    start_date: str
    seats: Optional[int] = None
    contract_end_date: Optional[str] = None
    addons: Optional[List[Dict[str, Any]]] = None


class SubscriptionChange(BaseModel):
    subscription_id: str
    change_type: ChangeType
    new_plan_id: Optional[str] = None
    new_mrr: Optional[float] = None
    effective_date: str
    reason: Optional[str] = None


# In-memory storage
subscriptions = {}
subscription_changes = {}
renewal_forecasts = {}
churn_predictions = {}
expansion_opportunities = {}
subscription_metrics = {}
usage_data = {}
invoices = {}


# Subscriptions CRUD
@router.post("/subscriptions")
async def create_subscription(
    request: SubscriptionCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a subscription"""
    subscription_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    subscription = {
        "id": subscription_id,
        "account_id": request.account_id,
        "account_name": request.account_name,
        "plan_id": request.plan_id,
        "plan_name": request.plan_name,
        "billing_interval": request.billing_interval.value,
        "mrr": request.mrr,
        "arr": request.mrr * 12,
        "start_date": request.start_date,
        "seats": request.seats,
        "contract_end_date": request.contract_end_date,
        "addons": request.addons or [],
        "status": SubscriptionStatus.ACTIVE.value,
        "health_score": random.randint(60, 100),
        "last_invoice_date": None,
        "next_billing_date": calculate_next_billing(request.start_date, request.billing_interval),
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    subscriptions[subscription_id] = subscription
    
    logger.info("subscription_created", subscription_id=subscription_id, mrr=request.mrr)
    return subscription


@router.get("/subscriptions")
async def list_subscriptions(
    status: Optional[SubscriptionStatus] = None,
    plan_id: Optional[str] = None,
    billing_interval: Optional[BillingInterval] = None,
    min_mrr: Optional[float] = None,
    max_mrr: Optional[float] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List subscriptions"""
    result = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id]
    
    if status:
        result = [s for s in result if s.get("status") == status.value]
    if plan_id:
        result = [s for s in result if s.get("plan_id") == plan_id]
    if billing_interval:
        result = [s for s in result if s.get("billing_interval") == billing_interval.value]
    if min_mrr is not None:
        result = [s for s in result if s.get("mrr", 0) >= min_mrr]
    if max_mrr is not None:
        result = [s for s in result if s.get("mrr", 0) <= max_mrr]
    
    result.sort(key=lambda x: x.get("mrr", 0), reverse=True)
    
    return {
        "subscriptions": result[offset:offset + limit],
        "total": len(result),
        "total_mrr": sum(s.get("mrr", 0) for s in result),
        "limit": limit,
        "offset": offset
    }


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Get subscription details"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = subscriptions[subscription_id]
    changes = [c for c in subscription_changes.values() if c.get("subscription_id") == subscription_id]
    usage = usage_data.get(subscription_id, {})
    
    return {
        **sub,
        "change_history": sorted(changes, key=lambda x: x.get("effective_date", ""), reverse=True)[:10],
        "usage": usage,
        "churn_risk": random.uniform(0.05, 0.4),
        "expansion_potential": random.uniform(0.1, 0.5)
    }


@router.put("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    status: Optional[SubscriptionStatus] = None,
    seats: Optional[int] = None,
    contract_end_date: Optional[str] = None
):
    """Update subscription"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = subscriptions[subscription_id]
    
    if status is not None:
        sub["status"] = status.value
    if seats is not None:
        sub["seats"] = seats
    if contract_end_date is not None:
        sub["contract_end_date"] = contract_end_date
    
    sub["updated_at"] = datetime.utcnow().isoformat()
    
    return sub


# Subscription Changes
@router.post("/changes")
async def create_subscription_change(
    request: SubscriptionChange,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create subscription change"""
    if request.subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    change_id = str(uuid.uuid4())
    now = datetime.utcnow()
    sub = subscriptions[request.subscription_id]
    
    change = {
        "id": change_id,
        "subscription_id": request.subscription_id,
        "change_type": request.change_type.value,
        "previous_plan_id": sub["plan_id"],
        "previous_mrr": sub["mrr"],
        "new_plan_id": request.new_plan_id,
        "new_mrr": request.new_mrr,
        "mrr_delta": (request.new_mrr or 0) - sub["mrr"],
        "effective_date": request.effective_date,
        "reason": request.reason,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    subscription_changes[change_id] = change
    
    # Apply change to subscription
    if request.new_plan_id:
        sub["plan_id"] = request.new_plan_id
    if request.new_mrr is not None:
        sub["mrr"] = request.new_mrr
        sub["arr"] = request.new_mrr * 12
    
    if request.change_type == ChangeType.CANCELLATION:
        sub["status"] = SubscriptionStatus.CANCELLED.value
        sub["cancelled_at"] = request.effective_date
    elif request.change_type == ChangeType.PAUSE:
        sub["status"] = SubscriptionStatus.PAUSED.value
    elif request.change_type == ChangeType.RESUME:
        sub["status"] = SubscriptionStatus.ACTIVE.value
    
    logger.info("subscription_change_created", change_id=change_id, type=request.change_type.value)
    return change


@router.get("/changes")
async def list_subscription_changes(
    subscription_id: Optional[str] = None,
    change_type: Optional[ChangeType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List subscription changes"""
    result = [c for c in subscription_changes.values() if c.get("tenant_id") == tenant_id]
    
    if subscription_id:
        result = [c for c in result if c.get("subscription_id") == subscription_id]
    if change_type:
        result = [c for c in result if c.get("change_type") == change_type.value]
    if start_date:
        result = [c for c in result if c.get("effective_date", "") >= start_date]
    if end_date:
        result = [c for c in result if c.get("effective_date", "") <= end_date]
    
    result.sort(key=lambda x: x.get("effective_date", ""), reverse=True)
    
    return {"changes": result, "total": len(result)}


# Cancellation Flow
@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    reason: ChurnReason,
    feedback: Optional[str] = None,
    effective_date: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Cancel a subscription"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = subscriptions[subscription_id]
    now = datetime.utcnow()
    effective = effective_date or now.isoformat()[:10]
    
    cancellation = {
        "subscription_id": subscription_id,
        "reason": reason.value,
        "feedback": feedback,
        "effective_date": effective,
        "mrr_lost": sub["mrr"],
        "cancelled_by": user_id,
        "cancelled_at": now.isoformat()
    }
    
    sub["status"] = SubscriptionStatus.CANCELLED.value
    sub["cancellation"] = cancellation
    
    logger.info("subscription_cancelled", subscription_id=subscription_id, reason=reason.value)
    return cancellation


@router.post("/subscriptions/{subscription_id}/cancel-prevention")
async def get_cancel_prevention_offers(subscription_id: str):
    """Get offers to prevent cancellation"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = subscriptions[subscription_id]
    
    offers = [
        {
            "offer_type": "discount",
            "description": "20% discount for 3 months",
            "value_saved": sub["mrr"] * 0.2 * 3,
            "validity_days": 7
        },
        {
            "offer_type": "pause",
            "description": "Pause subscription for up to 3 months",
            "value_saved": sub["mrr"] * 3,
            "validity_days": 7
        },
        {
            "offer_type": "downgrade",
            "description": "Switch to a lower tier with essential features",
            "value_saved": sub["mrr"] * 0.5,
            "validity_days": 7
        },
        {
            "offer_type": "training",
            "description": "Free onboarding session to maximize value",
            "value_saved": 500,
            "validity_days": 14
        }
    ]
    
    return {
        "subscription_id": subscription_id,
        "current_mrr": sub["mrr"],
        "offers": offers,
        "recommended_offer": offers[0]
    }


# Renewals
@router.get("/renewals/upcoming")
async def get_upcoming_renewals(
    days: int = Query(default=90, ge=30, le=365),
    min_mrr: Optional[float] = None,
    tenant_id: str = Query(default="default")
):
    """Get upcoming renewals"""
    cutoff = (datetime.utcnow() + timedelta(days=days)).isoformat()[:10]
    
    tenant_subs = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id]
    
    renewals = []
    for sub in tenant_subs:
        contract_end = sub.get("contract_end_date")
        if contract_end and contract_end <= cutoff:
            if min_mrr is None or sub.get("mrr", 0) >= min_mrr:
                renewals.append({
                    "subscription_id": sub["id"],
                    "account_name": sub["account_name"],
                    "mrr": sub["mrr"],
                    "arr": sub["arr"],
                    "contract_end_date": contract_end,
                    "days_until_renewal": days_between(datetime.utcnow().isoformat()[:10], contract_end),
                    "health_score": sub.get("health_score", 50),
                    "renewal_probability": random.uniform(0.6, 0.95)
                })
    
    renewals.sort(key=lambda x: x.get("contract_end_date", ""))
    
    total_arr_at_risk = sum(r["arr"] for r in renewals)
    
    return {
        "renewals": renewals,
        "total": len(renewals),
        "total_arr_at_risk": total_arr_at_risk,
        "period_days": days
    }


@router.post("/subscriptions/{subscription_id}/renew")
async def renew_subscription(
    subscription_id: str,
    new_contract_end_date: str,
    price_change_pct: float = 0,
    user_id: str = Query(default="default")
):
    """Renew a subscription"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = subscriptions[subscription_id]
    now = datetime.utcnow()
    
    old_mrr = sub["mrr"]
    new_mrr = old_mrr * (1 + price_change_pct / 100)
    
    # Create renewal change
    change = {
        "id": str(uuid.uuid4()),
        "subscription_id": subscription_id,
        "change_type": ChangeType.RENEWAL.value,
        "previous_mrr": old_mrr,
        "new_mrr": new_mrr,
        "mrr_delta": new_mrr - old_mrr,
        "effective_date": sub.get("contract_end_date"),
        "created_by": user_id,
        "created_at": now.isoformat()
    }
    
    subscription_changes[change["id"]] = change
    
    # Update subscription
    sub["mrr"] = new_mrr
    sub["arr"] = new_mrr * 12
    sub["contract_end_date"] = new_contract_end_date
    sub["last_renewal_date"] = now.isoformat()
    sub["renewal_count"] = sub.get("renewal_count", 0) + 1
    
    logger.info("subscription_renewed", subscription_id=subscription_id, new_mrr=new_mrr)
    return sub


# Churn Prediction
@router.get("/churn/at-risk")
async def get_at_risk_subscriptions(
    risk_threshold: float = Query(default=0.3, ge=0.1, le=0.9),
    tenant_id: str = Query(default="default")
):
    """Get subscriptions at risk of churn"""
    tenant_subs = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id and s.get("status") == "active"]
    
    at_risk = []
    for sub in tenant_subs:
        risk_score = random.uniform(0.05, 0.6)
        if risk_score >= risk_threshold:
            at_risk.append({
                "subscription_id": sub["id"],
                "account_name": sub["account_name"],
                "mrr": sub["mrr"],
                "churn_risk": round(risk_score, 2),
                "risk_factors": random.sample([
                    "Low product usage",
                    "Support tickets increasing",
                    "No login in 30 days",
                    "Contract ending soon",
                    "Key user left"
                ], k=random.randint(1, 3)),
                "recommended_actions": [
                    "Schedule health check call",
                    "Send re-engagement email",
                    "Offer training session"
                ]
            })
    
    at_risk.sort(key=lambda x: x["churn_risk"], reverse=True)
    total_mrr_at_risk = sum(r["mrr"] for r in at_risk)
    
    return {
        "at_risk_subscriptions": at_risk,
        "total": len(at_risk),
        "total_mrr_at_risk": total_mrr_at_risk
    }


# Expansion
@router.get("/expansion/opportunities")
async def get_expansion_opportunities(
    min_potential: float = Query(default=100, ge=0),
    tenant_id: str = Query(default="default")
):
    """Get expansion opportunities"""
    tenant_subs = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id and s.get("status") == "active"]
    
    opportunities = []
    for sub in tenant_subs:
        potential = random.uniform(0.1, 0.5) * sub["mrr"]
        if potential >= min_potential:
            opportunities.append({
                "subscription_id": sub["id"],
                "account_name": sub["account_name"],
                "current_mrr": sub["mrr"],
                "expansion_potential": round(potential, 2),
                "expansion_type": random.choice(["upsell", "cross-sell", "seats"]),
                "signals": random.sample([
                    "High feature usage",
                    "Approaching seat limit",
                    "Growing company",
                    "Power user adoption",
                    "API usage increasing"
                ], k=random.randint(1, 3)),
                "recommended_offer": random.choice([
                    "Enterprise upgrade",
                    "Additional seats",
                    "Premium support",
                    "API access tier"
                ])
            })
    
    opportunities.sort(key=lambda x: x["expansion_potential"], reverse=True)
    total_potential = sum(o["expansion_potential"] for o in opportunities)
    
    return {
        "opportunities": opportunities,
        "total": len(opportunities),
        "total_potential_mrr": total_potential
    }


# Usage Tracking
@router.post("/subscriptions/{subscription_id}/usage")
async def record_usage(
    subscription_id: str,
    metric: str,
    value: float,
    period: Optional[str] = None
):
    """Record usage data"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    now = datetime.utcnow()
    period = period or now.isoformat()[:7]
    
    if subscription_id not in usage_data:
        usage_data[subscription_id] = {}
    if period not in usage_data[subscription_id]:
        usage_data[subscription_id][period] = {}
    
    usage_data[subscription_id][period][metric] = value
    
    return {
        "subscription_id": subscription_id,
        "metric": metric,
        "value": value,
        "period": period,
        "recorded_at": now.isoformat()
    }


@router.get("/subscriptions/{subscription_id}/usage")
async def get_usage(subscription_id: str, periods: int = Query(default=6, ge=1, le=12)):
    """Get usage data"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    usage = usage_data.get(subscription_id, {})
    
    # Generate mock data if empty
    if not usage:
        now = datetime.utcnow()
        for i in range(periods):
            period = (now - timedelta(days=30 * i)).isoformat()[:7]
            usage[period] = {
                "active_users": random.randint(10, 100),
                "api_calls": random.randint(1000, 50000),
                "storage_gb": random.uniform(1, 100),
                "feature_usage_score": random.randint(40, 100)
            }
    
    return {
        "subscription_id": subscription_id,
        "usage_by_period": dict(sorted(usage.items(), reverse=True)[:periods])
    }


# Metrics & Analytics
@router.get("/metrics/mrr")
async def get_mrr_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get MRR metrics"""
    tenant_subs = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id and s.get("status") == "active"]
    
    current_mrr = sum(s.get("mrr", 0) for s in tenant_subs)
    
    # Calculate MRR movements (mock)
    return {
        "current_mrr": current_mrr,
        "current_arr": current_mrr * 12,
        "mrr_movements": {
            "new_mrr": random.randint(5000, 20000),
            "expansion_mrr": random.randint(2000, 10000),
            "contraction_mrr": random.randint(1000, 5000),
            "churn_mrr": random.randint(2000, 8000),
            "net_new_mrr": random.randint(-2000, 10000)
        },
        "mrr_growth_rate": round(random.uniform(0.02, 0.15), 3),
        "total_subscriptions": len(tenant_subs),
        "avg_mrr_per_subscription": round(current_mrr / max(1, len(tenant_subs)), 2)
    }


@router.get("/metrics/cohort")
async def get_cohort_analysis(
    months: int = Query(default=12, ge=6, le=24),
    tenant_id: str = Query(default="default")
):
    """Get cohort retention analysis"""
    cohorts = []
    now = datetime.utcnow()
    
    for i in range(months):
        cohort_date = (now - timedelta(days=30 * i)).isoformat()[:7]
        initial_mrr = random.randint(10000, 50000)
        
        retention = []
        current = initial_mrr
        for month in range(min(i + 1, 12)):
            retention_rate = random.uniform(0.9, 0.98)
            current = current * retention_rate
            retention.append({
                "month": month + 1,
                "mrr": round(current, 2),
                "retention_pct": round(current / initial_mrr, 3)
            })
        
        cohorts.append({
            "cohort": cohort_date,
            "initial_mrr": initial_mrr,
            "initial_customers": random.randint(10, 50),
            "retention": retention
        })
    
    return {"cohorts": cohorts}


@router.get("/metrics/ltv")
async def get_ltv_metrics(tenant_id: str = Query(default="default")):
    """Get LTV metrics"""
    tenant_subs = [s for s in subscriptions.values() if s.get("tenant_id") == tenant_id]
    
    if not tenant_subs:
        return {"message": "No subscriptions found"}
    
    avg_mrr = sum(s.get("mrr", 0) for s in tenant_subs) / len(tenant_subs)
    
    return {
        "avg_customer_lifespan_months": random.randint(24, 48),
        "avg_mrr": round(avg_mrr, 2),
        "ltv": round(avg_mrr * random.randint(24, 48), 2),
        "cac": random.randint(1000, 5000),
        "ltv_cac_ratio": round(random.uniform(2.5, 5.0), 2),
        "payback_period_months": random.randint(6, 18),
        "gross_margin_pct": round(random.uniform(0.7, 0.85), 2)
    }


# Helper functions
def calculate_next_billing(start_date: str, interval: BillingInterval) -> str:
    """Calculate next billing date"""
    start = datetime.fromisoformat(start_date[:10])
    
    if interval == BillingInterval.MONTHLY:
        next_date = start + timedelta(days=30)
    elif interval == BillingInterval.QUARTERLY:
        next_date = start + timedelta(days=90)
    elif interval == BillingInterval.ANNUALLY:
        next_date = start + timedelta(days=365)
    else:
        next_date = start + timedelta(days=30)
    
    return next_date.isoformat()[:10]


def days_between(date1: str, date2: str) -> int:
    """Calculate days between two dates"""
    d1 = datetime.fromisoformat(date1)
    d2 = datetime.fromisoformat(date2)
    return (d2 - d1).days
