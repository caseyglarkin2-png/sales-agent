"""
Calendar Integration Routes - Calendar sync and scheduling
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

router = APIRouter(prefix="/calendar", tags=["Calendar Integration"])


class CalendarProvider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"
    EXCHANGE = "exchange"


class EventType(str, Enum):
    MEETING = "meeting"
    CALL = "call"
    DEMO = "demo"
    FOLLOW_UP = "follow_up"
    INTERNAL = "internal"
    BLOCKED = "blocked"
    OUT_OF_OFFICE = "out_of_office"


class EventStatus(str, Enum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class RSVPStatus(str, Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    PENDING = "pending"


class SyncStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"


# In-memory storage
calendar_connections = {}
calendar_events = {}
availability_settings = {}
booking_links = {}
meeting_types = {}


class CalendarConnect(BaseModel):
    provider: CalendarProvider
    auth_code: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    event_type: EventType
    start_time: str
    end_time: str
    attendees: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    related_record_id: Optional[str] = None
    related_record_type: Optional[str] = None


class AvailabilitySettings(BaseModel):
    working_hours_start: str = "09:00"
    working_hours_end: str = "17:00"
    working_days: List[int] = [0, 1, 2, 3, 4]  # Mon-Fri
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 15
    min_notice_hours: int = 24


class BookingLinkCreate(BaseModel):
    name: str
    meeting_type_id: str
    duration_minutes: int = 30
    custom_questions: Optional[List[Dict[str, Any]]] = None


# Calendar Connections
@router.post("/connect")
async def connect_calendar(
    request: CalendarConnect,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Connect a calendar provider"""
    connection_id = f"{tenant_id}_{user_id}_{request.provider.value}"
    now = datetime.utcnow()
    
    connection = {
        "id": connection_id,
        "provider": request.provider.value,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "status": SyncStatus.CONNECTED.value,
        "calendars": [
            {"id": "primary", "name": "Primary Calendar", "is_primary": True},
            {"id": "work", "name": "Work", "is_primary": False}
        ],
        "last_sync_at": now.isoformat(),
        "connected_at": now.isoformat()
    }
    
    calendar_connections[connection_id] = connection
    
    return connection


