"""Google Calendar connector for availability management."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarConnector:
    """Connector for Google Calendar API."""

    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize Calendar connector."""
        self.credentials = credentials
        self.service = None

    def _build_service(self) -> None:
        """Build Calendar service from credentials."""
        if self.credentials:
            self.service = build("calendar", "v3", credentials=self.credentials)

    async def get_freebusy(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get freebusy information for calendars."""
        if not self.service:
            self._build_service()

        if not time_min:
            time_min = datetime.utcnow()
        if not time_max:
            time_max = time_min + timedelta(days=7)
        if not calendar_ids:
            calendar_ids = ["primary"]

        try:
            body = {
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "items": [{"id": cal_id} for cal_id in calendar_ids],
            }

            result = self.service.freebusy().query(body=body).execute()
            logger.info(f"Retrieved freebusy for {len(calendar_ids)} calendars")
            return result
        except Exception as e:
            logger.error(f"Error retrieving freebusy: {e}")
            return {}

    async def find_available_slots(
        self,
        duration_minutes: int = 30,
        num_slots: int = 3,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Find available time slots."""
        if not self.service:
            self._build_service()

        if not time_min:
            time_min = datetime.utcnow()
            # Round up to next 30 minutes
            if time_min.minute % 30 != 0:
                time_min = time_min.replace(minute=(time_min.minute // 30 + 1) * 30, second=0, microsecond=0)
        if not time_max:
            time_max = time_min + timedelta(days=7)

        try:
            freebusy = await self.get_freebusy(time_min=time_min, time_max=time_max)
            
            slots = []
            current = time_min
            busy_times = set()
            
            # Parse busy times
            if "calendars" in freebusy and "primary" in freebusy["calendars"]:
                for busy_period in freebusy["calendars"]["primary"].get("busy", []):
                    busy_start = datetime.fromisoformat(busy_period["start"].replace("Z", "+00:00"))
                    busy_end = datetime.fromisoformat(busy_period["end"].replace("Z", "+00:00"))
                    busy_times.add((busy_start, busy_end))
            
            # Find available slots
            while current < time_max and len(slots) < num_slots:
                slot_end = current + timedelta(minutes=duration_minutes)
                
                # Check if slot is free
                is_available = True
                for busy_start, busy_end in busy_times:
                    if not (slot_end <= busy_start or current >= busy_end):
                        is_available = False
                        break
                
                if is_available:
                    slots.append({
                        "start": current.isoformat() + "Z",
                        "end": slot_end.isoformat() + "Z",
                        "duration_minutes": duration_minutes,
                    })
                
                current += timedelta(minutes=30)
            
            logger.info(f"Found {len(slots)} available slots")
            return slots
        except Exception as e:
            logger.error(f"Error finding available slots: {e}")
            return []

    async def create_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        attendees: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Create a calendar event."""
        if not self.service:
            self._build_service()

        try:
            event = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            }

            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            result = self.service.events().insert(calendarId="primary", body=event).execute()
            logger.info(f"Created calendar event {result['id']}")
            return result["id"]
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None
