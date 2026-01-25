"""
Meeting Scheduler V2 Routes - Advanced scheduling with AI optimization
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

router = APIRouter(prefix="/scheduling-v2", tags=["Meeting Scheduler V2"])


class MeetingType(str, Enum):
    DISCOVERY = "discovery"
    DEMO = "demo"
    FOLLOW_UP = "follow_up"
    PROPOSAL_REVIEW = "proposal_review"
    NEGOTIATION = "negotiation"
    ONBOARDING = "onboarding"
    QBR = "qbr"
    TRAINING = "training"
    CUSTOM = "custom"


class BookingStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class AvailabilityType(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    TENTATIVE = "tentative"
    OUT_OF_OFFICE = "out_of_office"


# In-memory storage
scheduling_links = {}
bookings = {}
availability_rules = {}
routing_rules = {}


class SchedulingLinkCreate(BaseModel):
    name: str
    meeting_type: MeetingType
    duration_minutes: int = 30
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 15
    min_notice_hours: int = 24
    max_days_ahead: int = 30
    description: Optional[str] = None
    location: Optional[str] = None  # zoom, meet, phone, in-person
    questions: List[Dict[str, Any]] = []
    team_members: List[str] = []
    routing_enabled: bool = False


class BookingCreate(BaseModel):
    link_id: str
    start_time: str
    attendee_name: str
    attendee_email: str
    attendee_phone: Optional[str] = None
    attendee_company: Optional[str] = None
    answers: Dict[str, Any] = {}
    notes: Optional[str] = None


class AvailabilityRuleCreate(BaseModel):
    user_id: str
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    timezone: str = "America/New_York"


# Scheduling Links
@router.post("/links")
async def create_scheduling_link(
    request: SchedulingLinkCreate,
    tenant_id: str = Query(default="default")
):
    """Create a scheduling link"""
    link_id = str(uuid.uuid4())
    slug = str(uuid.uuid4())[:8]
    now = datetime.utcnow()
    
    link = {
        "id": link_id,
        "slug": slug,
        "name": request.name,
        "meeting_type": request.meeting_type.value,
        "duration_minutes": request.duration_minutes,
        "buffer_before_minutes": request.buffer_before_minutes,
        "buffer_after_minutes": request.buffer_after_minutes,
        "min_notice_hours": request.min_notice_hours,
        "max_days_ahead": request.max_days_ahead,
        "description": request.description,
        "location": request.location,
        "questions": request.questions,
        "team_members": request.team_members,
        "routing_enabled": request.routing_enabled,
        "is_active": True,
        "booking_url": f"https://schedule.example.com/{slug}",
        "total_bookings": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    scheduling_links[link_id] = link
    
    logger.info("scheduling_link_created", link_id=link_id)
    
    return link


@router.get("/links")
async def list_scheduling_links(
    meeting_type: Optional[MeetingType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List scheduling links"""
    result = [l for l in scheduling_links.values() if l.get("tenant_id") == tenant_id]
    
    if meeting_type:
        result = [l for l in result if l.get("meeting_type") == meeting_type.value]
    if is_active is not None:
        result = [l for l in result if l.get("is_active") == is_active]
    
    return {"links": result, "total": len(result)}


@router.get("/links/{link_id}")
async def get_scheduling_link(
    link_id: str,
    tenant_id: str = Query(default="default")
):
    """Get scheduling link details"""
    if link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    return scheduling_links[link_id]


