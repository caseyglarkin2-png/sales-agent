"""
Call Service - Call Tracking and Recording
==========================================
Handles call logging, recording, transcription, and analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class CallDirection(str, Enum):
    """Call direction."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallOutcome(str, Enum):
    """Call outcome."""
    CONNECTED = "connected"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    VOICEMAIL = "voicemail"
    WRONG_NUMBER = "wrong_number"
    LEFT_MESSAGE = "left_message"
    SCHEDULED_CALLBACK = "scheduled_callback"
    NOT_INTERESTED = "not_interested"
    INTERESTED = "interested"
    MEETING_BOOKED = "meeting_booked"


class CallStatus(str, Enum):
    """Call status."""
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SentimentScore(str, Enum):
    """Call sentiment score."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class CallRecording:
    """A call recording."""
    id: str
    call_id: str
    
    # File info
    file_url: str
    file_size: int = 0  # bytes
    duration_seconds: int = 0
    format: str = "mp3"
    
    # Transcription
    transcription: Optional[str] = None
    transcription_status: str = "pending"  # pending, processing, completed, failed
    
    # Analysis
    sentiment: Optional[SentimentScore] = None
    key_phrases: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CallNote:
    """A note on a call."""
    id: str
    call_id: str
    content: str
    
    # Timing
    timestamp_seconds: Optional[int] = None  # When in the call
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class CallDisposition:
    """Call disposition/wrap-up."""
    outcome: CallOutcome
    notes: Optional[str] = None
    
    # Follow-up
    callback_scheduled: Optional[datetime] = None
    next_action: Optional[str] = None
    task_created_id: Optional[str] = None


@dataclass
class Call:
    """A phone call record."""
    id: str
    
    # Direction and status
    direction: CallDirection = CallDirection.OUTBOUND
    status: CallStatus = CallStatus.COMPLETED
    
    # Parties
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    
    # Related entities
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    ring_duration_seconds: int = 0
    
    # Disposition
    outcome: Optional[CallOutcome] = None
    disposition: Optional[CallDisposition] = None
    
    # Recording
    is_recorded: bool = False
    recording: Optional[CallRecording] = None
    
    # Notes
    notes: list[CallNote] = field(default_factory=list)
    summary: Optional[str] = None
    
    # Tags
    tags: list[str] = field(default_factory=list)
    
    # Integration
    external_id: Optional[str] = None
    provider: Optional[str] = None  # twilio, dialpad, etc.
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CallScript:
    """A call script template."""
    id: str
    name: str
    
    # Script content
    opening: Optional[str] = None
    questions: list[str] = field(default_factory=list)
    objection_handlers: dict[str, str] = field(default_factory=dict)
    closing: Optional[str] = None
    
    # Targeting
    use_cases: list[str] = field(default_factory=list)
    
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class CallService:
    """Service for call management."""
    
    def __init__(self):
        self.calls: dict[str, Call] = {}
        self.scripts: dict[str, CallScript] = {}
    
    # Call CRUD
    async def create_call(
        self,
        direction: CallDirection = CallDirection.OUTBOUND,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Call:
        """Create a call record."""
        call = Call(
            id=str(uuid.uuid4()),
            direction=direction,
            from_number=from_number,
            to_number=to_number,
            contact_id=contact_id,
            account_id=account_id,
            deal_id=deal_id,
            user_id=user_id,
            status=CallStatus.RINGING,
            **kwargs
        )
        
        self.calls[call.id] = call
        return call
    
    async def get_call(self, call_id: str) -> Optional[Call]:
        """Get a call by ID."""
        return self.calls.get(call_id)
    
    async def update_call(
        self,
        call_id: str,
        updates: dict[str, Any]
    ) -> Optional[Call]:
        """Update a call."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        for key, value in updates.items():
            if hasattr(call, key):
                setattr(call, key, value)
        
        call.updated_at = datetime.utcnow()
        return call
    
    async def delete_call(self, call_id: str) -> bool:
        """Delete a call."""
        if call_id in self.calls:
            del self.calls[call_id]
            return True
        return False
    
    async def list_calls(
        self,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        direction: Optional[CallDirection] = None,
        outcome: Optional[CallOutcome] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[Call], int]:
        """List calls with filters."""
        calls = list(self.calls.values())
        
        if contact_id:
            calls = [c for c in calls if c.contact_id == contact_id]
        if account_id:
            calls = [c for c in calls if c.account_id == account_id]
        if deal_id:
            calls = [c for c in calls if c.deal_id == deal_id]
        if user_id:
            calls = [c for c in calls if c.user_id == user_id]
        if direction:
            calls = [c for c in calls if c.direction == direction]
        if outcome:
            calls = [c for c in calls if c.outcome == outcome]
        if from_date:
            calls = [c for c in calls if c.started_at >= from_date]
        if to_date:
            calls = [c for c in calls if c.started_at <= to_date]
        
        calls.sort(key=lambda c: c.started_at, reverse=True)
        total = len(calls)
        
        return calls[offset:offset + limit], total
    
    # Call lifecycle
    async def answer_call(self, call_id: str) -> Optional[Call]:
        """Mark call as answered."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        call.status = CallStatus.IN_PROGRESS
        call.answered_at = datetime.utcnow()
        if call.started_at:
            call.ring_duration_seconds = int((call.answered_at - call.started_at).total_seconds())
        call.updated_at = datetime.utcnow()
        
        return call
    
    async def end_call(
        self,
        call_id: str,
        outcome: Optional[CallOutcome] = None,
        duration_seconds: Optional[int] = None
    ) -> Optional[Call]:
        """End a call."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.utcnow()
        
        if duration_seconds is not None:
            call.duration_seconds = duration_seconds
        elif call.answered_at:
            call.duration_seconds = int((call.ended_at - call.answered_at).total_seconds())
        
        if outcome:
            call.outcome = outcome
        
        call.updated_at = datetime.utcnow()
        
        return call
    
    async def set_disposition(
        self,
        call_id: str,
        outcome: CallOutcome,
        notes: Optional[str] = None,
        callback_scheduled: Optional[datetime] = None,
        next_action: Optional[str] = None
    ) -> Optional[Call]:
        """Set call disposition."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        call.outcome = outcome
        call.disposition = CallDisposition(
            outcome=outcome,
            notes=notes,
            callback_scheduled=callback_scheduled,
            next_action=next_action,
        )
        call.updated_at = datetime.utcnow()
        
        return call
    
    # Notes
    async def add_note(
        self,
        call_id: str,
        content: str,
        timestamp_seconds: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Optional[CallNote]:
        """Add a note to a call."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        note = CallNote(
            id=str(uuid.uuid4()),
            call_id=call_id,
            content=content,
            timestamp_seconds=timestamp_seconds,
            created_by=created_by,
        )
        
        call.notes.append(note)
        call.updated_at = datetime.utcnow()
        
        return note
    
    async def delete_note(self, call_id: str, note_id: str) -> bool:
        """Delete a note from a call."""
        call = self.calls.get(call_id)
        if not call:
            return False
        
        original = len(call.notes)
        call.notes = [n for n in call.notes if n.id != note_id]
        
        return len(call.notes) < original
    
    # Recording
    async def add_recording(
        self,
        call_id: str,
        file_url: str,
        file_size: int = 0,
        duration_seconds: int = 0,
        format: str = "mp3"
    ) -> Optional[CallRecording]:
        """Add a recording to a call."""
        call = self.calls.get(call_id)
        if not call:
            return None
        
        recording = CallRecording(
            id=str(uuid.uuid4()),
            call_id=call_id,
            file_url=file_url,
            file_size=file_size,
            duration_seconds=duration_seconds,
            format=format,
        )
        
        call.is_recorded = True
        call.recording = recording
        call.updated_at = datetime.utcnow()
        
        return recording
    
    async def update_transcription(
        self,
        call_id: str,
        transcription: str,
        sentiment: Optional[SentimentScore] = None,
        key_phrases: Optional[list[str]] = None,
        action_items: Optional[list[str]] = None
    ) -> bool:
        """Update call transcription."""
        call = self.calls.get(call_id)
        if not call or not call.recording:
            return False
        
        call.recording.transcription = transcription
        call.recording.transcription_status = "completed"
        
        if sentiment:
            call.recording.sentiment = sentiment
        if key_phrases:
            call.recording.key_phrases = key_phrases
        if action_items:
            call.recording.action_items = action_items
        
        call.updated_at = datetime.utcnow()
        
        return True
    
    # Scripts
    async def create_script(
        self,
        name: str,
        opening: Optional[str] = None,
        questions: Optional[list[str]] = None,
        objection_handlers: Optional[dict[str, str]] = None,
        closing: Optional[str] = None,
        **kwargs
    ) -> CallScript:
        """Create a call script."""
        script = CallScript(
            id=str(uuid.uuid4()),
            name=name,
            opening=opening,
            questions=questions or [],
            objection_handlers=objection_handlers or {},
            closing=closing,
            **kwargs
        )
        
        self.scripts[script.id] = script
        return script
    
    async def get_script(self, script_id: str) -> Optional[CallScript]:
        """Get a script by ID."""
        return self.scripts.get(script_id)
    
    async def list_scripts(
        self,
        active_only: bool = True
    ) -> list[CallScript]:
        """List scripts."""
        scripts = list(self.scripts.values())
        
        if active_only:
            scripts = [s for s in scripts if s.is_active]
        
        scripts.sort(key=lambda s: s.name)
        return scripts
    
    # Analytics
    async def get_call_stats(
        self,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get call statistics."""
        calls, total = await self.list_calls(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=10000
        )
        
        total_duration = sum(c.duration_seconds for c in calls)
        avg_duration = total_duration / len(calls) if calls else 0
        
        # Outcome breakdown
        outcome_counts: dict[str, int] = {}
        for call in calls:
            if call.outcome:
                key = call.outcome.value
                outcome_counts[key] = outcome_counts.get(key, 0) + 1
        
        # Direction breakdown
        direction_counts = {
            "inbound": len([c for c in calls if c.direction == CallDirection.INBOUND]),
            "outbound": len([c for c in calls if c.direction == CallDirection.OUTBOUND]),
        }
        
        # Connect rate
        connected = len([c for c in calls if c.outcome == CallOutcome.CONNECTED or c.duration_seconds > 0])
        connect_rate = (connected / len(calls) * 100) if calls else 0
        
        return {
            "total_calls": total,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "connect_rate": connect_rate,
            "outcome_breakdown": outcome_counts,
            "direction_breakdown": direction_counts,
            "calls_with_recording": len([c for c in calls if c.is_recorded]),
        }
    
    async def get_user_leaderboard(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get user call leaderboard."""
        calls, _ = await self.list_calls(
            from_date=from_date,
            to_date=to_date,
            limit=10000
        )
        
        user_stats: dict[str, dict[str, Any]] = {}
        
        for call in calls:
            if not call.user_id:
                continue
            
            if call.user_id not in user_stats:
                user_stats[call.user_id] = {
                    "user_id": call.user_id,
                    "total_calls": 0,
                    "total_duration": 0,
                    "connected": 0,
                    "meetings_booked": 0,
                }
            
            stats = user_stats[call.user_id]
            stats["total_calls"] += 1
            stats["total_duration"] += call.duration_seconds
            
            if call.outcome == CallOutcome.CONNECTED or call.duration_seconds > 0:
                stats["connected"] += 1
            if call.outcome == CallOutcome.MEETING_BOOKED:
                stats["meetings_booked"] += 1
        
        leaderboard = list(user_stats.values())
        leaderboard.sort(key=lambda x: x["total_calls"], reverse=True)
        
        return leaderboard[:limit]
    
    async def get_hourly_activity(
        self,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> list[dict[str, Any]]:
        """Get hourly call activity."""
        from_date = datetime.utcnow() - timedelta(days=days)
        
        calls, _ = await self.list_calls(
            user_id=user_id,
            from_date=from_date,
            limit=10000
        )
        
        hourly: dict[int, int] = {h: 0 for h in range(24)}
        
        for call in calls:
            hour = call.started_at.hour
            hourly[hour] += 1
        
        return [
            {"hour": hour, "count": count}
            for hour, count in sorted(hourly.items())
        ]


# Singleton instance
_call_service: Optional[CallService] = None


def get_call_service() -> CallService:
    """Get call service singleton."""
    global _call_service
    if _call_service is None:
        _call_service = CallService()
    return _call_service
