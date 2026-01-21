"""
Template Routes.

API endpoints for email template management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.templates import get_template_library, TemplateCategory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["templates"])


class CreateTemplateRequest(BaseModel):
    name: str
    category: str
    subject: str
    body: str
    personas: List[str]
    industries: Optional[List[str]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class RenderTemplateRequest(BaseModel):
    template_id: str
    context: Dict[str, str]


@router.get("/")
async def list_templates(
    category: Optional[str] = None,
    persona: Optional[str] = None,
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """List all templates with optional filters."""
    library = get_template_library()
    
    cat_filter = None
    if category:
        try:
            cat_filter = TemplateCategory(category)
        except ValueError:
            pass
    
    templates = library.list_templates(
        category=cat_filter,
        persona=persona,
        tag=tag,
    )
    
    return {
        "templates": templates,
        "count": len(templates),
    }


@router.get("/categories")
async def get_categories() -> Dict[str, Any]:
    """Get available template categories."""
    return {
        "categories": [
            {"id": cat.value, "name": cat.value.replace("_", " ").title()}
            for cat in TemplateCategory
        ],
    }


@router.get("/search")
async def search_templates(query: str) -> Dict[str, Any]:
    """Search templates."""
    library = get_template_library()
    templates = library.search_templates(query)
    
    return {
        "templates": templates,
        "count": len(templates),
    }


@router.get("/{template_id}")
async def get_template(template_id: str) -> Dict[str, Any]:
    """Get a template by ID."""
    library = get_template_library()
    template = library.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template": template.to_dict(),
    }


@router.post("/")
async def create_template(request: CreateTemplateRequest) -> Dict[str, Any]:
    """Create a new template."""
    library = get_template_library()
    
    try:
        category = TemplateCategory(request.category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {request.category}")
    
    template = library.create_template(
        name=request.name,
        category=category,
        subject=request.subject,
        body=request.body,
        personas=request.personas,
        industries=request.industries,
        description=request.description,
        tags=request.tags,
    )
    
    return {
        "status": "success",
        "template": template.to_dict(),
    }


@router.post("/render")
async def render_template(request: RenderTemplateRequest) -> Dict[str, Any]:
    """Render a template with context variables."""
    library = get_template_library()
    
    result = library.render_template(
        template_id=request.template_id,
        context=request.context,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    
    subject, body = result
    
    return {
        "subject": subject,
        "body": body,
    }


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> Dict[str, Any]:
    """Delete a template."""
    library = get_template_library()
    
    success = library.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "status": "success",
    }


@router.get("/category/{category}")
async def get_by_category(category: str) -> Dict[str, Any]:
    """Get templates by category."""
    library = get_template_library()
    
    try:
        cat = TemplateCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    templates = library.get_by_category(cat)
    
    return {
        "templates": templates,
        "count": len(templates),
    }


@router.get("/persona/{persona}")
async def get_by_persona(persona: str) -> Dict[str, Any]:
    """Get templates for a specific persona."""
    library = get_template_library()
    templates = library.list_templates(persona=persona)
    
    return {
        "templates": templates,
        "count": len(templates),
    }
