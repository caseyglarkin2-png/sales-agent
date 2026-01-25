"""
Proposal Templates Routes - Proposal document management and generation
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

router = APIRouter(prefix="/proposal-templates", tags=["Proposal Templates"])


class TemplateType(str, Enum):
    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"
    RENEWAL = "renewal"
    UPSELL = "upsell"
    PILOT = "pilot"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SectionType(str, Enum):
    COVER = "cover"
    EXECUTIVE_SUMMARY = "executive_summary"
    PROBLEM_STATEMENT = "problem_statement"
    SOLUTION_OVERVIEW = "solution_overview"
    FEATURES = "features"
    PRICING = "pricing"
    CASE_STUDIES = "case_studies"
    IMPLEMENTATION = "implementation"
    TERMS = "terms"
    NEXT_STEPS = "next_steps"
    CUSTOM = "custom"


# In-memory storage
proposal_templates = {}
template_sections = {}
generated_proposals = {}


class TemplateSectionCreate(BaseModel):
    section_type: SectionType
    title: str
    content: str
    order: int
    is_required: bool = True
    variables: List[str] = []  # Dynamic placeholders like {{company_name}}


class ProposalTemplateCreate(BaseModel):
    name: str
    type: TemplateType
    description: Optional[str] = None
    industries: List[str] = []
    deal_sizes: List[str] = []  # small, medium, large, enterprise
    sections: List[TemplateSectionCreate] = []
    branding: Optional[Dict[str, Any]] = None


class ProposalGenerateRequest(BaseModel):
    template_id: str
    deal_id: Optional[str] = None
    account_id: Optional[str] = None
    variables: Dict[str, Any] = {}
    excluded_sections: List[str] = []


# Templates CRUD
@router.post("")
async def create_proposal_template(
    request: ProposalTemplateCreate,
    tenant_id: str = Query(default="default")
):
    """Create a proposal template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": request.name,
        "type": request.type.value,
        "description": request.description,
        "industries": request.industries,
        "deal_sizes": request.deal_sizes,
        "status": TemplateStatus.DRAFT.value,
        "branding": request.branding or {
            "logo_url": None,
            "primary_color": "#0066cc",
            "secondary_color": "#333333",
            "font_family": "Inter"
        },
        "section_count": len(request.sections),
        "usage_count": 0,
        "last_used_at": None,
        "created_by": "user_1",
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    proposal_templates[template_id] = template
    
    # Create sections
    for section_data in request.sections:
        section_id = str(uuid.uuid4())
        section = {
            "id": section_id,
            "template_id": template_id,
            "section_type": section_data.section_type.value,
            "title": section_data.title,
            "content": section_data.content,
            "order": section_data.order,
            "is_required": section_data.is_required,
            "variables": section_data.variables,
            "created_at": now.isoformat()
        }
        template_sections[section_id] = section
    
    logger.info("proposal_template_created", template_id=template_id)
    
    return template


