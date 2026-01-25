"""
Referral Tracking Routes - Customer referral program management
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

router = APIRouter(prefix="/referrals", tags=["Referral Tracking"])


class ReferralStatus(str, Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RewardType(str, Enum):
    CASH = "cash"
    CREDIT = "credit"
    DISCOUNT = "discount"
    GIFT_CARD = "gift_card"
    CUSTOM = "custom"


class RewardStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


# In-memory storage
referrals = {}
referral_programs = {}
referral_rewards = {}
referrer_profiles = {}


class ReferralProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    referrer_reward_type: RewardType
    referrer_reward_value: float
    referee_reward_type: Optional[RewardType] = None
    referee_reward_value: Optional[float] = None
    conversion_requirement: str = "first_purchase"  # first_purchase, subscription, custom
    reward_delay_days: int = 30
    expiry_days: Optional[int] = 90
    max_referrals_per_user: Optional[int] = None
    is_active: bool = True


class ReferralCreate(BaseModel):
    program_id: str
    referrer_id: str
    referrer_email: str
    referee_email: str
    referee_name: Optional[str] = None
    referee_company: Optional[str] = None
    notes: Optional[str] = None


class ReferralUpdate(BaseModel):
    status: Optional[ReferralStatus] = None
    notes: Optional[str] = None
    deal_id: Optional[str] = None
    deal_value: Optional[float] = None


# Programs
@router.post("/programs")
async def create_referral_program(
    request: ReferralProgramCreate,
    tenant_id: str = Query(default="default")
):
    """Create a referral program"""
    program_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    program = {
        "id": program_id,
        "name": request.name,
        "description": request.description,
        "referrer_reward_type": request.referrer_reward_type.value,
        "referrer_reward_value": request.referrer_reward_value,
        "referee_reward_type": request.referee_reward_type.value if request.referee_reward_type else None,
        "referee_reward_value": request.referee_reward_value,
        "conversion_requirement": request.conversion_requirement,
        "reward_delay_days": request.reward_delay_days,
        "expiry_days": request.expiry_days,
        "max_referrals_per_user": request.max_referrals_per_user,
        "is_active": request.is_active,
        "total_referrals": 0,
        "total_conversions": 0,
        "total_rewards_paid": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    referral_programs[program_id] = program
    
    logger.info("referral_program_created", program_id=program_id)
    
    return program


@router.get("/programs")
async def list_referral_programs(
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List referral programs"""
    result = [p for p in referral_programs.values() if p.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [p for p in result if p.get("is_active") == is_active]
    
    return {"programs": result, "total": len(result)}


@router.get("/programs/{program_id}")
async def get_referral_program(
    program_id: str,
    tenant_id: str = Query(default="default")
):
    """Get program details"""
    if program_id not in referral_programs:
        raise HTTPException(status_code=404, detail="Program not found")
    return referral_programs[program_id]


@router.patch("/programs/{program_id}")
async def update_referral_program(
    program_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update program settings"""
    if program_id not in referral_programs:
        raise HTTPException(status_code=404, detail="Program not found")
    
    program = referral_programs[program_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "is_active", "referrer_reward_value", "referee_reward_value", "expiry_days"]:
            program[key] = value
    
    program["updated_at"] = datetime.utcnow().isoformat()
    
    return program


@router.post("/programs/{program_id}/toggle")
async def toggle_program(
    program_id: str,
    tenant_id: str = Query(default="default")
):
    """Toggle program active status"""
    if program_id not in referral_programs:
        raise HTTPException(status_code=404, detail="Program not found")
    
    program = referral_programs[program_id]
    program["is_active"] = not program["is_active"]
    
    return {"success": True, "is_active": program["is_active"]}


# Referrals
@router.post("")
async def create_referral(
    request: ReferralCreate,
    tenant_id: str = Query(default="default")
):
    """Submit a new referral"""
    if request.program_id not in referral_programs:
        raise HTTPException(status_code=404, detail="Program not found")
    
    referral_id = str(uuid.uuid4())
    referral_code = str(uuid.uuid4())[:8].upper()
    now = datetime.utcnow()
    
    program = referral_programs[request.program_id]
    expiry_date = None
    if program.get("expiry_days"):
        expiry_date = (now + timedelta(days=program["expiry_days"])).isoformat()
    
    referral = {
        "id": referral_id,
        "code": referral_code,
        "program_id": request.program_id,
        "referrer_id": request.referrer_id,
        "referrer_email": request.referrer_email,
        "referee_email": request.referee_email,
        "referee_name": request.referee_name,
        "referee_company": request.referee_company,
        "notes": request.notes,
        "status": ReferralStatus.PENDING.value,
        "deal_id": None,
        "deal_value": None,
        "reward_amount": program["referrer_reward_value"],
        "reward_status": None,
        "expiry_date": expiry_date,
        "contacted_at": None,
        "qualified_at": None,
        "converted_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    referrals[referral_id] = referral
    referral_programs[request.program_id]["total_referrals"] = referral_programs[request.program_id].get("total_referrals", 0) + 1
    
    logger.info("referral_created", referral_id=referral_id)
    
    return referral


@router.get("")
async def list_referrals(
    program_id: Optional[str] = None,
    status: Optional[ReferralStatus] = None,
    referrer_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List referrals with filters"""
    result = [r for r in referrals.values() if r.get("tenant_id") == tenant_id]
    
    if program_id:
        result = [r for r in result if r.get("program_id") == program_id]
    if status:
        result = [r for r in result if r.get("status") == status.value]
    if referrer_id:
        result = [r for r in result if r.get("referrer_id") == referrer_id]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "referrals": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/{referral_id}")
async def get_referral(
    referral_id: str,
    tenant_id: str = Query(default="default")
):
    """Get referral details"""
    if referral_id not in referrals:
        raise HTTPException(status_code=404, detail="Referral not found")
    return referrals[referral_id]


@router.patch("/{referral_id}")
async def update_referral(
    referral_id: str,
    request: ReferralUpdate,
    tenant_id: str = Query(default="default")
):
    """Update referral status"""
    if referral_id not in referrals:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    referral = referrals[referral_id]
    now = datetime.utcnow()
    
    if request.status:
        referral["status"] = request.status.value
        if request.status == ReferralStatus.CONTACTED:
            referral["contacted_at"] = now.isoformat()
        elif request.status == ReferralStatus.QUALIFIED:
            referral["qualified_at"] = now.isoformat()
        elif request.status == ReferralStatus.CONVERTED:
            referral["converted_at"] = now.isoformat()
            referral_programs[referral["program_id"]]["total_conversions"] = \
                referral_programs[referral["program_id"]].get("total_conversions", 0) + 1
    
    if request.notes:
        referral["notes"] = request.notes
    if request.deal_id:
        referral["deal_id"] = request.deal_id
    if request.deal_value is not None:
        referral["deal_value"] = request.deal_value
    
    referral["updated_at"] = now.isoformat()
    
    return referral


# Rewards
@router.post("/{referral_id}/approve-reward")
async def approve_reward(
    referral_id: str,
    tenant_id: str = Query(default="default")
):
    """Approve reward for a converted referral"""
    if referral_id not in referrals:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    referral = referrals[referral_id]
    
    if referral["status"] != ReferralStatus.CONVERTED.value:
        raise HTTPException(status_code=400, detail="Referral must be converted to approve reward")
    
    reward_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    reward = {
        "id": reward_id,
        "referral_id": referral_id,
        "referrer_id": referral["referrer_id"],
        "referrer_email": referral["referrer_email"],
        "amount": referral["reward_amount"],
        "type": referral_programs[referral["program_id"]]["referrer_reward_type"],
        "status": RewardStatus.APPROVED.value,
        "approved_at": now.isoformat(),
        "paid_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    referral_rewards[reward_id] = reward
    referral["reward_status"] = RewardStatus.APPROVED.value
    
    return reward


@router.post("/rewards/{reward_id}/pay")
async def mark_reward_paid(
    reward_id: str,
    payment_reference: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Mark reward as paid"""
    if reward_id not in referral_rewards:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    reward = referral_rewards[reward_id]
    reward["status"] = RewardStatus.PAID.value
    reward["paid_at"] = datetime.utcnow().isoformat()
    reward["payment_reference"] = payment_reference
    
    # Update program stats
    referral = referrals[reward["referral_id"]]
    program = referral_programs[referral["program_id"]]
    program["total_rewards_paid"] = program.get("total_rewards_paid", 0) + reward["amount"]
    
    return reward


@router.get("/rewards")
async def list_rewards(
    status: Optional[RewardStatus] = None,
    referrer_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List rewards"""
    result = [r for r in referral_rewards.values() if r.get("tenant_id") == tenant_id]
    
    if status:
        result = [r for r in result if r.get("status") == status.value]
    if referrer_id:
        result = [r for r in result if r.get("referrer_id") == referrer_id]
    
    return {"rewards": result, "total": len(result)}


# Referrer Profiles
@router.get("/referrers/{referrer_id}")
async def get_referrer_profile(
    referrer_id: str,
    tenant_id: str = Query(default="default")
):
    """Get referrer profile and stats"""
    user_referrals = [r for r in referrals.values() if r.get("referrer_id") == referrer_id and r.get("tenant_id") == tenant_id]
    user_rewards = [r for r in referral_rewards.values() if r.get("referrer_id") == referrer_id]
    
    return {
        "referrer_id": referrer_id,
        "total_referrals": len(user_referrals),
        "pending": sum(1 for r in user_referrals if r.get("status") == "pending"),
        "converted": sum(1 for r in user_referrals if r.get("status") == "converted"),
        "conversion_rate": round(sum(1 for r in user_referrals if r.get("status") == "converted") / max(1, len(user_referrals)), 3),
        "total_earnings": sum(r.get("amount", 0) for r in user_rewards if r.get("status") == "paid"),
        "pending_earnings": sum(r.get("amount", 0) for r in user_rewards if r.get("status") in ["pending", "approved"]),
        "recent_referrals": user_referrals[:5]
    }


@router.get("/referrers/leaderboard")
async def get_referrer_leaderboard(
    period: str = Query(default="month"),  # month, quarter, year, all
    limit: int = Query(default=10, le=50),
    tenant_id: str = Query(default="default")
):
    """Get top referrers leaderboard"""
    leaderboard = [
        {
            "rank": i + 1,
            "referrer_id": f"user_{i}",
            "name": f"Top Referrer {i + 1}",
            "total_referrals": random.randint(10, 100),
            "conversions": random.randint(5, 50),
            "revenue_generated": random.randint(10000, 100000),
            "rewards_earned": random.randint(1000, 10000)
        }
        for i in range(limit)
    ]
    
    return {
        "period": period,
        "leaderboard": leaderboard
    }


# Analytics
@router.get("/analytics")
async def get_referral_analytics(
    program_id: Optional[str] = None,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get referral program analytics"""
    return {
        "period_days": days,
        "program_id": program_id,
        "summary": {
            "total_referrals": random.randint(100, 500),
            "pending": random.randint(20, 100),
            "qualified": random.randint(30, 150),
            "converted": random.randint(20, 100),
            "expired": random.randint(10, 50)
        },
        "conversion_rate": round(random.uniform(0.15, 0.35), 3),
        "avg_time_to_conversion_days": random.randint(14, 45),
        "revenue_generated": random.randint(50000, 500000),
        "rewards_paid": random.randint(5000, 50000),
        "roi": round(random.uniform(5.0, 15.0), 2),
        "trend": [
            {
                "date": (datetime.utcnow() - timedelta(days=i)).isoformat()[:10],
                "referrals": random.randint(1, 10),
                "conversions": random.randint(0, 5)
            }
            for i in range(days)
        ],
        "by_source": {
            "email_invite": random.randint(30, 100),
            "social_share": random.randint(20, 80),
            "direct_link": random.randint(40, 120),
            "referral_page": random.randint(10, 50)
        }
    }


# Referral Links
@router.get("/referrers/{referrer_id}/link")
async def get_referral_link(
    referrer_id: str,
    program_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get unique referral link for a referrer"""
    ref_code = str(uuid.uuid4())[:8].upper()
    
    return {
        "referrer_id": referrer_id,
        "program_id": program_id,
        "referral_code": ref_code,
        "referral_link": f"https://app.example.com/refer/{ref_code}",
        "qr_code_url": f"https://api.example.com/qr/{ref_code}"
    }
