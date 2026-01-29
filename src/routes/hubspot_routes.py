"""HubSpot Routes - Sprint 65.2.

Enhanced HubSpot API endpoints for contact timeline, profiles, and list building.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.hubspot import create_hubspot_connector
from src.db import get_db
from src.logger import get_logger
from src.models.hubspot import HubSpotContact, HubSpotCompany, HubSpotDeal
from src.tasks.hubspot_sync import sync_contact_deep, sync_company_deep

logger = get_logger(__name__)
router = APIRouter(prefix="/api/hubspot", tags=["hubspot"])

# Templates for UI routes
templates = Jinja2Templates(directory="src/templates")


# ============================================================
# Response Models
# ============================================================

class TimelineActivity(BaseModel):
    """Single timeline activity."""
    type: str
    id: str
    timestamp: Optional[str] = None
    subject: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None
    duration: Optional[str] = None
    disposition: Optional[str] = None
    outcome: Optional[str] = None
    end_time: Optional[str] = None


class TimelineResponse(BaseModel):
    """Contact timeline response."""
    contact_id: str
    hubspot_contact_id: str
    activities: list[TimelineActivity]
    total: int


class ContactProfileResponse(BaseModel):
    """Full contact profile response."""
    id: str
    hubspot_contact_id: str
    email: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    full_name: str
    company: Optional[dict] = None
    custom_properties: Optional[dict] = None
    deals: list[dict] = Field(default_factory=list)
    engagements: list[dict] = Field(default_factory=list)
    synced_at: Optional[str] = None


class CompanyProfileResponse(BaseModel):
    """Full company profile response."""
    id: str
    hubspot_company_id: str
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    custom_properties: Optional[dict] = None
    contacts: list[dict] = Field(default_factory=list)
    deals: list[dict] = Field(default_factory=list)
    synced_at: Optional[str] = None


class ContactListFilter(BaseModel):
    """Filters for contact list builder."""
    job_title: Optional[str] = None
    job_title_contains: Optional[str] = None
    company_domain: Optional[str] = None
    industry: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    lead_status: Optional[str] = None
    min_deal_amount: Optional[float] = None
    has_recent_activity: Optional[bool] = None


class ContactListResponse(BaseModel):
    """Contact list response."""
    contacts: list[dict]
    total: int
    filters_applied: dict


# ============================================================
# Timeline Endpoints - Task 65.2
# ============================================================

@router.get("/contacts/{contact_id}/timeline", response_model=TimelineResponse)
async def get_contact_timeline(
    contact_id: str,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get activity timeline for a contact.
    
    Returns emails, calls, meetings, notes associated with the contact,
    sorted by timestamp descending.
    
    Args:
        contact_id: Local DB UUID or HubSpot contact ID
        limit: Max activities to return (default 50, max 100)
    """
    # Find contact
    contact = await _find_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Get timeline from HubSpot
    connector = create_hubspot_connector()
    activities = await connector.get_contact_timeline(
        contact.hubspot_contact_id, 
        limit=limit
    )
    
    return TimelineResponse(
        contact_id=str(contact.id),
        hubspot_contact_id=contact.hubspot_contact_id,
        activities=[TimelineActivity(**a) for a in activities],
        total=len(activities),
    )


