"""
Workflow state machine implementation.

Provides finite state machine (FSM) for workflow lifecycle management with:
- Atomic state transitions
- Idempotent operations (safe to retry)
- State persistence in PostgreSQL
- Event-driven architecture
- Recovery from partial failures
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.workflow import Workflow, WorkflowStatus
from src.logger import get_logger

logger = get_logger(__name__)


class WorkflowEvent(str, Enum):
    """Events that trigger state transitions."""
    START = "start"
    DRAFT_CREATED = "draft_created"
    HUBSPOT_WRITTEN = "hubspot_written"
    EMAIL_SENT = "email_sent"
    ERROR = "error"
    RETRY = "retry"
    ABORT = "abort"


class WorkflowStateMachine:
    """
    Finite state machine for workflow lifecycle.
    
    State diagram:
    
    TRIGGERED → PROCESSING → DRAFT_CREATED → HUBSPOT_WRITTEN → COMPLETED
                    ↓             ↓               ↓                ↓
                  FAILED ← ← ← ← ← ← ← ← ← ← ← ← 
    
    All transitions are atomic and logged.
    """
    
    # Valid state transitions
    TRANSITIONS = {
        WorkflowStatus.TRIGGERED: {
            WorkflowEvent.START: WorkflowStatus.PROCESSING,
            WorkflowEvent.ERROR: WorkflowStatus.FAILED,
        },
        WorkflowStatus.PROCESSING: {
            WorkflowEvent.DRAFT_CREATED: WorkflowStatus.COMPLETED,  # DRAFT_ONLY mode
            WorkflowEvent.EMAIL_SENT: WorkflowStatus.COMPLETED,     # SEND mode
            WorkflowEvent.ERROR: WorkflowStatus.FAILED,
        },
        WorkflowStatus.FAILED: {
            WorkflowEvent.RETRY: WorkflowStatus.PROCESSING,
            WorkflowEvent.ABORT: WorkflowStatus.FAILED,
        },
        WorkflowStatus.COMPLETED: {
            # Terminal state - no transitions out
        }
    }
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize state machine.
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db = db_session
    
    async def transition(
        self,
        workflow_id: UUID,
        event: WorkflowEvent,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition workflow to new state.
        
        Args:
            workflow_id: Workflow ID
            event: Event triggering transition
            metadata: Optional metadata (error message, timing, etc.)
        
        Returns:
            True if transition succeeded, False if invalid
        """
        # Fetch current workflow
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False
        
        current_state = workflow.status
        
        # Check if transition is valid
        valid_transitions = self.TRANSITIONS.get(current_state, {})
        new_state = valid_transitions.get(event)
        
        if not new_state:
            logger.warning(
                f"Invalid transition: {current_state} + {event} (workflow {workflow_id})"
            )
            return False
        
        # Perform transition
        logger.info(
            f"Workflow {workflow_id}: {current_state} → {new_state} (event: {event})"
        )
        
        workflow.status = new_state
        workflow.updated_at = datetime.utcnow()
        
        # Handle metadata updates
        if metadata:
            if "error_message" in metadata:
                workflow.error_message = metadata["error_message"]
                workflow.error_count += 1
            
            if event == WorkflowEvent.DRAFT_CREATED or event == WorkflowEvent.EMAIL_SENT:
                workflow.completed_at = datetime.utcnow()
            
            if event == WorkflowEvent.RETRY:
                # Clear error state on retry
                workflow.error_message = None
        
        await self.db.commit()
        await self.db.refresh(workflow)
        
        return True
    
    async def get_state(self, workflow_id: UUID) -> Optional[WorkflowStatus]:
        """Get current workflow state."""
        result = await self.db.execute(
            select(Workflow.status).where(Workflow.id == workflow_id)
        )
        status = result.scalar_one_or_none()
        return status
    
    async def can_transition(
        self,
        workflow_id: UUID,
        event: WorkflowEvent
    ) -> bool:
        """Check if transition is valid without executing it."""
        current_state = await self.get_state(workflow_id)
        if not current_state:
            return False
        
        valid_transitions = self.TRANSITIONS.get(current_state, {})
        return event in valid_transitions
    
    async def get_failed_workflows(
        self,
        max_retries: int = 3,
        limit: int = 100
    ) -> List[Workflow]:
        """
        Get workflows in FAILED state eligible for retry.
        
        Args:
            max_retries: Maximum retry count before giving up
            limit: Maximum number of workflows to return
        
        Returns:
            List of failed workflows
        """
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.status == WorkflowStatus.FAILED.value)
            .where(Workflow.error_count < max_retries)
            .order_by(Workflow.created_at.desc())
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def mark_workflow_failed(
        self,
        workflow_id: UUID,
        error_message: str
    ) -> bool:
        """Convenience method to mark workflow as failed."""
        return await self.transition(
            workflow_id,
            WorkflowEvent.ERROR,
            metadata={"error_message": error_message}
        )
    
    async def mark_workflow_completed(
        self,
        workflow_id: UUID,
        sent: bool = False
    ) -> bool:
        """Convenience method to mark workflow as completed."""
        event = WorkflowEvent.EMAIL_SENT if sent else WorkflowEvent.DRAFT_CREATED
        return await self.transition(workflow_id, event)
    
    async def retry_workflow(self, workflow_id: UUID) -> bool:
        """Retry a failed workflow."""
        return await self.transition(workflow_id, WorkflowEvent.RETRY)


