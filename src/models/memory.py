"""
Persistent Memory Models for Jarvis.

These models enable Jarvis to remember conversations across sessions,
creating a "Henry-style" always-on assistant experience.

Tables:
- JarvisSession: User sessions with active context
- ConversationMemory: Individual messages with embeddings for semantic search
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.db import Base, SafeJSON


class JarvisSession(Base):
    """
    Persistent session for Jarvis conversations.
    
    Each user can have multiple named sessions (e.g., "Morning Standup",
    "Deal Review", "Quick Question"). Sessions persist across server restarts.
    """
    __tablename__ = "jarvis_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    session_name = Column(String(255), default="default")
    
    # Active context - the current "working memory"
    active_context = Column(SafeJSON, default=dict)
    
    # User preferences for this session
    preferences = Column(SafeJSON, default=dict)
    # Example: {"voice_enabled": True, "notification_level": "urgent_only"}
    
    # Last topic for resume capability
    last_topic = Column(String(500), nullable=True)
    
    # Current focus (what Jarvis is helping with)
    current_focus = Column(String(255), nullable=True)
    # Examples: "prospecting", "deal_review", "email_drafts", "meeting_prep"
    
    # Session state
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)
    
    # Timestamps
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("ConversationMemory", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_jarvis_sessions_user_active", "user_id", "is_active"),
        Index("ix_jarvis_sessions_last_active", "last_active"),
    )
    
    def __repr__(self):
        return f"<JarvisSession(id={self.id}, user={self.user_id}, name={self.session_name})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "session_name": self.session_name,
            "active_context": self.active_context or {},
            "preferences": self.preferences or {},
            "last_topic": self.last_topic,
            "current_focus": self.current_focus,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConversationMemory(Base):
    """
    Individual conversation messages with embeddings for semantic search.
    
    This enables Jarvis to recall relevant past context when answering
    new questions - the core of the "Henry" experience.
    """
    __tablename__ = "conversation_memory"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("jarvis_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Message content
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    
    # Embedding for semantic search (stored as JSONB array for now, can upgrade to pgvector)
    # Format: list of floats from OpenAI embeddings
    embedding = Column(SafeJSON, nullable=True)
    
    # Metadata about the message (renamed from 'metadata' which is reserved)
    message_metadata = Column("metadata", SafeJSON, default=dict)
    # Examples: {"agent_used": "prospecting", "action_taken": "draft_created", "entities": ["Acme Corp"]}
    
    # For threading multi-turn conversations
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("conversation_memory.id"), nullable=True)
    
    # Token count for context window management
    token_count = Column(Integer, nullable=True)
    
    # Importance score (0-1) for context pruning
    importance = Column(Integer, default=50)  # 0-100, higher = more important to remember
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("JarvisSession", back_populates="messages")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_conversation_memory_session_created", "session_id", "created_at"),
        Index("ix_conversation_memory_role", "role"),
        Index("ix_conversation_memory_importance", "importance"),
    )
    
    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ConversationMemory(id={self.id}, role={self.role}, content='{preview}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "metadata": self.message_metadata or {},
            "importance": self.importance,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MemorySummary(Base):
    """
    Compressed summaries of old conversations.
    
    To prevent memory bloat, old messages are summarized into
    compact representations that preserve key facts.
    """
    __tablename__ = "memory_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("jarvis_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Summary content (LLM-generated)
    summary = Column(Text, nullable=False)
    
    # Key facts extracted (for quick lookup)
    key_facts = Column(SafeJSON, default=list)
    # Example: ["User prefers morning meetings", "Working on Acme Corp deal", "Renewal due March 15"]
    
    # Time range covered
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # How many messages were summarized
    message_count = Column(Integer, default=0)
    
    # Embedding for semantic search
    embedding = Column(SafeJSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_memory_summaries_session", "session_id"),
        Index("ix_memory_summaries_date_range", "session_id", "start_date", "end_date"),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "summary": self.summary,
            "key_facts": self.key_facts or [],
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
