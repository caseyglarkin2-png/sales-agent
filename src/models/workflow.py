"""Workflow execution tracking models."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from src.db import Base


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    
    TRIGGERED = "triggered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowMode(str, Enum):
    """Workflow execution mode."""
    
    DRAFT_ONLY = "DRAFT_ONLY"
    SEND = "SEND"


class Workflow(Base):
    """Workflow execution tracking.
    
    Tracks the complete lifecycle of a workflow from trigger to completion.
    Stores state, timing, errors, and relationships to submissions and outputs.
    """
    
    __tablename__ = "workflows"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    form_submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("form_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Status and mode
    status = Column(
        SQLEnum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.TRIGGERED,
        index=True
    )
    mode = Column(
        SQLEnum(WorkflowMode),
        nullable=False,
        default=WorkflowMode.DRAFT_ONLY
    )
    
    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    
    # Audit timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    form_submission = relationship(
        "FormSubmission",
        back_populates="workflows",
        foreign_keys=[form_submission_id]
    )
    draft_emails = relationship(
        "DraftEmail",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    hubspot_tasks = relationship(
        "HubSpotTask",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    errors = relationship(
        "WorkflowError",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowError.created_at.desc()"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_workflows_status_created", "status", "created_at"),
        Index("idx_workflows_form_submission", "form_submission_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Workflow(id={self.id}, status={self.status.value}, "
            f"mode={self.mode.value}, started={self.started_at})>"
        )


class DraftEmail(Base):
    """Draft email storage and approval tracking.
    
    Stores generated email drafts with approval workflow.
    Tracks who approved, when, and if/when the email was sent.
    """
    
    __tablename__ = "draft_emails"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    form_submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("form_submissions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Gmail reference
    gmail_draft_id = Column(String(255), nullable=True, index=True)
    
    # Email content
    recipient_email = Column(String(255), nullable=False, index=True)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    
    # Approval workflow
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Send tracking
    sent_at = Column(DateTime, nullable=True, index=True)
    gmail_message_id = Column(String(255), nullable=True)
    
    # Audit timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    workflow = relationship("Workflow", back_populates="draft_emails")
    form_submission = relationship("FormSubmission", back_populates="draft_emails")
    
    __table_args__ = (
        Index("idx_draft_emails_workflow", "workflow_id"),
        Index("idx_draft_emails_approval_status", "approved_at", "sent_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DraftEmail(id={self.id}, recipient={self.recipient_email}, "
            f"approved={self.approved_at is not None}, sent={self.sent_at is not None})>"
        )


class HubSpotTask(Base):
    """HubSpot task reference tracking.
    
    Stores references to HubSpot tasks created by workflows.
    Enables audit trail and reconciliation with HubSpot.
    """
    
    __tablename__ = "hubspot_tasks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # HubSpot references
    hubspot_task_id = Column(String(255), nullable=False, unique=True, index=True)
    contact_id = Column(String(255), nullable=False, index=True)
    
    # Task details
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    hubspot_created_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="hubspot_tasks")
    
    __table_args__ = (
        Index("idx_hubspot_tasks_workflow", "workflow_id"),
        Index("idx_hubspot_tasks_contact", "contact_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<HubSpotTask(id={self.id}, hubspot_id={self.hubspot_task_id}, "
            f"contact={self.contact_id})>"
        )


class WorkflowError(Base):
    """Workflow error tracking and retry state.
    
    Stores errors encountered during workflow execution.
    Supports retry logic with exponential backoff.
    """
    
    __tablename__ = "workflow_errors"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Error details
    error_type = Column(String(255), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    traceback = Column(Text, nullable=True)
    step_name = Column(String(255), nullable=True, index=True)
    
    # Retry configuration
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="errors")
    
    __table_args__ = (
        Index("idx_workflow_errors_workflow", "workflow_id"),
        Index("idx_workflow_errors_retry", "next_retry_at", "retry_count"),
        Index("idx_workflow_errors_type_step", "error_type", "step_name"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<WorkflowError(id={self.id}, type={self.error_type}, "
            f"retries={self.retry_count}/{self.max_retries})>"
        )
