"""
Events Routes - Activity and Event Tracking API
================================================
REST API endpoints for event and activity management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..events import (
    EventService,
    EventType,
    EventCategory,
    get_event_service,
)


router = APIRouter(prefix="/events", tags=["Events"])


# Request/Response models
class LogEventRequest(BaseModel):
    """Log event request."""
    event_type: str
    title: str
    description: Optional[str] = None
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    source: str = "app"
    occurred_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class LogEmailEventRequest(BaseModel):
    """Log email event request."""
    contact_id: str
    subject: str
    email_id: Optional[str] = None
    user_id: Optional[str] = None


class LogCallEventRequest(BaseModel):
    """Log call event request."""
    contact_id: str
    direction: str = "outbound"
    duration_seconds: int = 0
    user_id: Optional[str] = None
    call_id: Optional[str] = None
    notes: Optional[str] = None


class LogMeetingEventRequest(BaseModel):
    """Log meeting event request."""
    contact_id: str
    title: str
    status: str = "scheduled"
    user_id: Optional[str] = None
    meeting_id: Optional[str] = None


class LogDealStageChangeRequest(BaseModel):
    """Log deal stage change request."""
    deal_id: str
    from_stage: str
    to_stage: str
    contact_id: Optional[str] = None
    user_id: Optional[str] = None


class CreateFeedRequest(BaseModel):
    """Create activity feed request."""
    name: str
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None
    event_types: Optional[list[str]] = None
    categories: Optional[list[str]] = None


def get_service() -> EventService:
    """Get event service instance."""
    return get_event_service()


# Event logging
@router.post("")
async def log_event(request: LogEventRequest):
    """Log a custom event."""
    service = get_service()
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        event_type = EventType.CUSTOM
    
    event = await service.log_event(
        event_type=event_type,
        title=request.title,
        description=request.description,
        contact_id=request.contact_id,
        account_id=request.account_id,
        deal_id=request.deal_id,
        user_id=request.user_id,
        object_type=request.object_type,
        object_id=request.object_id,
        metadata=request.metadata,
        source=request.source,
        occurred_at=request.occurred_at,
        duration_seconds=request.duration_seconds,
    )
    
    return {
        "id": event.id,
        "event_type": event.event_type.value,
        "category": event.category.value,
        "title": event.title,
        "occurred_at": event.occurred_at.isoformat(),
    }


@router.get("")
async def list_events(
    contact_id: Optional[str] = None,
    account_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    user_id: Optional[str] = None,
    event_types: Optional[str] = None,
    categories: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    source: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List events with filters."""
    service = get_service()
    
    type_list = None
    if event_types:
        type_list = []
        for t in event_types.split(","):
            try:
                type_list.append(EventType(t))
            except ValueError:
                pass
    
    category_list = None
    if categories:
        category_list = []
        for c in categories.split(","):
            try:
                category_list.append(EventCategory(c))
            except ValueError:
                pass
    
    events, total = await service.list_events(
        contact_id=contact_id,
        account_id=account_id,
        deal_id=deal_id,
        user_id=user_id,
        event_types=type_list,
        categories=category_list,
        from_date=from_date,
        to_date=to_date,
        source=source,
        limit=limit,
        offset=offset
    )
    
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "category": e.category.value,
                "title": e.title,
                "description": e.description,
                "contact_id": e.contact_id,
                "account_id": e.account_id,
                "deal_id": e.deal_id,
                "user_id": e.user_id,
                "object_type": e.object_type,
                "object_id": e.object_id,
                "source": e.source,
                "occurred_at": e.occurred_at.isoformat(),
                "duration_seconds": e.duration_seconds,
            }
            for e in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/types")
async def list_event_types():
    """List available event types."""
    return {
        "event_types": [
            {"value": t.value, "name": t.name}
            for t in EventType
        ]
    }


@router.get("/categories")
async def list_categories():
    """List event categories."""
    return {
        "categories": [
            {"value": c.value, "name": c.name}
            for c in EventCategory
        ]
    }


@router.get("/{event_id}")
async def get_event(event_id: str):
    """Get an event by ID."""
    service = get_service()
    event = await service.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "id": event.id,
        "event_type": event.event_type.value,
        "category": event.category.value,
        "title": event.title,
        "description": event.description,
        "contact_id": event.contact_id,
        "account_id": event.account_id,
        "deal_id": event.deal_id,
        "user_id": event.user_id,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "metadata": event.metadata,
        "source": event.source,
        "occurred_at": event.occurred_at.isoformat(),
        "duration_seconds": event.duration_seconds,
        "is_private": event.is_private,
        "created_at": event.created_at.isoformat(),
        "created_by": event.created_by,
    }


