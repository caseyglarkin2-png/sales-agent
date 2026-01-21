"""
Partner Portal Routes - Channel partner and reseller management
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/partner-portal", tags=["Partner Portal"])


class PartnerType(str, Enum):
    RESELLER = "reseller"
    REFERRAL = "referral"
    AFFILIATE = "affiliate"
    DISTRIBUTOR = "distributor"
    TECHNOLOGY = "technology"
    CONSULTING = "consulting"
    MSP = "msp"
    VAR = "var"


class PartnerTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class PartnerStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class DealRegStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WON = "won"
    LOST = "lost"


class PartnerCreate(BaseModel):
    name: str
    company: str
    partner_type: PartnerType
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    specializations: Optional[List[str]] = None
    commission_rate: float = Field(default=10.0, ge=0, le=50)


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    tier: Optional[PartnerTier] = None
    status: Optional[PartnerStatus] = None
    commission_rate: Optional[float] = None
    specializations: Optional[List[str]] = None


class DealRegistrationCreate(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_phone: Optional[str] = None
    customer_contact: Optional[str] = None
    opportunity_name: str
    opportunity_value: float = Field(ge=0)
    product_interest: Optional[List[str]] = None
    expected_close_date: str
    description: Optional[str] = None


class DealRegistrationReview(BaseModel):
    approved: bool
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ResourceCreate(BaseModel):
    title: str
    description: Optional[str] = None
    resource_type: str  # document, video, training, template
    category: str
    file_url: Optional[str] = None
    external_url: Optional[str] = None
    access_tiers: Optional[List[PartnerTier]] = None
    is_featured: bool = False


class PartnerUserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "member"  # admin, manager, member


# In-memory storage
partners = {}
deal_registrations = {}
resources = {}
partner_users = {}
partner_activities = {}


@router.post("/partners")
async def create_partner(
    request: PartnerCreate,
    tenant_id: str = Query(default="default")
):
    """Register a new partner"""
    import uuid
    
    partner_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    partner = {
        "id": partner_id,
        "name": request.name,
        "company": request.company,
        "partner_type": request.partner_type.value,
        "tier": PartnerTier.BRONZE.value,
        "status": PartnerStatus.PENDING.value,
        "contact_name": request.contact_name,
        "contact_email": request.contact_email,
        "contact_phone": request.contact_phone,
        "website": request.website,
        "address": request.address or {},
        "specializations": request.specializations or [],
        "commission_rate": request.commission_rate,
        "deal_registration_enabled": True,
        "portal_access": True,
        "onboarding_completed": False,
        "total_revenue": 0,
        "total_deals": 0,
        "active_deals": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    partners[partner_id] = partner
    partner_users[partner_id] = []
    
    logger.info("partner_created", partner_id=partner_id, company=request.company)
    return partner


@router.get("/partners")
async def list_partners(
    partner_type: Optional[PartnerType] = None,
    tier: Optional[PartnerTier] = None,
    status: Optional[PartnerStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List partners"""
    result = [p for p in partners.values() if p.get("tenant_id") == tenant_id]
    
    if partner_type:
        result = [p for p in result if p.get("partner_type") == partner_type.value]
    if tier:
        result = [p for p in result if p.get("tier") == tier.value]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)
    
    return {
        "partners": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/partners/{partner_id}")
async def get_partner(partner_id: str):
    """Get partner details"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partners[partner_id]


@router.put("/partners/{partner_id}")
async def update_partner(partner_id: str, request: PartnerUpdate):
    """Update partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = partners[partner_id]
    
    if request.name is not None:
        partner["name"] = request.name
    if request.contact_name is not None:
        partner["contact_name"] = request.contact_name
    if request.contact_email is not None:
        partner["contact_email"] = request.contact_email
    if request.contact_phone is not None:
        partner["contact_phone"] = request.contact_phone
    if request.website is not None:
        partner["website"] = request.website
    if request.tier is not None:
        partner["tier"] = request.tier.value
    if request.status is not None:
        partner["status"] = request.status.value
    if request.commission_rate is not None:
        partner["commission_rate"] = request.commission_rate
    if request.specializations is not None:
        partner["specializations"] = request.specializations
    
    partner["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("partner_updated", partner_id=partner_id)
    return partner


@router.post("/partners/{partner_id}/approve")
async def approve_partner(
    partner_id: str,
    reviewer_id: str = Query(default="default")
):
    """Approve a pending partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = partners[partner_id]
    partner["status"] = PartnerStatus.ACTIVE.value
    partner["approved_by"] = reviewer_id
    partner["approved_at"] = datetime.utcnow().isoformat()
    partner["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("partner_approved", partner_id=partner_id)
    return partner


@router.post("/partners/{partner_id}/suspend")
async def suspend_partner(
    partner_id: str,
    reason: Optional[str] = None
):
    """Suspend a partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = partners[partner_id]
    partner["status"] = PartnerStatus.SUSPENDED.value
    partner["suspension_reason"] = reason
    partner["suspended_at"] = datetime.utcnow().isoformat()
    partner["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("partner_suspended", partner_id=partner_id)
    return partner


@router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str):
    """Delete a partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    del partners[partner_id]
    if partner_id in partner_users:
        del partner_users[partner_id]
    
    logger.info("partner_deleted", partner_id=partner_id)
    return {"status": "deleted", "partner_id": partner_id}


# Deal Registrations
@router.post("/partners/{partner_id}/deal-registrations")
async def create_deal_registration(
    partner_id: str,
    request: DealRegistrationCreate,
    tenant_id: str = Query(default="default")
):
    """Create a deal registration"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    import uuid
    from datetime import timedelta
    
    registration_id = str(uuid.uuid4())
    now = datetime.utcnow()
    partner = partners[partner_id]
    
    registration = {
        "id": registration_id,
        "partner_id": partner_id,
        "partner_name": partner["name"],
        "customer_name": request.customer_name,
        "customer_email": request.customer_email,
        "customer_phone": request.customer_phone,
        "customer_contact": request.customer_contact,
        "opportunity_name": request.opportunity_name,
        "opportunity_value": request.opportunity_value,
        "product_interest": request.product_interest or [],
        "expected_close_date": request.expected_close_date,
        "description": request.description,
        "status": DealRegStatus.SUBMITTED.value,
        "expiration_date": (now + timedelta(days=90)).isoformat(),
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    deal_registrations[registration_id] = registration
    
    logger.info("deal_registration_created", registration_id=registration_id, partner_id=partner_id)
    return registration


@router.get("/deal-registrations")
async def list_deal_registrations(
    partner_id: Optional[str] = None,
    status: Optional[DealRegStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List deal registrations"""
    result = [r for r in deal_registrations.values() if r.get("tenant_id") == tenant_id]
    
    if partner_id:
        result = [r for r in result if r.get("partner_id") == partner_id]
    if status:
        result = [r for r in result if r.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "deal_registrations": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/deal-registrations/{registration_id}")
async def get_deal_registration(registration_id: str):
    """Get deal registration details"""
    if registration_id not in deal_registrations:
        raise HTTPException(status_code=404, detail="Deal registration not found")
    return deal_registrations[registration_id]


@router.post("/deal-registrations/{registration_id}/review")
async def review_deal_registration(
    registration_id: str,
    request: DealRegistrationReview,
    reviewer_id: str = Query(default="default")
):
    """Review and approve/reject deal registration"""
    if registration_id not in deal_registrations:
        raise HTTPException(status_code=404, detail="Deal registration not found")
    
    registration = deal_registrations[registration_id]
    now = datetime.utcnow()
    
    registration["reviewer_id"] = reviewer_id
    registration["review_notes"] = request.notes
    
    if request.approved:
        registration["status"] = DealRegStatus.APPROVED.value
        registration["approved_at"] = now.isoformat()
    else:
        registration["status"] = DealRegStatus.REJECTED.value
        registration["rejected_at"] = now.isoformat()
        registration["rejection_reason"] = request.rejection_reason
    
    registration["updated_at"] = now.isoformat()
    
    logger.info("deal_registration_reviewed", registration_id=registration_id, approved=request.approved)
    return registration


@router.post("/deal-registrations/{registration_id}/mark-won")
async def mark_deal_won(
    registration_id: str,
    final_value: Optional[float] = None
):
    """Mark deal registration as won"""
    if registration_id not in deal_registrations:
        raise HTTPException(status_code=404, detail="Deal registration not found")
    
    registration = deal_registrations[registration_id]
    now = datetime.utcnow()
    
    registration["status"] = DealRegStatus.WON.value
    registration["won_at"] = now.isoformat()
    
    if final_value:
        registration["final_value"] = final_value
    
    # Calculate commission
    partner = partners.get(registration["partner_id"])
    if partner:
        commission_rate = partner.get("commission_rate", 10.0)
        value = final_value or registration["opportunity_value"]
        registration["commission_earned"] = value * (commission_rate / 100)
        
        # Update partner stats
        partner["total_revenue"] = partner.get("total_revenue", 0) + value
        partner["total_deals"] = partner.get("total_deals", 0) + 1
    
    registration["updated_at"] = now.isoformat()
    
    logger.info("deal_registration_won", registration_id=registration_id)
    return registration


# Resources
@router.post("/resources")
async def create_resource(
    request: ResourceCreate,
    tenant_id: str = Query(default="default")
):
    """Create a partner resource"""
    import uuid
    
    resource_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    resource = {
        "id": resource_id,
        "title": request.title,
        "description": request.description,
        "resource_type": request.resource_type,
        "category": request.category,
        "file_url": request.file_url,
        "external_url": request.external_url,
        "access_tiers": [t.value for t in (request.access_tiers or list(PartnerTier))],
        "is_featured": request.is_featured,
        "view_count": 0,
        "download_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    resources[resource_id] = resource
    
    logger.info("resource_created", resource_id=resource_id, title=request.title)
    return resource


@router.get("/resources")
async def list_resources(
    resource_type: Optional[str] = None,
    category: Optional[str] = None,
    partner_tier: Optional[PartnerTier] = None,
    tenant_id: str = Query(default="default")
):
    """List partner resources"""
    result = [r for r in resources.values() if r.get("tenant_id") == tenant_id]
    
    if resource_type:
        result = [r for r in result if r.get("resource_type") == resource_type]
    if category:
        result = [r for r in result if r.get("category") == category]
    if partner_tier:
        result = [r for r in result if partner_tier.value in r.get("access_tiers", [])]
    
    # Featured first, then by view count
    result.sort(key=lambda x: (not x.get("is_featured", False), -x.get("view_count", 0)))
    
    return {"resources": result, "total": len(result)}


@router.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    """Get resource and increment view count"""
    if resource_id not in resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    resource = resources[resource_id]
    resource["view_count"] = resource.get("view_count", 0) + 1
    return resource


@router.post("/resources/{resource_id}/download")
async def track_resource_download(resource_id: str):
    """Track resource download"""
    if resource_id not in resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    resource = resources[resource_id]
    resource["download_count"] = resource.get("download_count", 0) + 1
    
    return {
        "resource_id": resource_id,
        "download_url": resource.get("file_url") or resource.get("external_url")
    }


@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: str):
    """Delete a resource"""
    if resource_id not in resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    del resources[resource_id]
    return {"status": "deleted", "resource_id": resource_id}


# Partner Users
@router.post("/partners/{partner_id}/users")
async def add_partner_user(
    partner_id: str,
    request: PartnerUserCreate
):
    """Add a user to partner organization"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    import uuid
    
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    user = {
        "id": user_id,
        "email": request.email,
        "first_name": request.first_name,
        "last_name": request.last_name,
        "role": request.role,
        "partner_id": partner_id,
        "is_active": True,
        "created_at": now.isoformat()
    }
    
    if partner_id not in partner_users:
        partner_users[partner_id] = []
    partner_users[partner_id].append(user)
    
    logger.info("partner_user_added", user_id=user_id, partner_id=partner_id)
    return user


@router.get("/partners/{partner_id}/users")
async def list_partner_users(partner_id: str):
    """List users for a partner"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    users = partner_users.get(partner_id, [])
    return {"users": users, "total": len(users)}


@router.delete("/partners/{partner_id}/users/{user_id}")
async def remove_partner_user(partner_id: str, user_id: str):
    """Remove a user from partner organization"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    users = partner_users.get(partner_id, [])
    partner_users[partner_id] = [u for u in users if u.get("id") != user_id]
    
    return {"status": "removed", "user_id": user_id}


# Stats
@router.get("/partners/{partner_id}/stats")
async def get_partner_stats(partner_id: str):
    """Get partner statistics"""
    if partner_id not in partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = partners[partner_id]
    registrations = [r for r in deal_registrations.values() if r.get("partner_id") == partner_id]
    
    return {
        "partner_id": partner_id,
        "tier": partner.get("tier"),
        "total_revenue": partner.get("total_revenue", 0),
        "total_deals": partner.get("total_deals", 0),
        "active_deals": partner.get("active_deals", 0),
        "deal_registrations": {
            "total": len(registrations),
            "submitted": len([r for r in registrations if r.get("status") == DealRegStatus.SUBMITTED.value]),
            "approved": len([r for r in registrations if r.get("status") == DealRegStatus.APPROVED.value]),
            "won": len([r for r in registrations if r.get("status") == DealRegStatus.WON.value]),
            "pipeline_value": sum(r.get("opportunity_value", 0) for r in registrations if r.get("status") in [DealRegStatus.SUBMITTED.value, DealRegStatus.APPROVED.value])
        },
        "commission_earned": sum(r.get("commission_earned", 0) for r in registrations)
    }


@router.get("/stats")
async def get_portal_stats(tenant_id: str = Query(default="default")):
    """Get overall partner portal statistics"""
    tenant_partners = [p for p in partners.values() if p.get("tenant_id") == tenant_id]
    tenant_registrations = [r for r in deal_registrations.values() if r.get("tenant_id") == tenant_id]
    
    return {
        "total_partners": len(tenant_partners),
        "active_partners": len([p for p in tenant_partners if p.get("status") == PartnerStatus.ACTIVE.value]),
        "pending_partners": len([p for p in tenant_partners if p.get("status") == PartnerStatus.PENDING.value]),
        "by_tier": {
            tier.value: len([p for p in tenant_partners if p.get("tier") == tier.value])
            for tier in PartnerTier
        },
        "deal_registrations": {
            "total": len(tenant_registrations),
            "pending_review": len([r for r in tenant_registrations if r.get("status") == DealRegStatus.SUBMITTED.value]),
            "approved": len([r for r in tenant_registrations if r.get("status") == DealRegStatus.APPROVED.value]),
            "won": len([r for r in tenant_registrations if r.get("status") == DealRegStatus.WON.value]),
            "total_pipeline": sum(r.get("opportunity_value", 0) for r in tenant_registrations if r.get("status") in [DealRegStatus.SUBMITTED.value, DealRegStatus.APPROVED.value])
        },
        "total_partner_revenue": sum(p.get("total_revenue", 0) for p in tenant_partners),
        "total_resources": len([r for r in resources.values() if r.get("tenant_id") == tenant_id])
    }
