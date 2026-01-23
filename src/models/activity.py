"""SQLAlchemy models for agent tasks and notes."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.db import Base


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class AgentTask(Base):
    """Agent task (CRM activity) model."""

    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hubspot_task_id = Column(String(255), nullable=True, unique=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_contacts.id"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True)
    title = Column(String(512), nullable=False)
    body = Column(Text, nullable=True)
    type = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentNote(Base):
    """Agent note (CRM activity) model."""

    __tablename__ = "agent_notes"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hubspot_note_id = Column(String(255), nullable=True, unique=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_contacts.id"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True)
    body = Column(Text, nullable=False)
    context_json = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
