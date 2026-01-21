"""
Advanced Email Templates Routes - Dynamic templating with personalization
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import re

logger = structlog.get_logger()

router = APIRouter(prefix="/email-templates-v2", tags=["Email Templates V2"])


class TemplateCategory(str, Enum):
    PROSPECTING = "prospecting"
    FOLLOW_UP = "follow_up"
    NURTURE = "nurture"
    MEETING = "meeting"
    PROPOSAL = "proposal"
    CLOSING = "closing"
    ONBOARDING = "onboarding"
    RENEWAL = "renewal"
    RE_ENGAGEMENT = "re_engagement"


class PersonalizationType(str, Enum):
    MERGE_FIELD = "merge_field"
    CONDITIONAL = "conditional"
    DYNAMIC_CONTENT = "dynamic_content"
    AI_GENERATED = "ai_generated"
    SNIPPET = "snippet"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    TESTING = "testing"


class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    category: TemplateCategory
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None
    is_shared: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    category: Optional[TemplateCategory] = None
    status: Optional[TemplateStatus] = None
    tags: Optional[List[str]] = None


class SnippetCreate(BaseModel):
    name: str
    shortcut: str
    content: str
    category: Optional[str] = None
    is_shared: bool = True


class DynamicBlockCreate(BaseModel):
    name: str
    block_type: str  # text, image, button, html
    variants: List[Dict[str, Any]]
    conditions: Dict[str, Any]


class PersonalizationContext(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    custom_fields: Optional[Dict[str, str]] = None


# In-memory storage
templates = {}
snippets = {}
dynamic_blocks = {}
folders = {}
template_versions = {}
analytics = {}


# Available merge fields
MERGE_FIELDS = {
    "first_name": "{{first_name}}",
    "last_name": "{{last_name}}",
    "full_name": "{{full_name}}",
    "email": "{{email}}",
    "company": "{{company}}",
    "title": "{{title}}",
    "phone": "{{phone}}",
    "industry": "{{industry}}",
    "company_size": "{{company_size}}",
    "website": "{{website}}",
    "sender_name": "{{sender.name}}",
    "sender_email": "{{sender.email}}",
    "sender_phone": "{{sender.phone}}",
    "sender_title": "{{sender.title}}",
    "sender_company": "{{sender.company}}",
    "meeting_link": "{{meeting_link}}",
    "unsubscribe_link": "{{unsubscribe_link}}",
    "current_date": "{{current_date}}",
    "current_year": "{{current_year}}"
}


@router.get("/merge-fields")
async def get_available_merge_fields():
    """Get available merge fields for templates"""
    return {
        "merge_fields": MERGE_FIELDS,
        "categories": {
            "recipient": ["first_name", "last_name", "full_name", "email", "company", "title", "phone"],
            "company": ["industry", "company_size", "website"],
            "sender": ["sender_name", "sender_email", "sender_phone", "sender_title", "sender_company"],
            "links": ["meeting_link", "unsubscribe_link"],
            "dates": ["current_date", "current_year"]
        }
    }


# Templates CRUD
@router.post("/templates")
async def create_template(
    request: TemplateCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a new email template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Extract merge fields used
    all_text = request.subject + " " + request.body_html
    merge_fields_used = re.findall(r'\{\{([^}]+)\}\}', all_text)
    
    template = {
        "id": template_id,
        "name": request.name,
        "subject": request.subject,
        "body_html": request.body_html,
        "body_text": request.body_text or strip_html(request.body_html),
        "category": request.category.value,
        "description": request.description,
        "tags": request.tags or [],
        "folder_id": request.folder_id,
        "status": TemplateStatus.DRAFT.value,
        "is_shared": request.is_shared,
        "merge_fields_used": list(set(merge_fields_used)),
        "version": 1,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "stats": {
            "times_used": 0,
            "opens": 0,
            "clicks": 0,
            "replies": 0,
            "open_rate": 0,
            "click_rate": 0,
            "reply_rate": 0
        }
    }
    
    templates[template_id] = template
    
    # Store version
    template_versions[template_id] = [{
        "version": 1,
        "subject": request.subject,
        "body_html": request.body_html,
        "created_at": now.isoformat(),
        "created_by": user_id
    }]
    
    logger.info("template_created", template_id=template_id, name=request.name)
    return template


@router.get("/templates")
async def list_templates(
    category: Optional[TemplateCategory] = None,
    status: Optional[TemplateStatus] = None,
    folder_id: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="updated_at", regex="^(name|updated_at|times_used|open_rate)$"),
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List email templates"""
    result = [t for t in templates.values() if t.get("tenant_id") == tenant_id]
    
    if category:
        result = [t for t in result if t.get("category") == category.value]
    if status:
        result = [t for t in result if t.get("status") == status.value]
    if folder_id:
        result = [t for t in result if t.get("folder_id") == folder_id]
    if tag:
        result = [t for t in result if tag in t.get("tags", [])]
    if search:
        search_lower = search.lower()
        result = [t for t in result if search_lower in t.get("name", "").lower() or search_lower in t.get("subject", "").lower()]
    
    # Sort
    if sort_by == "name":
        result.sort(key=lambda x: x.get("name", ""))
    elif sort_by == "times_used":
        result.sort(key=lambda x: x.get("stats", {}).get("times_used", 0), reverse=True)
    elif sort_by == "open_rate":
        result.sort(key=lambda x: x.get("stats", {}).get("open_rate", 0), reverse=True)
    else:
        result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return {
        "templates": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates[template_id]


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: TemplateUpdate,
    user_id: str = Query(default="default")
):
    """Update a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    now = datetime.utcnow()
    
    # Track if content changed for versioning
    content_changed = False
    
    if request.name is not None:
        template["name"] = request.name
    if request.subject is not None:
        if template["subject"] != request.subject:
            content_changed = True
        template["subject"] = request.subject
    if request.body_html is not None:
        if template["body_html"] != request.body_html:
            content_changed = True
        template["body_html"] = request.body_html
        template["body_text"] = request.body_text or strip_html(request.body_html)
        
        # Update merge fields used
        all_text = template["subject"] + " " + template["body_html"]
        template["merge_fields_used"] = list(set(re.findall(r'\{\{([^}]+)\}\}', all_text)))
    
    if request.category is not None:
        template["category"] = request.category.value
    if request.status is not None:
        template["status"] = request.status.value
    if request.tags is not None:
        template["tags"] = request.tags
    
    template["updated_at"] = now.isoformat()
    
    # Create new version if content changed
    if content_changed:
        template["version"] = template.get("version", 1) + 1
        if template_id not in template_versions:
            template_versions[template_id] = []
        template_versions[template_id].append({
            "version": template["version"],
            "subject": template["subject"],
            "body_html": template["body_html"],
            "created_at": now.isoformat(),
            "created_by": user_id
        })
    
    logger.info("template_updated", template_id=template_id, content_changed=content_changed)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    del templates[template_id]
    if template_id in template_versions:
        del template_versions[template_id]
    
    return {"status": "deleted", "template_id": template_id}


@router.post("/templates/{template_id}/duplicate")
async def duplicate_template(
    template_id: str,
    new_name: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Duplicate a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    original = templates[template_id]
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_template = original.copy()
    new_template["id"] = new_id
    new_template["name"] = new_name or f"{original['name']} (Copy)"
    new_template["status"] = TemplateStatus.DRAFT.value
    new_template["version"] = 1
    new_template["created_by"] = user_id
    new_template["created_at"] = now.isoformat()
    new_template["updated_at"] = now.isoformat()
    new_template["stats"] = {"times_used": 0, "opens": 0, "clicks": 0, "replies": 0, "open_rate": 0, "click_rate": 0, "reply_rate": 0}
    
    templates[new_id] = new_template
    
    return new_template


@router.get("/templates/{template_id}/versions")
async def get_template_versions(template_id: str):
    """Get version history for a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    versions = template_versions.get(template_id, [])
    return {"template_id": template_id, "versions": versions, "total": len(versions)}


