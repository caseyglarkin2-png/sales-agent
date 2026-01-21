"""
Meeting Scheduling Routes.

API endpoints for meeting scheduling and calendar integration.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.scheduling import get_meeting_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/meetings", tags=["meetings"])


class CreateMeetingRequest(BaseModel):
    contact_email: str
    contact_name: str
    company: str
    subject: str
    duration_minutes: int = 30
    preferred_days: int = 5
    notes: Optional[str] = None


class ScheduleMeetingRequest(BaseModel):
    request_id: str
    selected_time: str  # ISO format


@router.get("/availability")
async def get_availability(
    days: int = 5,
    duration_minutes: int = 30,
) -> Dict[str, Any]:
    """Get available meeting time slots."""
    scheduler = get_meeting_scheduler()
    
    start_date = datetime.utcnow()
    slots = await scheduler.get_availability(
        start_date=start_date,
        days=days,
        duration_minutes=duration_minutes,
    )
    
    return {
        "slots": [s.to_dict() for s in slots],
        "count": len(slots),
    }


@router.post("/request")
async def create_meeting_request(request: CreateMeetingRequest) -> Dict[str, Any]:
    """Create a new meeting request with proposed times."""
    scheduler = get_meeting_scheduler()
    
    meeting_request = await scheduler.create_meeting_request(
        contact_email=request.contact_email,
        contact_name=request.contact_name,
        company=request.company,
        subject=request.subject,
        duration_minutes=request.duration_minutes,
        preferred_days=request.preferred_days,
        notes=request.notes,
    )
    
    return {
        "status": "success",
        "meeting_request": meeting_request.to_dict(),
    }


@router.post("/schedule")
async def schedule_meeting(request: ScheduleMeetingRequest) -> Dict[str, Any]:
    """Schedule a meeting at the selected time."""
    scheduler = get_meeting_scheduler()
    
    try:
        selected_time = datetime.fromisoformat(request.selected_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format")
    
    try:
        result = await scheduler.schedule_meeting(
            request_id=request.request_id,
            selected_time=selected_time,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_requests() -> Dict[str, Any]:
    """Get all pending meeting requests."""
    scheduler = get_meeting_scheduler()
    requests = scheduler.get_pending_requests()
    
    return {
        "requests": requests,
        "count": len(requests),
    }


@router.get("/scheduled")
async def get_scheduled_meetings(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get scheduled meetings."""
    scheduler = get_meeting_scheduler()
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    meetings = scheduler.get_scheduled_meetings(start_date=start, end_date=end)
    
    return {
        "meetings": meetings,
        "count": len(meetings),
    }


@router.get("/{request_id}")
async def get_meeting_request(request_id: str) -> Dict[str, Any]:
    """Get a meeting request by ID."""
    scheduler = get_meeting_scheduler()
    request = scheduler.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Meeting request not found")
    
    return {
        "meeting_request": request,
    }
