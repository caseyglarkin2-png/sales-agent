"""
Calls Routes - Call Tracking API
=================================
REST API endpoints for call management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..calls import (
    CallService,
    CallDirection,
    CallOutcome,
    SentimentScore,
    get_call_service,
)


router = APIRouter(prefix="/calls", tags=["Calls"])


# Request/Response models
class CreateCallRequest(BaseModel):
    """Create call request."""
    direction: str = "outbound"
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None


class UpdateCallRequest(BaseModel):
    """Update call request."""
    summary: Optional[str] = None
    tags: Optional[list[str]] = None


class EndCallRequest(BaseModel):
    """End call request."""
    outcome: Optional[str] = None
    duration_seconds: Optional[int] = None


class SetDispositionRequest(BaseModel):
    """Set disposition request."""
    outcome: str
    notes: Optional[str] = None
    callback_scheduled: Optional[datetime] = None
    next_action: Optional[str] = None


class AddNoteRequest(BaseModel):
    """Add note request."""
    content: str
    timestamp_seconds: Optional[int] = None


class AddRecordingRequest(BaseModel):
    """Add recording request."""
    file_url: str
    file_size: int = 0
    duration_seconds: int = 0
    format: str = "mp3"


class UpdateTranscriptionRequest(BaseModel):
    """Update transcription request."""
    transcription: str
    sentiment: Optional[str] = None
    key_phrases: Optional[list[str]] = None
    action_items: Optional[list[str]] = None


class CreateScriptRequest(BaseModel):
    """Create script request."""
    name: str
    opening: Optional[str] = None
    questions: Optional[list[str]] = None
    objection_handlers: Optional[dict[str, str]] = None
    closing: Optional[str] = None
    use_cases: Optional[list[str]] = None


def get_service() -> CallService:
    """Get call service instance."""
    return get_call_service()


# Call CRUD
@router.post("")
async def create_call(request: CreateCallRequest):
    """Create a new call."""
    service = get_service()
    
    try:
        direction = CallDirection(request.direction)
    except ValueError:
        direction = CallDirection.OUTBOUND
    
    call = await service.create_call(
        direction=direction,
        from_number=request.from_number,
        to_number=request.to_number,
        contact_id=request.contact_id,
        account_id=request.account_id,
        deal_id=request.deal_id,
        user_id=request.user_id,
    )
    
    return {
        "id": call.id,
        "direction": call.direction.value,
        "status": call.status.value,
        "started_at": call.started_at.isoformat(),
    }


@router.get("")
async def list_calls(
    contact_id: Optional[str] = None,
    account_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    user_id: Optional[str] = None,
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List calls."""
    service = get_service()
    
    direction_enum = None
    if direction:
        try:
            direction_enum = CallDirection(direction)
        except ValueError:
            pass
    
    outcome_enum = None
    if outcome:
        try:
            outcome_enum = CallOutcome(outcome)
        except ValueError:
            pass
    
    calls, total = await service.list_calls(
        contact_id=contact_id,
        account_id=account_id,
        deal_id=deal_id,
        user_id=user_id,
        direction=direction_enum,
        outcome=outcome_enum,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "calls": [
            {
                "id": c.id,
                "direction": c.direction.value,
                "status": c.status.value,
                "from_number": c.from_number,
                "to_number": c.to_number,
                "contact_id": c.contact_id,
                "user_id": c.user_id,
                "outcome": c.outcome.value if c.outcome else None,
                "duration_seconds": c.duration_seconds,
                "is_recorded": c.is_recorded,
                "started_at": c.started_at.isoformat(),
            }
            for c in calls
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_call_stats(
    user_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get call statistics."""
    service = get_service()
    return await service.get_call_stats(
        user_id=user_id,
        from_date=from_date,
        to_date=to_date
    )


@router.get("/leaderboard")
async def get_leaderboard(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=10, le=50)
):
    """Get user call leaderboard."""
    service = get_service()
    return await service.get_user_leaderboard(
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


@router.get("/hourly-activity")
async def get_hourly_activity(
    user_id: Optional[str] = None,
    days: int = Query(default=7, le=30)
):
    """Get hourly call activity."""
    service = get_service()
    activity = await service.get_hourly_activity(user_id=user_id, days=days)
    return {"activity": activity, "days": days}


@router.get("/outcomes")
async def list_outcomes():
    """List available call outcomes."""
    return {
        "outcomes": [
            {"value": o.value, "name": o.name}
            for o in CallOutcome
        ]
    }


@router.get("/{call_id}")
async def get_call(call_id: str):
    """Get a call by ID."""
    service = get_service()
    call = await service.get_call(call_id)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": call.id,
        "direction": call.direction.value,
        "status": call.status.value,
        "from_number": call.from_number,
        "to_number": call.to_number,
        "contact_id": call.contact_id,
        "account_id": call.account_id,
        "deal_id": call.deal_id,
        "user_id": call.user_id,
        "outcome": call.outcome.value if call.outcome else None,
        "disposition": {
            "outcome": call.disposition.outcome.value,
            "notes": call.disposition.notes,
            "callback_scheduled": call.disposition.callback_scheduled.isoformat() if call.disposition.callback_scheduled else None,
            "next_action": call.disposition.next_action,
        } if call.disposition else None,
        "duration_seconds": call.duration_seconds,
        "ring_duration_seconds": call.ring_duration_seconds,
        "started_at": call.started_at.isoformat(),
        "answered_at": call.answered_at.isoformat() if call.answered_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "is_recorded": call.is_recorded,
        "recording": {
            "id": call.recording.id,
            "file_url": call.recording.file_url,
            "duration_seconds": call.recording.duration_seconds,
            "transcription_status": call.recording.transcription_status,
            "sentiment": call.recording.sentiment.value if call.recording.sentiment else None,
        } if call.recording else None,
        "notes": [
            {
                "id": n.id,
                "content": n.content,
                "timestamp_seconds": n.timestamp_seconds,
                "created_at": n.created_at.isoformat(),
            }
            for n in call.notes
        ],
        "summary": call.summary,
        "tags": call.tags,
        "created_at": call.created_at.isoformat(),
    }


@router.patch("/{call_id}")
async def update_call(call_id: str, request: UpdateCallRequest):
    """Update a call."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    call = await service.update_call(call_id, updates)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {"success": True, "call_id": call_id}


@router.delete("/{call_id}")
async def delete_call(call_id: str):
    """Delete a call."""
    service = get_service()
    
    if not await service.delete_call(call_id):
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {"success": True}


# Call lifecycle
@router.post("/{call_id}/answer")
async def answer_call(call_id: str):
    """Mark call as answered."""
    service = get_service()
    
    call = await service.answer_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {"success": True, "status": call.status.value}


@router.post("/{call_id}/end")
async def end_call(call_id: str, request: EndCallRequest):
    """End a call."""
    service = get_service()
    
    outcome_enum = None
    if request.outcome:
        try:
            outcome_enum = CallOutcome(request.outcome)
        except ValueError:
            pass
    
    call = await service.end_call(
        call_id,
        outcome=outcome_enum,
        duration_seconds=request.duration_seconds
    )
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "success": True,
        "status": call.status.value,
        "duration_seconds": call.duration_seconds,
    }


@router.post("/{call_id}/disposition")
async def set_disposition(call_id: str, request: SetDispositionRequest):
    """Set call disposition."""
    service = get_service()
    
    try:
        outcome = CallOutcome(request.outcome)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid outcome")
    
    call = await service.set_disposition(
        call_id,
        outcome=outcome,
        notes=request.notes,
        callback_scheduled=request.callback_scheduled,
        next_action=request.next_action
    )
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {"success": True, "outcome": outcome.value}


# Notes
@router.post("/{call_id}/notes")
async def add_note(call_id: str, request: AddNoteRequest):
    """Add a note to a call."""
    service = get_service()
    
    note = await service.add_note(
        call_id,
        content=request.content,
        timestamp_seconds=request.timestamp_seconds
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": note.id,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
    }


@router.delete("/{call_id}/notes/{note_id}")
async def delete_note(call_id: str, note_id: str):
    """Delete a note from a call."""
    service = get_service()
    
    if not await service.delete_note(call_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"success": True}


# Recording
@router.post("/{call_id}/recording")
async def add_recording(call_id: str, request: AddRecordingRequest):
    """Add a recording to a call."""
    service = get_service()
    
    recording = await service.add_recording(
        call_id,
        file_url=request.file_url,
        file_size=request.file_size,
        duration_seconds=request.duration_seconds,
        format=request.format
    )
    
    if not recording:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": recording.id,
        "file_url": recording.file_url,
    }


@router.post("/{call_id}/transcription")
async def update_transcription(call_id: str, request: UpdateTranscriptionRequest):
    """Update call transcription."""
    service = get_service()
    
    sentiment = None
    if request.sentiment:
        try:
            sentiment = SentimentScore(request.sentiment)
        except ValueError:
            pass
    
    if not await service.update_transcription(
        call_id,
        transcription=request.transcription,
        sentiment=sentiment,
        key_phrases=request.key_phrases,
        action_items=request.action_items
    ):
        raise HTTPException(status_code=400, detail="Cannot update transcription")
    
    return {"success": True}


# Scripts
@router.get("/scripts")
async def list_scripts(active_only: bool = True):
    """List call scripts."""
    service = get_service()
    scripts = await service.list_scripts(active_only=active_only)
    
    return {
        "scripts": [
            {
                "id": s.id,
                "name": s.name,
                "use_cases": s.use_cases,
                "is_active": s.is_active,
            }
            for s in scripts
        ]
    }


@router.post("/scripts")
async def create_script(request: CreateScriptRequest):
    """Create a call script."""
    service = get_service()
    
    script = await service.create_script(
        name=request.name,
        opening=request.opening,
        questions=request.questions,
        objection_handlers=request.objection_handlers,
        closing=request.closing,
        use_cases=request.use_cases or [],
    )
    
    return {
        "id": script.id,
        "name": script.name,
    }


@router.get("/scripts/{script_id}")
async def get_script(script_id: str):
    """Get a call script."""
    service = get_service()
    script = await service.get_script(script_id)
    
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    return {
        "id": script.id,
        "name": script.name,
        "opening": script.opening,
        "questions": script.questions,
        "objection_handlers": script.objection_handlers,
        "closing": script.closing,
        "use_cases": script.use_cases,
        "is_active": script.is_active,
    }
