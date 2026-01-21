"""
Sales Compensation Routes - Commission plans, payouts, and compensation management
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

router = APIRouter(prefix="/compensation-v2", tags=["Sales Compensation V2"])


class CompensationType(str, Enum):
    COMMISSION = "commission"
    BONUS = "bonus"
    SPIFF = "spiff"
    ACCELERATOR = "accelerator"
    DRAW = "draw"


class CompStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class PayoutStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    PAID = "paid"
    DISPUTED = "disputed"


class PeriodType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class TierType(str, Enum):
    FLAT = "flat"
    TIERED = "tiered"
    ACCELERATOR = "accelerator"
    DECELERATOR = "decelerator"


# In-memory storage
comp_plans = {}
earnings = {}
payouts = {}
adjustments = {}
spiffs = {}


class TierCreate(BaseModel):
    min_attainment: float  # e.g., 0.0 = 0%
    max_attainment: Optional[float] = None  # None = unlimited
    rate: float  # e.g., 0.10 = 10%


class CompPlanCreate(BaseModel):
    name: str
    period_type: PeriodType
    base_rate: float
    quota: float
    on_target_earnings: float
    compensation_type: CompensationType = CompensationType.COMMISSION
    tiers: Optional[List[TierCreate]] = None
    tier_type: TierType = TierType.FLAT


class EarningCreate(BaseModel):
    rep_id: str
    deal_id: str
    deal_name: str
    deal_amount: float
    plan_id: str
    commission_rate: float


class AdjustmentCreate(BaseModel):
    rep_id: str
    adjustment_type: str  # bonus, deduction, correction
    amount: float
    reason: str
    period: str


# Compensation Plans
@router.post("/plans")
async def create_comp_plan(
    request: CompPlanCreate,
    tenant_id: str = Query(default="default")
):
    """Create a compensation plan"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    plan = {
        "id": plan_id,
        "name": request.name,
        "period_type": request.period_type.value,
        "base_rate": request.base_rate,
        "quota": request.quota,
        "on_target_earnings": request.on_target_earnings,
        "compensation_type": request.compensation_type.value,
        "tier_type": request.tier_type.value,
        "tiers": [
            {
                "min_attainment": t.min_attainment,
                "max_attainment": t.max_attainment,
                "rate": t.rate
            }
            for t in (request.tiers or [])
        ],
        "status": CompStatus.ACTIVE.value,
        "assigned_reps": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    comp_plans[plan_id] = plan
    
    return plan


@router.get("/plans")
async def list_comp_plans(
    status: Optional[CompStatus] = None,
    period_type: Optional[PeriodType] = None,
    tenant_id: str = Query(default="default")
):
    """List compensation plans"""
    result = [p for p in comp_plans.values() if p.get("tenant_id") == tenant_id]
    
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if period_type:
        result = [p for p in result if p.get("period_type") == period_type.value]
    
    return {"plans": result, "total": len(result)}


@router.get("/plans/{plan_id}")
async def get_comp_plan(
    plan_id: str,
    tenant_id: str = Query(default="default")
):
    """Get compensation plan by ID"""
    plan = comp_plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/plans/{plan_id}/assign")
async def assign_plan_to_rep(
    plan_id: str,
    rep_id: str,
    effective_date: Optional[datetime] = None,
    tenant_id: str = Query(default="default")
):
    """Assign a compensation plan to a rep"""
    plan = comp_plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    assignment = {
        "rep_id": rep_id,
        "effective_date": (effective_date or datetime.utcnow()).isoformat(),
        "assigned_at": datetime.utcnow().isoformat()
    }
    
    plan["assigned_reps"].append(assignment)
    
    return {"plan_id": plan_id, "rep_id": rep_id, "assignment": assignment}


# Earnings
@router.post("/earnings")
async def record_earning(
    request: EarningCreate,
    tenant_id: str = Query(default="default")
):
    """Record a commission earning"""
    earning_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    commission_amount = request.deal_amount * request.commission_rate
    
    earning = {
        "id": earning_id,
        "rep_id": request.rep_id,
        "deal_id": request.deal_id,
        "deal_name": request.deal_name,
        "deal_amount": request.deal_amount,
        "plan_id": request.plan_id,
        "commission_rate": request.commission_rate,
        "commission_amount": commission_amount,
        "status": PayoutStatus.PENDING.value,
        "period": now.strftime("%Y-%m"),
        "tenant_id": tenant_id,
        "earned_at": now.isoformat()
    }
    
    earnings[earning_id] = earning
    
    return earning


