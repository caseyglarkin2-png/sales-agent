"""SQLAlchemy models for audit logging."""
from datetime import datetime
from typing import Literal

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.db import Base


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
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_draft_audit_log_draft_id", "draft_id"),
        Index("ix_draft_audit_log_contact_id", "contact_id"),
        Index("ix_draft_audit_log_company_id", "company_id"),
        Index("ix_draft_audit_log_created_at", "created_at"),
    )
