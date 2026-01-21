"""
Commission Calculator Routes - Sales compensation and commission management
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

router = APIRouter(prefix="/commissions", tags=["Commission Calculator"])


class CommissionType(str, Enum):
    PERCENTAGE = "percentage"
    FLAT_RATE = "flat_rate"
    TIERED = "tiered"
    ACCELERATOR = "accelerator"
    HYBRID = "hybrid"


class CommissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CLAWED_BACK = "clawed_back"


class PeriodType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


# In-memory storage
commission_plans = {}
commission_records = {}
payout_history = {}
quotas = {}


class CommissionPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    commission_type: CommissionType
    base_rate: float  # Base percentage or flat amount
    tiers: Optional[List[Dict[str, Any]]] = None  # For tiered plans
    accelerators: Optional[List[Dict[str, Any]]] = None  # For quota acceleration
    period_type: PeriodType = PeriodType.MONTHLY
    effective_date: str
    end_date: Optional[str] = None


class DealCommissionCreate(BaseModel):
    deal_id: str
    deal_value: float
    rep_id: str
    plan_id: str
    close_date: str
    product_category: Optional[str] = None
    is_new_business: bool = True
    split_with: Optional[List[Dict[str, Any]]] = None  # For split commissions


class QuotaCreate(BaseModel):
    rep_id: str
    period: str  # e.g., "2024-Q1" or "2024-01"
    period_type: PeriodType
    quota_amount: float
    quota_unit: str = "revenue"  # revenue, deals, units


# Commission Plans
@router.post("/plans")
async def create_commission_plan(
    request: CommissionPlanCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new commission plan"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    plan = {
        "id": plan_id,
        "name": request.name,
        "description": request.description,
        "commission_type": request.commission_type.value,
        "base_rate": request.base_rate,
        "tiers": request.tiers or [],
        "accelerators": request.accelerators or [],
        "period_type": request.period_type.value,
        "effective_date": request.effective_date,
        "end_date": request.end_date,
        "is_active": True,
        "assigned_reps": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    commission_plans[plan_id] = plan
    
    logger.info("commission_plan_created", plan_id=plan_id, name=request.name)
    
    return plan


@router.get("/plans")
async def list_commission_plans(
    commission_type: Optional[CommissionType] = None,
    active_only: bool = True,
    tenant_id: str = Query(default="default")
):
    """List all commission plans"""
    result = [p for p in commission_plans.values() if p.get("tenant_id") == tenant_id]
    
    if commission_type:
        result = [p for p in result if p.get("commission_type") == commission_type.value]
    if active_only:
        result = [p for p in result if p.get("is_active", True)]
    
    return {"plans": result, "total": len(result)}


@router.get("/plans/{plan_id}")
async def get_commission_plan(
    plan_id: str,
    tenant_id: str = Query(default="default")
):
    """Get commission plan details"""
    if plan_id not in commission_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    return commission_plans[plan_id]


@router.patch("/plans/{plan_id}")
async def update_commission_plan(
    plan_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update commission plan"""
    if plan_id not in commission_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = commission_plans[plan_id]
    
    allowed_fields = ["name", "description", "tiers", "accelerators", "is_active", "end_date"]
    for key, value in updates.items():
        if key in allowed_fields:
            plan[key] = value
    
    plan["updated_at"] = datetime.utcnow().isoformat()
    
    return plan


@router.post("/plans/{plan_id}/assign")
async def assign_plan_to_reps(
    plan_id: str,
    rep_ids: List[str],
    tenant_id: str = Query(default="default")
):
    """Assign commission plan to reps"""
    if plan_id not in commission_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = commission_plans[plan_id]
    plan["assigned_reps"] = list(set(plan.get("assigned_reps", []) + rep_ids))
    
    return {"message": f"Plan assigned to {len(rep_ids)} reps", "assigned_reps": plan["assigned_reps"]}


