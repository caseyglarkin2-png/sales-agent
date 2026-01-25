"""
Activity Feed Routes - Activity Feed API
=========================================
REST API endpoints for activity feed, timeline, and notifications.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..activity_feed import (
    ActivityFeedService,
    get_activity_feed_service,
)
from ..activity_feed.activity_feed_service import (
    ActivityType,
    TargetType,
    ActorType,
    ActivityActor,
    ActivityTarget,
    ActivityFilter,
)


router = APIRouter(prefix="/activity-feed", tags=["Activity Feed"])


# Request models
class LogActivityRequest(BaseModel):
    """Log activity request."""
    activity_type: str
    actor_id: str
    actor_name: str
    target_type: str
    target_id: str
    target_name: str
    description: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    is_important: bool = False


class CreateActivityRequest(BaseModel):
    """Create activity request."""
    activity_type: str
    actor: dict[str, Any]
    target: dict[str, Any]
    description: str
    details: Optional[dict[str, Any]] = None
    secondary_targets: Optional[list[dict[str, Any]]] = None
    is_important: bool = False
    metadata: Optional[dict[str, Any]] = None


class MarkReadRequest(BaseModel):
    """Mark read request."""
    activity_ids: list[str]


class SubscribeRequest(BaseModel):
    """Subscribe request."""
    entity_type: str
    entity_id: str
    notify_on_activity: bool = True


def get_service() -> ActivityFeedService:
    """Get activity feed service instance."""
    return get_activity_feed_service()


# Enums
@router.get("/activity-types")
async def list_activity_types():
    """List activity types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in ActivityType
        ]
    }