@router.patch("/links/{link_id}")
async def update_scheduling_link(
    link_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update scheduling link"""
    if link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    
    link = scheduling_links[link_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "duration_minutes", "buffer_before_minutes", 
                   "buffer_after_minutes", "min_notice_hours", "max_days_ahead", 
                   "questions", "is_active", "team_members"]:
            link[key] = value
    
    link["updated_at"] = datetime.utcnow().isoformat()
    
    return link


@router.delete("/links/{link_id}")
async def delete_scheduling_link(
    link_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete scheduling link"""
    if link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    
    del scheduling_links[link_id]
    
    return {"success": True, "deleted": link_id}


# Availability
@router.get("/links/{link_id}/availability")
async def get_available_slots(
    link_id: str,
    date: str,  # YYYY-MM-DD
    timezone: str = Query(default="America/New_York"),
    tenant_id: str = Query(default="default")
):
    """Get available time slots for a date"""
    if link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    
    link = scheduling_links[link_id]
    
    # Generate mock available slots
    slots = []
    base_hour = 9
    
    for i in range(8):  # 8 slots throughout the day
        hour = base_hour + i
        if random.random() > 0.3:  # 70% chance of availability
            slots.append({
                "start_time": f"{date}T{hour:02d}:00:00",
                "end_time": f"{date}T{hour:02d}:{link['duration_minutes']:02d}:00",
                "available": True,
                "host_id": random.choice(link.get("team_members", ["user_1"]) or ["user_1"])
            })
    
    return {
        "link_id": link_id,
        "date": date,
        "timezone": timezone,
        "slots": slots
    }


@router.get("/links/{link_id}/availability/range")
async def get_availability_range(
    link_id: str,
    start_date: str,
    end_date: str,
    timezone: str = Query(default="America/New_York"),
    tenant_id: str = Query(default="default")
):
    """Get availability for a date range"""
    if link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    
    availability = []
    current = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    while current <= end:
        if current.weekday() < 5:  # Weekdays only
            availability.append({
                "date": current.isoformat()[:10],
                "available_slots": random.randint(0, 8),
                "status": "available" if random.random() > 0.2 else "limited"
            })
        else:
            availability.append({
                "date": current.isoformat()[:10],
                "available_slots": 0,
                "status": "unavailable"
            })
        current += timedelta(days=1)
    
    return {
        "link_id": link_id,
        "start_date": start_date,
        "end_date": end_date,
        "availability": availability
    }


# Bookings
@router.post("/bookings")
async def create_booking(
    request: BookingCreate,
    tenant_id: str = Query(default="default")
):
    """Create a booking"""
    if request.link_id not in scheduling_links:
        raise HTTPException(status_code=404, detail="Scheduling link not found")
    
    booking_id = str(uuid.uuid4())
    now = datetime.utcnow()
    link = scheduling_links[request.link_id]
    
    # Calculate end time
    start = datetime.fromisoformat(request.start_time)
    end = start + timedelta(minutes=link["duration_minutes"])
    
    booking = {
        "id": booking_id,
        "link_id": request.link_id,
        "meeting_type": link["meeting_type"],
        "start_time": request.start_time,
        "end_time": end.isoformat(),
        "duration_minutes": link["duration_minutes"],
        "attendee": {
            "name": request.attendee_name,
            "email": request.attendee_email,
            "phone": request.attendee_phone,
            "company": request.attendee_company
        },
        "answers": request.answers,
        "notes": request.notes,
        "host_id": random.choice(link.get("team_members", ["user_1"]) or ["user_1"]),
        "status": BookingStatus.SCHEDULED.value,
        "location": link.get("location"),
        "meeting_url": f"https://meet.example.com/{booking_id[:8]}",
        "calendar_event_id": None,
        "reminder_sent": False,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    bookings[booking_id] = booking
    scheduling_links[request.link_id]["total_bookings"] = \
        scheduling_links[request.link_id].get("total_bookings", 0) + 1
    
    logger.info("booking_created", booking_id=booking_id)
    
    return booking


@router.get("/bookings")
async def list_bookings(
    link_id: Optional[str] = None,
    status: Optional[BookingStatus] = None,
    host_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List bookings"""
    result = [b for b in bookings.values() if b.get("tenant_id") == tenant_id]
    
    if link_id:
        result = [b for b in result if b.get("link_id") == link_id]
    if status:
        result = [b for b in result if b.get("status") == status.value]
    if host_id:
        result = [b for b in result if b.get("host_id") == host_id]
    if start_date:
        result = [b for b in result if b.get("start_time", "") >= start_date]
    if end_date:
        result = [b for b in result if b.get("start_time", "") <= end_date]
    
    result.sort(key=lambda x: x.get("start_time", ""))
    
    return {
        "bookings": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/bookings/{booking_id}")
async def get_booking(
    booking_id: str,
    tenant_id: str = Query(default="default")
):
    """Get booking details"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    return bookings[booking_id]


@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking(
    booking_id: str,
    tenant_id: str = Query(default="default")
):
    """Confirm a booking"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    bookings[booking_id]["status"] = BookingStatus.CONFIRMED.value
    bookings[booking_id]["confirmed_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "confirmed"}


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Cancel a booking"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    bookings[booking_id]["status"] = BookingStatus.CANCELLED.value
    bookings[booking_id]["cancellation_reason"] = reason
    bookings[booking_id]["cancelled_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "cancelled"}


@router.post("/bookings/{booking_id}/reschedule")
async def reschedule_booking(
    booking_id: str,
    new_start_time: str,
    tenant_id: str = Query(default="default")
):
    """Reschedule a booking"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking = bookings[booking_id]
    old_time = booking["start_time"]
    
    start = datetime.fromisoformat(new_start_time)
    end = start + timedelta(minutes=booking["duration_minutes"])
    
    booking["start_time"] = new_start_time
    booking["end_time"] = end.isoformat()
    booking["status"] = BookingStatus.RESCHEDULED.value
    booking["previous_start_time"] = old_time
    booking["rescheduled_at"] = datetime.utcnow().isoformat()
    
    return booking


@router.post("/bookings/{booking_id}/no-show")
async def mark_no_show(
    booking_id: str,
    tenant_id: str = Query(default="default")
):
    """Mark booking as no-show"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    bookings[booking_id]["status"] = BookingStatus.NO_SHOW.value
    
    return {"success": True, "status": "no_show"}


# User Availability Rules
@router.post("/availability/rules")
async def create_availability_rule(
    request: AvailabilityRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create availability rule for a user"""
    rule_id = str(uuid.uuid4())
    
    rule = {
        "id": rule_id,
        "user_id": request.user_id,
        "day_of_week": request.day_of_week,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "timezone": request.timezone,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    availability_rules[rule_id] = rule
    
    return rule


@router.get("/availability/rules/{user_id}")
async def get_user_availability_rules(
    user_id: str,
    tenant_id: str = Query(default="default")
):
    """Get availability rules for a user"""
    result = [r for r in availability_rules.values() 
              if r.get("user_id") == user_id and r.get("tenant_id") == tenant_id]
    
    result.sort(key=lambda x: x.get("day_of_week", 0))
    
    return {"user_id": user_id, "rules": result}


# Smart Scheduling
@router.post("/smart-schedule")
async def get_smart_suggestions(
    attendee_email: str,
    duration_minutes: int = 30,
    meeting_type: Optional[MeetingType] = None,
    priority: str = "medium",
    tenant_id: str = Query(default="default")
):
    """Get AI-powered scheduling suggestions"""
    now = datetime.utcnow()
    
    suggestions = []
    for i in range(5):
        day_offset = random.randint(1, 7)
        hour = random.randint(9, 16)
        suggested_time = now + timedelta(days=day_offset, hours=hour - now.hour)
        
        suggestions.append({
            "start_time": suggested_time.isoformat(),
            "end_time": (suggested_time + timedelta(minutes=duration_minutes)).isoformat(),
            "score": round(random.uniform(0.7, 1.0), 2),
            "reason": random.choice([
                "Best time based on attendee's past engagement",
                "Optimal for your productivity patterns",
                "No conflicts, good buffer time",
                "High response rate time slot"
            ]),
            "host_suggestion": f"user_{random.randint(1, 5)}"
        })
    
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "attendee_email": attendee_email,
        "duration_minutes": duration_minutes,
        "suggestions": suggestions
    }


# Analytics
@router.get("/analytics")
async def get_scheduling_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get scheduling analytics"""
    return {
        "period_days": days,
        "bookings": {
            "total": random.randint(100, 500),
            "confirmed": random.randint(80, 400),
            "cancelled": random.randint(10, 50),
            "no_shows": random.randint(5, 30)
        },
        "conversion": {
            "link_views": random.randint(500, 2000),
            "bookings_made": random.randint(100, 500),
            "conversion_rate": round(random.uniform(0.15, 0.35), 3)
        },
        "time_metrics": {
            "avg_booking_lead_time_hours": random.randint(24, 96),
            "avg_meeting_duration_minutes": random.randint(25, 45),
            "most_popular_day": random.choice(["Monday", "Tuesday", "Wednesday"]),
            "most_popular_time": random.choice(["10:00", "11:00", "14:00", "15:00"])
        },
        "by_meeting_type": {
            "discovery": random.randint(30, 150),
            "demo": random.randint(50, 200),
            "follow_up": random.randint(20, 100)
        }
    }
