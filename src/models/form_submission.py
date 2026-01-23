"""Form submission storage models."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.db import Base


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class FormSubmission(Base):
    """HubSpot form submission storage.
    
    Stores raw form submissions from HubSpot webhooks.
    Maintains idempotency and provides audit trail for all submissions.
    """
    
    __tablename__ = "form_submissions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # HubSpot identifiers
    portal_id = Column(Integer, nullable=False, index=True)
    form_id = Column(String(255), nullable=False, index=True)
    form_submission_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Prospect information (extracted from form fields)
    prospect_email = Column(String(255), nullable=False, index=True)
    prospect_first_name = Column(String(255), nullable=True)
    prospect_last_name = Column(String(255), nullable=True)
    prospect_company = Column(String(255), nullable=True, index=True)
    prospect_phone = Column(String(100), nullable=True)
    prospect_title = Column(String(255), nullable=True)
    
    # Raw webhook payload (for debugging and audit)
    raw_payload = Column(JSONType, nullable=True)
    
    # HubSpot entity references (resolved after submission)
    hubspot_contact_id = Column(String(255), nullable=True, index=True)
    hubspot_company_id = Column(String(255), nullable=True, index=True)
    
    # Processing state
    processed = Column(Integer, default=0, nullable=False)  # 0=pending, 1=processed, 2=failed
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflows = relationship(
        "Workflow",
        back_populates="form_submission",
        cascade="all, delete-orphan",
        order_by="Workflow.created_at.desc()"
    )
    draft_emails = relationship(
        "DraftEmail",
        back_populates="form_submission",
        cascade="all, delete-orphan"
    )
    
    # Unique constraint for idempotency
    __table_args__ = (
        UniqueConstraint(
            "portal_id",
            "form_id",
            "form_submission_id",
            name="uq_form_submission"
        ),
        Index("idx_form_submissions_email", "prospect_email"),
        Index("idx_form_submissions_received", "received_at"),
        Index("idx_form_submissions_portal_form", "portal_id", "form_id"),
        Index("idx_form_submissions_hubspot_contact", "hubspot_contact_id"),
        Index("idx_form_submissions_processing_state", "processed", "received_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FormSubmission(id={self.id}, email={self.prospect_email}, "
            f"form={self.form_id}, received={self.received_at})>"
        )
    
    @property
    def prospect_full_name(self) -> Optional[str]:
        """Get prospect's full name."""
        if self.prospect_first_name and self.prospect_last_name:
            return f"{self.prospect_first_name} {self.prospect_last_name}"
        return self.prospect_first_name or self.prospect_last_name
    
    @property
    def is_processed(self) -> bool:
        """Check if submission has been processed."""
        return self.processed == 1
    
    @property
    def is_failed(self) -> bool:
        """Check if processing failed."""
        return self.processed == 2
    
    @property
    def is_pending(self) -> bool:
        """Check if submission is pending processing."""
        return self.processed == 0
