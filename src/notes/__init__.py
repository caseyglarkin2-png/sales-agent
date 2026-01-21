"""
Notes/Interactions Module
=========================
Contact notes, call logs, and interaction tracking.
"""

from src.notes.notes_service import (
    NotesService,
    Note,
    NoteType,
    Interaction,
    InteractionType,
    get_notes_service,
)

__all__ = [
    "NotesService",
    "Note",
    "NoteType",
    "Interaction",
    "InteractionType",
    "get_notes_service",
]
