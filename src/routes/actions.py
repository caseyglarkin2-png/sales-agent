"""API routes for action execution in CaseyOS.

Provides endpoints for:
- Executing actions from the Command Queue
- Dry-run previews
- Rollback operations
- Execution status
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.actions.contracts import ActionType, ActionStatus
from src.actions.executor import get_executor, _executed_actions
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)
router = APIRouter(prefix="/api/actions", tags=["actions"])


# ============ Request/Response Models ============

class ExecuteActionRequest(BaseModel):
    """Request to execute an action."""
    queue_item_id: str
    action_type: str  # Will be validated against ActionType enum
    context: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
    operator: str = "casey"


class ExecuteActionResponse(BaseModel):
    """Response from action execution."""
    success: bool
    status: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    rollback_token: Optional[str] = None
    executed_at: datetime
    dry_run: bool = False


class RollbackActionRequest(BaseModel):
    """Request to rollback an action."""
    rollback_token: str
    operator: str
    reason: str


class RollbackActionResponse(BaseModel):
    """Response from rollback operation."""
    success: bool
    message: str
    original_action: Optional[Dict[str, Any]] = None
    rolled_back_at: datetime


class ExecutionHistoryItem(BaseModel):
    """Item in execution history."""
    idempotency_key: str
    status: str
    message: str
    executed_at: datetime
    execution_time_ms: float
    dry_run: bool


# ============ API Endpoints ============

@router.post("/execute", response_model=ExecuteActionResponse)
async def execute_action(request: ExecuteActionRequest):
    """
    Execute an action from the Command Queue.
    
    This is the primary endpoint for taking action on Today's Moves.
    
    **Safety Features:**
    - Kill switch: Actions blocked if emergency stop is active
    - Rate limiting: Prevents abuse of external APIs
    - Dry-run mode: Preview what would happen without executing
    - Idempotency: Prevents duplicate execution
    - Audit trail: All actions logged
    
    **Example:**
    ```bash
    curl -X POST /api/actions/execute \\
      -H "Content-Type: application/json" \\
      -d '{
        "queue_item_id": "abc123",
        "action_type": "send_email",
        "context": {"recipient": "john@acme.com", "subject": "Follow up"},
        "dry_run": true,
        "operator": "casey"
      }'
    ```
    """
    try:
        # Validate action type
        try:
            action_type = ActionType(request.action_type)
        except ValueError:
            valid_types = [t.value for t in ActionType]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action_type. Valid types: {valid_types}"
            )
        
        # Get executor and execute
        executor = get_executor()
        
        from src.actions.contracts import ActionRequest
        action_request = ActionRequest(
            queue_item_id=request.queue_item_id,
            action_type=action_type,
            context=request.context,
            dry_run=request.dry_run,
            operator=request.operator
        )
        
        result = await executor.execute(action_request)
        
        return ExecuteActionResponse(
            success=result.success,
            status=result.status.value,
            message=result.message,
            data=result.data,
            execution_time_ms=result.execution_time_ms,
            rollback_token=result.rollback_token,
            executed_at=result.executed_at,
            dry_run=result.dry_run
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Action execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution failed: {str(e)}"
        )


@router.post("/execute/{queue_item_id}", response_model=ExecuteActionResponse)
async def execute_queue_item(
    queue_item_id: str,
    action_type: str = Query(..., description="Type of action to execute"),
    dry_run: bool = Query(False, description="If true, preview without executing"),
    operator: str = Query("casey", description="Who is executing this action")
):
    """
    Quick execute endpoint for a specific queue item.
    
    Simpler than the full execute endpoint - useful for one-click execution
    from the UI.
    
    **Example:**
    ```bash
    curl -X POST "/api/actions/execute/abc123?action_type=follow_up&dry_run=true"
    ```
    """
    request = ExecuteActionRequest(
        queue_item_id=queue_item_id,
        action_type=action_type,
        dry_run=dry_run,
        operator=operator
    )
    return await execute_action(request)


@router.post("/rollback", response_model=RollbackActionResponse)
async def rollback_action(request: RollbackActionRequest):
    """
    Rollback a previously executed action.
    
    Uses the rollback_token returned from the original execute call.
    Not all actions support rollback.
    
    **Example:**
    ```bash
    curl -X POST /api/actions/rollback \\
      -H "Content-Type: application/json" \\
      -d '{
        "rollback_token": "abc123-token",
        "operator": "casey",
        "reason": "Sent to wrong recipient"
      }'
    ```
    """
    try:
        executor = get_executor()
        
        from src.actions.contracts import RollbackRequest
        rollback_request = RollbackRequest(
            rollback_token=request.rollback_token,
            operator=request.operator,
            reason=request.reason
        )
        
        result = await executor.rollback(rollback_request)
        
        return RollbackActionResponse(
            success=result.success,
            message=result.message,
            original_action=result.original_action,
            rolled_back_at=result.rolled_back_at
        )
        
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.get("/types")
async def list_action_types():
    """
    List all available action types.
    
    Returns the action types that can be executed.
    """
    return {
        "action_types": [
            {"value": t.value, "name": t.name}
            for t in ActionType
        ]
    }


@router.get("/history", response_model=List[ExecutionHistoryItem])
async def get_execution_history(
    limit: int = Query(50, ge=1, le=200, description="Max items to return")
):
    """
    Get recent action execution history.
    
    Returns the most recent executed actions (from in-memory store).
    
    Note: In production, this should query the database/audit log.
    """
    history = []
    for key, result in list(_executed_actions.items())[-limit:]:
        history.append(ExecutionHistoryItem(
            idempotency_key=key,
            status=result.status.value,
            message=result.message,
            executed_at=result.executed_at,
            execution_time_ms=result.execution_time_ms,
            dry_run=result.dry_run
        ))
    
    # Sort by most recent first
    history.sort(key=lambda x: x.executed_at, reverse=True)
    return history


@router.get("/status")
async def get_executor_status():
    """
    Get current status of the action executor.
    
    Returns:
    - Whether actions are enabled (kill switch status)
    - Rate limit status
    - Recent execution stats
    """
    executor = get_executor()
    
    # Count recent executions by status
    status_counts = {}
    for result in _executed_actions.values():
        status_value = result.status.value
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
    
    return {
        "actions_enabled": executor._is_actions_enabled(),
        "kill_switch_active": not executor._is_actions_enabled(),
        "total_executions": len(_executed_actions),
        "executions_by_status": status_counts,
        "rate_limiter_active": True,
        "supported_action_types": [t.value for t in ActionType]
    }


@router.delete("/history/clear")
async def clear_execution_history():
    """
    Clear the in-memory execution history.
    
    ⚠️ Admin only - clears idempotency cache.
    This allows previously executed actions to be re-executed.
    """
    global _executed_actions
    count = len(_executed_actions)
    _executed_actions.clear()
    
    await log_event("execution_history_cleared", properties={"count": count})
    
    return {
        "success": True,
        "message": f"Cleared {count} execution records",
        "cleared_at": datetime.utcnow().isoformat()
    }