@router.post("/templates/{template_id}/restore/{version}")
async def restore_template_version(
    template_id: str,
    version: int,
    user_id: str = Query(default="default")
):
    """Restore a previous version"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    versions = template_versions.get(template_id, [])
    target_version = next((v for v in versions if v["version"] == version), None)
    
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    template = templates[template_id]
    template["subject"] = target_version["subject"]
    template["body_html"] = target_version["body_html"]
    template["version"] = template.get("version", 1) + 1
    template["updated_at"] = datetime.utcnow().isoformat()
    
    # Add new version entry
    versions.append({
        "version": template["version"],
        "subject": template["subject"],
        "body_html": template["body_html"],
        "created_at": template["updated_at"],
        "created_by": user_id,
        "restored_from": version
    })
    
    return template


# Template Preview & Personalization
@router.post("/templates/{template_id}/preview")
async def preview_template(
    template_id: str,
    context: PersonalizationContext
):
    """Preview a template with personalization"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    # Build context dict
    ctx = {
        "first_name": context.first_name or "John",
        "last_name": context.last_name or "Doe",
        "full_name": f"{context.first_name or 'John'} {context.last_name or 'Doe'}",
        "company": context.company or "Acme Corp",
        "title": context.title or "VP of Sales",
        "industry": context.industry or "Technology",
        "company_size": context.company_size or "51-200",
        "email": "john.doe@example.com",
        "sender.name": "Your Name",
        "sender.email": "you@company.com",
        "sender.title": "Account Executive",
        "meeting_link": "https://calendly.com/yourlink",
        "unsubscribe_link": "https://app.example.com/unsubscribe",
        "current_date": datetime.utcnow().strftime("%B %d, %Y"),
        "current_year": str(datetime.utcnow().year),
        **(context.custom_fields or {})
    }
    
    # Replace merge fields
    subject = template["subject"]
    body_html = template["body_html"]
    
    for key, value in ctx.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
        body_html = body_html.replace(f"{{{{{key}}}}}", str(value))
    
    return {
        "template_id": template_id,
        "subject": subject,
        "body_html": body_html,
        "merge_fields_applied": list(ctx.keys())
    }


