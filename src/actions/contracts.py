"""Action contracts and data structures for CaseyOS execution engine.

Defines the request/response contracts for action execution with
full type safety and validation.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Supported action types for execution."""
    # Email actions
    SEND_EMAIL = "send_email"
    CREATE_DRAFT = "create_draft"
    
    # Meeting actions
    BOOK_MEETING = "book_meeting"
    PREP_MEETING = "prep_meeting"
    
    # Task actions
    CREATE_TASK = "create_task"
    COMPLETE_TASK = "complete_task"
    
    # Follow-up actions
    FOLLOW_UP = "follow_up"
    CHECK_IN = "check_in"
    
    # Deal actions
    REVIEW_DEAL = "review_deal"
    SEND_PROPOSAL = "send_proposal"
    UPDATE_DEAL_STAGE = "update_deal_stage"
    
    # Other
    CUSTOM = "custom"


class ActionStatus(str, Enum):
    """Status of action execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"  # Kill switch active


class ActionRequest(BaseModel):
    """Request to execute an action from the Command Queue.
    
    Attributes:
        queue_item_id: ID of the CommandQueueItem to execute
        action_type: Type of action to perform
        context: Action-specific context (recipient, subject, etc.)
        dry_run: If True, simulate without actually executing
        operator: Who initiated the action
        idempotency_key: Optional key to prevent duplicate execution
    """
    queue_item_id: str
    action_type: ActionType
    context: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
    operator: str = "system"
    idempotency_key: Optional[str] = None
    
    def generate_idempotency_key(self) -> str:
        """Generate idempotency key if not provided."""
        if self.idempotency_key:
            return self.idempotency_key
        # Use queue_item_id + action_type as default key
        return f"{self.queue_item_id}:{self.action_type.value}"


class ActionResult(BaseModel):
    """Result of action execution.
    
    Attributes:
        success: Whether the action succeeded
        status: Detailed status of execution
        message: Human-readable result message
        data: Action-specific result data
        execution_time_ms: How long execution took
        rollback_token: Token to undo this action (if applicable)
    """
    success: bool
    status: ActionStatus
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    rollback_token: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None
    dry_run: bool = False
    
    @classmethod
    def dry_run_result(cls, action_type: ActionType, context: Dict[str, Any]) -> "ActionResult":
        """Create a dry-run result showing what would happen."""
        return cls(
            success=True,
            status=ActionStatus.DRY_RUN,
            message=f"DRY RUN: Would execute {action_type.value}",
            data={
                "would_execute": action_type.value,
                "context": context,
                "preview": f"Action '{action_type.value}' with context: {context}"
            },
            dry_run=True
        )
    
    @classmethod
    def blocked_result(cls, reason: str) -> "ActionResult":
        """Create a blocked result (kill switch active)."""
        return cls(
            success=False,
            status=ActionStatus.BLOCKED,
            message=f"Action blocked: {reason}",
            data={"blocked_reason": reason}
        )
    
    @classmethod
    def rate_limited_result(cls, limit_info: str) -> "ActionResult":
        """Create a rate-limited result."""
        return cls(
            success=False,
            status=ActionStatus.RATE_LIMITED,
            message=f"Rate limit exceeded: {limit_info}",
            data={"rate_limit_info": limit_info}
        )
    
    @classmethod
    def failed_result(cls, error: str, execution_time_ms: float = 0) -> "ActionResult":
        """Create a failure result."""
        return cls(
            success=False,
            status=ActionStatus.FAILED,
            message=f"Action failed: {error}",
            data={"error": error},
            execution_time_ms=execution_time_ms
        )
    
    @classmethod
    def success_result(
        cls, 
        message: str, 
        data: Dict[str, Any] = None,
        execution_time_ms: float = 0,
        rollback_token: Optional[str] = None
    ) -> "ActionResult":
        """Create a success result."""
        return cls(
            success=True,
            status=ActionStatus.SUCCESS,
            message=message,
            data=data or {},
            execution_time_ms=execution_time_ms,
            rollback_token=rollback_token
        )


class RollbackRequest(BaseModel):
    """Request to rollback a previously executed action."""
    rollback_token: str
    operator: str
    reason: str


class RollbackResult(BaseModel):
    """Result of rollback operation."""
    success: bool
    message: str
    original_action: Optional[Dict[str, Any]] = None
    rolled_back_at: datetime = Field(default_factory=datetime.utcnow)
