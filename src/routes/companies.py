"""
Company Routes - Company/Account API Endpoints
===============================================
REST API for company management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.companies.company_service import (
    get_company_service,
    CompanyType,
    CompanySize,
    Industry,
)

router = APIRouter(prefix="/companies", tags=["companies"])


class CreateCompanyRequest(BaseModel):
    """Request to create a company."""
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    linkedin_url: Optional[str] = None
    tags: Optional[list[str]] = None
    owner_id: Optional[str] = None


class UpdateCompanyRequest(BaseModel):
    """Request to update a company."""
    name: Optional[str] = None
    domain: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    linkedin_url: Optional[str] = None
    tags: Optional[list[str]] = None
    owner_id: Optional[str] = None
    custom_fields: Optional[dict] = None


class AddContactRequest(BaseModel):
    """Request to add contact to company."""
    contact_id: str
    role: str
    is_primary: bool = False
    is_decision_maker: bool = False


class AddNoteRequest(BaseModel):
    """Request to add note to company."""
    content: str
    author_id: str
    is_pinned: bool = False


class LogActivityRequest(BaseModel):
    """Request to log activity."""
    activity_type: str
    description: str
    contact_id: Optional[str] = None
    metadata: Optional[dict] = None


class SetParentRequest(BaseModel):
    """Request to set parent company."""
    parent_id: str


class MergeRequest(BaseModel):
    """Request to merge companies."""
    duplicate_id: str


@router.post("")
async def create_company(request: CreateCompanyRequest):
    """Create a new company."""
    service = get_company_service()
    
    kwargs = {}
    if request.industry:
        kwargs["industry"] = Industry(request.industry)
    if request.size:
        kwargs["size"] = CompanySize(request.size)
    if request.company_type:
        kwargs["company_type"] = CompanyType(request.company_type)
    if request.website:
        kwargs["website"] = request.website
    if request.address:
        kwargs["address"] = request.address
    if request.city:
        kwargs["city"] = request.city
    if request.state:
        kwargs["state"] = request.state
    if request.country:
        kwargs["country"] = request.country
    if request.annual_revenue:
        kwargs["annual_revenue"] = request.annual_revenue
    if request.employee_count:
        kwargs["employee_count"] = request.employee_count
    if request.linkedin_url:
        kwargs["linkedin_url"] = request.linkedin_url
    if request.tags:
        kwargs["tags"] = request.tags
    if request.owner_id:
        kwargs["owner_id"] = request.owner_id
    
    company = await service.create_company(
        name=request.name,
        domain=request.domain,
        **kwargs
    )
    
    return {
        "success": True,
        "company": {
            "id": company.id,
            "name": company.name,
            "domain": company.domain,
            "industry": company.industry.value if company.industry else None,
            "size": company.size.value if company.size else None,
            "company_type": company.company_type.value,
            "created_at": company.created_at.isoformat()
        }
    }


@router.get("")
async def list_companies(
    company_type: Optional[str] = None,
    industry: Optional[str] = None,
    size: Optional[str] = None,
    tags: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List companies with optional filters."""
    service = get_company_service()
    
    type_enum = CompanyType(company_type) if company_type else None
    industry_enum = Industry(industry) if industry else None
    size_enum = CompanySize(size) if size else None
    tag_list = tags.split(",") if tags else None
    
    companies = await service.list_companies(
        company_type=type_enum,
        industry=industry_enum,
        size=size_enum,
        tags=tag_list,
        owner_id=owner_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "companies": [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "industry": c.industry.value if c.industry else None,
                "size": c.size.value if c.size else None,
                "company_type": c.company_type.value,
                "city": c.city,
                "country": c.country,
                "employee_count": c.employee_count,
                "health_score": c.health_score,
                "contact_count": len(c.contacts),
                "is_enriched": c.is_enriched
            }
            for c in companies
        ],
        "count": len(companies),
        "offset": offset,
        "limit": limit
    }