class WorkflowRecovery:
    """
    Recovery utilities for stuck/failed workflows.
    
    Provides tools to:
    - Detect stuck workflows (processing > 10min)
    - Auto-retry failed workflows
    - Manual intervention for edge cases
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize recovery utilities."""
        self.db = db_session
        self.fsm = WorkflowStateMachine(db_session)
    
    async def find_stuck_workflows(
        self,
        timeout_minutes: int = 10
    ) -> List[Workflow]:
        """
        Find workflows stuck in PROCESSING state.
        
        Args:
            timeout_minutes: Consider stuck if processing > this many minutes
        
        Returns:
            List of stuck workflows
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.status == WorkflowStatus.PROCESSING.value)
            .where(Workflow.started_at < cutoff_time)
        )
        
        return list(result.scalars().all())
    
    async def auto_recover_stuck_workflows(
        self,
        timeout_minutes: int = 10,
        max_to_recover: int = 50
    ) -> int:
        """
        Automatically recover stuck workflows.
        
        Marks them as FAILED so they can be retried.
        
        Returns:
            Number of workflows recovered
        """
        stuck = await self.find_stuck_workflows(timeout_minutes)
        stuck = stuck[:max_to_recover]
        
        recovered = 0
        for workflow in stuck:
            success = await self.fsm.mark_workflow_failed(
                workflow.id,
                f"Workflow stuck in PROCESSING for >{timeout_minutes}min"
            )
            if success:
                recovered += 1
                logger.info(f"Recovered stuck workflow {workflow.id}")
        
        return recovered
    
    async def retry_failed_workflows(
        self,
        max_retries: int = 3,
        max_to_retry: int = 50
    ) -> int:
        """
        Retry failed workflows that are eligible.
        
        Returns:
            Number of workflows retried
        """
        failed = await self.fsm.get_failed_workflows(
            max_retries=max_retries,
            limit=max_to_retry
        )
        
        retried = 0
        for workflow in failed:
            success = await self.fsm.retry_workflow(workflow.id)
            if success:
                retried += 1
                logger.info(f"Retrying workflow {workflow.id} (attempt {workflow.error_count + 1})")
        
        return retried
    
    async def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        from sqlalchemy import func
        
        # Count by status
        status_counts = await self.db.execute(
            select(
                Workflow.status,
                func.count(Workflow.id).label('count')
            ).group_by(Workflow.status)
        )
        
        status_map = {row[0]: row[1] for row in status_counts}
        
        # Find stuck
        stuck = await self.find_stuck_workflows()
        
        # Find eligible for retry
        eligible_for_retry = await self.fsm.get_failed_workflows(max_retries=3, limit=1000)
        
        return {
            "by_status": status_map,
            "stuck_workflows": len(stuck),
            "eligible_for_retry": len(eligible_for_retry),
            "timestamp": datetime.utcnow().isoformat()
        }