@router.post("/contacts/{contact_id}/sync")
async def trigger_contact_sync(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger deep sync for a contact.
    
    Queues a Celery task to sync enhanced properties from HubSpot.
    """
    contact = await _find_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Queue sync task
    task = sync_contact_deep.delay(contact.hubspot_contact_id)
    
    return {
        "status": "queued",
        "task_id": task.id,
        "contact_id": str(contact.id),
        "hubspot_contact_id": contact.hubspot_contact_id,
    }


# ============================================================
# Profile Endpoints - Task 65.3
# ============================================================

@router.get("/contacts/{contact_id}/profile", response_model=ContactProfileResponse)
async def get_contact_profile(
    contact_id: str,
    include_deals: bool = Query(default=True),
    include_engagements: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Get full contact profile with HubSpot data.
    
    Args:
        contact_id: Local DB UUID or HubSpot contact ID
        include_deals: Include associated deals
        include_engagements: Include recent engagements
    """
    contact = await _find_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    connector = create_hubspot_connector()
    
    # Get company info
    company_data = None
    if contact.company_id:
        stmt = select(HubSpotCompany).where(HubSpotCompany.id == contact.company_id)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        if company:
            company_data = {
                "id": str(company.id),
                "hubspot_company_id": company.hubspot_company_id,
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
            }
    
    # Get deals and engagements from HubSpot
    deals = []
    engagements = []
    
    if include_deals:
        deals = await connector.get_contact_deals(contact.hubspot_contact_id)
    
    if include_engagements:
        engagements = await connector.get_contact_engagements(
            contact.hubspot_contact_id, 
            limit=20
        )
    
    return ContactProfileResponse(
        id=str(contact.id),
        hubspot_contact_id=contact.hubspot_contact_id,
        email=contact.email,
        firstname=contact.firstname,
        lastname=contact.lastname,
        full_name=f"{contact.firstname or ''} {contact.lastname or ''}".strip() or contact.email,
        company=company_data,
        custom_properties=contact.custom_properties,
        deals=deals,
        engagements=engagements,
        synced_at=contact.synced_at.isoformat() if contact.synced_at else None,
    )


@router.get("/companies/{company_id}/profile", response_model=CompanyProfileResponse)
async def get_company_profile(
    company_id: str,
    include_contacts: bool = Query(default=True),
    include_deals: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Get full company profile with HubSpot data.
    
    Args:
        company_id: Local DB UUID or HubSpot company ID
        include_contacts: Include associated contacts
        include_deals: Include associated deals
    """
    company = await _find_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get contacts
    contacts = []
    if include_contacts:
        stmt = select(HubSpotContact).where(HubSpotContact.company_id == company.id).limit(50)
        result = await db.execute(stmt)
        for c in result.scalars().all():
            contacts.append({
                "id": str(c.id),
                "hubspot_contact_id": c.hubspot_contact_id,
                "email": c.email,
                "firstname": c.firstname,
                "lastname": c.lastname,
            })
    
    # Get deals
    deals = []
    if include_deals:
        stmt = select(HubSpotDeal).where(HubSpotDeal.company_id == company.id).limit(20)
        result = await db.execute(stmt)
        for d in result.scalars().all():
            deals.append({
                "id": str(d.id),
                "hubspot_deal_id": d.hubspot_deal_id,
                "dealname": d.dealname,
                "stage": d.stage,
                "amount": d.amount,
            })
    
    return CompanyProfileResponse(
        id=str(company.id),
        hubspot_company_id=company.hubspot_company_id,
        name=company.name,
        domain=company.domain,
        industry=company.industry,
        custom_properties=company.custom_properties,
        contacts=contacts,
        deals=deals,
        synced_at=company.synced_at.isoformat() if company.synced_at else None,
    )


@router.post("/companies/{company_id}/sync")
async def trigger_company_sync(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger deep sync for a company."""
    company = await _find_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    task = sync_company_deep.delay(company.hubspot_company_id)
    
    return {
        "status": "queued",
        "task_id": task.id,
        "company_id": str(company.id),
        "hubspot_company_id": company.hubspot_company_id,
    }


# ============================================================
# Smart List Builder - Task 65.4
# ============================================================

@router.post("/contacts/list", response_model=ContactListResponse)
async def build_contact_list(
    filters: ContactListFilter,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Build a smart contact list with filters.
    
    Filter contacts by job title, company, industry, lifecycle stage, etc.
    """
    # Build query
    stmt = select(HubSpotContact)
    conditions = []
    filters_applied = {}
    
    if filters.job_title:
        # Exact match on job title in custom_properties
        conditions.append(
            HubSpotContact.custom_properties["job_title"].astext == filters.job_title
        )
        filters_applied["job_title"] = filters.job_title
    
    if filters.job_title_contains:
        # Contains match
        conditions.append(
            HubSpotContact.custom_properties["job_title"].astext.ilike(
                f"%{filters.job_title_contains}%"
            )
        )
        filters_applied["job_title_contains"] = filters.job_title_contains
    
    if filters.lifecycle_stage:
        conditions.append(
            HubSpotContact.custom_properties["lifecycle_stage"].astext == filters.lifecycle_stage
        )
        filters_applied["lifecycle_stage"] = filters.lifecycle_stage
    
    if filters.lead_status:
        conditions.append(
            HubSpotContact.custom_properties["lead_status"].astext == filters.lead_status
        )
        filters_applied["lead_status"] = filters.lead_status
    
    if filters.min_deal_amount:
        # Filter by recent_deal_amount in custom_properties
        conditions.append(
            HubSpotContact.custom_properties["recent_deal_amount"].astext.cast(db.bind.dialect.type_descriptor(db.bind.dialect)).isnot(None)
        )
        filters_applied["min_deal_amount"] = filters.min_deal_amount
    
    if filters.company_domain:
        # Join with company to filter by domain
        stmt = stmt.join(HubSpotCompany, HubSpotContact.company_id == HubSpotCompany.id)
        conditions.append(HubSpotCompany.domain.ilike(f"%{filters.company_domain}%"))
        filters_applied["company_domain"] = filters.company_domain
    
    if filters.industry:
        if HubSpotCompany not in [t.entity for t in stmt.froms]:
            stmt = stmt.join(HubSpotCompany, HubSpotContact.company_id == HubSpotCompany.id)
        conditions.append(HubSpotCompany.industry.ilike(f"%{filters.industry}%"))
        filters_applied["industry"] = filters.industry
    
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    # Get total count
    count_stmt = select(HubSpotContact.id)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = len(count_result.fetchall())
    
    # Apply pagination
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    
    contact_list = []
    for c in contacts:
        contact_list.append({
            "id": str(c.id),
            "hubspot_contact_id": c.hubspot_contact_id,
            "email": c.email,
            "firstname": c.firstname,
            "lastname": c.lastname,
            "full_name": f"{c.firstname or ''} {c.lastname or ''}".strip() or c.email,
            "custom_properties": c.custom_properties,
        })
    
    return ContactListResponse(
        contacts=contact_list,
        total=total,
        filters_applied=filters_applied,
    )


@router.get("/contacts/list/lifecycle-stages")
async def get_lifecycle_stages():
    """Get available lifecycle stages for filtering."""
    return {
        "stages": [
            {"value": "subscriber", "label": "Subscriber"},
            {"value": "lead", "label": "Lead"},
            {"value": "marketingqualifiedlead", "label": "Marketing Qualified Lead"},
            {"value": "salesqualifiedlead", "label": "Sales Qualified Lead"},
            {"value": "opportunity", "label": "Opportunity"},
            {"value": "customer", "label": "Customer"},
            {"value": "evangelist", "label": "Evangelist"},
            {"value": "other", "label": "Other"},
        ]
    }


@router.get("/contacts/list/lead-statuses")
async def get_lead_statuses():
    """Get available lead statuses for filtering."""
    return {
        "statuses": [
            {"value": "NEW", "label": "New"},
            {"value": "OPEN", "label": "Open"},
            {"value": "IN_PROGRESS", "label": "In Progress"},
            {"value": "OPEN_DEAL", "label": "Open Deal"},
            {"value": "UNQUALIFIED", "label": "Unqualified"},
            {"value": "ATTEMPTED_TO_CONTACT", "label": "Attempted to Contact"},
            {"value": "CONNECTED", "label": "Connected"},
            {"value": "BAD_TIMING", "label": "Bad Timing"},
        ]
    }


# ============================================================
# Helper Functions
# ============================================================

async def _find_contact(db: AsyncSession, contact_id: str) -> Optional[HubSpotContact]:
    """Find contact by UUID or HubSpot ID."""
    # Try as UUID first
    try:
        uuid_id = UUID(contact_id)
        stmt = select(HubSpotContact).where(HubSpotContact.id == uuid_id)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()
        if contact:
            return contact
    except ValueError:
        pass
    
    # Try as HubSpot ID
    stmt = select(HubSpotContact).where(HubSpotContact.hubspot_contact_id == contact_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _find_company(db: AsyncSession, company_id: str) -> Optional[HubSpotCompany]:
    """Find company by UUID or HubSpot ID."""
    try:
        uuid_id = UUID(company_id)
        stmt = select(HubSpotCompany).where(HubSpotCompany.id == uuid_id)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        if company:
            return company
    except ValueError:
        pass
    
    stmt = select(HubSpotCompany).where(HubSpotCompany.hubspot_company_id == company_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================
# UI Routes
# ============================================================

@router.get("/contacts/{contact_id}/view", include_in_schema=False)
async def contact_profile_page(
    request: Request,
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """UI: Contact profile page."""
    contact = await _find_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return templates.TemplateResponse(
        "contact_profile.html",
        {
            "request": request,
            "active_tab": "contacts",
            "contact_id": str(contact.id),
        }
    )


@router.get("/companies/{company_id}/view", include_in_schema=False)
async def company_profile_page(
    request: Request,
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """UI: Company profile page."""
    company = await _find_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return templates.TemplateResponse(
        "company_profile.html",
        {
            "request": request,
            "active_tab": "companies",
            "company_id": str(company.id),
        }
    )


@router.get("/list-builder", include_in_schema=False)
async def list_builder_page(request: Request):
    """UI: Smart contact list builder."""
    return templates.TemplateResponse(
        "contact_list_builder.html",
        {
            "request": request,
            "active_tab": "contacts",
        }
    )
