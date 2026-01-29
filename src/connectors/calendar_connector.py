"""Google Calendar connector for availability management.

Sprint 67: Added retry for Google API calls
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

T = TypeVar("T")


def with_google_api_retry(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    retryable_statuses: frozenset = frozenset({429, 500, 502, 503, 504}),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for Google API calls.
    
    Handles rate limiting (429) and transient server errors.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except HttpError as e:
                    last_error = e
                    if e.resp.status in retryable_statuses and attempt < max_retries:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            f"Google API error {e.resp.status}, retry {attempt + 1}/{max_retries} "
                            f"in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    # Non-Google API errors (network, etc.)
                    last_error = e
                    if attempt < max_retries:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            f"API call error: {e}, retry {attempt + 1}/{max_retries} in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            raise last_error
        return wrapper
    return decorator


def create_calendar_connector() -> "CalendarConnector":
    """Create a CalendarConnector with credentials from environment.
    
    Looks for:
    1. GOOGLE_CREDENTIALS_FILE - path to service account JSON
    2. GOOGLE_CREDENTIALS_JSON - JSON content directly (or base64 encoded)
    """
    import base64
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    delegated_user = os.environ.get("CALENDAR_DELEGATED_USER") or os.environ.get("GMAIL_DELEGATED_USER")
    
    credentials = None
    
    if creds_file and os.path.exists(creds_file):
        logger.info(f"Loading Calendar credentials from file: {creds_file}")
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    elif creds_json:
        logger.info("Loading Calendar credentials from JSON env var")
        # Try to decode base64 first, fall back to raw JSON
        try:
            decoded = base64.b64decode(creds_json).decode('utf-8')
            creds_data = json.loads(decoded)
        except Exception:
            # Not base64, try raw JSON
            creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    else:
        logger.warning("No Google credentials found, Calendar connector will be in mock mode")
    
    return CalendarConnector(credentials=credentials)


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

    async def health_check(self) -> Dict[str, Any]:
        """Check Calendar API connectivity and return health status.
        
        Uses a lightweight calendar list call.
        
        Returns:
            Dict with status, latency_ms, and optional error
        """
        import time
        
        start_time = time.time()
        
        if not self.credentials:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "error": "No credentials configured",
            }
        
        try:
            if not self.service:
                self._build_service()
            
            # Lightweight call: list calendars with minimal results
            result = self.service.calendarList().list(maxResults=1).execute()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            calendars = result.get("items", [])
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "calendars_accessible": len(calendars) > 0,
                "error": None,
            }
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Calendar health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "error": str(e),
            }

    @with_google_api_retry(max_retries=3, backoff_base=1.0)
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
        business_hours_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find available time slots.
        
        Args:
            duration_minutes: Slot duration (default 30)
            num_slots: Number of slots to find (default 3)
            time_min: Start of search window
            time_max: End of search window
            business_hours_only: Only find slots 9am-5pm weekdays
        
        Returns:
            List of available slots with start, end, and display format
        """
        if not self.service:
            self._build_service()

        if not time_min:
            time_min = datetime.utcnow()
            # Round up to next 30 minutes
            mins = time_min.minute
            if mins % 30 != 0:
                time_min = time_min.replace(
                    minute=((mins // 30) + 1) * 30 % 60,
                    second=0, 
                    microsecond=0
                )
                if mins >= 30:
                    time_min += timedelta(hours=1)
        
        if not time_max:
            time_max = time_min + timedelta(days=5)  # Look 5 days ahead

        # If no service, return mock slots for testing
        if not self.service:
            return self._generate_mock_slots(time_min, num_slots, duration_minutes)

        try:
            freebusy = await self.get_freebusy(time_min=time_min, time_max=time_max)
            
            slots = []
            current = time_min
            busy_times = []
            
            # Parse busy times
            if "calendars" in freebusy and "primary" in freebusy["calendars"]:
                for busy_period in freebusy["calendars"]["primary"].get("busy", []):
                    busy_start = datetime.fromisoformat(busy_period["start"].replace("Z", "+00:00"))
                    busy_end = datetime.fromisoformat(busy_period["end"].replace("Z", "+00:00"))
                    busy_times.append((busy_start, busy_end))
            
            # Find available slots
            while current < time_max and len(slots) < num_slots:
                slot_end = current + timedelta(minutes=duration_minutes)
                
                # Skip weekends if business hours only
                if business_hours_only and current.weekday() >= 5:
                    current += timedelta(days=1)
                    current = current.replace(hour=9, minute=0)
                    continue
                
                # Skip outside business hours (9am-5pm)
                if business_hours_only:
                    if current.hour < 9:
                        current = current.replace(hour=9, minute=0)
                        continue
                    if current.hour >= 17:
                        current += timedelta(days=1)
                        current = current.replace(hour=9, minute=0)
                        continue
                
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
                        "display": self._format_slot_display(current, duration_minutes),
                    })
                
                current += timedelta(minutes=30)
            
            logger.info(f"Found {len(slots)} available slots")
            return slots
        except Exception as e:
            logger.error(f"Error finding available slots: {e}")
            return []

    @with_google_api_retry(max_retries=3, backoff_base=1.0)
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

    def _format_slot_display(self, dt: datetime, duration_minutes: int) -> str:
        """Format a datetime as human-readable slot display."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = day_names[dt.weekday()]
        
        # Format time in 12-hour format
        hour = dt.hour
        am_pm = "AM" if hour < 12 else "PM"
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        
        minute = f":{dt.minute:02d}" if dt.minute else ""
        
        return f"{day_name}, {dt.strftime('%b %d')} at {hour}{minute} {am_pm}"
    
    def _generate_mock_slots(
        self, 
        start: datetime, 
        num_slots: int, 
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Generate mock slots for testing when Calendar API unavailable."""
        slots = []
        current = start
        
        while len(slots) < num_slots:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                current = current.replace(hour=9, minute=0)
                continue
            
            # Skip outside business hours
            if current.hour < 9:
                current = current.replace(hour=9, minute=0)
                continue
            if current.hour >= 17:
                current += timedelta(days=1)
                current = current.replace(hour=9, minute=0)
                continue
            
            slot_end = current + timedelta(minutes=duration_minutes)
            slots.append({
                "start": current.isoformat() + "Z",
                "end": slot_end.isoformat() + "Z",
                "duration_minutes": duration_minutes,
                "display": self._format_slot_display(current, duration_minutes),
            })
            
            # Jump to different times to spread out options
            current += timedelta(hours=4)
        
        return slots