@router.get("/search")
async def search_companies(
    q: str,
    limit: int = Query(default=20, le=50)
):
    """Search companies by name or domain."""
    service = get_company_service()
    
    results = await service.search_companies(query=q, limit=limit)
    
    return {
        "results": [
            {
                "company": {
                    "id": r.company.id,
                    "name": r.company.name,
                    "domain": r.company.domain,
                    "industry": r.company.industry.value if r.company.industry else None
                },
                "match_score": r.match_score,
                "matched_fields": r.matched_fields
            }
            for r in results
        ],
        "count": len(results)
    }


@router.get("/stats")
async def get_company_stats():
    """Get overall company statistics."""
    service = get_company_service()
    stats = await service.get_company_stats()
    return stats


@router.get("/by-domain/{domain}")
async def get_company_by_domain(domain: str):
    """Get a company by domain."""
    service = get_company_service()
    
    company = await service.get_company_by_domain(domain)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "id": company.id,
        "name": company.name,
        "domain": company.domain,
        "website": company.website,
        "industry": company.industry.value if company.industry else None,
        "size": company.size.value if company.size else None,
        "company_type": company.company_type.value,
        "city": company.city,
        "state": company.state,
        "country": company.country,
        "employee_count": company.employee_count,
        "annual_revenue": company.annual_revenue,
        "linkedin_url": company.linkedin_url,
        "health_score": company.health_score,
        "is_enriched": company.is_enriched,
        "contact_count": len(company.contacts),
        "deal_count": len(company.deals)
    }


@router.get("/{company_id}")
async def get_company(company_id: str):
    """Get a company by ID."""
    service = get_company_service()
    
    company = await service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "id": company.id,
        "name": company.name,
        "domain": company.domain,
        "website": company.website,
        "industry": company.industry.value if company.industry else None,
        "size": company.size.value if company.size else None,
        "company_type": company.company_type.value,
        "address": company.address,
        "city": company.city,
        "state": company.state,
        "country": company.country,
        "postal_code": company.postal_code,
        "employee_count": company.employee_count,
        "annual_revenue": company.annual_revenue,
        "funding_raised": company.funding_raised,
        "linkedin_url": company.linkedin_url,
        "twitter_url": company.twitter_url,
        "health_score": company.health_score,
        "engagement_score": company.engagement_score,
        "is_enriched": company.is_enriched,
        "enriched_at": company.enriched_at.isoformat() if company.enriched_at else None,
        "tags": company.tags,
        "custom_fields": company.custom_fields,
        "hubspot_id": company.hubspot_id,
        "salesforce_id": company.salesforce_id,
        "contact_count": len(company.contacts),
        "deal_count": len(company.deals),
        "note_count": len(company.notes),
        "owner_id": company.owner_id,
        "created_at": company.created_at.isoformat(),
        "updated_at": company.updated_at.isoformat(),
        "last_contacted_at": company.last_contacted_at.isoformat() if company.last_contacted_at else None
    }


@router.patch("/{company_id}")
async def update_company(company_id: str, request: UpdateCompanyRequest):
    """Update a company."""
    service = get_company_service()
    
    updates = request.dict(exclude_none=True)
    
    # Convert enum values
    if "industry" in updates:
        updates["industry"] = Industry(updates["industry"])
    if "size" in updates:
        updates["size"] = CompanySize(updates["size"])
    if "company_type" in updates:
        updates["company_type"] = CompanyType(updates["company_type"])
    
    company = await service.update_company(company_id, updates)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "company": {
            "id": company.id,
            "name": company.name,
            "updated_at": company.updated_at.isoformat()
        }
    }


@router.delete("/{company_id}")
async def delete_company(company_id: str):
    """Delete a company."""
    service = get_company_service()
    
    success = await service.delete_company(company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"success": True, "deleted": company_id}


@router.post("/{company_id}/contacts")
async def add_contact_to_company(company_id: str, request: AddContactRequest):
    """Add a contact to a company."""
    service = get_company_service()
    
    contact = await service.add_contact_to_company(
        company_id=company_id,
        contact_id=request.contact_id,
        role=request.role,
        is_primary=request.is_primary,
        is_decision_maker=request.is_decision_maker
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "contact": {
            "contact_id": contact.contact_id,
            "role": contact.role,
            "is_primary": contact.is_primary,
            "is_decision_maker": contact.is_decision_maker
        }
    }


