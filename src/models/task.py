"""Failed task model for dead letter queue tracking."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class FailedTask(Base):
    """Model for tracking failed Celery tasks in dead letter queue."""

    __tablename__ = "failed_tasks"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Task tracking
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., 'formlead', 'email_send'

    # Task data
    payload: Mapped[Dict[str, Any]] = mapped_column(
        "payload",
        comment="Original task payload that failed",
    )
    error: Mapped[str] = mapped_column(String(2000), nullable=False)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default="failed"
    )  # failed, manual_retry, resolved
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        String(2000), comment="Notes from manual resolution"
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(255), comment="User who resolved the issue"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    def __repr__(self) -> str:
        return f"<FailedTask id={self.id} task_type={self.task_type} status={self.status}>"
