"""SQLAlchemy models for audit logging."""
from datetime import datetime
from typing import Literal

from sqlalchemy import Column, DateTime, Index, String, Text, JSON, TypeDecorator
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


class DraftAuditLog(Base):
    """Immutable audit log for draft operations."""

    __tablename__ = "draft_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True)
    action = Column(String(255), nullable=False)
    actor = Column(String(255), nullable=False)
    draft_id = Column(String(255), nullable=False, index=True)
    contact_id = Column(String(255), nullable=False, index=True)
    company_id = Column(String(255), nullable=False, index=True)
    mode = Column(String(50), nullable=False)  # DRAFT_ONLY | SEND_ALLOWED
    status = Column(String(50), nullable=False)  # CREATED | SENT | BLOCKED | REJECTED
    reason = Column(Text, nullable=True)
    metadata = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_draft_audit_log_draft_id", "draft_id"),
        Index("ix_draft_audit_log_contact_id", "contact_id"),
        Index("ix_draft_audit_log_company_id", "company_id"),
        Index("ix_draft_audit_log_created_at", "created_at"),
    )