@router.get("/{company_id}/contacts")
async def get_company_contacts(company_id: str):
    """Get all contacts for a company."""
    service = get_company_service()
    
    contacts = await service.get_company_contacts(company_id)
    
    return {
        "contacts": [
            {
                "contact_id": c.contact_id,
                "role": c.role,
                "is_primary": c.is_primary,
                "is_decision_maker": c.is_decision_maker,
                "added_at": c.added_at.isoformat()
            }
            for c in contacts
        ],
        "count": len(contacts)
    }


@router.delete("/{company_id}/contacts/{contact_id}")
async def remove_contact_from_company(company_id: str, contact_id: str):
    """Remove a contact from a company."""
    service = get_company_service()
    
    success = await service.remove_contact_from_company(company_id, contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company or contact not found")
    
    return {"success": True}


@router.post("/{company_id}/notes")
async def add_note_to_company(company_id: str, request: AddNoteRequest):
    """Add a note to a company."""
    service = get_company_service()
    
    note = await service.add_note_to_company(
        company_id=company_id,
        content=request.content,
        author_id=request.author_id,
        is_pinned=request.is_pinned
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "note": {
            "id": note.id,
            "content": note.content,
            "is_pinned": note.is_pinned,
            "created_at": note.created_at.isoformat()
        }
    }


@router.post("/{company_id}/activities")
async def log_company_activity(company_id: str, request: LogActivityRequest):
    """Log an activity for a company."""
    service = get_company_service()
    
    activity = await service.log_activity(
        company_id=company_id,
        activity_type=request.activity_type,
        description=request.description,
        contact_id=request.contact_id,
        metadata=request.metadata
    )
    
    if not activity:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "activity": {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "timestamp": activity.timestamp.isoformat()
        }
    }


@router.get("/{company_id}/activities")
async def get_company_activities(
    company_id: str,
    activity_type: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get activities for a company."""
    service = get_company_service()
    
    activities = await service.get_company_activities(
        company_id=company_id,
        activity_type=activity_type,
        limit=limit
    )
    
    return {
        "activities": [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "description": a.description,
                "contact_id": a.contact_id,
                "timestamp": a.timestamp.isoformat(),
                "metadata": a.metadata
            }
            for a in activities
        ],
        "count": len(activities)
    }


@router.post("/{company_id}/enrich")
async def enrich_company(
    company_id: str,
    source: str = Query(default="clearbit")
):
    """Enrich company data from external source."""
    service = get_company_service()
    
    company = await service.enrich_company(company_id, source)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "company_id": company_id,
        "is_enriched": company.is_enriched,
        "enriched_at": company.enriched_at.isoformat() if company.enriched_at else None,
        "source": source
    }


@router.get("/{company_id}/health-score")
async def calculate_health_score(company_id: str):
    """Calculate health score for a company."""
    service = get_company_service()
    
    result = await service.calculate_health_score(company_id)
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return result


@router.get("/{company_id}/hierarchy")
async def get_company_hierarchy(company_id: str):
    """Get company hierarchy (parent/subsidiaries)."""
    service = get_company_service()
    
    result = await service.get_company_hierarchy(company_id)
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    
    def serialize_company(c):
        if not c:
            return None
        return {
            "id": c.id,
            "name": c.name,
            "domain": c.domain
        }
    
    return {
        "company": serialize_company(result.get("company")),
        "parent": serialize_company(result.get("parent")),
        "subsidiaries": [serialize_company(s) for s in result.get("subsidiaries", [])]
    }


@router.post("/{company_id}/parent")
async def set_parent_company(company_id: str, request: SetParentRequest):
    """Set parent company relationship."""
    service = get_company_service()
    
    success = await service.set_parent_company(company_id, request.parent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"success": True, "company_id": company_id, "parent_id": request.parent_id}


@router.post("/{company_id}/merge")
async def merge_companies(company_id: str, request: MergeRequest):
    """Merge duplicate company into primary."""
    service = get_company_service()
    
    company = await service.merge_companies(company_id, request.duplicate_id)
    if not company:
        raise HTTPException(status_code=404, detail="One or both companies not found")
    
    return {
        "success": True,
        "merged_into": company_id,
        "deleted": request.duplicate_id,
        "contact_count": len(company.contacts),
        "deal_count": len(company.deals)
    }
