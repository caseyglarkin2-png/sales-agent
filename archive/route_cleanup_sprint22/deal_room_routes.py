"""
Deal Room Routes - Virtual deal collaboration rooms
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

router = APIRouter(prefix="/deal-rooms", tags=["Deal Rooms"])


class RoomStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    WON = "won"
    LOST = "lost"


class ParticipantRole(str, Enum):
    OWNER = "owner"
    SELLER = "seller"
    BUYER = "buyer"
    EXECUTIVE_SPONSOR = "executive_sponsor"
    TECHNICAL_EVALUATOR = "technical_evaluator"
    PROCUREMENT = "procurement"
    VIEWER = "viewer"


class ContentType(str, Enum):
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    VIDEO = "video"
    PROPOSAL = "proposal"
    CONTRACT = "contract"
    MUTUAL_ACTION_PLAN = "mutual_action_plan"
    RECORDING = "recording"
    LINK = "link"


class ActivityType(str, Enum):
    VIEW = "view"
    DOWNLOAD = "download"
    COMMENT = "comment"
    SHARE = "share"
    UPLOAD = "upload"
    INVITE = "invite"
    COMPLETE_ACTION = "complete_action"


class DealRoomCreate(BaseModel):
    name: str
    deal_id: Optional[str] = None
    account_name: str
    description: Optional[str] = None
    expected_close_date: Optional[str] = None
    deal_value: Optional[float] = None


class ParticipantAdd(BaseModel):
    email: str
    name: str
    role: ParticipantRole
    company: Optional[str] = None
    title: Optional[str] = None


class ContentAdd(BaseModel):
    name: str
    content_type: ContentType
    url: Optional[str] = None
    description: Optional[str] = None
    is_featured: bool = False


class MutualActionPlanItem(BaseModel):
    title: str
    description: Optional[str] = None
    owner: str
    owner_type: str  # "seller" or "buyer"
    due_date: str
    dependencies: Optional[List[str]] = None


# In-memory storage
deal_rooms = {}
room_participants = {}
room_content = {}
room_activities = {}
mutual_action_plans = {}
room_comments = {}
engagement_scores = {}


# Deal Rooms CRUD
@router.post("/rooms")
async def create_deal_room(
    request: DealRoomCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a deal room"""
    room_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate access code
    access_code = str(uuid.uuid4())[:8].upper()
    
    room = {
        "id": room_id,
        "name": request.name,
        "deal_id": request.deal_id,
        "account_name": request.account_name,
        "description": request.description,
        "expected_close_date": request.expected_close_date,
        "deal_value": request.deal_value,
        "status": RoomStatus.ACTIVE.value,
        "access_code": access_code,
        "access_url": f"https://app.example.com/room/{room_id}?code={access_code}",
        "participant_count": 1,
        "content_count": 0,
        "last_activity": now.isoformat(),
        "engagement_score": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    deal_rooms[room_id] = room
    
    # Add creator as owner
    room_participants[room_id] = [{
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "email": f"{user_id}@company.com",
        "name": "Room Owner",
        "role": ParticipantRole.OWNER.value,
        "is_internal": True,
        "added_at": now.isoformat(),
        "last_active": now.isoformat()
    }]
    
    logger.info("deal_room_created", room_id=room_id, name=request.name)
    return room


@router.get("/rooms")
async def list_deal_rooms(
    status: Optional[RoomStatus] = None,
    deal_id: Optional[str] = None,
    account_name: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List deal rooms"""
    result = [r for r in deal_rooms.values() if r.get("tenant_id") == tenant_id]
    
    if status:
        result = [r for r in result if r.get("status") == status.value]
    if deal_id:
        result = [r for r in result if r.get("deal_id") == deal_id]
    if account_name:
        result = [r for r in result if account_name.lower() in r.get("account_name", "").lower()]
    
    result.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
    
    return {
        "rooms": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/rooms/{room_id}")
async def get_deal_room(room_id: str):
    """Get deal room details"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = deal_rooms[room_id]
    participants = room_participants.get(room_id, [])
    content = room_content.get(room_id, [])
    activities = room_activities.get(room_id, [])[-20:]
    map_items = mutual_action_plans.get(room_id, [])
    
    return {
        **room,
        "participants": participants,
        "content": content,
        "recent_activities": activities,
        "mutual_action_plan": map_items,
        "engagement_score": calculate_engagement_score(room_id)
    }


@router.put("/rooms/{room_id}")
async def update_deal_room(
    room_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    expected_close_date: Optional[str] = None,
    deal_value: Optional[float] = None,
    status: Optional[RoomStatus] = None
):
    """Update deal room"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = deal_rooms[room_id]
    
    if name is not None:
        room["name"] = name
    if description is not None:
        room["description"] = description
    if expected_close_date is not None:
        room["expected_close_date"] = expected_close_date
    if deal_value is not None:
        room["deal_value"] = deal_value
    if status is not None:
        room["status"] = status.value
    
    room["updated_at"] = datetime.utcnow().isoformat()
    
    return room


@router.post("/rooms/{room_id}/archive")
async def archive_deal_room(room_id: str, outcome: RoomStatus = RoomStatus.ARCHIVED):
    """Archive a deal room"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = deal_rooms[room_id]
    room["status"] = outcome.value
    room["archived_at"] = datetime.utcnow().isoformat()
    
    return room


# Participants
@router.post("/rooms/{room_id}/participants")
async def add_participant(
    room_id: str,
    request: ParticipantAdd,
    user_id: str = Query(default="default")
):
    """Add participant to deal room"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    participant_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    participant = {
        "id": participant_id,
        "email": request.email,
        "name": request.name,
        "role": request.role.value,
        "company": request.company,
        "title": request.title,
        "is_internal": request.role.value in ["owner", "seller"],
        "invited_by": user_id,
        "added_at": now.isoformat(),
        "last_active": None,
        "total_views": 0,
        "total_time_seconds": 0
    }
    
    if room_id not in room_participants:
        room_participants[room_id] = []
    room_participants[room_id].append(participant)
    
    # Update room count
    room = deal_rooms[room_id]
    room["participant_count"] = len(room_participants[room_id])
    
    # Record activity
    record_activity(room_id, ActivityType.INVITE, user_id, {"participant": request.name})
    
    return participant


@router.get("/rooms/{room_id}/participants")
async def get_participants(room_id: str):
    """Get room participants"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    participants = room_participants.get(room_id, [])
    
    # Add engagement data
    for p in participants:
        p["engagement_score"] = random.randint(20, 100)
    
    return {"participants": participants, "total": len(participants)}


@router.delete("/rooms/{room_id}/participants/{participant_id}")
async def remove_participant(room_id: str, participant_id: str):
    """Remove participant from room"""
    if room_id not in room_participants:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room_participants[room_id] = [
        p for p in room_participants[room_id]
        if p.get("id") != participant_id
    ]
    
    # Update room count
    room = deal_rooms[room_id]
    room["participant_count"] = len(room_participants[room_id])
    
    return {"status": "removed", "participant_id": participant_id}


# Content
@router.post("/rooms/{room_id}/content")
async def add_content(
    room_id: str,
    request: ContentAdd,
    user_id: str = Query(default="default")
):
    """Add content to deal room"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    content_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    content = {
        "id": content_id,
        "name": request.name,
        "content_type": request.content_type.value,
        "url": request.url,
        "description": request.description,
        "is_featured": request.is_featured,
        "views": 0,
        "downloads": 0,
        "time_spent_seconds": 0,
        "uploaded_by": user_id,
        "uploaded_at": now.isoformat()
    }
    
    if room_id not in room_content:
        room_content[room_id] = []
    room_content[room_id].append(content)
    
    # Update room count
    room = deal_rooms[room_id]
    room["content_count"] = len(room_content[room_id])
    
    # Record activity
    record_activity(room_id, ActivityType.UPLOAD, user_id, {"content": request.name})
    
    return content


@router.get("/rooms/{room_id}/content")
async def get_content(
    room_id: str,
    content_type: Optional[ContentType] = None
):
    """Get room content"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    content = room_content.get(room_id, [])
    
    if content_type:
        content = [c for c in content if c.get("content_type") == content_type.value]
    
    return {"content": content, "total": len(content)}


@router.post("/rooms/{room_id}/content/{content_id}/view")
async def record_content_view(
    room_id: str,
    content_id: str,
    viewer_id: str,
    time_spent_seconds: int = 0
):
    """Record content view"""
    content = room_content.get(room_id, [])
    
    for c in content:
        if c.get("id") == content_id:
            c["views"] = c.get("views", 0) + 1
            c["time_spent_seconds"] = c.get("time_spent_seconds", 0) + time_spent_seconds
            c["last_viewed_at"] = datetime.utcnow().isoformat()
            
            # Record activity
            record_activity(room_id, ActivityType.VIEW, viewer_id, {"content_id": content_id})
            
            return {"status": "recorded", "views": c["views"]}
    
    raise HTTPException(status_code=404, detail="Content not found")


# Mutual Action Plan
@router.post("/rooms/{room_id}/action-plan")
async def add_action_plan_item(
    room_id: str,
    request: MutualActionPlanItem,
    user_id: str = Query(default="default")
):
    """Add item to mutual action plan"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    item_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    item = {
        "id": item_id,
        "title": request.title,
        "description": request.description,
        "owner": request.owner,
        "owner_type": request.owner_type,
        "due_date": request.due_date,
        "dependencies": request.dependencies or [],
        "status": "pending",
        "completed_at": None,
        "created_by": user_id,
        "created_at": now.isoformat()
    }
    
    if room_id not in mutual_action_plans:
        mutual_action_plans[room_id] = []
    mutual_action_plans[room_id].append(item)
    
    return item


@router.get("/rooms/{room_id}/action-plan")
async def get_action_plan(room_id: str):
    """Get mutual action plan"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    items = mutual_action_plans.get(room_id, [])
    
    completed = [i for i in items if i.get("status") == "completed"]
    pending = [i for i in items if i.get("status") == "pending"]
    overdue = [
        i for i in pending
        if i.get("due_date", "") < datetime.utcnow().isoformat()[:10]
    ]
    
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "completed": len(completed),
            "pending": len(pending),
            "overdue": len(overdue),
            "completion_rate": round(len(completed) / max(1, len(items)), 2)
        }
    }


