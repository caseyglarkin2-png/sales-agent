"""
Timeline API Routes
===================
Endpoints for managing activity timelines.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import structlog

from src.timeline import get_timeline_service, EventType, EventSource

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/timeline", tags=["Timeline"])


class RecordEventRequest(BaseModel):
    contact_id: str
    event_type: str
    title: str
    description: str = ""
    source: str = "api"
    metadata: dict = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    is_important: bool = False


class RecordEmailEventRequest(BaseModel):
    contact_id: str
    event_type: str
    email_id: str
    subject: str
    metadata: dict = None


class RecordMeetingEventRequest(BaseModel):
    contact_id: str
    event_type: str
    meeting_id: str
    meeting_title: str
    metadata: dict = None


@router.get("/contacts/{contact_id}")
async def get_contact_timeline(
    contact_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_types: Optional[str] = None,
    sources: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    important_only: bool = False,
):
    """Get timeline for a specific contact."""
    service = get_timeline_service()
    
    # Parse event types
    type_filters = None
    if event_types:
        try:
            type_filters = [EventType(t.strip()) for t in event_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")
    
    # Parse sources
    source_filters = None
    if sources:
        try:
            source_filters = [EventSource(s.strip()) for s in sources.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid source: {e}")
    
    events = service.get_contact_timeline(
        contact_id=contact_id,
        limit=limit,
        offset=offset,
        event_types=type_filters,
        sources=source_filters,
        start_date=start_date,
        end_date=end_date,
        important_only=important_only,
    )
    
    return {
        "contact_id": contact_id,
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "offset": offset,
        "limit": limit,
    }


@router.get("/global")
async def get_global_timeline(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    event_types: Optional[str] = None,
    sources: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get global timeline across all contacts."""
    service = get_timeline_service()
    
    # Parse event types
    type_filters = None
    if event_types:
        try:
            type_filters = [EventType(t.strip()) for t in event_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")
    
    # Parse sources
    source_filters = None
    if sources:
        try:
            source_filters = [EventSource(s.strip()) for s in sources.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid source: {e}")
    
    events = service.get_global_timeline(
        limit=limit,
        offset=offset,
        event_types=type_filters,
        sources=source_filters,
        start_date=start_date,
        end_date=end_date,
    )
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "offset": offset,
        "limit": limit,
    }


@router.get("/contacts/{contact_id}/recent")
async def get_recent_activity(
    contact_id: str,
    hours: int = Query(24, ge=1, le=168),
):
    """Get recent activity for a contact."""
    service = get_timeline_service()
    
    events = service.get_recent_activity(
        contact_id=contact_id,
        hours=hours,
    )
    
    return {
        "contact_id": contact_id,
        "hours": hours,
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


@router.get("/contacts/{contact_id}/summary")
async def get_activity_summary(
    contact_id: str,
    days: int = Query(30, ge=1, le=365),
):
    """Get activity summary for a contact."""
    service = get_timeline_service()
    
    return service.get_activity_summary(
        contact_id=contact_id,
        days=days,
    )


@router.get("/trends")
async def get_activity_trends(
    contact_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
):
    """Get activity trends over time."""
    service = get_timeline_service()
    
    return service.get_activity_trends(
        contact_id=contact_id,
        days=days,
    )


@router.post("/events")
async def record_event(request: RecordEventRequest):
    """Record a new event in the timeline."""
    service = get_timeline_service()
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}",
        )
    
    try:
        source = EventSource(request.source)
    except ValueError:
        source = EventSource.API
    
    event = service.record_event(
        contact_id=request.contact_id,
        event_type=event_type,
        title=request.title,
        description=request.description,
        source=source,
        metadata=request.metadata,
        actor_id=request.actor_id,
        actor_name=request.actor_name,
        related_entity_type=request.related_entity_type,
        related_entity_id=request.related_entity_id,
        is_important=request.is_important,
    )
    
    return {
        "message": "Event recorded",
        "event": event.to_dict(),
    }


@router.post("/events/email")
async def record_email_event(request: RecordEmailEventRequest):
    """Record an email event."""
    service = get_timeline_service()
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}",
        )
    
    event = service.record_email_event(
        contact_id=request.contact_id,
        event_type=event_type,
        email_id=request.email_id,
        subject=request.subject,
        metadata=request.metadata,
    )
    
    return {
        "message": "Email event recorded",
        "event": event.to_dict(),
    }


@router.post("/events/meeting")
async def record_meeting_event(request: RecordMeetingEventRequest):
    """Record a meeting event."""
    service = get_timeline_service()
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}",
        )
    
    event = service.record_meeting_event(
        contact_id=request.contact_id,
        event_type=event_type,
        meeting_id=request.meeting_id,
        meeting_title=request.meeting_title,
        metadata=request.metadata,
    )
    
    return {
        "message": "Meeting event recorded",
        "event": event.to_dict(),
    }


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event from the timeline."""
    service = get_timeline_service()
    
    if not service.delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event deleted"}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get a specific event by ID."""
    service = get_timeline_service()
    
    event = service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"event": event.to_dict()}


@router.get("/event-types")
async def list_event_types():
    """List available event types."""
    return {
        "event_types": [
            {"value": et.value, "name": et.name}
            for et in EventType
        ]
    }


@router.get("/sources")
async def list_sources():
    """List available event sources."""
    return {
        "sources": [
            {"value": s.value, "name": s.name}
            for s in EventSource
        ]
    }
