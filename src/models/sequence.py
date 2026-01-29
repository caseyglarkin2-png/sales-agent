"""SQLAlchemy models for email sequences with database persistence."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, SafeJSON


class SequenceStatus(str, PyEnum):
    """Sequence status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class EnrollmentStatus(str, PyEnum):
    """Enrollment status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class StepChannel(str, PyEnum):
    """Step channel type."""
    EMAIL = "email"
    LINKEDIN = "linkedin"
    CALL = "call"
    TASK = "task"


class Sequence(Base):
    """A multi-step outreach sequence."""

    __tablename__ = "sequences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=SequenceStatus.DRAFT.value)
    
    # Configuration
    target_persona: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Ownership
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Metrics (denormalized)
    total_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    active_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    completed_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    replied_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    steps: Mapped[List["SequenceStep"]] = relationship(
        "SequenceStep", back_populates="sequence", cascade="all, delete-orphan", order_by="SequenceStep.step_number"
    )
    enrollments: Mapped[List["SequenceEnrollment"]] = relationship(
        "SequenceEnrollment", back_populates="sequence", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sequences_status", "status"),
        Index("ix_sequences_owner", "owner_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "target_persona": self.target_persona,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "total_enrollments": self.total_enrollments,
            "active_enrollments": self.active_enrollments,
            "completed_enrollments": self.completed_enrollments,
            "replied_enrollments": self.replied_enrollments,
            "step_count": len(self.steps) if self.steps else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SequenceStep(Base):
    """A single step in a sequence."""

    __tablename__ = "sequence_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False
    )
    
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default=StepChannel.EMAIL.value)
    
    # Timing
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    
    # Email content templates (with placeholders)
    subject_template: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For non-email steps
    task_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    task_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sequence: Mapped["Sequence"] = relationship("Sequence", back_populates="steps")

    __table_args__ = (
        Index("ix_sequence_steps_sequence", "sequence_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "sequence_id": str(self.sequence_id),
            "step_number": self.step_number,
            "channel": self.channel,
            "delay_days": self.delay_days,
            "delay_hours": self.delay_hours,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "task_type": self.task_type,
            "task_description": self.task_description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SequenceEnrollment(Base):
    """A contact enrolled in a sequence."""

    __tablename__ = "sequence_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False
    )
    
    # Contact info
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubspot_contacts.id"), nullable=True
    )
    
    # Context for personalization
    context: Mapped[Optional[dict]] = mapped_column(SafeJSON, nullable=True)
    # e.g., {"company": "Acme", "title": "VP Sales", "trigger": "Downloaded whitepaper"}
    
    # Progress tracking
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default=EnrollmentStatus.ACTIVE.value)
    
    # Timing
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_step_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # History
    step_history: Mapped[Optional[dict]] = mapped_column(SafeJSON, nullable=True)
    # [{"step": 1, "sent_at": "...", "status": "sent"}, ...]
    
    # Relationships
    sequence: Mapped["Sequence"] = relationship("Sequence", back_populates="enrollments")

    __table_args__ = (
        Index("ix_sequence_enrollments_sequence", "sequence_id"),
        Index("ix_sequence_enrollments_status", "status"),
        Index("ix_sequence_enrollments_next_step", "next_step_at"),
        Index("ix_sequence_enrollments_email", "contact_email"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "sequence_id": str(self.sequence_id),
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "contact_id": str(self.contact_id) if self.contact_id else None,
            "context": self.context,
            "current_step": self.current_step,
            "status": self.status,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
            "next_step_at": self.next_step_at.isoformat() if self.next_step_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "step_history": self.step_history,
        }
