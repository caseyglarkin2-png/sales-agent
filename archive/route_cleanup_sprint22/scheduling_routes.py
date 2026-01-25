"""
Scheduling Routes - Meeting scheduling, availability, and calendar management
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# Request/Response Models
class TimeSlotResponse(BaseModel):
    start: str
    end: str
    duration_minutes: int


class AvailabilityRequest(BaseModel):
    start_date: Optional[str] = None
    days: int = Field(default=5, ge=1, le=30)
    duration_minutes: int = Field(default=30, ge=15, le=480)
    timezone: Optional[str] = "UTC"


class MeetingRequestCreate(BaseModel):
    contact_email: str
    contact_name: str
    company: Optional[str] = ""
    subject: str
    duration_minutes: int = Field(default=30, ge=15, le=480)
    proposed_times: Optional[List[str]] = None  # ISO datetime strings
    notes: Optional[str] = None
    urgency: Optional[str] = "normal"  # low, normal, high, urgent


class MeetingConfirmation(BaseModel):
    request_id: str
    selected_time: str  # ISO datetime
    attendees: Optional[List[str]] = None
    location: Optional[str] = None
    meeting_type: Optional[str] = "video"  # video, phone, in_person


class RescheduleRequest(BaseModel):
    new_time: str
    reason: Optional[str] = None
    notify_attendees: bool = True


class WorkingHoursConfig(BaseModel):
    start_hour: int = Field(default=9, ge=0, le=23)
    end_hour: int = Field(default=17, ge=1, le=24)
    timezone: str = "UTC"
    days: List[int] = Field(default=[0, 1, 2, 3, 4])  # Mon-Fri
    buffer_minutes: int = Field(default=0, ge=0, le=60)


class BookingLinkCreate(BaseModel):
    name: str
    duration_minutes: int = Field(default=30, ge=15, le=480)
    description: Optional[str] = None
    questions: Optional[List[dict]] = None
    confirmation_message: Optional[str] = None
    is_active: bool = True


class CalendarSyncRequest(BaseModel):
    provider: str  # google, microsoft, apple
    calendar_ids: Optional[List[str]] = None
    sync_direction: str = "both"  # inbound, outbound, both


# In-memory storage
meeting_requests = {}
booking_links = {}
working_hours_config = {}
calendar_syncs = {}


@router.get("/availability")
async def get_availability(
    start_date: Optional[str] = None,
    days: int = Query(default=5, ge=1, le=30),
    duration_minutes: int = Query(default=30, ge=15, le=480),
    timezone: str = "UTC",
    tenant_id: str = Query(default="default")
):
    """Get available time slots for scheduling"""
    try:
        if not start_date:
            start = datetime.utcnow()
        else:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        
        # Generate available slots (mock implementation)
        slots = []
        current = start
        
        for day in range(days):
            check_date = start + timedelta(days=day)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                continue
            
            # Generate slots for 9 AM to 5 PM
            for hour in range(9, 17):
                for minute in [0, 30]:
                    slot_start = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    if slot_end.hour <= 17:
                        slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "duration_minutes": duration_minutes,
                            "available": True
                        })
        
        logger.info("availability_retrieved", slots=len(slots), days=days)
        return {
            "slots": slots[:20],  # Limit response
            "timezone": timezone,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=days)).isoformat()
        }
    except Exception as e:
        logger.error("availability_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meetings")
async def create_meeting_request(
    request: MeetingRequestCreate,
    tenant_id: str = Query(default="default")
):
    """Create a meeting scheduling request"""
    import uuid
    
    meeting_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    meeting = {
        "id": meeting_id,
        "contact_email": request.contact_email,
        "contact_name": request.contact_name,
        "company": request.company,
        "subject": request.subject,
        "duration_minutes": request.duration_minutes,
        "proposed_times": request.proposed_times or [],
        "notes": request.notes,
        "urgency": request.urgency,
        "status": "pending",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    meeting_requests[meeting_id] = meeting
    logger.info("meeting_request_created", meeting_id=meeting_id, contact=request.contact_email)
    
    return meeting


@router.get("/meetings")
async def list_meeting_requests(
    status: Optional[str] = None,
    contact_email: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List meeting requests"""
    meetings = [m for m in meeting_requests.values() if m.get("tenant_id") == tenant_id]
    
    if status:
        meetings = [m for m in meetings if m.get("status") == status]
    if contact_email:
        meetings = [m for m in meetings if m.get("contact_email") == contact_email]
    
    meetings.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "meetings": meetings[offset:offset + limit],
        "total": len(meetings),
        "limit": limit,
        "offset": offset
    }