@router.post("/templates/{template_id}/render")
async def render_template(
    template_id: str,
    recipient_data: Dict[str, Any]
):
    """Render a template for actual sending"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    # Replace all merge fields
    subject = template["subject"]
    body_html = template["body_html"]
    body_text = template.get("body_text", "")
    
    for key, value in recipient_data.items():
        placeholder = f"{{{{{key}}}}}"
        subject = subject.replace(placeholder, str(value) if value else "")
        body_html = body_html.replace(placeholder, str(value) if value else "")
        body_text = body_text.replace(placeholder, str(value) if value else "")
    
    # Update usage stats
    template["stats"]["times_used"] = template["stats"].get("times_used", 0) + 1
    
    return {
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text,
        "template_id": template_id,
        "rendered_at": datetime.utcnow().isoformat()
    }


# Snippets
@router.post("/snippets")
async def create_snippet(
    request: SnippetCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a reusable snippet"""
    snippet_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    snippet = {
        "id": snippet_id,
        "name": request.name,
        "shortcut": request.shortcut,
        "content": request.content,
        "category": request.category,
        "is_shared": request.is_shared,
        "times_used": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    snippets[snippet_id] = snippet
    
    logger.info("snippet_created", snippet_id=snippet_id, shortcut=request.shortcut)
    return snippet


@router.get("/snippets")
async def list_snippets(
    category: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List snippets"""
    result = [s for s in snippets.values() if s.get("tenant_id") == tenant_id]
    
    if category:
        result = [s for s in result if s.get("category") == category]
    if search:
        search_lower = search.lower()
        result = [s for s in result if search_lower in s.get("name", "").lower() or search_lower in s.get("shortcut", "").lower()]
    
    return {"snippets": result, "total": len(result)}


@router.get("/snippets/{snippet_id}")
async def get_snippet(snippet_id: str):
    """Get snippet details"""
    if snippet_id not in snippets:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippets[snippet_id]


@router.get("/snippets/shortcut/{shortcut}")
async def get_snippet_by_shortcut(
    shortcut: str,
    tenant_id: str = Query(default="default")
):
    """Get snippet by shortcut"""
    for snippet in snippets.values():
        if snippet.get("shortcut") == shortcut and snippet.get("tenant_id") == tenant_id:
            snippet["times_used"] = snippet.get("times_used", 0) + 1
            return snippet
    
    raise HTTPException(status_code=404, detail="Snippet not found")


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(snippet_id: str):
    """Delete a snippet"""
    if snippet_id not in snippets:
        raise HTTPException(status_code=404, detail="Snippet not found")
    
    del snippets[snippet_id]
    return {"status": "deleted", "snippet_id": snippet_id}


# Dynamic Blocks
@router.post("/dynamic-blocks")
async def create_dynamic_block(
    request: DynamicBlockCreate,
    tenant_id: str = Query(default="default")
):
    """Create a dynamic content block"""
    block_id = str(uuid.uuid4())
    
    block = {
        "id": block_id,
        "name": request.name,
        "block_type": request.block_type,
        "variants": request.variants,
        "conditions": request.conditions,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    dynamic_blocks[block_id] = block
    
    return block


@router.get("/dynamic-blocks")
async def list_dynamic_blocks(tenant_id: str = Query(default="default")):
    """List dynamic content blocks"""
    result = [b for b in dynamic_blocks.values() if b.get("tenant_id") == tenant_id]
    return {"blocks": result, "total": len(result)}


@router.post("/dynamic-blocks/{block_id}/evaluate")
async def evaluate_dynamic_block(
    block_id: str,
    context: Dict[str, Any]
):
    """Evaluate which variant to show based on conditions"""
    if block_id not in dynamic_blocks:
        raise HTTPException(status_code=404, detail="Block not found")
    
    block = dynamic_blocks[block_id]
    
    # Simple condition matching (in production, use proper rule engine)
    for variant in block.get("variants", []):
        conditions = variant.get("conditions", {})
        match = all(context.get(k) == v for k, v in conditions.items())
        if match:
            return {"variant": variant, "matched": True}
    
    # Return default variant (first one)
    default_variant = block.get("variants", [{}])[0] if block.get("variants") else {}
    return {"variant": default_variant, "matched": False, "default": True}


# Folders
@router.post("/folders")
async def create_folder(
    name: str,
    parent_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a template folder"""
    folder_id = str(uuid.uuid4())
    
    folder = {
        "id": folder_id,
        "name": name,
        "parent_id": parent_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    folders[folder_id] = folder
    
    return folder


@router.get("/folders")
async def list_folders(tenant_id: str = Query(default="default")):
    """List template folders"""
    result = [f for f in folders.values() if f.get("tenant_id") == tenant_id]
    
    # Build tree structure
    def build_tree(parent_id=None):
        children = [f for f in result if f.get("parent_id") == parent_id]
        for child in children:
            child["children"] = build_tree(child["id"])
            child["template_count"] = len([t for t in templates.values() if t.get("folder_id") == child["id"]])
        return children
    
    return {"folders": build_tree(), "total": len(result)}


# Analytics
@router.get("/templates/{template_id}/analytics")
async def get_template_analytics(
    template_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get template performance analytics"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    return {
        "template_id": template_id,
        "period_days": days,
        "stats": template.get("stats", {}),
        "performance": {
            "emails_sent": template.get("stats", {}).get("times_used", 0),
            "opens": template.get("stats", {}).get("opens", 0),
            "unique_opens": template.get("stats", {}).get("opens", 0) - 5,
            "clicks": template.get("stats", {}).get("clicks", 0),
            "replies": template.get("stats", {}).get("replies", 0),
            "unsubscribes": 2,
            "bounces": 1
        },
        "rates": {
            "open_rate": template.get("stats", {}).get("open_rate", 0),
            "click_rate": template.get("stats", {}).get("click_rate", 0),
            "reply_rate": template.get("stats", {}).get("reply_rate", 0),
            "bounce_rate": 0.5
        },
        "comparison": {
            "vs_category_avg": {
                "open_rate": 5.2,
                "click_rate": 2.1,
                "reply_rate": 1.5
            },
            "vs_all_templates": {
                "open_rate": 8.3,
                "click_rate": 3.2,
                "reply_rate": 2.0
            }
        }
    }


@router.put("/templates/{template_id}/analytics")
async def update_template_analytics(
    template_id: str,
    opens: int = 0,
    clicks: int = 0,
    replies: int = 0
):
    """Update template analytics (for tracking purposes)"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    stats = template.get("stats", {})
    
    stats["opens"] = stats.get("opens", 0) + opens
    stats["clicks"] = stats.get("clicks", 0) + clicks
    stats["replies"] = stats.get("replies", 0) + replies
    
    times_used = stats.get("times_used", 1)
    if times_used > 0:
        stats["open_rate"] = round(stats["opens"] / times_used * 100, 2)
        stats["click_rate"] = round(stats["clicks"] / times_used * 100, 2)
        stats["reply_rate"] = round(stats["replies"] / times_used * 100, 2)
    
    template["stats"] = stats
    
    return stats


# AI Features
@router.post("/templates/generate")
async def generate_template(
    category: TemplateCategory,
    product_context: str,
    target_persona: str,
    tone: str = "professional",
    tenant_id: str = Query(default="default")
):
    """Generate a template using AI"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Mock AI-generated template
    subject_options = {
        "prospecting": "Quick question about {{company}}'s growth strategy",
        "follow_up": "Following up on our conversation, {{first_name}}",
        "meeting": "Confirming our meeting - {{first_name}}",
        "proposal": "Your custom proposal for {{company}}",
        "closing": "Next steps for {{company}} partnership"
    }
    
    body_template = f"""<p>Hi {{{{first_name}}}},</p>

<p>I noticed {{{{company}}}} has been {product_context}. Given your role as {{{{title}}}}, I thought you might be interested in how we help {target_persona} achieve better results.</p>

<p>Would you have 15 minutes this week to discuss how we could help {{{{company}}}}?</p>

<p>Best regards,<br/>
{{{{sender.name}}}}<br/>
{{{{sender.title}}}}</p>"""
    
    template = {
        "id": template_id,
        "name": f"AI-Generated {category.value.title()} Template",
        "subject": subject_options.get(category.value, "Quick question for {{first_name}}"),
        "body_html": body_template,
        "body_text": strip_html(body_template),
        "category": category.value,
        "description": f"AI-generated template for {target_persona}",
        "tags": ["ai-generated", category.value],
        "status": TemplateStatus.DRAFT.value,
        "ai_generated": True,
        "generation_params": {
            "category": category.value,
            "product_context": product_context,
            "target_persona": target_persona,
            "tone": tone
        },
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "stats": {"times_used": 0, "opens": 0, "clicks": 0, "replies": 0, "open_rate": 0, "click_rate": 0, "reply_rate": 0}
    }
    
    templates[template_id] = template
    
    logger.info("template_generated", template_id=template_id, category=category.value)
    return template


@router.post("/templates/{template_id}/optimize")
async def optimize_template(template_id: str):
    """Get AI suggestions to optimize a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    return {
        "template_id": template_id,
        "suggestions": [
            {
                "type": "subject_line",
                "current": template.get("subject"),
                "suggested": "A quick idea for {{company}}'s Q4 goals",
                "reason": "Shorter subject lines with personalization tend to perform 15% better"
            },
            {
                "type": "opening",
                "suggestion": "Start with a specific observation about the company rather than introducing yourself",
                "expected_impact": "+10% reply rate"
            },
            {
                "type": "call_to_action",
                "suggestion": "Use a specific time suggestion (e.g., 'Tuesday at 2pm') instead of open-ended availability",
                "expected_impact": "+25% meeting bookings"
            },
            {
                "type": "length",
                "suggestion": "Template is 180 words. Consider reducing to under 120 words for better engagement",
                "expected_impact": "+8% reply rate"
            }
        ],
        "alternative_subjects": [
            "Quick thought on {{company}}'s strategy",
            "Idea for {{first_name}} at {{company}}",
            "Saw {{company}}'s news - had a question"
        ]
    }


def strip_html(html_content: str) -> str:
    """Simple HTML to text conversion"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