@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Delete an event."""
    service = get_service()
    
    if not await service.delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"success": True}


# Convenience logging endpoints
@router.post("/email/sent")
async def log_email_sent(request: LogEmailEventRequest):
    """Log an email sent event."""
    service = get_service()
    
    event = await service.log_email_sent(
        contact_id=request.contact_id,
        subject=request.subject,
        user_id=request.user_id,
        email_id=request.email_id,
    )
    
    return {"id": event.id, "event_type": event.event_type.value}


@router.post("/email/opened")
async def log_email_opened(request: LogEmailEventRequest):
    """Log an email opened event."""
    service = get_service()
    
    event = await service.log_email_opened(
        contact_id=request.contact_id,
        subject=request.subject,
        email_id=request.email_id,
    )
    
    return {"id": event.id, "event_type": event.event_type.value}


@router.post("/call")
async def log_call(request: LogCallEventRequest):
    """Log a call event."""
    service = get_service()
    
    event = await service.log_call(
        contact_id=request.contact_id,
        direction=request.direction,
        duration_seconds=request.duration_seconds,
        user_id=request.user_id,
        call_id=request.call_id,
        notes=request.notes,
    )
    
    return {"id": event.id, "event_type": event.event_type.value}


@router.post("/meeting")
async def log_meeting(request: LogMeetingEventRequest):
    """Log a meeting event."""
    service = get_service()
    
    event = await service.log_meeting(
        contact_id=request.contact_id,
        title=request.title,
        status=request.status,
        user_id=request.user_id,
        meeting_id=request.meeting_id,
    )
    
    return {"id": event.id, "event_type": event.event_type.value}


@router.post("/deal/stage-change")
async def log_deal_stage_change(request: LogDealStageChangeRequest):
    """Log a deal stage change event."""
    service = get_service()
    
    event = await service.log_deal_stage_change(
        deal_id=request.deal_id,
        from_stage=request.from_stage,
        to_stage=request.to_stage,
        contact_id=request.contact_id,
        user_id=request.user_id,
    )
    
    return {"id": event.id, "event_type": event.event_type.value}


# Timeline endpoints
@router.get("/timeline/contact/{contact_id}")
async def get_contact_timeline(
    contact_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get timeline for a contact."""
    service = get_service()
    events = await service.get_contact_timeline(contact_id, limit=limit)
    
    return {
        "contact_id": contact_id,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "category": e.category.value,
                "title": e.title,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events)
    }


@router.get("/timeline/deal/{deal_id}")
async def get_deal_timeline(
    deal_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get timeline for a deal."""
    service = get_service()
    events = await service.get_deal_timeline(deal_id, limit=limit)
    
    return {
        "deal_id": deal_id,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "category": e.category.value,
                "title": e.title,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events)
    }


@router.get("/timeline/account/{account_id}")
async def get_account_timeline(
    account_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get timeline for an account."""
    service = get_service()
    events = await service.get_account_timeline(account_id, limit=limit)
    
    return {
        "account_id": account_id,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "category": e.category.value,
                "title": e.title,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events)
    }


# Activity feeds
@router.post("/feeds")
async def create_feed(request: CreateFeedRequest):
    """Create an activity feed."""
    service = get_service()
    
    event_types = None
    if request.event_types:
        event_types = []
        for t in request.event_types:
            try:
                event_types.append(EventType(t))
            except ValueError:
                pass
    
    categories = None
    if request.categories:
        categories = []
        for c in request.categories:
            try:
                categories.append(EventCategory(c))
            except ValueError:
                pass
    
    feed = await service.create_feed(
        name=request.name,
        contact_id=request.contact_id,
        account_id=request.account_id,
        deal_id=request.deal_id,
        user_id=request.user_id,
        event_types=event_types or [],
        categories=categories or [],
    )
    
    return {
        "id": feed.id,
        "name": feed.name,
    }


@router.get("/feeds/{feed_id}")
async def get_feed_events(
    feed_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get events for an activity feed."""
    service = get_service()
    events = await service.get_feed_events(feed_id, limit=limit)
    
    return {
        "feed_id": feed_id,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "category": e.category.value,
                "title": e.title,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events)
    }


# Analytics
@router.get("/analytics/counts")
async def get_event_counts(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    group_by: str = "type"
):
    """Get event counts grouped by dimension."""
    service = get_service()
    counts = await service.get_event_counts(
        from_date=from_date,
        to_date=to_date,
        group_by=group_by
    )
    
    return {"counts": counts, "group_by": group_by}


@router.get("/analytics/daily")
async def get_daily_activity(
    days: int = Query(default=30, le=90),
    user_id: Optional[str] = None
):
    """Get daily activity summary."""
    service = get_service()
    daily = await service.get_daily_activity(days=days, user_id=user_id)
    
    return {"daily": daily, "days": days}


@router.get("/analytics/engagement/{contact_id}")
async def get_engagement_score(
    contact_id: str,
    days: int = Query(default=30, le=90)
):
    """Get engagement score for a contact."""
    service = get_service()
    return await service.get_engagement_score(contact_id, days=days)