@router.post("/rooms/{room_id}/action-plan/{item_id}/complete")
async def complete_action_item(room_id: str, item_id: str, user_id: str = Query(default="default")):
    """Mark action item as complete"""
    items = mutual_action_plans.get(room_id, [])
    
    for item in items:
        if item.get("id") == item_id:
            item["status"] = "completed"
            item["completed_at"] = datetime.utcnow().isoformat()
            item["completed_by"] = user_id
            
            # Record activity
            record_activity(room_id, ActivityType.COMPLETE_ACTION, user_id, {"item": item["title"]})
            
            return item
    
    raise HTTPException(status_code=404, detail="Item not found")


# Comments & Discussions
@router.post("/rooms/{room_id}/comments")
async def add_comment(
    room_id: str,
    content: str,
    content_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Add comment to room or content"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    comment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    comment = {
        "id": comment_id,
        "content": content,
        "content_id": content_id,
        "parent_id": parent_id,
        "author_id": user_id,
        "author_name": "User",
        "created_at": now.isoformat()
    }
    
    if room_id not in room_comments:
        room_comments[room_id] = []
    room_comments[room_id].append(comment)
    
    # Record activity
    record_activity(room_id, ActivityType.COMMENT, user_id, {"content_id": content_id})
    
    return comment


@router.get("/rooms/{room_id}/comments")
async def get_comments(room_id: str, content_id: Optional[str] = None):
    """Get room comments"""
    comments = room_comments.get(room_id, [])
    
    if content_id:
        comments = [c for c in comments if c.get("content_id") == content_id]
    
    return {"comments": comments, "total": len(comments)}