@router.get("/target-types")
async def list_target_types():
    """List target entity types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in TargetType
        ]
    }


# Feed endpoints
@router.get("")
async def get_feed(
    org_id: str,
    user_id: Optional[str] = None,
    activity_types: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    is_important: Optional[bool] = None,
    since: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get activity feed."""
    service = get_service()
    
    # Build filters
    filters = ActivityFilter()
    
    if activity_types:
        types = []
        for t in activity_types.split(","):
            try:
                types.append(ActivityType(t))
            except ValueError:
                pass
        if types:
            filters.activity_types = types
    
    if target_type:
        try:
            filters.target_types = [TargetType(target_type)]
        except ValueError:
            pass
    
    if target_id:
        filters.target_ids = [target_id]
    
    if is_important is not None:
        filters.is_important = is_important
    
    if since:
        filters.since = since
    
    activities = await service.get_feed(
        org_id=org_id,
        user_id=user_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )
    
    return {
        "activities": [
            {
                "id": a.id,
                "type": a.type.value,
                "actor": {
                    "id": a.actor.id,
                    "type": a.actor.type.value,
                    "name": a.actor.name,
                    "email": a.actor.email,
                    "avatar_url": a.actor.avatar_url,
                },
                "target": {
                    "id": a.target.id,
                    "type": a.target.type.value,
                    "name": a.target.name,
                    "url": a.target.url,
                },
                "description": a.description,
                "details": a.details,
                "is_important": a.is_important,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
                "read_at": a.read_at.isoformat() if a.read_at else None,
            }
            for a in activities
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def create_activity(request: CreateActivityRequest, org_id: str):
    """Create a new activity."""
    service = get_service()
    
    try:
        activity_type = ActivityType(request.activity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid activity type")
    
    try:
        actor = ActivityActor(
            id=request.actor["id"],
            type=ActorType(request.actor.get("type", "user")),
            name=request.actor["name"],
            email=request.actor.get("email"),
            avatar_url=request.actor.get("avatar_url"),
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid actor: {e}")
    
    try:
        target = ActivityTarget(
            id=request.target["id"],
            type=TargetType(request.target["type"]),
            name=request.target["name"],
            url=request.target.get("url"),
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid target: {e}")
    
    secondary_targets = []
    if request.secondary_targets:
        for t in request.secondary_targets:
            try:
                secondary_targets.append(ActivityTarget(
                    id=t["id"],
                    type=TargetType(t["type"]),
                    name=t["name"],
                    url=t.get("url"),
                ))
            except (KeyError, ValueError):
                pass
    
    activity = await service.create_activity(
        activity_type=activity_type,
        actor=actor,
        target=target,
        org_id=org_id,
        description=request.description,
        details=request.details,
        secondary_targets=secondary_targets,
        is_important=request.is_important,
        metadata=request.metadata,
    )
    
    return {"id": activity.id, "created_at": activity.created_at.isoformat()}


@router.post("/log")
async def log_activity(request: LogActivityRequest, org_id: str):
    """Log an activity (simplified)."""
    service = get_service()
    
    try:
        activity_type = ActivityType(request.activity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid activity type")
    
    try:
        target_type = TargetType(request.target_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target type")
    
    activity = await service.log_activity(
        activity_type=activity_type,
        actor_id=request.actor_id,
        actor_name=request.actor_name,
        target_type=target_type,
        target_id=request.target_id,
        target_name=request.target_name,
        org_id=org_id,
        description=request.description,
        details=request.details,
        is_important=request.is_important,
    )
    
    return {"id": activity.id, "created_at": activity.created_at.isoformat()}


@router.get("/{activity_id}")
async def get_activity(activity_id: str):
    """Get an activity by ID."""
    service = get_service()
    activity = await service.get_activity(activity_id)
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {
        "id": activity.id,
        "type": activity.type.value,
        "actor": {
            "id": activity.actor.id,
            "type": activity.actor.type.value,
            "name": activity.actor.name,
        },
        "target": {
            "id": activity.target.id,
            "type": activity.target.type.value,
            "name": activity.target.name,
        },
        "description": activity.description,
        "details": activity.details,
        "secondary_targets": [
            {"id": t.id, "type": t.type.value, "name": t.name}
            for t in activity.secondary_targets
        ],
        "mentions": [
            {"user_id": m.user_id, "user_name": m.user_name}
            for m in activity.mentions
        ],
        "is_important": activity.is_important,
        "metadata": activity.metadata,
        "created_at": activity.created_at.isoformat(),
    }


# Timeline endpoints
@router.get("/timeline/{entity_type}/{entity_id}")
async def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    """Get activity timeline for an entity."""
    service = get_service()
    
    try:
        target_type = TargetType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    activities = await service.get_entity_timeline(target_type, entity_id, limit)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "activities": [
            {
                "id": a.id,
                "type": a.type.value,
                "actor_name": a.actor.name,
                "description": a.description,
                "is_important": a.is_important,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
    }


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    """Get activities by a specific user."""
    service = get_service()
    activities = await service.get_user_activity(user_id, limit)
    
    return {
        "user_id": user_id,
        "activities": [
            {
                "id": a.id,
                "type": a.type.value,
                "target_name": a.target.name,
                "description": a.description,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
    }


# Mentions
@router.get("/mentions")
async def get_mentions(
    user_id: str,
    include_read: bool = False,
):
    """Get activities where user was mentioned."""
    service = get_service()
    activities = await service.get_mentions(user_id, include_read)
    
    return {
        "mentions": [
            {
                "id": a.id,
                "type": a.type.value,
                "actor_name": a.actor.name,
                "description": a.description,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
        "count": len(activities),
    }


# Read status
@router.post("/mark-read")
async def mark_as_read(user_id: str, request: MarkReadRequest):
    """Mark activities as read for a user."""
    service = get_service()
    await service.mark_as_read(user_id, request.activity_ids)
    return {"success": True}


@router.post("/mark-all-read")
async def mark_all_as_read(user_id: str, org_id: str):
    """Mark all activities as read for a user."""
    service = get_service()
    await service.mark_all_as_read(user_id, org_id)
    return {"success": True}


@router.get("/unread-count")
async def get_unread_count(user_id: str, org_id: str):
    """Get unread activity counts for a user."""
    service = get_service()
    counts = await service.get_unread_count(user_id, org_id)
    
    return {
        "total": counts.total,
        "important": counts.important,
        "mentions": counts.mentions,
        "by_type": counts.by_type,
    }


# Subscriptions
@router.post("/subscriptions")
async def subscribe(user_id: str, request: SubscribeRequest):
    """Subscribe to an entity's activity."""
    service = get_service()
    
    try:
        entity_type = TargetType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    sub = await service.subscribe(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=request.entity_id,
        notify_on_activity=request.notify_on_activity,
    )
    
    return {"subscription_id": sub.id}


@router.delete("/subscriptions")
async def unsubscribe(
    user_id: str,
    entity_type: str,
    entity_id: str,
):
    """Unsubscribe from an entity's activity."""
    service = get_service()
    
    try:
        et = TargetType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    if not await service.unsubscribe(user_id, et, entity_id):
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True}


@router.get("/subscriptions")
async def get_subscriptions(user_id: str):
    """Get user's subscriptions."""
    service = get_service()
    subs = await service.get_subscriptions(user_id)
    
    return {
        "subscriptions": [
            {
                "id": s.id,
                "entity_type": s.entity_type.value,
                "entity_id": s.entity_id,
                "notify_on_activity": s.notify_on_activity,
                "created_at": s.created_at.isoformat(),
            }
            for s in subs
        ]
    }


@router.get("/subscribers/{entity_type}/{entity_id}")
async def get_subscribers(entity_type: str, entity_id: str):
    """Get users subscribed to an entity."""
    service = get_service()
    
    try:
        et = TargetType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    subscribers = await service.get_subscribers(et, entity_id)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "subscribers": subscribers,
    }


# Stats
@router.get("/stats")
async def get_activity_stats(
    org_id: str,
    since: Optional[datetime] = None,
):
    """Get activity statistics."""
    service = get_service()
    return await service.get_activity_stats(org_id, since)


# Cleanup
@router.delete("/cleanup")
async def delete_old_activities(
    org_id: str,
    older_than_days: int = Query(90, ge=1),
):
    """Delete old activities."""
    service = get_service()
    deleted = await service.delete_old_activities(org_id, older_than_days)
    return {"deleted": deleted}