# Commission Calculation
@router.post("/calculate")
async def calculate_commission(
    request: DealCommissionCreate,
    tenant_id: str = Query(default="default")
):
    """Calculate commission for a deal"""
    commission_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get plan (use mock data if not found)
    plan = commission_plans.get(request.plan_id, {
        "commission_type": "percentage",
        "base_rate": 0.10,
        "tiers": [],
        "accelerators": []
    })
    
    # Calculate base commission
    base_rate = plan.get("base_rate", 0.10)
    base_commission = request.deal_value * base_rate
    
    # Apply tier adjustments if tiered plan
    tier_bonus = 0
    if plan.get("tiers"):
        for tier in plan["tiers"]:
            if request.deal_value >= tier.get("threshold", 0):
                tier_bonus = request.deal_value * tier.get("bonus_rate", 0)
    
    # Apply accelerators based on quota attainment
    accelerator_multiplier = 1.0
    if plan.get("accelerators"):
        # Check quota attainment
        for accel in plan["accelerators"]:
            if accel.get("attainment_pct", 0) <= 100:  # Simplified check
                accelerator_multiplier = max(accelerator_multiplier, accel.get("multiplier", 1.0))
    
    # Calculate final commission
    total_commission = (base_commission + tier_bonus) * accelerator_multiplier
    
    # Handle splits
    splits = []
    if request.split_with:
        for split in request.split_with:
            split_amount = total_commission * split.get("percentage", 0)
            splits.append({
                "rep_id": split.get("rep_id"),
                "percentage": split.get("percentage"),
                "amount": split_amount
            })
            total_commission -= split_amount
    
    commission_record = {
        "id": commission_id,
        "deal_id": request.deal_id,
        "deal_value": request.deal_value,
        "rep_id": request.rep_id,
        "plan_id": request.plan_id,
        "close_date": request.close_date,
        "base_rate": base_rate,
        "base_commission": base_commission,
        "tier_bonus": tier_bonus,
        "accelerator_multiplier": accelerator_multiplier,
        "splits": splits,
        "total_commission": total_commission,
        "status": CommissionStatus.PENDING.value,
        "tenant_id": tenant_id,
        "calculated_at": now.isoformat()
    }
    
    commission_records[commission_id] = commission_record
    
    return commission_record


