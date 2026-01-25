"""
Partner Management Routes - Partner and reseller channel management
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

router = APIRouter(prefix="/partners", tags=["Partner Management"])


class PartnerType(str, Enum):
    RESELLER = "reseller"
    REFERRAL = "referral"
    TECHNOLOGY = "technology"
    SOLUTION = "solution"
    CONSULTING = "consulting"
    DISTRIBUTOR = "distributor"
    AFFILIATE = "affiliate"


class PartnerTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    ELITE = "elite"


class PartnerStatus(str, Enum):
    PROSPECT = "prospect"
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CHURNED = "churned"


class DealRegistrationStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WON = "won"
    LOST = "lost"


# In-memory storage
partners = {}
partner_deals = {}
partner_activities = {}
partner_certifications = {}
mdf_requests = {}


class PartnerCreate(BaseModel):
    company_name: str
    partner_type: PartnerType
    tier: PartnerTier = PartnerTier.BRONZE
    primary_contact_name: str
    primary_contact_email: str
    primary_contact_phone: Optional[str] = None
    website: Optional[str] = None
    industry_focus: List[str] = []
    geo_coverage: List[str] = []
    commission_rate: float = 0.20
    deal_reg_protection_days: int = 90


class DealRegistrationCreate(BaseModel):
    partner_id: str
    company_name: str
    contact_name: str
    contact_email: str
    estimated_value: float
    product_interest: List[str] = []
    expected_close_date: Optional[str] = None
    notes: Optional[str] = None


class MDFRequestCreate(BaseModel):
    partner_id: str
    campaign_name: str
    campaign_type: str  # event, digital, content, etc.
    requested_amount: float
    campaign_description: str
    expected_leads: int
    start_date: str
    end_date: str


# Partner CRUD
@router.post("")
async def create_partner(
    request: PartnerCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new partner"""
    partner_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    partner = {
        "id": partner_id,
        "company_name": request.company_name,
        "partner_type": request.partner_type.value,
        "tier": request.tier.value,
        "status": PartnerStatus.PENDING.value,
        "primary_contact": {
            "name": request.primary_contact_name,
            "email": request.primary_contact_email,
            "phone": request.primary_contact_phone
        },
        "website": request.website,
        "industry_focus": request.industry_focus,
        "geo_coverage": request.geo_coverage,
        "commission_rate": request.commission_rate,
        "deal_reg_protection_days": request.deal_reg_protection_days,
        "stats": {
            "total_deals": 0,
            "won_deals": 0,
            "total_revenue": 0,
            "active_opportunities": 0,
            "certifications": 0
        },
        "partner_manager_id": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    partners[partner_id] = partner
    
    logger.info("partner_created", partner_id=partner_id)
    
    return partner


@router.get("")
async def list_partners(
    type: Optional[PartnerType] = None,
    tier: Optional[PartnerTier] = None,
    status: Optional[PartnerStatus] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List partners with filters"""
    result = [p for p in partners.values() if p.get("tenant_id") == tenant_id]
    
    if type:
        result = [p for p in result if p.get("partner_type") == type.value]
    if tier:
        result = [p for p in result if p.get("tier") == tier.value]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if search:
        result = [p for p in result if search.lower() in p.get("company_name", "").lower()]
    
    return {
        "partners": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/{partner_id}")
async def get_partner(
    partner_id: str,
    tenant_id: str = Query(default="default")
):
    """Get partner details"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partners[partner_id]


@router.patch("/{partner_id}")
async def update_partner(
    partner_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update partner information"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = partners[partner_id]
    
    for key, value in updates.items():
        if key in ["tier", "status", "commission_rate", "partner_manager_id", "industry_focus", "geo_coverage"]:
            partner[key] = value
    
    partner["updated_at"] = datetime.utcnow().isoformat()
    
    return partner


@router.post("/{partner_id}/activate")
async def activate_partner(
    partner_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate a partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partners[partner_id]["status"] = PartnerStatus.ACTIVE.value
    partners[partner_id]["activated_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "active"}


@router.post("/{partner_id}/upgrade")
async def upgrade_partner_tier(
    partner_id: str,
    new_tier: PartnerTier,
    tenant_id: str = Query(default="default")
):
    """Upgrade partner tier"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    old_tier = partners[partner_id]["tier"]
    partners[partner_id]["tier"] = new_tier.value
    partners[partner_id]["tier_upgraded_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "old_tier": old_tier, "new_tier": new_tier.value}


# Deal Registration
@router.post("/deal-registration")
async def submit_deal_registration(
    request: DealRegistrationCreate,
    tenant_id: str = Query(default="default")
):
    """Submit a deal registration"""
    if request.partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    deal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    partner = partners[request.partner_id]
    expiry_date = (now + timedelta(days=partner.get("deal_reg_protection_days", 90))).isoformat()
    
    deal = {
        "id": deal_id,
        "partner_id": request.partner_id,
        "partner_name": partner["company_name"],
        "company_name": request.company_name,
        "contact_name": request.contact_name,
        "contact_email": request.contact_email,
        "estimated_value": request.estimated_value,
        "product_interest": request.product_interest,
        "expected_close_date": request.expected_close_date,
        "notes": request.notes,
        "status": DealRegistrationStatus.SUBMITTED.value,
        "protection_expiry": expiry_date,
        "approved_discount": None,
        "reviewer_id": None,
        "reviewed_at": None,
        "tenant_id": tenant_id,
        "submitted_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    partner_deals[deal_id] = deal
    
    return deal


@router.get("/deal-registration")
async def list_deal_registrations(
    partner_id: Optional[str] = None,
    status: Optional[DealRegistrationStatus] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List deal registrations"""
    result = [d for d in partner_deals.values() if d.get("tenant_id") == tenant_id]
    
    if partner_id:
        result = [d for d in result if d.get("partner_id") == partner_id]
    if status:
        result = [d for d in result if d.get("status") == status.value]
    
    return {"deal_registrations": result, "total": len(result)}


@router.post("/deal-registration/{deal_id}/approve")
async def approve_deal_registration(
    deal_id: str,
    approved_discount: Optional[float] = None,
    tenant_id: str = Query(default="default")
):
    """Approve a deal registration"""
    if deal_id not in partner_deals:
        raise HTTPException(status_code=404, detail="Deal registration not found")
    
    deal = partner_deals[deal_id]
    deal["status"] = DealRegistrationStatus.APPROVED.value
    deal["approved_discount"] = approved_discount
    deal["reviewed_at"] = datetime.utcnow().isoformat()
    
    return deal


@router.post("/deal-registration/{deal_id}/reject")
async def reject_deal_registration(
    deal_id: str,
    reason: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Reject a deal registration"""
    if deal_id not in partner_deals:
        raise HTTPException(status_code=404, detail="Deal registration not found")
    
    deal = partner_deals[deal_id]
    deal["status"] = DealRegistrationStatus.REJECTED.value
    deal["rejection_reason"] = reason
    deal["reviewed_at"] = datetime.utcnow().isoformat()
    
    return deal


# MDF (Market Development Funds)
@router.post("/mdf")
async def submit_mdf_request(
    request: MDFRequestCreate,
    tenant_id: str = Query(default="default")
):
    """Submit MDF request"""
    if request.partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    mdf_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    mdf = {
        "id": mdf_id,
        "partner_id": request.partner_id,
        "campaign_name": request.campaign_name,
        "campaign_type": request.campaign_type,
        "requested_amount": request.requested_amount,
        "approved_amount": None,
        "campaign_description": request.campaign_description,
        "expected_leads": request.expected_leads,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "status": "submitted",
        "actual_leads": None,
        "actual_spend": None,
        "tenant_id": tenant_id,
        "submitted_at": now.isoformat()
    }
    
    mdf_requests[mdf_id] = mdf
    
    return mdf


@router.get("/mdf")
async def list_mdf_requests(
    partner_id: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List MDF requests"""
    result = [m for m in mdf_requests.values() if m.get("tenant_id") == tenant_id]
    
    if partner_id:
        result = [m for m in result if m.get("partner_id") == partner_id]
    if status:
        result = [m for m in result if m.get("status") == status]
    
    return {"mdf_requests": result, "total": len(result)}


@router.post("/mdf/{mdf_id}/approve")
async def approve_mdf_request(
    mdf_id: str,
    approved_amount: float,
    tenant_id: str = Query(default="default")
):
    """Approve MDF request"""
    if mdf_id not in mdf_requests:
        raise HTTPException(status_code=404, detail="MDF request not found")
    
    mdf_requests[mdf_id]["status"] = "approved"
    mdf_requests[mdf_id]["approved_amount"] = approved_amount
    mdf_requests[mdf_id]["approved_at"] = datetime.utcnow().isoformat()
    
    return mdf_requests[mdf_id]


# Partner Performance
@router.get("/{partner_id}/performance")
async def get_partner_performance(
    partner_id: str,
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get partner performance metrics"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return {
        "partner_id": partner_id,
        "period": period,
        "revenue": {
            "total": random.randint(100000, 1000000),
            "target": random.randint(150000, 1200000),
            "attainment": round(random.uniform(0.6, 1.2), 2)
        },
        "deals": {
            "registered": random.randint(10, 50),
            "approved": random.randint(8, 40),
            "won": random.randint(3, 20),
            "pipeline_value": random.randint(200000, 2000000)
        },
        "activity": {
            "leads_generated": random.randint(50, 300),
            "meetings_scheduled": random.randint(20, 100),
            "demos_conducted": random.randint(10, 50)
        },
        "certifications": {
            "completed": random.randint(2, 10),
            "in_progress": random.randint(0, 5)
        },
        "engagement_score": random.randint(60, 95),
        "tier_progress": {
            "current_tier": partners[partner_id]["tier"],
            "next_tier": "gold",
            "progress": round(random.uniform(0.3, 0.9), 2)
        }
    }


# Certifications
@router.post("/{partner_id}/certifications")
async def add_certification(
    partner_id: str,
    certification_name: str,
    certification_date: str,
    expiry_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Add partner certification"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    cert_id = str(uuid.uuid4())
    
    cert = {
        "id": cert_id,
        "partner_id": partner_id,
        "certification_name": certification_name,
        "certification_date": certification_date,
        "expiry_date": expiry_date,
        "status": "active",
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    partner_certifications[cert_id] = cert
    
    return cert


@router.get("/{partner_id}/certifications")
async def list_partner_certifications(
    partner_id: str,
    tenant_id: str = Query(default="default")
):
    """List partner certifications"""
    result = [c for c in partner_certifications.values() if c.get("partner_id") == partner_id]
    return {"certifications": result, "total": len(result)}


# Analytics
@router.get("/analytics/overview")
async def get_partner_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get partner program analytics"""
    all_partners = [p for p in partners.values() if p.get("tenant_id") == tenant_id]
    
    return {
        "period": period,
        "summary": {
            "total_partners": len(all_partners),
            "active_partners": sum(1 for p in all_partners if p.get("status") == "active"),
            "new_partners": random.randint(5, 20)
        },
        "by_tier": {
            "bronze": sum(1 for p in all_partners if p.get("tier") == "bronze"),
            "silver": sum(1 for p in all_partners if p.get("tier") == "silver"),
            "gold": sum(1 for p in all_partners if p.get("tier") == "gold"),
            "platinum": sum(1 for p in all_partners if p.get("tier") == "platinum")
        },
        "revenue": {
            "partner_sourced": random.randint(1000000, 5000000),
            "partner_influenced": random.randint(500000, 2000000),
            "commissions_paid": random.randint(100000, 500000)
        },
        "deals": {
            "registrations": random.randint(50, 200),
            "approved": random.randint(40, 150),
            "won": random.randint(20, 80),
            "total_value": random.randint(2000000, 10000000)
        },
        "top_partners": [
            {
                "partner_id": str(uuid.uuid4()),
                "name": f"Top Partner {i + 1}",
                "revenue": random.randint(100000, 500000)
            }
            for i in range(5)
        ]
    }


# Leaderboard
@router.get("/leaderboard")
async def get_partner_leaderboard(
    metric: str = Query(default="revenue"),  # revenue, deals, leads
    period: str = Query(default="quarter"),
    limit: int = Query(default=10, le=25),
    tenant_id: str = Query(default="default")
):
    """Get partner leaderboard"""
    leaderboard = [
        {
            "rank": i + 1,
            "partner_id": str(uuid.uuid4()),
            "company_name": f"Partner Company {i + 1}",
            "tier": random.choice(["bronze", "silver", "gold", "platinum"]),
            "value": random.randint(50000, 500000),
            "change_from_previous": random.randint(-20, 30)
        }
        for i in range(limit)
    ]
    
    return {
        "metric": metric,
        "period": period,
        "leaderboard": leaderboard
    }
