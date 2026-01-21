"""
Content Library Routes - Sales content management and analytics
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/content-library", tags=["Content Library"])


class ContentType(str, Enum):
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    TEMPLATE = "template"
    CASE_STUDY = "case_study"
    WHITEPAPER = "whitepaper"
    EBOOK = "ebook"
    INFOGRAPHIC = "infographic"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class ContentCategory(str, Enum):
    SALES_DECK = "sales_deck"
    PRODUCT_INFO = "product_info"
    COMPETITOR_BATTLE_CARD = "competitor_battle_card"
    PRICING = "pricing"
    CASE_STUDY = "case_study"
    PROPOSAL_TEMPLATE = "proposal_template"
    EMAIL_TEMPLATE = "email_template"
    TRAINING = "training"
    ONBOARDING = "onboarding"


# In-memory storage
content_items = {}
content_folders = {}
content_shares = {}
content_versions = {}


class ContentCreate(BaseModel):
    name: str
    type: ContentType
    category: ContentCategory
    description: Optional[str] = None
    folder_id: Optional[str] = None
    tags: List[str] = []
    external_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expiry_date: Optional[str] = None


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None


class ContentShareCreate(BaseModel):
    content_id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    message: Optional[str] = None
    expires_in_days: int = 7
    require_email: bool = False
    password: Optional[str] = None


# Content CRUD
@router.post("")
async def create_content(
    request: ContentCreate,
    tenant_id: str = Query(default="default")
):
    """Create content item"""
    content_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    content = {
        "id": content_id,
        "name": request.name,
        "type": request.type.value,
        "category": request.category.value,
        "description": request.description,
        "folder_id": request.folder_id,
        "tags": request.tags,
        "external_url": request.external_url,
        "metadata": request.metadata or {},
        "status": ContentStatus.DRAFT.value,
        "file_size_bytes": random.randint(50000, 5000000),
        "file_extension": None,
        "mime_type": None,
        "thumbnail_url": None,
        "version": 1,
        "views": 0,
        "downloads": 0,
        "shares": 0,
        "avg_engagement_seconds": 0,
        "expiry_date": request.expiry_date,
        "created_by": "user_1",
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    content_items[content_id] = content
    
    logger.info("content_created", content_id=content_id, type=request.type.value)
    
    return content


@router.get("")
async def list_content(
    type: Optional[ContentType] = None,
    category: Optional[ContentCategory] = None,
    status: Optional[ContentStatus] = None,
    folder_id: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List content with filters"""
    result = [c for c in content_items.values() if c.get("tenant_id") == tenant_id]
    
    if type:
        result = [c for c in result if c.get("type") == type.value]
    if category:
        result = [c for c in result if c.get("category") == category.value]
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if folder_id:
        result = [c for c in result if c.get("folder_id") == folder_id]
    if search:
        result = [c for c in result if search.lower() in c.get("name", "").lower()]
    if tags:
        result = [c for c in result if any(t in c.get("tags", []) for t in tags)]
    
    return {
        "content": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/{content_id}")
async def get_content(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Get content details"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    return content_items[content_id]


@router.patch("/{content_id}")
async def update_content(
    content_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update content metadata"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_items[content_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "tags", "category", "folder_id", "expiry_date", "metadata"]:
            content[key] = value
    
    content["updated_at"] = datetime.utcnow().isoformat()
    
    return content


@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete content"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    del content_items[content_id]
    
    return {"success": True, "deleted": content_id}


# Publishing workflow
@router.post("/{content_id}/submit-review")
async def submit_for_review(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Submit content for review"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content_items[content_id]["status"] = ContentStatus.PENDING_REVIEW.value
    content_items[content_id]["submitted_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "pending_review"}


@router.post("/{content_id}/approve")
async def approve_content(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Approve content"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content_items[content_id]["status"] = ContentStatus.APPROVED.value
    content_items[content_id]["approved_at"] = datetime.utcnow().isoformat()
    content_items[content_id]["approved_by"] = "admin_1"
    
    return {"success": True, "status": "approved"}


@router.post("/{content_id}/publish")
async def publish_content(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Publish content"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content_items[content_id]["status"] = ContentStatus.PUBLISHED.value
    content_items[content_id]["published_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "published"}


@router.post("/{content_id}/archive")
async def archive_content(
    content_id: str,
    tenant_id: str = Query(default="default")
):
    """Archive content"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content_items[content_id]["status"] = ContentStatus.ARCHIVED.value
    
    return {"success": True, "status": "archived"}


# Folders
@router.post("/folders")
async def create_folder(
    request: FolderCreate,
    tenant_id: str = Query(default="default")
):
    """Create a folder"""
    folder_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    folder = {
        "id": folder_id,
        "name": request.name,
        "parent_id": request.parent_id,
        "description": request.description,
        "content_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    content_folders[folder_id] = folder
    
    return folder


@router.get("/folders")
async def list_folders(
    parent_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List folders"""
    result = [f for f in content_folders.values() if f.get("tenant_id") == tenant_id]
    
    if parent_id is not None:
        result = [f for f in result if f.get("parent_id") == parent_id]
    
    return {"folders": result, "total": len(result)}


@router.get("/folders/{folder_id}")
async def get_folder(
    folder_id: str,
    tenant_id: str = Query(default="default")
):
    """Get folder with contents"""
    if folder_id not in content_folders:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = content_folders[folder_id]
    contents = [c for c in content_items.values() if c.get("folder_id") == folder_id]
    subfolders = [f for f in content_folders.values() if f.get("parent_id") == folder_id]
    
    return {
        **folder,
        "contents": contents,
        "subfolders": subfolders
    }


# Sharing
@router.post("/share")
async def share_content(
    request: ContentShareCreate,
    tenant_id: str = Query(default="default")
):
    """Create shareable link for content"""
    if request.content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    share_id = str(uuid.uuid4())
    share_token = str(uuid.uuid4())[:12]
    now = datetime.utcnow()
    
    share = {
        "id": share_id,
        "content_id": request.content_id,
        "token": share_token,
        "share_url": f"https://share.example.com/c/{share_token}",
        "recipient_email": request.recipient_email,
        "recipient_name": request.recipient_name,
        "message": request.message,
        "require_email": request.require_email,
        "has_password": request.password is not None,
        "expires_at": (now + timedelta(days=request.expires_in_days)).isoformat(),
        "views": 0,
        "first_viewed_at": None,
        "last_viewed_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    content_shares[share_id] = share
    content_items[request.content_id]["shares"] = content_items[request.content_id].get("shares", 0) + 1
    
    return share


@router.get("/shares")
async def list_shares(
    content_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List content shares"""
    result = [s for s in content_shares.values() if s.get("tenant_id") == tenant_id]
    
    if content_id:
        result = [s for s in result if s.get("content_id") == content_id]
    
    return {"shares": result, "total": len(result)}


@router.delete("/shares/{share_id}")
async def revoke_share(
    share_id: str,
    tenant_id: str = Query(default="default")
):
    """Revoke a share link"""
    if share_id not in content_shares:
        raise HTTPException(status_code=404, detail="Share not found")
    
    del content_shares[share_id]
    
    return {"success": True, "revoked": share_id}


# Analytics
@router.get("/{content_id}/analytics")
async def get_content_analytics(
    content_id: str,
    days: int = Query(default=30, ge=1, le=90),
    tenant_id: str = Query(default="default")
):
    """Get content analytics"""
    if content_id not in content_items:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {
        "content_id": content_id,
        "period_days": days,
        "views": random.randint(50, 500),
        "unique_viewers": random.randint(30, 300),
        "downloads": random.randint(10, 100),
        "shares": random.randint(5, 50),
        "avg_view_duration_seconds": random.randint(30, 300),
        "completion_rate": round(random.uniform(0.3, 0.8), 3),
        "engagement_score": round(random.uniform(0.4, 0.9), 2),
        "views_by_day": [
            {"date": (datetime.utcnow() - timedelta(days=i)).isoformat()[:10], "views": random.randint(1, 20)}
            for i in range(days)
        ],
        "top_viewers": [
            {"user_id": f"user_{i}", "views": random.randint(5, 20), "time_spent_seconds": random.randint(60, 600)}
            for i in range(5)
        ]
    }


@router.get("/analytics/overview")
async def get_library_analytics(
    days: int = Query(default=30, ge=1, le=90),
    tenant_id: str = Query(default="default")
):
    """Get overall content library analytics"""
    return {
        "period_days": days,
        "total_content": random.randint(100, 500),
        "published_content": random.randint(80, 400),
        "total_views": random.randint(5000, 25000),
        "total_downloads": random.randint(500, 3000),
        "total_shares": random.randint(200, 1000),
        "top_content": [
            {"content_id": str(uuid.uuid4()), "name": f"Top Content {i}", "views": random.randint(100, 500)}
            for i in range(5)
        ],
        "by_category": {
            "sales_deck": random.randint(20, 100),
            "case_study": random.randint(10, 50),
            "product_info": random.randint(15, 75),
            "competitor_battle_card": random.randint(5, 25)
        },
        "engagement_trend": "up" if random.random() > 0.4 else "down"
    }


# Search
@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=2),
    types: Optional[List[ContentType]] = Query(default=None),
    categories: Optional[List[ContentCategory]] = Query(default=None),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Search content library"""
    result = [c for c in content_items.values() if c.get("tenant_id") == tenant_id]
    
    # Text search
    result = [
        c for c in result
        if q.lower() in c.get("name", "").lower() or 
           q.lower() in c.get("description", "").lower() or
           any(q.lower() in tag.lower() for tag in c.get("tags", []))
    ]
    
    if types:
        result = [c for c in result if c.get("type") in [t.value for t in types]]
    if categories:
        result = [c for c in result if c.get("category") in [cat.value for cat in categories]]
    
    return {
        "query": q,
        "results": result[:limit],
        "total": len(result)
    }


# Recommendations
@router.get("/recommendations")
async def get_content_recommendations(
    context: Optional[str] = None,  # deal_stage, persona, industry
    context_value: Optional[str] = None,
    limit: int = Query(default=10, le=20),
    tenant_id: str = Query(default="default")
):
    """Get recommended content based on context"""
    result = [c for c in content_items.values() if c.get("tenant_id") == tenant_id and c.get("status") == "published"]
    
    # Simulate recommendations with scores
    recommendations = [
        {
            **c,
            "relevance_score": round(random.uniform(0.6, 1.0), 2),
            "recommendation_reason": random.choice([
                "Popular with similar deals",
                "High engagement rate",
                "Recently updated",
                "Matches buyer persona"
            ])
        }
        for c in result[:limit]
    ]
    
    recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "context": context,
        "context_value": context_value,
        "recommendations": recommendations
    }
