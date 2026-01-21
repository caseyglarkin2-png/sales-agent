"""
Notes and Interactions API Routes
=================================
Endpoints for managing contact notes and interactions.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import structlog

from src.notes import (
    get_notes_service,
    NoteType,
    InteractionType,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/notes", tags=["Notes & Interactions"])


class CreateNoteRequest(BaseModel):
    contact_id: str
    content: str
    note_type: str = "general"
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    tags: list[str] = []
    is_pinned: bool = False
    is_private: bool = False


class UpdateNoteRequest(BaseModel):
    content: Optional[str] = None
    note_type: Optional[str] = None
    is_pinned: Optional[bool] = None
    tags: Optional[list[str]] = None


class LogInteractionRequest(BaseModel):
    contact_id: str
    interaction_type: str
    subject: str = ""
    summary: str = ""
    outcome: str = ""
    duration_seconds: int = 0
    direction: str = "outbound"
    sentiment: str = ""
    next_steps: str = ""
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    occurred_at: Optional[datetime] = None


class LogCallRequest(BaseModel):
    contact_id: str
    duration_seconds: int
    outcome: str
    summary: str = ""
    direction: str = "outbound"
    next_steps: str = ""
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class SearchNotesRequest(BaseModel):
    query: str
    contact_id: Optional[str] = None
    limit: int = 50


# Note endpoints
@router.get("")
async def list_notes(
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    company_id: Optional[str] = None,
    note_type: Optional[str] = None,
    author_id: Optional[str] = None,
    pinned_only: bool = False,
    tags: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List notes with optional filters."""
    service = get_notes_service()
    
    type_filter = None
    if note_type:
        try:
            type_filter = NoteType(note_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid note type: {note_type}")
    
    tag_list = tags.split(",") if tags else None
    
    notes = service.list_notes(
        contact_id=contact_id,
        deal_id=deal_id,
        company_id=company_id,
        note_type=type_filter,
        author_id=author_id,
        pinned_only=pinned_only,
        tags=tag_list,
        limit=limit,
    )
    
    return {
        "notes": [n.to_dict() for n in notes],
        "total": len(notes),
    }


@router.post("")
async def create_note(request: CreateNoteRequest):
    """Create a new note."""
    service = get_notes_service()
    
    try:
        note_type = NoteType(request.note_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid note type: {request.note_type}")
    
    note = service.create_note(
        contact_id=request.contact_id,
        content=request.content,
        note_type=note_type,
        author_id=request.author_id,
        author_name=request.author_name,
        deal_id=request.deal_id,
        company_id=request.company_id,
        tags=request.tags,
        is_pinned=request.is_pinned,
        is_private=request.is_private,
    )
    
    return {
        "message": "Note created",
        "note": note.to_dict(),
    }


@router.post("/search")
async def search_notes(request: SearchNotesRequest):
    """Search notes by content."""
    service = get_notes_service()
    
    notes = service.search_notes(
        query=request.query,
        contact_id=request.contact_id,
        limit=request.limit,
    )
    
    return {
        "notes": [n.to_dict() for n in notes],
        "total": len(notes),
    }


@router.get("/types")
async def list_note_types():
    """List available note types."""
    return {
        "types": [{"value": t.value, "name": t.name} for t in NoteType]
    }


@router.get("/{note_id}")
async def get_note(note_id: str):
    """Get a note by ID."""
    service = get_notes_service()
    note = service.get_note(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"note": note.to_dict()}


@router.put("/{note_id}")
async def update_note(note_id: str, request: UpdateNoteRequest):
    """Update a note."""
    service = get_notes_service()
    
    note_type = None
    if request.note_type:
        try:
            note_type = NoteType(request.note_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid note type: {request.note_type}")
    
    note = service.update_note(
        note_id=note_id,
        content=request.content,
        note_type=note_type,
        is_pinned=request.is_pinned,
        tags=request.tags,
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {
        "message": "Note updated",
        "note": note.to_dict(),
    }


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note."""
    service = get_notes_service()
    
    if not service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"message": "Note deleted"}


# Interaction endpoints
@router.get("/interactions")
async def list_interactions(
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    company_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List interactions with filters."""
    service = get_notes_service()
    
    type_filter = None
    if interaction_type:
        try:
            type_filter = InteractionType(interaction_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid interaction type: {interaction_type}")
    
    interactions = service.list_interactions(
        contact_id=contact_id,
        deal_id=deal_id,
        company_id=company_id,
        interaction_type=type_filter,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    return {
        "interactions": [i.to_dict() for i in interactions],
        "total": len(interactions),
    }


@router.post("/interactions")
async def log_interaction(request: LogInteractionRequest):
    """Log an interaction."""
    service = get_notes_service()
    
    try:
        interaction_type = InteractionType(request.interaction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid interaction type: {request.interaction_type}")
    
    interaction = service.log_interaction(
        contact_id=request.contact_id,
        interaction_type=interaction_type,
        subject=request.subject,
        summary=request.summary,
        outcome=request.outcome,
        duration_seconds=request.duration_seconds,
        direction=request.direction,
        sentiment=request.sentiment,
        next_steps=request.next_steps,
        user_id=request.user_id,
        user_name=request.user_name,
        deal_id=request.deal_id,
        company_id=request.company_id,
        occurred_at=request.occurred_at,
    )
    
    return {
        "message": "Interaction logged",
        "interaction": interaction.to_dict(),
    }


@router.post("/interactions/call")
async def log_call(request: LogCallRequest):
    """Log a phone call."""
    service = get_notes_service()
    
    interaction = service.log_call(
        contact_id=request.contact_id,
        duration_seconds=request.duration_seconds,
        outcome=request.outcome,
        summary=request.summary,
        direction=request.direction,
        next_steps=request.next_steps,
        user_id=request.user_id,
        user_name=request.user_name,
    )
    
    return {
        "message": "Call logged",
        "interaction": interaction.to_dict(),
    }


@router.get("/interactions/types")
async def list_interaction_types():
    """List available interaction types."""
    return {
        "types": [{"value": t.value, "name": t.name} for t in InteractionType]
    }


@router.get("/interactions/{interaction_id}")
async def get_interaction(interaction_id: str):
    """Get an interaction by ID."""
    service = get_notes_service()
    interaction = service.get_interaction(interaction_id)
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return {"interaction": interaction.to_dict()}


@router.delete("/interactions/{interaction_id}")
async def delete_interaction(interaction_id: str):
    """Delete an interaction."""
    service = get_notes_service()
    
    if not service.delete_interaction(interaction_id):
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return {"message": "Interaction deleted"}


# Summary endpoints
@router.get("/contacts/{contact_id}/summary")
async def get_contact_activity_summary(
    contact_id: str,
    days: int = Query(30, ge=1, le=365),
):
    """Get activity summary for a contact."""
    service = get_notes_service()
    
    return service.get_contact_activity_summary(
        contact_id=contact_id,
        days=days,
    )
