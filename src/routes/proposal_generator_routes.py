"""
Proposal Generator Routes - Automated proposal creation, templates, and e-signature workflow
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

router = APIRouter(prefix="/proposals", tags=["Proposal Generator"])


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVISION_REQUESTED = "revision_requested"


class ProposalType(str, Enum):
    NEW_BUSINESS = "new_business"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    CUSTOM = "custom"
    RFP_RESPONSE = "rfp_response"


class SectionType(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    PROBLEM_STATEMENT = "problem_statement"
    SOLUTION = "solution"
    PRICING = "pricing"
    TIMELINE = "timeline"
    TEAM = "team"
    CASE_STUDIES = "case_studies"
    TERMS = "terms"
    APPENDIX = "appendix"


# In-memory storage
proposals = {}
proposal_templates = {}
proposal_sections = {}


class ProposalCreate(BaseModel):
    deal_id: str
    customer_name: str
    proposal_type: ProposalType
    template_id: Optional[str] = None
    title: str
    valid_until: Optional[datetime] = None


class ProposalSectionCreate(BaseModel):
    section_type: SectionType
    title: str
    content: str
    order: int = 0
    is_required: bool = True


# Proposals
@router.post("")
async def create_proposal(
    request: ProposalCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new proposal"""
    proposal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    valid_until = request.valid_until or (now + timedelta(days=30))
    
    proposal = {
        "id": proposal_id,
        "deal_id": request.deal_id,
        "customer_name": request.customer_name,
        "proposal_type": request.proposal_type.value,
        "template_id": request.template_id,
        "title": request.title,
        "status": ProposalStatus.DRAFT.value,
        "version": 1,
        "sections": [],
        "valid_until": valid_until.isoformat(),
        "total_value": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    proposals[proposal_id] = proposal
    
    return proposal


@router.get("")
async def list_proposals(
    status: Optional[ProposalStatus] = None,
    proposal_type: Optional[ProposalType] = None,
    deal_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    tenant_id: str = Query(default="default")
):
    """List proposals"""
    result = [p for p in proposals.values() if p.get("tenant_id") == tenant_id]
    
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if proposal_type:
        result = [p for p in result if p.get("proposal_type") == proposal_type.value]
    if deal_id:
        result = [p for p in result if p.get("deal_id") == deal_id]
    
    return {"proposals": result[:limit], "total": len(result)}


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get proposal details"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return proposal


# Proposal Sections
@router.post("/{proposal_id}/sections")
async def add_proposal_section(
    proposal_id: str,
    request: ProposalSectionCreate,
    tenant_id: str = Query(default="default")
):
    """Add a section to a proposal"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    section_id = str(uuid.uuid4())
    section = {
        "id": section_id,
        "section_type": request.section_type.value,
        "title": request.title,
        "content": request.content,
        "order": request.order,
        "is_required": request.is_required,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if "sections" not in proposal:
        proposal["sections"] = []
    proposal["sections"].append(section)
    proposal["updated_at"] = datetime.utcnow().isoformat()
    
    return section


@router.put("/{proposal_id}/sections/{section_id}")
async def update_proposal_section(
    proposal_id: str,
    section_id: str,
    content: str,
    tenant_id: str = Query(default="default")
):
    """Update a proposal section"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    for section in proposal.get("sections", []):
        if section.get("id") == section_id:
            section["content"] = content
            section["updated_at"] = datetime.utcnow().isoformat()
            return section
    
    raise HTTPException(status_code=404, detail="Section not found")


# AI Generation
@router.post("/{proposal_id}/generate-section")
async def generate_proposal_section(
    proposal_id: str,
    section_type: SectionType,
    context: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Generate a proposal section using AI"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    customer = proposal.get("customer_name", "the customer")
    
    generated_content = {
        SectionType.EXECUTIVE_SUMMARY: f"""
## Executive Summary

We are pleased to present this proposal to {customer}, outlining how our solution will address your key business challenges and deliver measurable value.

**Key Benefits:**
- Increase sales productivity by 25%+
- Reduce sales cycle time by 30%
- Improve win rates through AI-powered insights
- Accelerate revenue growth with automated workflows

Our team has extensive experience helping organizations like yours achieve their revenue goals, and we're confident in our ability to deliver exceptional results.
        """,
        SectionType.PROBLEM_STATEMENT: f"""
## Understanding Your Challenges

Based on our discovery conversations with {customer}, we've identified several key challenges:

1. **Manual Processes** - Sales team spending excessive time on administrative tasks
2. **Limited Visibility** - Lack of real-time insights into pipeline health
3. **Inconsistent Execution** - Variable sales performance across team members
4. **Slow Response Times** - Leads not being followed up within optimal windows

These challenges are costing your organization an estimated $500K+ in lost opportunities annually.
        """,
        SectionType.SOLUTION: f"""
## Proposed Solution

We recommend implementing our AI-powered Sales Agent platform to address {customer}'s specific needs:

### Core Capabilities
- **Intelligent Lead Routing** - Automatically route leads to the right rep at the right time
- **AI Email Assistant** - Generate personalized outreach at scale
- **Pipeline Intelligence** - Real-time deal scoring and risk alerts
- **Coaching Insights** - AI-powered recommendations for each deal

### Implementation Approach
- Phase 1: Discovery & Configuration (2 weeks)
- Phase 2: Integration & Training (3 weeks)  
- Phase 3: Pilot & Optimization (4 weeks)
- Phase 4: Full Rollout (2 weeks)
        """,
        SectionType.PRICING: f"""
## Investment Summary

| Component | Price |
|-----------|-------|
| Platform License (Annual) | $60,000 |
| Implementation Services | $15,000 |
| Training & Enablement | $5,000 |
| **Total Year 1 Investment** | **$80,000** |

**Renewal Pricing:** $60,000/year (platform only)

**Payment Terms:** 50% upon signing, 50% upon go-live

**Expected ROI:** 300%+ based on productivity gains and increased win rates
        """
    }
    
    content = generated_content.get(section_type, f"Generated content for {section_type.value} section...")
    
    return {
        "proposal_id": proposal_id,
        "section_type": section_type.value,
        "generated_content": content.strip(),
        "generated_at": datetime.utcnow().isoformat(),
        "tokens_used": random.randint(500, 2000)
    }


@router.post("/{proposal_id}/generate-full")
async def generate_full_proposal(
    proposal_id: str,
    tenant_id: str = Query(default="default")
):
    """Generate all sections of a proposal using AI"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    sections = [
        SectionType.EXECUTIVE_SUMMARY,
        SectionType.PROBLEM_STATEMENT,
        SectionType.SOLUTION,
        SectionType.PRICING,
        SectionType.TIMELINE,
        SectionType.TERMS
    ]
    
    proposal["sections"] = []
    for i, section_type in enumerate(sections):
        proposal["sections"].append({
            "id": str(uuid.uuid4()),
            "section_type": section_type.value,
            "title": section_type.value.replace("_", " ").title(),
            "content": f"AI-generated content for {section_type.value}...",
            "order": i,
            "is_required": True
        })
    
    proposal["updated_at"] = datetime.utcnow().isoformat()
    
    return {
        "proposal_id": proposal_id,
        "sections_generated": len(sections),
        "total_tokens": random.randint(3000, 8000)
    }


# Workflow
@router.post("/{proposal_id}/submit-for-review")
async def submit_for_review(
    proposal_id: str,
    reviewer_email: str,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Submit proposal for internal review"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal["status"] = ProposalStatus.PENDING_REVIEW.value
    proposal["submitted_for_review_at"] = datetime.utcnow().isoformat()
    proposal["reviewer"] = reviewer_email
    proposal["review_notes"] = notes
    
    return {
        "proposal_id": proposal_id,
        "status": proposal["status"],
        "reviewer": reviewer_email
    }


@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    approver_email: str,
    tenant_id: str = Query(default="default")
):
    """Approve a proposal"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal["status"] = ProposalStatus.APPROVED.value
    proposal["approved_at"] = datetime.utcnow().isoformat()
    proposal["approved_by"] = approver_email
    
    return {"proposal_id": proposal_id, "status": "approved"}


@router.post("/{proposal_id}/send")
async def send_proposal(
    proposal_id: str,
    recipient_emails: List[str],
    subject: Optional[str] = None,
    message: Optional[str] = None,
    require_signature: bool = False,
    tenant_id: str = Query(default="default")
):
    """Send proposal to customer"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    proposal["status"] = ProposalStatus.SENT.value
    proposal["sent_at"] = datetime.utcnow().isoformat()
    proposal["sent_to"] = recipient_emails
    proposal["view_link"] = f"https://proposals.example.com/{proposal_id}"
    
    if require_signature:
        proposal["signature_required"] = True
        proposal["signature_link"] = f"https://proposals.example.com/{proposal_id}/sign"
    
    return {
        "proposal_id": proposal_id,
        "status": "sent",
        "sent_to": recipient_emails,
        "view_link": proposal["view_link"]
    }


@router.post("/{proposal_id}/track-view")
async def track_proposal_view(
    proposal_id: str,
    viewer_email: str,
    tenant_id: str = Query(default="default")
):
    """Track when a proposal is viewed"""
    proposal = proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal["status"] == ProposalStatus.SENT.value:
        proposal["status"] = ProposalStatus.VIEWED.value
    
    if "views" not in proposal:
        proposal["views"] = []
    proposal["views"].append({
        "viewer": viewer_email,
        "viewed_at": datetime.utcnow().isoformat(),
        "duration_seconds": random.randint(60, 600),
        "sections_viewed": random.sample(["executive_summary", "solution", "pricing", "terms"], 3)
    })
    
    return {"tracked": True, "total_views": len(proposal["views"])}


# Templates
@router.post("/templates")
async def create_proposal_template(
    name: str,
    proposal_type: ProposalType,
    sections: List[ProposalSectionCreate],
    tenant_id: str = Query(default="default")
):
    """Create a proposal template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": name,
        "proposal_type": proposal_type.value,
        "sections": [
            {
                "section_type": s.section_type.value,
                "title": s.title,
                "content": s.content,
                "order": s.order,
                "is_required": s.is_required
            }
            for s in sections
        ],
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    proposal_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_proposal_templates(
    proposal_type: Optional[ProposalType] = None,
    tenant_id: str = Query(default="default")
):
    """List proposal templates"""
    result = [t for t in proposal_templates.values() if t.get("tenant_id") == tenant_id]
    
    if proposal_type:
        result = [t for t in result if t.get("proposal_type") == proposal_type.value]
    
    return {"templates": result, "total": len(result)}


@router.post("/{proposal_id}/clone")
async def clone_proposal(
    proposal_id: str,
    new_customer_name: str,
    new_deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Clone a proposal as a template for a new deal"""
    original = proposals.get(proposal_id)
    if not original:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    cloned = {
        **original,
        "id": new_id,
        "deal_id": new_deal_id,
        "customer_name": new_customer_name,
        "status": ProposalStatus.DRAFT.value,
        "version": 1,
        "cloned_from": proposal_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Remove sent/viewed data
    for key in ["sent_at", "sent_to", "views", "approved_at", "approved_by"]:
        cloned.pop(key, None)
    
    proposals[new_id] = cloned
    
    return cloned


# Analytics
@router.get("/analytics/performance")
async def get_proposal_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get proposal performance analytics"""
    return {
        "period": period,
        "summary": {
            "total_proposals": random.randint(50, 150),
            "sent": random.randint(40, 120),
            "viewed": random.randint(35, 100),
            "accepted": random.randint(20, 60),
            "declined": random.randint(5, 20),
            "pending": random.randint(10, 30)
        },
        "conversion_rates": {
            "sent_to_viewed": round(random.uniform(0.75, 0.95), 2),
            "viewed_to_accepted": round(random.uniform(0.40, 0.65), 2),
            "overall_win_rate": round(random.uniform(0.35, 0.55), 2)
        },
        "timing": {
            "avg_time_to_send": f"{random.randint(2, 5)} days",
            "avg_time_to_view": f"{random.randint(1, 3)} hours",
            "avg_time_to_decision": f"{random.randint(5, 15)} days"
        },
        "engagement": {
            "avg_view_duration": f"{random.randint(3, 12)} minutes",
            "most_viewed_section": random.choice(["pricing", "solution", "executive_summary"]),
            "proposals_with_multiple_views": round(random.uniform(0.40, 0.70), 2)
        },
        "top_templates": [
            {"name": "Enterprise New Business", "usage": random.randint(20, 50), "win_rate": round(random.uniform(0.45, 0.60), 2)},
            {"name": "SMB Quick Start", "usage": random.randint(15, 40), "win_rate": round(random.uniform(0.50, 0.70), 2)},
            {"name": "Renewal Standard", "usage": random.randint(25, 60), "win_rate": round(random.uniform(0.75, 0.90), 2)}
        ]
    }