@router.get("/earnings")
async def list_earnings(
    rep_id: Optional[str] = None,
    period: Optional[str] = None,
    status: Optional[PayoutStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List earnings"""
    result = [e for e in earnings.values() if e.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [e for e in result if e.get("rep_id") == rep_id]
    if period:
        result = [e for e in result if e.get("period") == period]
    if status:
        result = [e for e in result if e.get("status") == status.value]
    
    return {
        "earnings": result,
        "total": len(result),
        "total_amount": sum(e.get("commission_amount", 0) for e in result)
    }


@router.get("/earnings/{rep_id}/summary")
async def get_rep_earnings_summary(
    rep_id: str,
    period: str = Query(default=None),
    tenant_id: str = Query(default="default")
):
    """Get earnings summary for a rep"""
    now = datetime.utcnow()
    current_period = period or now.strftime("%Y-%m")
    
    return {
        "rep_id": rep_id,
        "period": current_period,
        "summary": {
            "quota": random.randint(300000, 800000),
            "attainment": random.randint(200000, 900000),
            "attainment_pct": round(random.uniform(0.60, 1.30), 2),
            "base_commission": random.randint(5000, 25000),
            "accelerator_bonus": random.randint(0, 10000),
            "spiffs_earned": random.randint(0, 5000),
            "adjustments": random.randint(-1000, 2000),
            "total_earnings": random.randint(8000, 40000)
        },
        "deals_credited": random.randint(3, 15),
        "avg_commission_rate": round(random.uniform(0.08, 0.15), 3),
        "ytd_earnings": random.randint(50000, 200000),
        "ytd_attainment_pct": round(random.uniform(0.70, 1.20), 2)
    }


# Payouts
@router.post("/payouts/process")
async def process_payouts(
    period: str,
    tenant_id: str = Query(default="default")
):
    """Process payouts for a period"""
    payout_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get pending earnings for period
    period_earnings = [e for e in earnings.values() 
                       if e.get("period") == period 
                       and e.get("status") == PayoutStatus.PENDING.value
                       and e.get("tenant_id") == tenant_id]
    
    # Group by rep
    rep_payouts = {}
    for e in period_earnings:
        rep_id = e["rep_id"]
        if rep_id not in rep_payouts:
            rep_payouts[rep_id] = {"earnings": [], "total": 0}
        rep_payouts[rep_id]["earnings"].append(e)
        rep_payouts[rep_id]["total"] += e.get("commission_amount", 0)
    
    payout = {
        "id": payout_id,
        "period": period,
        "status": PayoutStatus.PROCESSING.value,
        "rep_payouts": [
            {
                "rep_id": rep_id,
                "total_amount": data["total"],
                "earning_count": len(data["earnings"]),
                "status": PayoutStatus.PROCESSING.value
            }
            for rep_id, data in rep_payouts.items()
        ],
        "total_payout": sum(data["total"] for data in rep_payouts.values()),
        "tenant_id": tenant_id,
        "processed_at": now.isoformat()
    }
    
    payouts[payout_id] = payout
    
    return payout


@router.get("/payouts")
async def list_payouts(
    period: Optional[str] = None,
    status: Optional[PayoutStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List payouts"""
    result = [p for p in payouts.values() if p.get("tenant_id") == tenant_id]
    
    if period:
        result = [p for p in result if p.get("period") == period]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    
    return {"payouts": result, "total": len(result)}


@router.post("/payouts/{payout_id}/approve")
async def approve_payout(
    payout_id: str,
    approved_by: str,
    tenant_id: str = Query(default="default")
):
    """Approve a payout"""
    payout = payouts.get(payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    payout["status"] = PayoutStatus.APPROVED.value
    payout["approved_by"] = approved_by
    payout["approved_at"] = datetime.utcnow().isoformat()
    
    return payout


# Adjustments
@router.post("/adjustments")
async def create_adjustment(
    request: AdjustmentCreate,
    tenant_id: str = Query(default="default")
):
    """Create a compensation adjustment"""
    adjustment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    adjustment = {
        "id": adjustment_id,
        "rep_id": request.rep_id,
        "adjustment_type": request.adjustment_type,
        "amount": request.amount,
        "reason": request.reason,
        "period": request.period,
        "status": "pending",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    adjustments[adjustment_id] = adjustment
    
    return adjustment


@router.get("/adjustments")
async def list_adjustments(
    rep_id: Optional[str] = None,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List adjustments"""
    result = [a for a in adjustments.values() if a.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [a for a in result if a.get("rep_id") == rep_id]
    if period:
        result = [a for a in result if a.get("period") == period]
    
    return {"adjustments": result, "total": len(result)}


# SPIFFs
@router.post("/spiffs")
async def create_spiff(
    name: str,
    description: str,
    amount: float,
    criteria: Dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    tenant_id: str = Query(default="default")
):
    """Create a SPIFF (Special Performance Incentive Fund)"""
    spiff_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    spiff = {
        "id": spiff_id,
        "name": name,
        "description": description,
        "amount": amount,
        "criteria": criteria,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": "active",
        "claims": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    spiffs[spiff_id] = spiff
    
    return spiff


@router.get("/spiffs")
async def list_spiffs(
    active_only: bool = True,
    tenant_id: str = Query(default="default")
):
    """List SPIFFs"""
    result = [s for s in spiffs.values() if s.get("tenant_id") == tenant_id]
    
    if active_only:
        result = [s for s in result if s.get("status") == "active"]
    
    return {"spiffs": result, "total": len(result)}


@router.post("/spiffs/{spiff_id}/claim")
async def claim_spiff(
    spiff_id: str,
    rep_id: str,
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Claim a SPIFF for a deal"""
    spiff = spiffs.get(spiff_id)
    if not spiff:
        raise HTTPException(status_code=404, detail="SPIFF not found")
    
    claim = {
        "id": str(uuid.uuid4()),
        "rep_id": rep_id,
        "deal_id": deal_id,
        "amount": spiff["amount"],
        "status": "pending",
        "claimed_at": datetime.utcnow().isoformat()
    }
    
    spiff["claims"].append(claim)
    
    return claim


# Statements
@router.get("/statements/{rep_id}")
async def get_comp_statement(
    rep_id: str,
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get compensation statement for a rep"""
    now = datetime.utcnow()
    current_period = period or now.strftime("%Y-%m")
    
    deal_earnings = []
    for i in range(random.randint(3, 10)):
        deal_earnings.append({
            "deal_id": str(uuid.uuid4()),
            "deal_name": f"Deal {i + 1}",
            "close_date": (now - timedelta(days=random.randint(1, 25))).isoformat(),
            "deal_amount": random.randint(20000, 150000),
            "commission_rate": round(random.uniform(0.08, 0.15), 3),
            "commission_amount": random.randint(2000, 15000)
        })
    
    return {
        "rep_id": rep_id,
        "period": current_period,
        "statement_date": now.isoformat(),
        "quota": random.randint(400000, 1000000),
        "attainment": {
            "deals_closed": len(deal_earnings),
            "total_bookings": sum(d["deal_amount"] for d in deal_earnings),
            "quota_pct": round(random.uniform(0.60, 1.30), 2)
        },
        "earnings_detail": {
            "base_commission": sum(d["commission_amount"] for d in deal_earnings),
            "accelerator": random.randint(0, 8000),
            "spiffs": random.randint(0, 3000),
            "adjustments": random.randint(-500, 1000)
        },
        "deal_earnings": deal_earnings,
        "total_earnings": random.randint(10000, 50000),
        "ytd_earnings": random.randint(60000, 250000),
        "status": "finalized"
    }


# Analytics
@router.get("/analytics")
async def get_comp_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get compensation analytics"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_commissions_paid": random.randint(500000, 2000000),
            "total_quota": random.randint(10000000, 30000000),
            "overall_attainment": round(random.uniform(0.80, 1.10), 2),
            "reps_above_quota_pct": round(random.uniform(0.35, 0.55), 2),
            "avg_earnings_per_rep": random.randint(15000, 50000),
            "top_earner": random.randint(60000, 150000)
        },
        "distribution": {
            "below_50_pct": random.randint(2, 8),
            "50_to_100_pct": random.randint(15, 40),
            "100_to_150_pct": random.randint(10, 25),
            "above_150_pct": random.randint(2, 8)
        },
        "cost_metrics": {
            "commission_to_revenue_ratio": round(random.uniform(0.08, 0.15), 3),
            "cost_per_rep": random.randint(80000, 150000),
            "roi_on_incentives": round(random.uniform(3.0, 6.0), 1)
        },
        "trends": {
            "earnings_vs_prior": round(random.uniform(-0.05, 0.15), 2),
            "attainment_vs_prior": round(random.uniform(-0.05, 0.10), 2)
        }
    }


# Quota Management
@router.get("/quotas")
async def get_quotas(
    period_type: PeriodType = PeriodType.QUARTERLY,
    tenant_id: str = Query(default="default")
):
    """Get quota assignments"""
    quotas = []
    for i in range(random.randint(10, 25)):
        quota_amount = random.randint(300000, 1000000)
        attainment = random.randint(150000, 1200000)
        quotas.append({
            "rep_id": f"rep_{i}",
            "rep_name": f"Sales Rep {i + 1}",
            "quota": quota_amount,
            "attainment": attainment,
            "attainment_pct": round(attainment / quota_amount, 2),
            "deals_closed": random.randint(2, 15),
            "pipeline": random.randint(500000, 2000000)
        })
    
    return {
        "period_type": period_type.value,
        "quotas": quotas,
        "total_quota": sum(q["quota"] for q in quotas),
        "total_attainment": sum(q["attainment"] for q in quotas)
    }


@router.post("/quotas/{rep_id}")
async def set_quota(
    rep_id: str,
    quota: float,
    period: str,
    effective_date: Optional[datetime] = None,
    tenant_id: str = Query(default="default")
):
    """Set quota for a rep"""
    return {
        "rep_id": rep_id,
        "quota": quota,
        "period": period,
        "effective_date": (effective_date or datetime.utcnow()).isoformat(),
        "status": "active"
    }