@router.get("/meetings/{meeting_id}")
async def get_meeting_request(meeting_id: str):
    """Get meeting request details"""
    if meeting_id not in meeting_requests:
        raise HTTPException(status_code=404, detail="Meeting request not found")
    return meeting_requests[meeting_id]


@router.post("/meetings/{meeting_id}/confirm")
async def confirm_meeting(meeting_id: str, confirmation: MeetingConfirmation):
    """Confirm and schedule a meeting"""
    if meeting_id not in meeting_requests:
        raise HTTPException(status_code=404, detail="Meeting request not found")
    
    meeting = meeting_requests[meeting_id]
    meeting["status"] = "scheduled"
    meeting["scheduled_time"] = confirmation.selected_time
    meeting["meeting_type"] = confirmation.meeting_type
    meeting["location"] = confirmation.location
    meeting["attendees"] = confirmation.attendees or []
    meeting["confirmed_at"] = datetime.utcnow().isoformat()
    meeting["updated_at"] = datetime.utcnow().isoformat()
    
    # Generate meeting link for video meetings
    if confirmation.meeting_type == "video":
        meeting["meeting_link"] = f"https://meet.example.com/{meeting_id[:8]}"
    
    logger.info("meeting_confirmed", meeting_id=meeting_id, time=confirmation.selected_time)
    return meeting


