"""
Proposal Management V2 Routes - Advanced proposal creation and tracking
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

router = APIRouter(prefix="/proposals-v2", tags=["Proposal Management V2"])


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProposalType(str, Enum):
    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    POC = "poc"


class SectionType(str, Enum):
    COVER = "cover"
    EXECUTIVE_SUMMARY = "executive_summary"
    PROBLEM_STATEMENT = "problem_statement"
    SOLUTION = "solution"
    PRICING = "pricing"
    TIMELINE = "timeline"
    TEAM = "team"
    CASE_STUDIES = "case_studies"
    TERMS = "terms"
    SIGNATURE = "signature"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


# In-memory storage
proposals = {}
proposal_templates = {}
proposal_sections = {}
proposal_versions = {}
proposal_approvals = {}
proposal_analytics = {}
content_library = {}


class ProposalCreate(BaseModel):
    name: str
    opportunity_id: str
    proposal_type: ProposalType = ProposalType.STANDARD
    template_id: Optional[str] = None
    valid_days: int = 30


class SectionContent(BaseModel):
    section_type: SectionType
    title: str
    content: str
    order: int


class TemplateCreate(BaseModel):
    name: str
    proposal_type: ProposalType
    sections: List[SectionContent]
    description: Optional[str] = None


# Proposals CRUD
@router.post("/proposals")
async def create_proposal(
    request: ProposalCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a new proposal"""
    proposal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    proposal = {
        "id": proposal_id,
        "name": request.name,
        "opportunity_id": request.opportunity_id,
        "proposal_type": request.proposal_type.value,
        "template_id": request.template_id,
        "status": ProposalStatus.DRAFT.value,
        "version": 1,
        "valid_until": (now + timedelta(days=request.valid_days)).isoformat(),
        "sections": [],
        "pricing": {
            "subtotal": 0,
            "discount": 0,
            "total": 0
        },
        "view_count": 0,
        "time_spent_seconds": 0,
        "owner_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    # Apply template if specified
    if request.template_id and request.template_id in proposal_templates:
        template = proposal_templates[request.template_id]
        proposal["sections"] = template.get("sections", [])
    
    proposals[proposal_id] = proposal
    
    # Create initial version
    await create_version(proposal_id, "Initial draft")
    
    logger.info("proposal_created", proposal_id=proposal_id)
    return proposal


@router.get("/proposals")
async def list_proposals(
    status: Optional[ProposalStatus] = None,
    proposal_type: Optional[ProposalType] = None,
    opportunity_id: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List proposals"""
    result = [p for p in proposals.values() if p.get("tenant_id") == tenant_id]
    
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if proposal_type:
        result = [p for p in result if p.get("proposal_type") == proposal_type.value]
    if opportunity_id:
        result = [p for p in result if p.get("opportunity_id") == opportunity_id]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "proposals": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Get proposal details"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    
    # Get versions
    versions = [v for v in proposal_versions.values() if v.get("proposal_id") == proposal_id]
    
    # Get approvals
    approvals = [a for a in proposal_approvals.values() if a.get("proposal_id") == proposal_id]
    
    return {
        **proposal,
        "versions": versions,
        "approvals": approvals
    }


@router.put("/proposals/{proposal_id}")
async def update_proposal(
    proposal_id: str,
    name: Optional[str] = None,
    valid_days: Optional[int] = None
):
    """Update proposal"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    
    if name:
        proposal["name"] = name
    if valid_days:
        proposal["valid_until"] = (datetime.utcnow() + timedelta(days=valid_days)).isoformat()
    
    proposal["updated_at"] = datetime.utcnow().isoformat()
    
    return proposal


@router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str):
    """Delete a proposal"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposals.pop(proposal_id)
    
    return {"message": "Proposal deleted", "proposal_id": proposal_id}


# Sections
@router.post("/proposals/{proposal_id}/sections")
async def add_section(
    proposal_id: str,
    request: SectionContent
):
    """Add a section to proposal"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    section_id = str(uuid.uuid4())
    
    section = {
        "id": section_id,
        "section_type": request.section_type.value,
        "title": request.title,
        "content": request.content,
        "order": request.order,
        "created_at": datetime.utcnow().isoformat()
    }
    
    proposals[proposal_id]["sections"].append(section)
    
    return section


@router.put("/proposals/{proposal_id}/sections/{section_id}")
async def update_section(
    proposal_id: str,
    section_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    order: Optional[int] = None
):
    """Update a section"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    section = next((s for s in proposal["sections"] if s.get("id") == section_id), None)
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    if title:
        section["title"] = title
    if content:
        section["content"] = content
    if order is not None:
        section["order"] = order
    
    section["updated_at"] = datetime.utcnow().isoformat()
    
    return section


@router.delete("/proposals/{proposal_id}/sections/{section_id}")
async def delete_section(proposal_id: str, section_id: str):
    """Delete a section"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    proposal["sections"] = [s for s in proposal["sections"] if s.get("id") != section_id]
    
    return {"message": "Section deleted"}


# Pricing
@router.put("/proposals/{proposal_id}/pricing")
async def update_pricing(
    proposal_id: str,
    line_items: List[Dict[str, Any]],
    discount_percent: float = 0
):
    """Update proposal pricing"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    
    subtotal = sum(item.get("amount", 0) * item.get("quantity", 1) for item in line_items)
    discount = subtotal * (discount_percent / 100)
    total = subtotal - discount
    
    proposal["pricing"] = {
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "discount_percent": discount_percent,
        "discount": round(discount, 2),
        "total": round(total, 2)
    }
    
    return proposal["pricing"]


# Status Transitions
@router.post("/proposals/{proposal_id}/submit-for-review")
async def submit_for_review(proposal_id: str, reviewers: List[str]):
    """Submit proposal for internal review"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    proposal["status"] = ProposalStatus.IN_REVIEW.value
    proposal["submitted_at"] = datetime.utcnow().isoformat()
    
    # Create approval requests
    for reviewer_id in reviewers:
        approval_id = str(uuid.uuid4())
        proposal_approvals[approval_id] = {
            "id": approval_id,
            "proposal_id": proposal_id,
            "reviewer_id": reviewer_id,
            "status": ApprovalStatus.PENDING.value,
            "requested_at": datetime.utcnow().isoformat()
        }
    
    return proposal


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    comments: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Approve a proposal"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Find approval request for this user
    approval = next(
        (a for a in proposal_approvals.values() 
         if a.get("proposal_id") == proposal_id and a.get("reviewer_id") == user_id),
        None
    )
    
    if approval:
        approval["status"] = ApprovalStatus.APPROVED.value
        approval["comments"] = comments
        approval["approved_at"] = datetime.utcnow().isoformat()
    
    # Check if all approvals are complete
    all_approvals = [a for a in proposal_approvals.values() if a.get("proposal_id") == proposal_id]
    if all(a.get("status") == ApprovalStatus.APPROVED.value for a in all_approvals):
        proposals[proposal_id]["status"] = ProposalStatus.APPROVED.value
    
    return proposals[proposal_id]


@router.post("/proposals/{proposal_id}/send")
async def send_proposal(
    proposal_id: str,
    recipient_emails: List[str],
    message: Optional[str] = None
):
    """Send proposal to prospect"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    now = datetime.utcnow()
    
    proposal["status"] = ProposalStatus.SENT.value
    proposal["sent_at"] = now.isoformat()
    proposal["recipients"] = recipient_emails
    proposal["share_link"] = f"https://proposals.example.com/view/{proposal_id}"
    
    return {
        "proposal_id": proposal_id,
        "status": "sent",
        "share_link": proposal["share_link"],
        "recipients": recipient_emails
    }


@router.post("/proposals/{proposal_id}/record-view")
async def record_view(
    proposal_id: str,
    viewer_email: Optional[str] = None,
    section_views: Optional[List[Dict[str, Any]]] = None
):
    """Record proposal view"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    now = datetime.utcnow()
    
    if proposal["status"] == ProposalStatus.SENT.value:
        proposal["status"] = ProposalStatus.VIEWED.value
        proposal["first_viewed_at"] = now.isoformat()
    
    proposal["view_count"] += 1
    proposal["last_viewed_at"] = now.isoformat()
    
    if section_views:
        for sv in section_views:
            proposal["time_spent_seconds"] += sv.get("duration_seconds", 0)
    
    return {"view_count": proposal["view_count"]}


@router.post("/proposals/{proposal_id}/accept")
async def accept_proposal(
    proposal_id: str,
    signer_name: str,
    signer_email: str,
    signature_data: Optional[str] = None
):
    """Accept/sign proposal"""
    if proposal_id not in proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal = proposals[proposal_id]
    now = datetime.utcnow()
    
    proposal["status"] = ProposalStatus.ACCEPTED.value
    proposal["accepted_at"] = now.isoformat()
    proposal["signature"] = {
        "signer_name": signer_name,
        "signer_email": signer_email,
        "signed_at": now.isoformat(),
        "ip_address": "192.168.1.1"
    }
    
    return proposal


# Versions
@router.get("/proposals/{proposal_id}/versions")
async def list_versions(proposal_id: str):
    """List proposal versions"""
    versions = [v for v in proposal_versions.values() if v.get("proposal_id") == proposal_id]
    versions.sort(key=lambda x: x.get("version", 0), reverse=True)
    
    return {"versions": versions, "total": len(versions)}


@router.post("/proposals/{proposal_id}/versions")
async def create_new_version(proposal_id: str, notes: Optional[str] = None):
    """Create a new version"""
    return await create_version(proposal_id, notes)


# Templates
@router.post("/templates")
async def create_template(
    request: TemplateCreate,
    tenant_id: str = Query(default="default")
):
    """Create a proposal template"""
    template_id = str(uuid.uuid4())
    
    template = {
        "id": template_id,
        "name": request.name,
        "proposal_type": request.proposal_type.value,
        "sections": [s.dict() for s in request.sections],
        "description": request.description,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    proposal_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_templates(
    proposal_type: Optional[ProposalType] = None,
    tenant_id: str = Query(default="default")
):
    """List templates"""
    result = [t for t in proposal_templates.values() if t.get("tenant_id") == tenant_id]
    
    if proposal_type:
        result = [t for t in result if t.get("proposal_type") == proposal_type.value]
    
    return {"templates": result, "total": len(result)}


# Content Library
@router.post("/content-library")
async def add_content_block(
    name: str,
    content: str,
    category: str,
    tags: Optional[List[str]] = None,
    tenant_id: str = Query(default="default")
):
    """Add content block to library"""
    block_id = str(uuid.uuid4())
    
    block = {
        "id": block_id,
        "name": name,
        "content": content,
        "category": category,
        "tags": tags or [],
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    content_library[block_id] = block
    
    return block


@router.get("/content-library")
async def search_content_library(
    category: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Search content library"""
    result = [c for c in content_library.values() if c.get("tenant_id") == tenant_id]
    
    if category:
        result = [c for c in result if c.get("category") == category]
    if search:
        result = [c for c in result if search.lower() in c.get("name", "").lower() or search.lower() in c.get("content", "").lower()]
    
    return {"content_blocks": result, "total": len(result)}


# Analytics
@router.get("/analytics")
async def get_proposal_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get proposal analytics"""
    tenant_proposals = [p for p in proposals.values() if p.get("tenant_id") == tenant_id]
    
    by_status = {}
    for status in ProposalStatus:
        by_status[status.value] = len([p for p in tenant_proposals if p.get("status") == status.value])
    
    return {
        "total_proposals": len(tenant_proposals),
        "by_status": by_status,
        "acceptance_rate": round(random.uniform(0.3, 0.6), 3),
        "avg_time_to_accept_days": round(random.uniform(3, 14), 1),
        "avg_view_count": round(random.uniform(2, 8), 1),
        "avg_time_spent_minutes": round(random.uniform(5, 20), 1),
        "most_viewed_sections": [
            {"section": "pricing", "avg_time_seconds": random.randint(60, 180)},
            {"section": "solution", "avg_time_seconds": random.randint(45, 120)},
            {"section": "case_studies", "avg_time_seconds": random.randint(30, 90)}
        ]
    }


# Helper functions
async def create_version(proposal_id: str, notes: Optional[str] = None):
    """Create a new proposal version"""
    if proposal_id not in proposals:
        return None
    
    proposal = proposals[proposal_id]
    version_id = str(uuid.uuid4())
    version_number = proposal["version"]
    
    version = {
        "id": version_id,
        "proposal_id": proposal_id,
        "version": version_number,
        "snapshot": dict(proposal),
        "notes": notes,
        "created_at": datetime.utcnow().isoformat()
    }
    
    proposal_versions[version_id] = version
    proposal["version"] = version_number + 1
    
    return version