@router.get("/connections")
async def list_connections(
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List calendar connections"""
    connections = [
        c for c in calendar_connections.values()
        if c.get("user_id") == user_id and c.get("tenant_id") == tenant_id
    ]
    
    return {"connections": connections, "total": len(connections)}


@router.delete("/connections/{connection_id}")
async def disconnect_calendar(connection_id: str):
    """Disconnect a calendar"""
    if connection_id not in calendar_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    calendar_connections.pop(connection_id)
    
    return {"message": "Calendar disconnected", "connection_id": connection_id}


@router.post("/connections/{connection_id}/sync")
async def sync_calendar(connection_id: str):
    """Trigger calendar sync"""
    if connection_id not in calendar_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = calendar_connections[connection_id]
    connection["status"] = SyncStatus.SYNCING.value
    
    # Simulate sync
    events_synced = random.randint(10, 50)
    
    connection["status"] = SyncStatus.CONNECTED.value
    connection["last_sync_at"] = datetime.utcnow().isoformat()
    
    return {
        "connection_id": connection_id,
        "events_synced": events_synced,
        "status": "completed"
    }


# Events
@router.post("/events")
async def create_event(
    request: EventCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a calendar event"""
    event_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    event = {
        "id": event_id,
        "title": request.title,
        "event_type": request.event_type.value,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "attendees": [
            {"email": email, "rsvp_status": RSVPStatus.PENDING.value}
            for email in (request.attendees or [])
        ],
        "location": request.location,
        "description": request.description,
        "related_record_id": request.related_record_id,
        "related_record_type": request.related_record_type,
        "status": EventStatus.CONFIRMED.value,
        "organizer_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    calendar_events[event_id] = event
    
    return event


@router.get("/events")
async def list_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[EventType] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List calendar events"""
    result = [
        e for e in calendar_events.values()
        if e.get("tenant_id") == tenant_id and e.get("organizer_id") == user_id
    ]
    
    if start_date:
        result = [e for e in result if e.get("start_time", "") >= start_date]
    if end_date:
        result = [e for e in result if e.get("end_time", "") <= end_date]
    if event_type:
        result = [e for e in result if e.get("event_type") == event_type.value]
    
    result.sort(key=lambda x: x.get("start_time", ""))
    
    return {"events": result, "total": len(result)}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get event details"""
    if event_id not in calendar_events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return calendar_events[event_id]


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None
):
    """Update a calendar event"""
    if event_id not in calendar_events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = calendar_events[event_id]
    
    if title:
        event["title"] = title
    if start_time:
        event["start_time"] = start_time
    if end_time:
        event["end_time"] = end_time
    if location:
        event["location"] = location
    if description:
        event["description"] = description
    
    event["updated_at"] = datetime.utcnow().isoformat()
    
    return event


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete a calendar event"""
    if event_id not in calendar_events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    calendar_events.pop(event_id)
    
    return {"message": "Event deleted", "event_id": event_id}


@router.post("/events/{event_id}/cancel")
async def cancel_event(event_id: str, notify_attendees: bool = True):
    """Cancel a calendar event"""
    if event_id not in calendar_events:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = calendar_events[event_id]
    event["status"] = EventStatus.CANCELLED.value
    event["cancelled_at"] = datetime.utcnow().isoformat()
    
    return {"event": event, "attendees_notified": notify_attendees}


# Availability
@router.put("/availability")
async def update_availability_settings(
    request: AvailabilitySettings,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Update availability settings"""
    settings_id = f"{tenant_id}_{user_id}"
    
    settings = {
        "id": settings_id,
        "working_hours_start": request.working_hours_start,
        "working_hours_end": request.working_hours_end,
        "working_days": request.working_days,
        "buffer_before_minutes": request.buffer_before_minutes,
        "buffer_after_minutes": request.buffer_after_minutes,
        "min_notice_hours": request.min_notice_hours,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    availability_settings[settings_id] = settings
    
    return settings


@router.get("/availability")
async def get_availability_settings(
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get availability settings"""
    settings_id = f"{tenant_id}_{user_id}"
    
    if settings_id not in availability_settings:
        return {
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "working_days": [0, 1, 2, 3, 4],
            "buffer_before_minutes": 0,
            "buffer_after_minutes": 15,
            "min_notice_hours": 24
        }
    
    return availability_settings[settings_id]


@router.get("/availability/slots")
async def get_available_slots(
    date: str,
    duration_minutes: int = Query(default=30),
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get available time slots for a date"""
    # Simulate available slots
    slots = []
    hours = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
             "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
    
    for hour in hours:
        if random.random() > 0.3:  # 70% availability
            slots.append({
                "start_time": f"{date}T{hour}:00Z",
                "end_time": f"{date}T{hour.replace(':00', ':30').replace(':30', ':00')}:00Z",
                "duration_minutes": duration_minutes,
                "available": True
            })
    
    return {"date": date, "slots": slots, "timezone": "UTC"}


# Booking Links
@router.post("/booking-links")
async def create_booking_link(
    request: BookingLinkCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a booking link"""
    link_id = str(uuid.uuid4())
    slug = f"{request.name.lower().replace(' ', '-')}-{link_id[:8]}"
    now = datetime.utcnow()
    
    booking_link = {
        "id": link_id,
        "name": request.name,
        "slug": slug,
        "url": f"https://book.example.com/{slug}",
        "meeting_type_id": request.meeting_type_id,
        "duration_minutes": request.duration_minutes,
        "custom_questions": request.custom_questions or [],
        "bookings_count": 0,
        "is_active": True,
        "owner_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    booking_links[link_id] = booking_link
    
    return booking_link


@router.get("/booking-links")
async def list_booking_links(
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List booking links"""
    links = [
        l for l in booking_links.values()
        if l.get("owner_id") == user_id and l.get("tenant_id") == tenant_id
    ]
    
    return {"booking_links": links, "total": len(links)}


@router.delete("/booking-links/{link_id}")
async def delete_booking_link(link_id: str):
    """Delete a booking link"""
    if link_id not in booking_links:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    booking_links.pop(link_id)
    
    return {"message": "Booking link deleted", "link_id": link_id}


# Meeting Types
@router.post("/meeting-types")
async def create_meeting_type(
    name: str,
    duration_minutes: int = 30,
    description: Optional[str] = None,
    color: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a meeting type"""
    type_id = str(uuid.uuid4())
    
    meeting_type = {
        "id": type_id,
        "name": name,
        "duration_minutes": duration_minutes,
        "description": description,
        "color": color or "#3B82F6",
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    meeting_types[type_id] = meeting_type
    
    return meeting_type


@router.get("/meeting-types")
async def list_meeting_types(tenant_id: str = Query(default="default")):
    """List meeting types"""
    types = [t for t in meeting_types.values() if t.get("tenant_id") == tenant_id]
    return {"meeting_types": types, "total": len(types)}


# Analytics
@router.get("/analytics")
async def get_calendar_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get calendar analytics"""
    user_events = [
        e for e in calendar_events.values()
        if e.get("organizer_id") == user_id and e.get("tenant_id") == tenant_id
    ]
    
    by_type = {}
    for event_type in EventType:
        by_type[event_type.value] = len([
            e for e in user_events if e.get("event_type") == event_type.value
        ])
    
    return {
        "total_events": len(user_events),
        "by_type": by_type,
        "meeting_hours_this_week": round(random.uniform(10, 30), 1),
        "avg_meeting_duration_minutes": random.randint(25, 45),
        "busiest_day": random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
        "no_show_rate": round(random.uniform(0.05, 0.15), 3),
        "booking_link_conversions": {
            "views": random.randint(50, 200),
            "bookings": random.randint(10, 50)
        }
    }