@router.post("/meetings/{meeting_id}/reschedule")
async def reschedule_meeting(meeting_id: str, request: RescheduleRequest):
    """Reschedule an existing meeting"""
    if meeting_id not in meeting_requests:
        raise HTTPException(status_code=404, detail="Meeting request not found")
    
    meeting = meeting_requests[meeting_id]
    old_time = meeting.get("scheduled_time")
    meeting["scheduled_time"] = request.new_time
    meeting["status"] = "rescheduled"
    meeting["reschedule_reason"] = request.reason
    meeting["updated_at"] = datetime.utcnow().isoformat()
    
    if "reschedule_history" not in meeting:
        meeting["reschedule_history"] = []
    meeting["reschedule_history"].append({
        "old_time": old_time,
        "new_time": request.new_time,
        "reason": request.reason,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    logger.info("meeting_rescheduled", meeting_id=meeting_id, new_time=request.new_time)
    return meeting


@router.post("/meetings/{meeting_id}/cancel")
async def cancel_meeting(
    meeting_id: str,
    reason: Optional[str] = None,
    notify_attendees: bool = True
):
    """Cancel a meeting"""
    if meeting_id not in meeting_requests:
        raise HTTPException(status_code=404, detail="Meeting request not found")
    
    meeting = meeting_requests[meeting_id]
    meeting["status"] = "cancelled"
    meeting["cancellation_reason"] = reason
    meeting["cancelled_at"] = datetime.utcnow().isoformat()
    meeting["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("meeting_cancelled", meeting_id=meeting_id)
    return meeting


@router.put("/working-hours")
async def set_working_hours(
    config: WorkingHoursConfig,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Configure working hours for availability"""
    key = f"{tenant_id}:{user_id}"
    working_hours_config[key] = {
        "start_hour": config.start_hour,
        "end_hour": config.end_hour,
        "timezone": config.timezone,
        "days": config.days,
        "buffer_minutes": config.buffer_minutes,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    logger.info("working_hours_updated", user_id=user_id)
    return working_hours_config[key]


@router.get("/working-hours")
async def get_working_hours(
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get working hours configuration"""
    key = f"{tenant_id}:{user_id}"
    if key not in working_hours_config:
        return {
            "start_hour": 9,
            "end_hour": 17,
            "timezone": "UTC",
            "days": [0, 1, 2, 3, 4],
            "buffer_minutes": 0
        }
    return working_hours_config[key]


@router.post("/booking-links")
async def create_booking_link(
    request: BookingLinkCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a shareable booking link"""
    import uuid
    
    link_id = str(uuid.uuid4())
    slug = request.name.lower().replace(" ", "-")[:30]
    
    link = {
        "id": link_id,
        "slug": slug,
        "name": request.name,
        "duration_minutes": request.duration_minutes,
        "description": request.description,
        "questions": request.questions or [],
        "confirmation_message": request.confirmation_message,
        "is_active": request.is_active,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "url": f"https://book.example.com/{slug}",
        "created_at": datetime.utcnow().isoformat()
    }
    
    booking_links[link_id] = link
    logger.info("booking_link_created", link_id=link_id, slug=slug)
    return link


@router.get("/booking-links")
async def list_booking_links(
    user_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List booking links"""
    links = [l for l in booking_links.values() if l.get("tenant_id") == tenant_id]
    
    if user_id:
        links = [l for l in links if l.get("user_id") == user_id]
    if is_active is not None:
        links = [l for l in links if l.get("is_active") == is_active]
    
    return {"booking_links": links, "total": len(links)}


@router.get("/booking-links/{link_id}")
async def get_booking_link(link_id: str):
    """Get booking link details"""
    if link_id not in booking_links:
        raise HTTPException(status_code=404, detail="Booking link not found")
    return booking_links[link_id]


@router.put("/booking-links/{link_id}")
async def update_booking_link(link_id: str, request: BookingLinkCreate):
    """Update a booking link"""
    if link_id not in booking_links:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    link = booking_links[link_id]
    link.update({
        "name": request.name,
        "duration_minutes": request.duration_minutes,
        "description": request.description,
        "questions": request.questions or [],
        "confirmation_message": request.confirmation_message,
        "is_active": request.is_active,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return link


@router.delete("/booking-links/{link_id}")
async def delete_booking_link(link_id: str):
    """Delete a booking link"""
    if link_id not in booking_links:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    del booking_links[link_id]
    return {"status": "deleted", "link_id": link_id}


@router.post("/calendar-sync")
async def setup_calendar_sync(
    request: CalendarSyncRequest,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Set up calendar synchronization"""
    import uuid
    
    sync_id = str(uuid.uuid4())
    
    sync = {
        "id": sync_id,
        "provider": request.provider,
        "calendar_ids": request.calendar_ids or ["primary"],
        "sync_direction": request.sync_direction,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "status": "active",
        "last_sync": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    calendar_syncs[sync_id] = sync
    logger.info("calendar_sync_created", sync_id=sync_id, provider=request.provider)
    return sync


@router.get("/calendar-sync")
async def list_calendar_syncs(
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List calendar sync configurations"""
    syncs = [s for s in calendar_syncs.values() if s.get("tenant_id") == tenant_id]
    
    if user_id:
        syncs = [s for s in syncs if s.get("user_id") == user_id]
    if provider:
        syncs = [s for s in syncs if s.get("provider") == provider]
    
    return {"syncs": syncs, "total": len(syncs)}


@router.post("/calendar-sync/{sync_id}/trigger")
async def trigger_calendar_sync(sync_id: str):
    """Trigger immediate calendar sync"""
    if sync_id not in calendar_syncs:
        raise HTTPException(status_code=404, detail="Calendar sync not found")
    
    sync = calendar_syncs[sync_id]
    sync["last_sync"] = datetime.utcnow().isoformat()
    sync["sync_status"] = "completed"
    
    logger.info("calendar_sync_triggered", sync_id=sync_id)
    return {"status": "sync_completed", "sync": sync}


@router.delete("/calendar-sync/{sync_id}")
async def remove_calendar_sync(sync_id: str):
    """Remove calendar sync configuration"""
    if sync_id not in calendar_syncs:
        raise HTTPException(status_code=404, detail="Calendar sync not found")
    
    del calendar_syncs[sync_id]
    return {"status": "deleted", "sync_id": sync_id}


@router.get("/upcoming")
async def get_upcoming_meetings(
    user_id: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=30),
    tenant_id: str = Query(default="default")
):
    """Get upcoming scheduled meetings"""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    
    meetings = [
        m for m in meeting_requests.values()
        if m.get("tenant_id") == tenant_id
        and m.get("status") == "scheduled"
        and m.get("scheduled_time")
    ]
    
    # Filter by date range
    upcoming = []
    for m in meetings:
        try:
            scheduled = datetime.fromisoformat(m["scheduled_time"].replace("Z", "+00:00"))
            if now <= scheduled <= cutoff:
                upcoming.append(m)
        except:
            pass
    
    upcoming.sort(key=lambda x: x.get("scheduled_time", ""))
    
    return {
        "meetings": upcoming,
        "total": len(upcoming),
        "period_days": days
    }


@router.get("/stats")
async def get_scheduling_stats(
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Query(default="default")
):
    """Get scheduling statistics"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    meetings = [
        m for m in meeting_requests.values()
        if m.get("tenant_id") == tenant_id
    ]
    
    # Filter by date
    recent = []
    for m in meetings:
        try:
            created = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
            if created >= cutoff:
                recent.append(m)
        except:
            pass
    
    total = len(recent)
    scheduled = len([m for m in recent if m.get("status") == "scheduled"])
    cancelled = len([m for m in recent if m.get("status") == "cancelled"])
    pending = len([m for m in recent if m.get("status") == "pending"])
    rescheduled = len([m for m in recent if m.get("status") == "rescheduled"])
    
    return {
        "period_days": days,
        "total_requests": total,
        "scheduled": scheduled,
        "cancelled": cancelled,
        "pending": pending,
        "rescheduled": rescheduled,
        "completion_rate": round(scheduled / total * 100, 2) if total > 0 else 0,
        "cancellation_rate": round(cancelled / total * 100, 2) if total > 0 else 0
    }