@router.get("")
async def list_proposal_templates(
    type: Optional[TemplateType] = None,
    status: Optional[TemplateStatus] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List proposal templates"""
    result = [t for t in proposal_templates.values() if t.get("tenant_id") == tenant_id]
    
    if type:
        result = [t for t in result if t.get("type") == type.value]
    if status:
        result = [t for t in result if t.get("status") == status.value]
    if industry:
        result = [t for t in result if industry in t.get("industries", [])]
    if search:
        result = [t for t in result if search.lower() in t.get("name", "").lower()]
    
    return {"templates": result, "total": len(result)}


@router.get("/{template_id}")
async def get_proposal_template(
    template_id: str,
    tenant_id: str = Query(default="default")
):
    """Get template with sections"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = proposal_templates[template_id]
    sections = [s for s in template_sections.values() if s.get("template_id") == template_id]
    sections.sort(key=lambda x: x.get("order", 0))
    
    return {**template, "sections": sections}


@router.patch("/{template_id}")
async def update_proposal_template(
    template_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = proposal_templates[template_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "industries", "deal_sizes", "branding"]:
            template[key] = value
    
    template["updated_at"] = datetime.utcnow().isoformat()
    
    return template


@router.delete("/{template_id}")
async def delete_proposal_template(
    template_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    del proposal_templates[template_id]
    
    # Delete sections
    to_delete = [sid for sid, s in template_sections.items() if s.get("template_id") == template_id]
    for sid in to_delete:
        del template_sections[sid]
    
    return {"success": True, "deleted": template_id}


# Template Status
@router.post("/{template_id}/activate")
async def activate_template(
    template_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate a template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    proposal_templates[template_id]["status"] = TemplateStatus.ACTIVE.value
    
    return {"success": True, "status": "active"}


@router.post("/{template_id}/archive")
async def archive_template(
    template_id: str,
    tenant_id: str = Query(default="default")
):
    """Archive a template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    proposal_templates[template_id]["status"] = TemplateStatus.ARCHIVED.value
    
    return {"success": True, "status": "archived"}


# Sections
@router.post("/{template_id}/sections")
async def add_section(
    template_id: str,
    request: TemplateSectionCreate,
    tenant_id: str = Query(default="default")
):
    """Add section to template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    section_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    section = {
        "id": section_id,
        "template_id": template_id,
        "section_type": request.section_type.value,
        "title": request.title,
        "content": request.content,
        "order": request.order,
        "is_required": request.is_required,
        "variables": request.variables,
        "created_at": now.isoformat()
    }
    
    template_sections[section_id] = section
    proposal_templates[template_id]["section_count"] = \
        proposal_templates[template_id].get("section_count", 0) + 1
    
    return section


@router.patch("/{template_id}/sections/{section_id}")
async def update_section(
    template_id: str,
    section_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update a section"""
    if section_id not in template_sections:
        raise HTTPException(status_code=404, detail="Section not found")
    
    section = template_sections[section_id]
    
    for key, value in updates.items():
        if key in ["title", "content", "order", "is_required", "variables"]:
            section[key] = value
    
    section["updated_at"] = datetime.utcnow().isoformat()
    
    return section


@router.delete("/{template_id}/sections/{section_id}")
async def delete_section(
    template_id: str,
    section_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete a section"""
    if section_id not in template_sections:
        raise HTTPException(status_code=404, detail="Section not found")
    
    del template_sections[section_id]
    proposal_templates[template_id]["section_count"] = \
        max(0, proposal_templates[template_id].get("section_count", 1) - 1)
    
    return {"success": True, "deleted": section_id}


@router.post("/{template_id}/sections/reorder")
async def reorder_sections(
    template_id: str,
    section_order: List[str],  # List of section IDs in desired order
    tenant_id: str = Query(default="default")
):
    """Reorder sections"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    for i, section_id in enumerate(section_order):
        if section_id in template_sections:
            template_sections[section_id]["order"] = i
    
    return {"success": True, "new_order": section_order}


# Generate Proposal
@router.post("/generate")
async def generate_proposal(
    request: ProposalGenerateRequest,
    tenant_id: str = Query(default="default")
):
    """Generate a proposal from template"""
    if request.template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    proposal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = proposal_templates[request.template_id]
    sections = [s for s in template_sections.values() if s.get("template_id") == request.template_id]
    
    # Filter out excluded sections
    sections = [s for s in sections if s["id"] not in request.excluded_sections]
    sections.sort(key=lambda x: x.get("order", 0))
    
    # Apply variable substitution (mock)
    generated_sections = []
    for section in sections:
        content = section["content"]
        for var, value in request.variables.items():
            content = content.replace(f"{{{{{var}}}}}", str(value))
        
        generated_sections.append({
            "section_type": section["section_type"],
            "title": section["title"],
            "content": content
        })
    
    proposal = {
        "id": proposal_id,
        "template_id": request.template_id,
        "template_name": template["name"],
        "deal_id": request.deal_id,
        "account_id": request.account_id,
        "variables_used": request.variables,
        "sections": generated_sections,
        "status": "draft",
        "version": 1,
        "word_count": random.randint(1000, 5000),
        "estimated_read_time_minutes": random.randint(5, 20),
        "tenant_id": tenant_id,
        "generated_at": now.isoformat()
    }
    
    generated_proposals[proposal_id] = proposal
    
    # Update template usage
    proposal_templates[request.template_id]["usage_count"] = \
        proposal_templates[request.template_id].get("usage_count", 0) + 1
    proposal_templates[request.template_id]["last_used_at"] = now.isoformat()
    
    return proposal


@router.get("/proposals")
async def list_generated_proposals(
    deal_id: Optional[str] = None,
    account_id: Optional[str] = None,
    template_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List generated proposals"""
    result = [p for p in generated_proposals.values() if p.get("tenant_id") == tenant_id]
    
    if deal_id:
        result = [p for p in result if p.get("deal_id") == deal_id]
    if account_id:
        result = [p for p in result if p.get("account_id") == account_id]
    if template_id:
        result = [p for p in result if p.get("template_id") == template_id]
    
    return {"proposals": result[:limit], "total": len(result)}


@router.get("/proposals/{proposal_id}")
async def get_generated_proposal(
    proposal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get generated proposal"""
    if proposal_id not in generated_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return generated_proposals[proposal_id]


@router.get("/proposals/{proposal_id}/export")
async def export_proposal(
    proposal_id: str,
    format: str = Query(default="pdf"),  # pdf, docx, pptx
    tenant_id: str = Query(default="default")
):
    """Export proposal to document"""
    if proposal_id not in generated_proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "proposal_id": proposal_id,
        "format": format,
        "download_url": f"https://api.example.com/proposals/export/{proposal_id}.{format}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


# Clone Template
@router.post("/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Clone a template"""
    if template_id not in proposal_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    original = proposal_templates[template_id]
    new_template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_template = {
        **original,
        "id": new_template_id,
        "name": new_name or f"{original['name']} (Copy)",
        "status": TemplateStatus.DRAFT.value,
        "usage_count": 0,
        "cloned_from": template_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    proposal_templates[new_template_id] = new_template
    
    # Clone sections
    original_sections = [s for s in template_sections.values() if s.get("template_id") == template_id]
    for section in original_sections:
        new_section_id = str(uuid.uuid4())
        new_section = {
            **section,
            "id": new_section_id,
            "template_id": new_template_id,
            "created_at": now.isoformat()
        }
        template_sections[new_section_id] = new_section
    
    return new_template


# Analytics
@router.get("/analytics")
async def get_template_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get proposal template analytics"""
    templates = [t for t in proposal_templates.values() if t.get("tenant_id") == tenant_id]
    
    return {
        "period_days": days,
        "summary": {
            "total_templates": len(templates),
            "active_templates": sum(1 for t in templates if t.get("status") == "active"),
            "proposals_generated": random.randint(50, 300)
        },
        "top_templates": [
            {
                "template_id": str(uuid.uuid4()),
                "name": f"Top Template {i + 1}",
                "usage_count": random.randint(10, 100)
            }
            for i in range(5)
        ],
        "conversion_metrics": {
            "proposals_sent": random.randint(40, 250),
            "proposals_viewed": random.randint(35, 220),
            "proposals_accepted": random.randint(15, 100),
            "acceptance_rate": round(random.uniform(0.25, 0.50), 3)
        }
    }
