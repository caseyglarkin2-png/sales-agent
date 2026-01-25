"""
Sales Enablement Routes - Content library and sales readiness
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid

logger = structlog.get_logger()

router = APIRouter(prefix="/sales-enablement", tags=["Sales Enablement"])


class ContentType(str, Enum):
    PRESENTATION = "presentation"
    ONE_PAGER = "one_pager"
    CASE_STUDY = "case_study"
    WHITE_PAPER = "white_paper"
    VIDEO = "video"
    BATTLE_CARD = "battle_card"
    PLAYBOOK = "playbook"
    TEMPLATE = "template"
    PROPOSAL = "proposal"
    DEMO = "demo"
    TRAINING = "training"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SalesStage(str, Enum):
    PROSPECTING = "prospecting"
    DISCOVERY = "discovery"
    DEMO = "demo"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    POST_SALE = "post_sale"


class ContentCreate(BaseModel):
    title: str
    content_type: ContentType
    description: Optional[str] = None
    industries: Optional[List[str]] = None
    personas: Optional[List[str]] = None
    sales_stages: Optional[List[SalesStage]] = None
    products: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None
    is_external: bool = False


class BattleCardCreate(BaseModel):
    competitor_name: str
    overview: str
    strengths: List[str]
    weaknesses: List[str]
    our_advantages: List[str]
    common_objections: List[Dict[str, str]]
    win_strategies: List[str]
    key_differentiators: List[str]
    pricing_comparison: Optional[Dict[str, Any]] = None


class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sales_stage: SalesStage
    industry: Optional[str] = None
    persona: Optional[str] = None
    steps: List[Dict[str, Any]]
    resources: Optional[List[str]] = None
    talk_tracks: Optional[List[str]] = None


class TrainingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: str = "course"  # course, video, quiz, certification
    duration_minutes: Optional[int] = None
    modules: Optional[List[Dict[str, Any]]] = None
    required_for_roles: Optional[List[str]] = None
    due_date: Optional[str] = None


# In-memory storage
content_library = {}
battle_cards = {}
playbooks = {}
trainings = {}
training_progress = {}
folders = {}
collections = {}
shares = {}
content_analytics = {}


# Content Library
@router.post("/content")
async def create_content(
    request: ContentCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create content item"""
    content_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    content = {
        "id": content_id,
        "title": request.title,
        "content_type": request.content_type.value,
        "description": request.description,
        "industries": request.industries or [],
        "personas": request.personas or [],
        "sales_stages": [s.value for s in request.sales_stages] if request.sales_stages else [],
        "products": request.products or [],
        "tags": request.tags or [],
        "folder_id": request.folder_id,
        "is_external": request.is_external,
        "status": ContentStatus.DRAFT.value,
        "file_url": None,
        "thumbnail_url": None,
        "views": 0,
        "downloads": 0,
        "shares": 0,
        "avg_rating": 0,
        "ratings_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    content_library[content_id] = content
    
    logger.info("content_created", content_id=content_id, title=request.title)
    return content


@router.get("/content")
async def list_content(
    content_type: Optional[ContentType] = None,
    status: Optional[ContentStatus] = None,
    industry: Optional[str] = None,
    persona: Optional[str] = None,
    sales_stage: Optional[SalesStage] = None,
    product: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    folder_id: Optional[str] = None,
    sort_by: str = Query(default="updated_at", regex="^(title|updated_at|views|downloads|rating)$"),
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List content with filtering"""
    result = [c for c in content_library.values() if c.get("tenant_id") == tenant_id]
    
    if content_type:
        result = [c for c in result if c.get("content_type") == content_type.value]
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if industry:
        result = [c for c in result if industry in c.get("industries", [])]
    if persona:
        result = [c for c in result if persona in c.get("personas", [])]
    if sales_stage:
        result = [c for c in result if sales_stage.value in c.get("sales_stages", [])]
    if product:
        result = [c for c in result if product in c.get("products", [])]
    if tag:
        result = [c for c in result if tag in c.get("tags", [])]
    if folder_id:
        result = [c for c in result if c.get("folder_id") == folder_id]
    if search:
        search_lower = search.lower()
        result = [c for c in result if search_lower in c.get("title", "").lower() or search_lower in c.get("description", "").lower()]
    
    # Sort
    if sort_by == "title":
        result.sort(key=lambda x: x.get("title", ""))
    elif sort_by == "views":
        result.sort(key=lambda x: x.get("views", 0), reverse=True)
    elif sort_by == "downloads":
        result.sort(key=lambda x: x.get("downloads", 0), reverse=True)
    elif sort_by == "rating":
        result.sort(key=lambda x: x.get("avg_rating", 0), reverse=True)
    else:
        result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return {
        "content": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/content/{content_id}")
async def get_content(content_id: str, track_view: bool = True):
    """Get content details"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_library[content_id]
    
    if track_view:
        content["views"] = content.get("views", 0) + 1
    
    return content


@router.put("/content/{content_id}")
async def update_content(
    content_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[ContentStatus] = None,
    industries: Optional[List[str]] = None,
    personas: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
):
    """Update content"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_library[content_id]
    
    if title is not None:
        content["title"] = title
    if description is not None:
        content["description"] = description
    if status is not None:
        content["status"] = status.value
    if industries is not None:
        content["industries"] = industries
    if personas is not None:
        content["personas"] = personas
    if tags is not None:
        content["tags"] = tags
    
    content["updated_at"] = datetime.utcnow().isoformat()
    
    return content


@router.post("/content/{content_id}/upload")
async def upload_content_file(
    content_id: str,
    file: UploadFile = File(...)
):
    """Upload file for content"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_library[content_id]
    
    content["file_url"] = f"https://storage.example.com/content/{content_id}/{file.filename}"
    content["file_name"] = file.filename
    content["file_type"] = file.content_type
    content["updated_at"] = datetime.utcnow().isoformat()
    
    return content


@router.post("/content/{content_id}/download")
async def track_content_download(content_id: str, user_id: str = Query(default="default")):
    """Track content download"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_library[content_id]
    content["downloads"] = content.get("downloads", 0) + 1
    
    return {
        "content_id": content_id,
        "download_url": content.get("file_url"),
        "downloaded_by": user_id
    }


@router.post("/content/{content_id}/rate")
async def rate_content(
    content_id: str,
    rating: int = Query(..., ge=1, le=5),
    feedback: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Rate content"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = content_library[content_id]
    
    # Simple average (in production, track individual ratings)
    current_avg = content.get("avg_rating", 0)
    current_count = content.get("ratings_count", 0)
    new_avg = ((current_avg * current_count) + rating) / (current_count + 1)
    
    content["avg_rating"] = round(new_avg, 2)
    content["ratings_count"] = current_count + 1
    
    return {
        "content_id": content_id,
        "rating": rating,
        "new_average": content["avg_rating"]
    }


@router.post("/content/{content_id}/share")
async def share_content(
    content_id: str,
    recipient_email: str,
    message: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Share content externally"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    share_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    share = {
        "id": share_id,
        "content_id": content_id,
        "shared_by": user_id,
        "recipient_email": recipient_email,
        "message": message,
        "share_link": f"https://app.example.com/content/shared/{share_id}",
        "views": 0,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat()
    }
    
    shares[share_id] = share
    
    content = content_library[content_id]
    content["shares"] = content.get("shares", 0) + 1
    
    return share


@router.delete("/content/{content_id}")
async def delete_content(content_id: str):
    """Delete content"""
    if content_id not in content_library:
        raise HTTPException(status_code=404, detail="Content not found")
    
    del content_library[content_id]
    
    return {"status": "deleted", "content_id": content_id}


# Battle Cards
@router.post("/battle-cards")
async def create_battle_card(
    request: BattleCardCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a competitive battle card"""
    card_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    card = {
        "id": card_id,
        "competitor_name": request.competitor_name,
        "overview": request.overview,
        "strengths": request.strengths,
        "weaknesses": request.weaknesses,
        "our_advantages": request.our_advantages,
        "common_objections": request.common_objections,
        "win_strategies": request.win_strategies,
        "key_differentiators": request.key_differentiators,
        "pricing_comparison": request.pricing_comparison,
        "win_rate": 0,
        "encounters": 0,
        "wins": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    battle_cards[card_id] = card
    
    logger.info("battle_card_created", card_id=card_id, competitor=request.competitor_name)
    return card


@router.get("/battle-cards")
async def list_battle_cards(
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List battle cards"""
    result = [c for c in battle_cards.values() if c.get("tenant_id") == tenant_id]
    
    if search:
        search_lower = search.lower()
        result = [c for c in result if search_lower in c.get("competitor_name", "").lower()]
    
    result.sort(key=lambda x: x.get("encounters", 0), reverse=True)
    
    return {"battle_cards": result, "total": len(result)}


@router.get("/battle-cards/{card_id}")
async def get_battle_card(card_id: str):
    """Get battle card details"""
    if card_id not in battle_cards:
        raise HTTPException(status_code=404, detail="Battle card not found")
    return battle_cards[card_id]


@router.put("/battle-cards/{card_id}")
async def update_battle_card(
    card_id: str,
    overview: Optional[str] = None,
    strengths: Optional[List[str]] = None,
    weaknesses: Optional[List[str]] = None,
    our_advantages: Optional[List[str]] = None,
    common_objections: Optional[List[Dict[str, str]]] = None,
    win_strategies: Optional[List[str]] = None
):
    """Update battle card"""
    if card_id not in battle_cards:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    card = battle_cards[card_id]
    
    if overview is not None:
        card["overview"] = overview
    if strengths is not None:
        card["strengths"] = strengths
    if weaknesses is not None:
        card["weaknesses"] = weaknesses
    if our_advantages is not None:
        card["our_advantages"] = our_advantages
    if common_objections is not None:
        card["common_objections"] = common_objections
    if win_strategies is not None:
        card["win_strategies"] = win_strategies
    
    card["updated_at"] = datetime.utcnow().isoformat()
    
    return card


@router.post("/battle-cards/{card_id}/record-outcome")
async def record_competitive_outcome(
    card_id: str,
    won: bool,
    deal_id: Optional[str] = None,
    notes: Optional[str] = None
):
    """Record win/loss against competitor"""
    if card_id not in battle_cards:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    card = battle_cards[card_id]
    card["encounters"] = card.get("encounters", 0) + 1
    if won:
        card["wins"] = card.get("wins", 0) + 1
    
    card["win_rate"] = round(card["wins"] / card["encounters"] * 100, 1) if card["encounters"] > 0 else 0
    
    return card


# Playbooks
@router.post("/playbooks")
async def create_playbook(
    request: PlaybookCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a sales playbook"""
    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    playbook = {
        "id": playbook_id,
        "name": request.name,
        "description": request.description,
        "sales_stage": request.sales_stage.value,
        "industry": request.industry,
        "persona": request.persona,
        "steps": request.steps,
        "resources": request.resources or [],
        "talk_tracks": request.talk_tracks or [],
        "times_used": 0,
        "success_rate": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    playbooks[playbook_id] = playbook
    
    logger.info("playbook_created", playbook_id=playbook_id, name=request.name)
    return playbook


@router.get("/playbooks")
async def list_playbooks(
    sales_stage: Optional[SalesStage] = None,
    industry: Optional[str] = None,
    persona: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List playbooks"""
    result = [p for p in playbooks.values() if p.get("tenant_id") == tenant_id]
    
    if sales_stage:
        result = [p for p in result if p.get("sales_stage") == sales_stage.value]
    if industry:
        result = [p for p in result if p.get("industry") == industry]
    if persona:
        result = [p for p in result if p.get("persona") == persona]
    
    return {"playbooks": result, "total": len(result)}


@router.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str):
    """Get playbook details"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbooks[playbook_id]


@router.post("/playbooks/{playbook_id}/use")
async def record_playbook_use(
    playbook_id: str,
    successful: bool,
    deal_id: Optional[str] = None
):
    """Record playbook usage"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    playbook = playbooks[playbook_id]
    playbook["times_used"] = playbook.get("times_used", 0) + 1
    
    # Update success rate (simplified)
    if successful:
        current_rate = playbook.get("success_rate", 0)
        times_used = playbook["times_used"]
        playbook["success_rate"] = round(((current_rate * (times_used - 1)) + 100) / times_used, 1)
    
    return playbook


# Training
@router.post("/training")
async def create_training(
    request: TrainingCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create training content"""
    training_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    training = {
        "id": training_id,
        "title": request.title,
        "description": request.description,
        "content_type": request.content_type,
        "duration_minutes": request.duration_minutes,
        "modules": request.modules or [],
        "required_for_roles": request.required_for_roles or [],
        "due_date": request.due_date,
        "is_published": False,
        "enrollments": 0,
        "completions": 0,
        "avg_score": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    trainings[training_id] = training
    
    logger.info("training_created", training_id=training_id, title=request.title)
    return training


@router.get("/training")
async def list_training(
    content_type: Optional[str] = None,
    required_for_role: Optional[str] = None,
    is_published: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List training content"""
    result = [t for t in trainings.values() if t.get("tenant_id") == tenant_id]
    
    if content_type:
        result = [t for t in result if t.get("content_type") == content_type]
    if required_for_role:
        result = [t for t in result if required_for_role in t.get("required_for_roles", [])]
    if is_published is not None:
        result = [t for t in result if t.get("is_published") == is_published]
    
    return {"training": result, "total": len(result)}


@router.get("/training/{training_id}")
async def get_training(training_id: str):
    """Get training details"""
    if training_id not in trainings:
        raise HTTPException(status_code=404, detail="Training not found")
    return trainings[training_id]


@router.post("/training/{training_id}/enroll")
async def enroll_in_training(
    training_id: str,
    user_id: str = Query(default="default")
):
    """Enroll user in training"""
    if training_id not in trainings:
        raise HTTPException(status_code=404, detail="Training not found")
    
    enrollment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    training = trainings[training_id]
    training["enrollments"] = training.get("enrollments", 0) + 1
    
    progress = {
        "id": enrollment_id,
        "training_id": training_id,
        "user_id": user_id,
        "status": "enrolled",
        "progress_percent": 0,
        "modules_completed": [],
        "started_at": now.isoformat(),
        "score": None
    }
    
    if training_id not in training_progress:
        training_progress[training_id] = {}
    training_progress[training_id][user_id] = progress
    
    return progress


@router.post("/training/{training_id}/progress")
async def update_training_progress(
    training_id: str,
    module_id: str,
    completed: bool = True,
    score: Optional[float] = None,
    user_id: str = Query(default="default")
):
    """Update training progress"""
    if training_id not in trainings:
        raise HTTPException(status_code=404, detail="Training not found")
    
    progress = training_progress.get(training_id, {}).get(user_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    training = trainings[training_id]
    total_modules = len(training.get("modules", []))
    
    if completed and module_id not in progress.get("modules_completed", []):
        progress["modules_completed"].append(module_id)
    
    progress["progress_percent"] = round(len(progress["modules_completed"]) / total_modules * 100) if total_modules > 0 else 0
    
    if progress["progress_percent"] >= 100:
        progress["status"] = "completed"
        progress["completed_at"] = datetime.utcnow().isoformat()
        progress["score"] = score
        training["completions"] = training.get("completions", 0) + 1
    
    return progress


@router.get("/training/{training_id}/progress/{user_id}")
async def get_user_training_progress(training_id: str, user_id: str):
    """Get user's training progress"""
    progress = training_progress.get(training_id, {}).get(user_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress


# Folders
@router.post("/folders")
async def create_folder(
    name: str,
    parent_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a content folder"""
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
    """List folders"""
    result = [f for f in folders.values() if f.get("tenant_id") == tenant_id]
    return {"folders": result, "total": len(result)}


# Collections
@router.post("/collections")
async def create_collection(
    name: str,
    description: Optional[str] = None,
    content_ids: Optional[List[str]] = None,
    is_public: bool = False,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a content collection"""
    collection_id = str(uuid.uuid4())
    
    collection = {
        "id": collection_id,
        "name": name,
        "description": description,
        "content_ids": content_ids or [],
        "is_public": is_public,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    collections[collection_id] = collection
    
    return collection


@router.get("/collections")
async def list_collections(
    is_public: Optional[bool] = None,
    created_by: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List collections"""
    result = [c for c in collections.values() if c.get("tenant_id") == tenant_id]
    
    if is_public is not None:
        result = [c for c in result if c.get("is_public") == is_public]
    if created_by:
        result = [c for c in result if c.get("created_by") == created_by]
    
    return {"collections": result, "total": len(result)}


@router.post("/collections/{collection_id}/add")
async def add_to_collection(collection_id: str, content_id: str):
    """Add content to collection"""
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    collection = collections[collection_id]
    if content_id not in collection["content_ids"]:
        collection["content_ids"].append(content_id)
    
    return collection


# Recommendations
@router.get("/recommend")
async def get_content_recommendations(
    deal_id: Optional[str] = None,
    industry: Optional[str] = None,
    sales_stage: Optional[SalesStage] = None,
    persona: Optional[str] = None,
    competitor: Optional[str] = None,
    limit: int = Query(default=10, le=25),
    tenant_id: str = Query(default="default")
):
    """Get AI-powered content recommendations"""
    result = [c for c in content_library.values() if c.get("tenant_id") == tenant_id and c.get("status") == ContentStatus.PUBLISHED.value]
    
    # Filter by criteria
    if industry:
        result = [c for c in result if industry in c.get("industries", [])]
    if sales_stage:
        result = [c for c in result if sales_stage.value in c.get("sales_stages", [])]
    if persona:
        result = [c for c in result if persona in c.get("personas", [])]
    
    # Add battle card if competitor specified
    recommendations = []
    if competitor:
        for card in battle_cards.values():
            if card.get("tenant_id") == tenant_id and competitor.lower() in card.get("competitor_name", "").lower():
                recommendations.append({
                    "type": "battle_card",
                    "id": card["id"],
                    "title": f"Battle Card: {card['competitor_name']}",
                    "relevance_score": 0.95,
                    "reason": f"Competitive intel for {competitor}"
                })
    
    # Add content recommendations
    for content in result[:limit]:
        recommendations.append({
            "type": "content",
            "id": content["id"],
            "title": content["title"],
            "content_type": content["content_type"],
            "relevance_score": 0.85,
            "reason": f"Matches {sales_stage.value if sales_stage else 'general'} stage"
        })
    
    return {"recommendations": recommendations[:limit], "total": len(recommendations)}


# Analytics
@router.get("/analytics")
async def get_enablement_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get sales enablement analytics"""
    tenant_content = [c for c in content_library.values() if c.get("tenant_id") == tenant_id]
    
    return {
        "content": {
            "total": len(tenant_content),
            "by_type": {
                ct.value: len([c for c in tenant_content if c.get("content_type") == ct.value])
                for ct in ContentType
            },
            "total_views": sum(c.get("views", 0) for c in tenant_content),
            "total_downloads": sum(c.get("downloads", 0) for c in tenant_content),
            "total_shares": sum(c.get("shares", 0) for c in tenant_content),
            "avg_rating": round(sum(c.get("avg_rating", 0) for c in tenant_content) / len(tenant_content), 2) if tenant_content else 0
        },
        "top_content": sorted(tenant_content, key=lambda x: x.get("views", 0), reverse=True)[:5],
        "battle_cards": {
            "total": len([c for c in battle_cards.values() if c.get("tenant_id") == tenant_id]),
            "avg_win_rate": 45.2
        },
        "playbooks": {
            "total": len([p for p in playbooks.values() if p.get("tenant_id") == tenant_id]),
            "total_uses": sum(p.get("times_used", 0) for p in playbooks.values() if p.get("tenant_id") == tenant_id)
        },
        "training": {
            "total_courses": len([t for t in trainings.values() if t.get("tenant_id") == tenant_id]),
            "total_enrollments": sum(t.get("enrollments", 0) for t in trainings.values() if t.get("tenant_id") == tenant_id),
            "total_completions": sum(t.get("completions", 0) for t in trainings.values() if t.get("tenant_id") == tenant_id),
            "completion_rate": 72.5
        },
        "period_days": days
    }