# Activity & Analytics
@router.get("/rooms/{room_id}/activities")
async def get_room_activities(
    room_id: str,
    activity_type: Optional[ActivityType] = None,
    limit: int = Query(default=50, le=100)
):
    """Get room activities"""
    activities = room_activities.get(room_id, [])
    
    if activity_type:
        activities = [a for a in activities if a.get("type") == activity_type.value]
    
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"activities": activities[:limit], "total": len(activities)}


@router.get("/rooms/{room_id}/analytics")
async def get_room_analytics(room_id: str):
    """Get room engagement analytics"""
    if room_id not in deal_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = deal_rooms[room_id]
    participants = room_participants.get(room_id, [])
    content = room_content.get(room_id, [])
    activities = room_activities.get(room_id, [])
    
    buyer_participants = [p for p in participants if not p.get("is_internal")]
    
    return {
        "room_id": room_id,
        "engagement_score": calculate_engagement_score(room_id),
        "total_views": sum(c.get("views", 0) for c in content),
        "total_time_spent_seconds": sum(c.get("time_spent_seconds", 0) for c in content),
        "unique_viewers": len(set(a.get("user_id") for a in activities if a.get("type") == "view")),
        "most_viewed_content": sorted(content, key=lambda x: x.get("views", 0), reverse=True)[:3],
        "buyer_engagement": {
            "total_buyers": len(buyer_participants),
            "active_buyers": len([p for p in buyer_participants if p.get("last_active")]),
            "avg_time_per_buyer": random.randint(60, 600)
        },
        "activity_by_day": generate_activity_by_day(activities),
        "deal_health_indicators": {
            "buyer_activity_trend": random.choice(["increasing", "stable", "decreasing"]),
            "executive_engagement": random.choice([True, False]),
            "days_since_last_buyer_activity": random.randint(0, 14),
            "action_plan_on_track": random.choice([True, False])
        }
    }


