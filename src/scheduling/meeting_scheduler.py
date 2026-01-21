"""
Meeting Scheduler.

Manages meeting scheduling, availability, and calendar integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid
import os
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Available time slot."""
    start: datetime
    end: datetime
    duration_minutes: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class MeetingRequest:
    """Meeting scheduling request."""
    id: str
    contact_email: str
    contact_name: str
    company: str
    subject: str
    proposed_times: List[TimeSlot]
    duration_minutes: int
    status: str  # pending, scheduled, declined, expired
    created_at: datetime
    meeting_link: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "company": self.company,
            "subject": self.subject,
            "proposed_times": [t.to_dict() for t in self.proposed_times],
            "duration_minutes": self.duration_minutes,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "meeting_link": self.meeting_link,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "notes": self.notes,
        }


class MeetingScheduler:
    """Handles meeting scheduling and calendar integration."""
    
    def __init__(self):
        self.calendar_service = None
        self.meeting_requests: Dict[str, MeetingRequest] = {}
        self.default_duration = 30
        self.working_hours = {"start": 9, "end": 17}  # 9 AM to 5 PM
        self._init_calendar()
    
    def _init_calendar(self):
        """Initialize Google Calendar API."""
        try:
            creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                creds_data = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_data,
                    scopes=["https://www.googleapis.com/auth/calendar"],
                )
                
                delegated_user = os.environ.get("GMAIL_DELEGATED_USER")
                if delegated_user:
                    credentials = credentials.with_subject(delegated_user)
                
                self.calendar_service = build("calendar", "v3", credentials=credentials)
                logger.info("Google Calendar initialized")
            else:
                logger.warning("Google credentials not configured")
        except Exception as e:
            logger.error(f"Error initializing Calendar: {e}")
    
    async def get_availability(
        self,
        start_date: datetime,
        days: int = 5,
        duration_minutes: int = 30,
    ) -> List[TimeSlot]:
        """Get available time slots.
        
        Args:
            start_date: Start date for availability
            days: Number of days to check
            duration_minutes: Meeting duration
            
        Returns:
            List of available slots
        """
        available_slots = []
        
        if not self.calendar_service:
            # Return mock availability if calendar not configured
            return self._generate_mock_slots(start_date, days, duration_minutes)
        
        try:
            # Get busy times from calendar
            time_min = start_date.replace(hour=0, minute=0, second=0)
            time_max = time_min + timedelta(days=days)
            
            body = {
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "items": [{"id": "primary"}],
            }
            
            freebusy = self.calendar_service.freebusy().query(body=body).execute()
            busy_times = freebusy.get("calendars", {}).get("primary", {}).get("busy", [])
            
            # Generate available slots avoiding busy times
            for day in range(days):
                current_date = start_date + timedelta(days=day)
                
                # Skip weekends
                if current_date.weekday() >= 5:
                    continue
                
                # Generate slots for working hours
                for hour in range(self.working_hours["start"], self.working_hours["end"]):
                    for minute in [0, 30]:
                        slot_start = current_date.replace(hour=hour, minute=minute, second=0)
                        slot_end = slot_start + timedelta(minutes=duration_minutes)
                        
                        # Check if slot is available
                        is_available = True
                        for busy in busy_times:
                            busy_start = datetime.fromisoformat(busy["start"].replace("Z", ""))
                            busy_end = datetime.fromisoformat(busy["end"].replace("Z", ""))
                            
                            if slot_start < busy_end and slot_end > busy_start:
                                is_available = False
                                break
                        
                        if is_available:
                            available_slots.append(TimeSlot(
                                start=slot_start,
                                end=slot_end,
                                duration_minutes=duration_minutes,
                            ))
            
            logger.info(f"Found {len(available_slots)} available slots")
            
        except Exception as e:
            logger.error(f"Error getting availability: {e}")
            return self._generate_mock_slots(start_date, days, duration_minutes)
        
        return available_slots
    
    def _generate_mock_slots(
        self,
        start_date: datetime,
        days: int,
        duration_minutes: int,
    ) -> List[TimeSlot]:
        """Generate mock availability slots."""
        slots = []
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            if current_date.weekday() >= 5:
                continue
            
            for hour in [10, 14, 16]:
                slot_start = current_date.replace(hour=hour, minute=0, second=0)
                slots.append(TimeSlot(
                    start=slot_start,
                    end=slot_start + timedelta(minutes=duration_minutes),
                    duration_minutes=duration_minutes,
                ))
        
        return slots
    
    async def create_meeting_request(
        self,
        contact_email: str,
        contact_name: str,
        company: str,
        subject: str,
        duration_minutes: int = 30,
        preferred_days: int = 5,
        notes: Optional[str] = None,
    ) -> MeetingRequest:
        """Create a meeting request with proposed times.
        
        Args:
            contact_email: Contact's email
            contact_name: Contact's name
            company: Company name
            subject: Meeting subject
            duration_minutes: Meeting length
            preferred_days: Days ahead to propose
            notes: Additional notes
            
        Returns:
            Created meeting request
        """
        request_id = f"mtg_{uuid.uuid4().hex[:8]}"
        
        # Get availability
        start_date = datetime.utcnow() + timedelta(days=1)
        slots = await self.get_availability(start_date, preferred_days, duration_minutes)
        
        # Select top 3 slots
        proposed_times = slots[:3]
        
        request = MeetingRequest(
            id=request_id,
            contact_email=contact_email,
            contact_name=contact_name,
            company=company,
            subject=subject,
            proposed_times=proposed_times,
            duration_minutes=duration_minutes,
            status="pending",
            created_at=datetime.utcnow(),
            notes=notes,
        )
        
        self.meeting_requests[request_id] = request
        logger.info(f"Created meeting request {request_id} for {contact_email}")
        
        return request
    
    async def schedule_meeting(
        self,
        request_id: str,
        selected_time: datetime,
    ) -> Dict[str, Any]:
        """Schedule a meeting at the selected time.
        
        Args:
            request_id: Meeting request ID
            selected_time: Selected time slot
            
        Returns:
            Scheduled meeting details
        """
        if request_id not in self.meeting_requests:
            raise ValueError(f"Meeting request {request_id} not found")
        
        request = self.meeting_requests[request_id]
        
        if not self.calendar_service:
            # Mock scheduling
            request.status = "scheduled"
            request.scheduled_time = selected_time
            request.meeting_link = f"https://meet.google.com/mock-{request.id[:8]}"
            
            return {
                "status": "success",
                "meeting": request.to_dict(),
            }
        
        try:
            # Create calendar event
            event = {
                "summary": request.subject,
                "description": f"Meeting with {request.contact_name} from {request.company}\n\n{request.notes or ''}",
                "start": {
                    "dateTime": selected_time.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": (selected_time + timedelta(minutes=request.duration_minutes)).isoformat(),
                    "timeZone": "UTC",
                },
                "attendees": [
                    {"email": request.contact_email},
                ],
                "conferenceData": {
                    "createRequest": {
                        "requestId": request.id,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    },
                },
            }
            
            created_event = self.calendar_service.events().insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
            ).execute()
            
            request.status = "scheduled"
            request.scheduled_time = selected_time
            request.meeting_link = created_event.get("hangoutLink", "")
            
            logger.info(f"Scheduled meeting {request_id} at {selected_time}")
            
            return {
                "status": "success",
                "meeting": request.to_dict(),
                "calendar_event_id": created_event["id"],
            }
            
        except Exception as e:
            logger.error(f"Error scheduling meeting: {e}")
            raise
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending meeting requests."""
        return [
            r.to_dict() for r in self.meeting_requests.values()
            if r.status == "pending"
        ]
    
    def get_scheduled_meetings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get scheduled meetings."""
        meetings = [
            r.to_dict() for r in self.meeting_requests.values()
            if r.status == "scheduled"
        ]
        
        if start_date:
            meetings = [m for m in meetings if m["scheduled_time"] and 
                       datetime.fromisoformat(m["scheduled_time"]) >= start_date]
        
        if end_date:
            meetings = [m for m in meetings if m["scheduled_time"] and 
                       datetime.fromisoformat(m["scheduled_time"]) <= end_date]
        
        return sorted(meetings, key=lambda x: x["scheduled_time"] or "")
    
    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting request by ID."""
        request = self.meeting_requests.get(request_id)
        return request.to_dict() if request else None


# Singleton
_scheduler: Optional[MeetingScheduler] = None


def get_meeting_scheduler() -> MeetingScheduler:
    """Get singleton meeting scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MeetingScheduler()
    return _scheduler