@router.get("/records")
async def list_commission_records(
    rep_id: Optional[str] = None,
    status: Optional[CommissionStatus] = None,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List commission records"""
    result = [r for r in commission_records.values() if r.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [r for r in result if r.get("rep_id") == rep_id]
    if status:
        result = [r for r in result if r.get("status") == status.value]
    
    return {"records": result, "total": len(result)}


@router.get("/records/{commission_id}")
async def get_commission_record(
    commission_id: str,
    tenant_id: str = Query(default="default")
):
    """Get commission record details"""
    if commission_id not in commission_records:
        raise HTTPException(status_code=404, detail="Commission record not found")
    return commission_records[commission_id]


@router.post("/records/{commission_id}/approve")
async def approve_commission(
    commission_id: str,
    tenant_id: str = Query(default="default")
):
    """Approve a commission for payout"""
    if commission_id not in commission_records:
        raise HTTPException(status_code=404, detail="Commission record not found")
    
    record = commission_records[commission_id]
    record["status"] = CommissionStatus.APPROVED.value
    record["approved_at"] = datetime.utcnow().isoformat()
    
    return record


@router.post("/records/{commission_id}/dispute")
async def dispute_commission(
    commission_id: str,
    reason: str,
    tenant_id: str = Query(default="default")
):
    """Dispute a commission"""
    if commission_id not in commission_records:
        raise HTTPException(status_code=404, detail="Commission record not found")
    
    record = commission_records[commission_id]
    record["status"] = CommissionStatus.DISPUTED.value
    record["dispute_reason"] = reason
    record["disputed_at"] = datetime.utcnow().isoformat()
    
    return record


# Quotas
@router.post("/quotas")
async def set_quota(
    request: QuotaCreate,
    tenant_id: str = Query(default="default")
):
    """Set quota for a rep"""
    quota_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    quota = {
        "id": quota_id,
        "rep_id": request.rep_id,
        "period": request.period,
        "period_type": request.period_type.value,
        "quota_amount": request.quota_amount,
        "quota_unit": request.quota_unit,
        "attainment": 0,
        "attainment_pct": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    quotas[quota_id] = quota
    
    return quota


@router.get("/quotas")
async def list_quotas(
    rep_id: Optional[str] = None,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List quotas"""
    result = [q for q in quotas.values() if q.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [q for q in result if q.get("rep_id") == rep_id]
    if period:
        result = [q for q in result if q.get("period") == period]
    
    return {"quotas": result, "total": len(result)}


@router.get("/quotas/{rep_id}/attainment")
async def get_quota_attainment(
    rep_id: str,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get quota attainment for a rep"""
    attainment = random.uniform(0.5, 1.5)
    
    return {
        "rep_id": rep_id,
        "period": period or "2024-Q1",
        "quota": random.randint(100000, 500000),
        "attainment": round(attainment * random.randint(100000, 500000), 2),
        "attainment_pct": round(attainment * 100, 1),
        "accelerator_tier": "standard" if attainment < 1.0 else "accelerated" if attainment < 1.2 else "super_accelerated",
        "days_remaining": random.randint(10, 60)
    }


# Payouts
@router.get("/payouts")
async def list_payouts(
    rep_id: Optional[str] = None,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List commission payouts"""
    result = [p for p in payout_history.values() if p.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [p for p in result if p.get("rep_id") == rep_id]
    if period:
        result = [p for p in result if p.get("period") == period]
    
    return {"payouts": result, "total": len(result)}


@router.post("/payouts/process")
async def process_payouts(
    period: str,
    tenant_id: str = Query(default="default")
):
    """Process payouts for a period"""
    # Get approved commissions for period
    approved_commissions = [
        r for r in commission_records.values()
        if r.get("status") == CommissionStatus.APPROVED.value
        and r.get("tenant_id") == tenant_id
    ]
    
    payouts_created = []
    for record in approved_commissions:
        payout_id = str(uuid.uuid4())
        payout = {
            "id": payout_id,
            "rep_id": record.get("rep_id"),
            "period": period,
            "commission_ids": [record["id"]],
            "total_amount": record.get("total_commission"),
            "status": "processed",
            "processed_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id
        }
        payout_history[payout_id] = payout
        payouts_created.append(payout)
        
        # Mark commission as paid
        record["status"] = CommissionStatus.PAID.value
    
    return {
        "message": f"Processed {len(payouts_created)} payouts",
        "payouts": payouts_created
    }


# Statements
@router.get("/statements/{rep_id}")
async def get_commission_statement(
    rep_id: str,
    period: str,
    tenant_id: str = Query(default="default")
):
    """Get commission statement for a rep"""
    return {
        "rep_id": rep_id,
        "period": period,
        "summary": {
            "total_deals": random.randint(5, 25),
            "total_deal_value": random.randint(100000, 1000000),
            "base_commission": random.randint(10000, 100000),
            "tier_bonuses": random.randint(1000, 20000),
            "accelerator_bonus": random.randint(0, 15000),
            "splits_deducted": random.randint(0, 5000),
            "adjustments": random.randint(-1000, 1000),
            "total_earned": random.randint(15000, 120000),
            "paid_ytd": random.randint(50000, 500000)
        },
        "deals": [
            {
                "deal_id": f"deal_{i}",
                "deal_name": f"Enterprise Deal {i + 1}",
                "deal_value": random.randint(10000, 100000),
                "commission_earned": random.randint(1000, 10000),
                "close_date": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
            }
            for i in range(5)
        ],
        "quota_status": {
            "quota": random.randint(200000, 500000),
            "attainment": round(random.uniform(0.6, 1.3), 3),
            "current_tier": "accelerated"
        }
    }


# Analytics
@router.get("/analytics")
async def get_commission_analytics(
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get commission analytics"""
    return {
        "period": period or "current",
        "summary": {
            "total_commissions_earned": random.randint(500000, 2000000),
            "total_deals": random.randint(50, 200),
            "avg_commission_per_deal": random.randint(5000, 20000),
            "avg_attainment_pct": round(random.uniform(85, 115), 1)
        },
        "by_plan_type": {
            "percentage": random.randint(200000, 800000),
            "tiered": random.randint(100000, 500000),
            "accelerator": random.randint(50000, 200000)
        },
        "top_earners": [
            {"rep_id": f"user_{i}", "name": f"Rep {i + 1}", "total_earned": random.randint(50000, 200000)}
            for i in range(5)
        ],
        "payout_status": {
            "pending": random.randint(50000, 200000),
            "approved": random.randint(100000, 400000),
            "paid": random.randint(300000, 1000000),
            "disputed": random.randint(5000, 30000)
        }
    }


# Forecasting
@router.get("/forecast/{rep_id}")
async def forecast_commission(
    rep_id: str,
    periods: int = Query(default=3, ge=1, le=12),
    tenant_id: str = Query(default="default")
):
    """Forecast future commissions for a rep"""
    return {
        "rep_id": rep_id,
        "current_run_rate": random.randint(10000, 50000),
        "forecast": [
            {
                "period": f"2024-Q{i + 1}",
                "projected_deals": random.randint(10, 30),
                "projected_revenue": random.randint(100000, 500000),
                "projected_commission": random.randint(10000, 50000),
                "confidence": round(random.uniform(0.6, 0.95), 2)
            }
            for i in range(periods)
        ],
        "upside_scenarios": {
            "conservative": random.randint(100000, 150000),
            "expected": random.randint(150000, 200000),
            "optimistic": random.randint(200000, 300000)
        }
    }