# Template Rooms
@router.post("/rooms/from-template")
async def create_room_from_template(
    template_id: str,
    name: str,
    deal_id: Optional[str] = None,
    account_name: str = "",
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create deal room from template"""
    # Mock template data
    templates = {
        "enterprise": {
            "default_content": ["Product Overview", "ROI Calculator", "Customer Stories"],
            "default_map": ["Discovery Call", "Technical Deep Dive", "Business Case Review", "Contract Negotiation"]
        },
        "smb": {
            "default_content": ["Product Demo", "Pricing Guide"],
            "default_map": ["Discovery", "Demo", "Proposal", "Close"]
        }
    }
    
    template = templates.get(template_id, templates["smb"])
    
    # Create room
    room_id = str(uuid.uuid4())
    now = datetime.utcnow()
    access_code = str(uuid.uuid4())[:8].upper()
    
    room = {
        "id": room_id,
        "name": name,
        "deal_id": deal_id,
        "account_name": account_name,
        "status": RoomStatus.ACTIVE.value,
        "access_code": access_code,
        "template_id": template_id,
        "participant_count": 1,
        "content_count": len(template["default_content"]),
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    deal_rooms[room_id] = room
    
    # Add template content
    room_content[room_id] = [
        {
            "id": str(uuid.uuid4()),
            "name": content_name,
            "content_type": "document",
            "views": 0,
            "uploaded_at": now.isoformat()
        }
        for content_name in template["default_content"]
    ]
    
    # Add template MAP
    mutual_action_plans[room_id] = [
        {
            "id": str(uuid.uuid4()),
            "title": step,
            "status": "pending",
            "owner": "TBD",
            "owner_type": "seller",
            "due_date": (now + timedelta(days=7 * (i + 1))).isoformat()[:10],
            "created_at": now.isoformat()
        }
        for i, step in enumerate(template["default_map"])
    ]
    
    return room


# Helper functions
def record_activity(room_id: str, activity_type: ActivityType, user_id: str, metadata: Dict = None):
    """Record activity in room"""
    if room_id not in room_activities:
        room_activities[room_id] = []
    
    activity = {
        "id": str(uuid.uuid4()),
        "type": activity_type.value,
        "user_id": user_id,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    room_activities[room_id].append(activity)
    
    # Update room last activity
    if room_id in deal_rooms:
        deal_rooms[room_id]["last_activity"] = activity["timestamp"]


def calculate_engagement_score(room_id: str) -> int:
    """Calculate engagement score for room"""
    content = room_content.get(room_id, [])
    activities = room_activities.get(room_id, [])
    participants = room_participants.get(room_id, [])
    
    # Score based on views, time, and buyer activity
    view_score = min(30, sum(c.get("views", 0) for c in content) * 2)
    activity_score = min(30, len(activities))
    buyer_score = min(40, len([p for p in participants if not p.get("is_internal") and p.get("last_active")]) * 10)
    
    return view_score + activity_score + buyer_score


def generate_activity_by_day(activities: List[Dict]) -> List[Dict]:
    """Generate activity counts by day"""
    day_counts = {}
    
    for activity in activities:
        date = activity.get("timestamp", "")[:10]
        if date:
            day_counts[date] = day_counts.get(date, 0) + 1
    
    return [
        {"date": date, "count": count}
        for date, count in sorted(day_counts.items())[-14:]
    ]
