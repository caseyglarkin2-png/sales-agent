"""Agent Execution tracking model for CaseyOS.

Tracks all agent executions with full audit trail including:
- Input context and output results
- Execution status and duration
- Error messages for failed executions
- Timestamps for debugging and analytics

Sprint 42.1: Agent Execution Infrastructure
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import String, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base, SafeJSON


class ExecutionStatus(str, Enum):
    """Status of an agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class AgentExecution(Base):
    """Track every agent execution with full audit trail.
    
    Used for:
    - Monitoring agent health and performance
    - Debugging failed executions
    - Analytics on agent usage patterns
    - Manual retry of failed executions
    """
    
    __tablename__ = "agent_executions"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Agent identification
    agent_name: Mapped[str] = mapped_column(
        String(128), 
        nullable=False,
        index=True
    )
    domain: Mapped[str] = mapped_column(
        String(64), 
        nullable=False,
        default="unknown"
    )
    
    # Execution status
    status: Mapped[str] = mapped_column(
        String(32), 
        nullable=False,
        default=ExecutionStatus.PENDING.value
    )
    
    # Input/Output (SafeJSON for Postgres/SQLite compatibility)
    input_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        SafeJSON, 
        default=dict
    )
    output_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        SafeJSON, 
        default=dict
    )
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )
    error_traceback: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )
    
    # Performance metrics
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    
    # Trigger source (manual, scheduled, signal)
    trigger_source: Mapped[str] = mapped_column(
        String(64),
        default="manual",
        nullable=False
    )
    
    # Optional user who triggered (null for automated)
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True
    )
    
    # Celery task ID for async tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True
    )
    
    # Table indexes for common queries
    __table_args__ = (
        Index('ix_agent_execution_created_at', 'created_at'),
        Index('ix_agent_execution_status', 'status'),
        Index('ix_agent_execution_agent_status', 'agent_name', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<AgentExecution {self.agent_name} status={self.status}>"
    
    def mark_running(self) -> None:
        """Mark execution as running."""
        self.status = ExecutionStatus.RUNNING.value
        self.started_at = datetime.utcnow()
    
    def mark_success(self, result: Dict[str, Any]) -> None:
        """Mark execution as successful with result."""
        self.status = ExecutionStatus.SUCCESS.value
        self.output_result = result
        self.completed_at = datetime.utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
    
    def mark_failed(self, error: str, traceback: Optional[str] = None) -> None:
        """Mark execution as failed with error."""
        self.status = ExecutionStatus.FAILED.value
        self.error_message = error
        self.error_traceback = traceback
        self.completed_at = datetime.utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
    
    def mark_timed_out(self) -> None:
        """Mark execution as timed out."""
        self.status = ExecutionStatus.TIMED_OUT.value
        self.error_message = "Execution exceeded time limit (300s)"
        self.completed_at = datetime.utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
    
    @property
    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.status in [
            ExecutionStatus.SUCCESS.value,
            ExecutionStatus.FAILED.value,
            ExecutionStatus.TIMED_OUT.value,
            ExecutionStatus.CANCELLED.value,
        ]
