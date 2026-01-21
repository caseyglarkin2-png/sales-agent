"""
Notes and Interactions Service
==============================
Manages contact notes, call logs, and interaction tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class NoteType(str, Enum):
    """Types of notes."""
    GENERAL = "general"
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    LINKEDIN = "linkedin"
    OBJECTION = "objection"
    REQUIREMENT = "requirement"
    DECISION = "decision"
    INTERNAL = "internal"


class InteractionType(str, Enum):
    """Types of interactions."""
    CALL_OUTBOUND = "call_outbound"
    CALL_INBOUND = "call_inbound"
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    MEETING = "meeting"
    LINKEDIN_MESSAGE = "linkedin_message"
    LINKEDIN_CONNECTION = "linkedin_connection"
    SMS = "sms"
    CHAT = "chat"


@dataclass
class Note:
    """A contact note."""
    id: str
    contact_id: str
    content: str
    note_type: NoteType = NoteType.GENERAL
    is_pinned: bool = False
    is_private: bool = False
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "content": self.content,
            "note_type": self.note_type.value,
            "is_pinned": self.is_pinned,
            "is_private": self.is_private,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "deal_id": self.deal_id,
            "company_id": self.company_id,
            "tags": self.tags,
            "mentions": self.mentions,
            "attachments": self.attachments,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Interaction:
    """A tracked interaction with a contact."""
    id: str
    contact_id: str
    interaction_type: InteractionType
    subject: str = ""
    summary: str = ""
    outcome: str = ""  # positive, negative, neutral
    duration_seconds: int = 0
    direction: str = "outbound"  # inbound, outbound
    channel: str = ""
    sentiment: str = ""  # positive, negative, neutral
    next_steps: str = ""
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "interaction_type": self.interaction_type.value,
            "subject": self.subject,
            "summary": self.summary,
            "outcome": self.outcome,
            "duration_seconds": self.duration_seconds,
            "duration_minutes": self.duration_seconds // 60 if self.duration_seconds else 0,
            "direction": self.direction,
            "channel": self.channel,
            "sentiment": self.sentiment,
            "next_steps": self.next_steps,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "deal_id": self.deal_id,
            "company_id": self.company_id,
            "occurred_at": self.occurred_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class NotesService:
    """
    Manages notes and interactions for contacts.
    """
    
    def __init__(self):
        self.notes: dict[str, Note] = {}
        self.interactions: dict[str, Interaction] = {}
    
    # Note methods
    def create_note(
        self,
        contact_id: str,
        content: str,
        note_type: NoteType = NoteType.GENERAL,
        author_id: str = None,
        author_name: str = None,
        deal_id: str = None,
        company_id: str = None,
        tags: list[str] = None,
        is_pinned: bool = False,
        is_private: bool = False,
    ) -> Note:
        """Create a new note."""
        # Extract mentions from content
        mentions = self._extract_mentions(content)
        
        note = Note(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            content=content,
            note_type=note_type,
            is_pinned=is_pinned,
            is_private=is_private,
            author_id=author_id,
            author_name=author_name,
            deal_id=deal_id,
            company_id=company_id,
            tags=tags or [],
            mentions=mentions,
        )
        
        self.notes[note.id] = note
        
        logger.info(
            "note_created",
            note_id=note.id,
            contact_id=contact_id,
            type=note_type.value,
        )
        
        return note
    
    def get_note(self, note_id: str) -> Optional[Note]:
        """Get a note by ID."""
        return self.notes.get(note_id)
    
    def list_notes(
        self,
        contact_id: str = None,
        deal_id: str = None,
        company_id: str = None,
        note_type: NoteType = None,
        author_id: str = None,
        pinned_only: bool = False,
        tags: list[str] = None,
        limit: int = 100,
    ) -> list[Note]:
        """List notes with filters."""
        notes = list(self.notes.values())
        
        if contact_id:
            notes = [n for n in notes if n.contact_id == contact_id]
        
        if deal_id:
            notes = [n for n in notes if n.deal_id == deal_id]
        
        if company_id:
            notes = [n for n in notes if n.company_id == company_id]
        
        if note_type:
            notes = [n for n in notes if n.note_type == note_type]
        
        if author_id:
            notes = [n for n in notes if n.author_id == author_id]
        
        if pinned_only:
            notes = [n for n in notes if n.is_pinned]
        
        if tags:
            notes = [n for n in notes if any(tag in n.tags for tag in tags)]
        
        # Sort: pinned first, then by date
        notes = sorted(
            notes,
            key=lambda n: (not n.is_pinned, n.created_at),
            reverse=True,
        )
        
        return notes[:limit]
    
    def update_note(
        self,
        note_id: str,
        content: str = None,
        note_type: NoteType = None,
        is_pinned: bool = None,
        tags: list[str] = None,
    ) -> Optional[Note]:
        """Update a note."""
        note = self.notes.get(note_id)
        if not note:
            return None
        
        if content is not None:
            note.content = content
            note.mentions = self._extract_mentions(content)
        
        if note_type is not None:
            note.note_type = note_type
        
        if is_pinned is not None:
            note.is_pinned = is_pinned
        
        if tags is not None:
            note.tags = tags
        
        note.updated_at = datetime.utcnow()
        return note
    
    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        if note_id in self.notes:
            del self.notes[note_id]
            return True
        return False
    
    def _extract_mentions(self, content: str) -> list[str]:
        """Extract @mentions from content."""
        import re
        return re.findall(r'@(\w+)', content)
    
    # Interaction methods
    def log_interaction(
        self,
        contact_id: str,
        interaction_type: InteractionType,
        subject: str = "",
        summary: str = "",
        outcome: str = "",
        duration_seconds: int = 0,
        direction: str = "outbound",
        sentiment: str = "",
        next_steps: str = "",
        user_id: str = None,
        user_name: str = None,
        deal_id: str = None,
        company_id: str = None,
        occurred_at: datetime = None,
        metadata: dict = None,
    ) -> Interaction:
        """Log an interaction."""
        interaction = Interaction(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            interaction_type=interaction_type,
            subject=subject,
            summary=summary,
            outcome=outcome,
            duration_seconds=duration_seconds,
            direction=direction,
            sentiment=sentiment,
            next_steps=next_steps,
            user_id=user_id,
            user_name=user_name,
            deal_id=deal_id,
            company_id=company_id,
            occurred_at=occurred_at or datetime.utcnow(),
            metadata=metadata or {},
        )
        
        self.interactions[interaction.id] = interaction
        
        logger.info(
            "interaction_logged",
            interaction_id=interaction.id,
            contact_id=contact_id,
            type=interaction_type.value,
        )
        
        return interaction
    
    def log_call(
        self,
        contact_id: str,
        duration_seconds: int,
        outcome: str,
        summary: str = "",
        direction: str = "outbound",
        next_steps: str = "",
        user_id: str = None,
        user_name: str = None,
    ) -> Interaction:
        """Log a phone call."""
        interaction_type = (
            InteractionType.CALL_OUTBOUND if direction == "outbound"
            else InteractionType.CALL_INBOUND
        )
        
        return self.log_interaction(
            contact_id=contact_id,
            interaction_type=interaction_type,
            summary=summary,
            outcome=outcome,
            duration_seconds=duration_seconds,
            direction=direction,
            next_steps=next_steps,
            user_id=user_id,
            user_name=user_name,
        )
    
    def get_interaction(self, interaction_id: str) -> Optional[Interaction]:
        """Get an interaction by ID."""
        return self.interactions.get(interaction_id)
    
    def list_interactions(
        self,
        contact_id: str = None,
        deal_id: str = None,
        company_id: str = None,
        interaction_type: InteractionType = None,
        user_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
    ) -> list[Interaction]:
        """List interactions with filters."""
        interactions = list(self.interactions.values())
        
        if contact_id:
            interactions = [i for i in interactions if i.contact_id == contact_id]
        
        if deal_id:
            interactions = [i for i in interactions if i.deal_id == deal_id]
        
        if company_id:
            interactions = [i for i in interactions if i.company_id == company_id]
        
        if interaction_type:
            interactions = [i for i in interactions if i.interaction_type == interaction_type]
        
        if user_id:
            interactions = [i for i in interactions if i.user_id == user_id]
        
        if start_date:
            interactions = [i for i in interactions if i.occurred_at >= start_date]
        
        if end_date:
            interactions = [i for i in interactions if i.occurred_at <= end_date]
        
        return sorted(interactions, key=lambda i: i.occurred_at, reverse=True)[:limit]
    
    def delete_interaction(self, interaction_id: str) -> bool:
        """Delete an interaction."""
        if interaction_id in self.interactions:
            del self.interactions[interaction_id]
            return True
        return False
    
    def get_contact_activity_summary(
        self,
        contact_id: str,
        days: int = 30,
    ) -> dict:
        """Get activity summary for a contact."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        notes = [n for n in self.notes.values() if n.contact_id == contact_id and n.created_at >= cutoff]
        interactions = [i for i in self.interactions.values() if i.contact_id == contact_id and i.occurred_at >= cutoff]
        
        # Count by type
        interaction_counts = {}
        for interaction in interactions:
            t = interaction.interaction_type.value
            interaction_counts[t] = interaction_counts.get(t, 0) + 1
        
        note_counts = {}
        for note in notes:
            t = note.note_type.value
            note_counts[t] = note_counts.get(t, 0) + 1
        
        # Calculate total talk time
        total_call_time = sum(
            i.duration_seconds for i in interactions
            if i.interaction_type in [InteractionType.CALL_OUTBOUND, InteractionType.CALL_INBOUND]
        )
        
        return {
            "contact_id": contact_id,
            "period_days": days,
            "total_notes": len(notes),
            "total_interactions": len(interactions),
            "notes_by_type": note_counts,
            "interactions_by_type": interaction_counts,
            "total_call_time_minutes": total_call_time // 60,
            "last_interaction": interactions[0].occurred_at.isoformat() if interactions else None,
            "last_note": notes[0].created_at.isoformat() if notes else None,
        }
    
    def search_notes(
        self,
        query: str,
        contact_id: str = None,
        limit: int = 50,
    ) -> list[Note]:
        """Search notes by content."""
        query_lower = query.lower()
        
        results = []
        for note in self.notes.values():
            if contact_id and note.contact_id != contact_id:
                continue
            
            if query_lower in note.content.lower():
                results.append(note)
        
        return sorted(results, key=lambda n: n.created_at, reverse=True)[:limit]


# Singleton instance
_service: Optional[NotesService] = None


def get_notes_service() -> NotesService:
    """Get the notes service singleton."""
    global _service
    if _service is None:
        _service = NotesService()
    return _service
