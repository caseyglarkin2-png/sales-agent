"""Async task and dead letter queue management routes."""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.logger import get_logger
from src.models.task import FailedTask
from src.celery_app import celery_app
from celery.result import AsyncResult

logger = get_logger(__name__)
router = APIRouter(prefix="/api/async", tags=["Async Tasks"])


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of a Celery task.

    Provides real-time status of async task execution including progress,
    result, or error information.

    Args:
        task_id: Celery task ID (same as workflow_id)

    Returns:
        Dict with task status, result, and metadata

    Example:
        GET /api/async/tasks/form-lead-123e4567-e89b/status
        {
            "task_id": "form-lead-123e4567-e89b",
            "status": "SUCCESS",
            "result": {"workflow_id": "...", "draft_id": "..."},
            "created_at": "2026-01-23T10:00:00Z"
        }
    """
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }

    # Add status-specific fields
    if result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.info)
        response["traceback"] = result.traceback
    elif result.status == "PENDING":
        response["message"] = "Task is waiting to be processed"
    elif result.status == "STARTED":
        response["message"] = "Task is currently executing"
    elif result.status == "RETRY":
        response["message"] = "Task is retrying after failure"

    logger.info(f"Retrieved task status: {task_id} -> {result.status}")

    return response


@router.get("/failed-tasks")
async def list_failed_tasks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (failed, manual_retry, resolved)"),
) -> Dict[str, Any]:
    """
    List failed tasks in the dead letter queue.

    Returns paginated list of failed tasks with error details and
    resolution status.

    Args:
        limit: Number of results to return (1-500, default 50)
        offset: Number of results to skip (default 0)
        status_filter: Filter by status (failed, manual_retry, resolved)

    Returns:
        Dict with total count and list of failed tasks

    Example:
        GET /api/async/failed-tasks?limit=10&status=failed
    """
    async with get_db() as session:
        query = select(FailedTask)

        if status_filter:
            query = query.where(FailedTask.status == status_filter)

        # Get total count
        count_query = select(func.count(FailedTask.id))
        if status_filter:
            count_query = count_query.where(FailedTask.status == status_filter)
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(FailedTask.created_at)).limit(limit).offset(offset)
        result = await session.execute(query)
        failed_tasks = result.scalars().all()

        logger.info(
            f"Retrieved {len(failed_tasks)} failed tasks (total: {total_count})",
            limit=limit,
            offset=offset,
            status=status_filter,
        )

        return {
            "total_count": total_count,
            "returned_count": len(failed_tasks),
            "limit": limit,
            "offset": offset,
            "tasks": [
                {
                    "id": task.id,
                    "task_id": task.task_id,
                    "workflow_id": task.workflow_id,
                    "task_type": task.task_type,
                    "error": task.error,
                    "retry_count": task.retry_count,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
                }
                for task in failed_tasks
            ],
        }


@router.post("/failed-tasks/{failed_task_id}/retry")
async def retry_failed_task(failed_task_id: str) -> Dict[str, Any]:
    """
    Retry a failed task by re-queueing it to Celery.

    Marks the task as "manual_retry" and queues it again for processing.
    Useful for recovering from transient failures.

    Args:
        failed_task_id: ID of the failed task to retry

    Returns:
        Dict with new task ID and status

    Raises:
        HTTPException: If task not found or retry fails

    Example:
        POST /api/async/failed-tasks/abc123/retry
        -> Returns new task_id for monitoring
    """
    async with get_db() as session:
        # Get the failed task
        result = await session.execute(
            select(FailedTask).where(FailedTask.id == failed_task_id)
        )
        failed_task = result.scalar_one_or_none()

        if not failed_task:
            logger.warning(f"Failed task not found: {failed_task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed task {failed_task_id} not found",
            )

        try:
            # Re-queue based on task type
            if failed_task.task_type == "formlead":
                from src.tasks.formlead_task import process_formlead_async

                new_task = process_formlead_async.apply_async(
                    args=(failed_task.payload,),
                    kwargs={"workflow_id": failed_task.workflow_id},
                )
            else:
                logger.error(f"Unknown task type: {failed_task.task_type}")
                raise ValueError(f"Unknown task type: {failed_task.task_type}")

            # Update failed task status
            failed_task.status = "manual_retry"
            await session.commit()

            logger.info(
                f"Retried failed task {failed_task_id}",
                new_task_id=new_task.id,
                task_type=failed_task.task_type,
            )

            return {
                "status": "retry_queued",
                "failed_task_id": failed_task_id,
                "new_task_id": new_task.id,
                "message": f"Task re-queued for processing",
                "status_url": f"/api/async/tasks/{new_task.id}/status",
            }

        except Exception as e:
            logger.exception(
                f"Error retrying failed task {failed_task_id}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retry task: {str(e)}",
            )


@router.post("/failed-tasks/{failed_task_id}/resolve")
async def resolve_failed_task(
    failed_task_id: str,
    notes: str = Query(..., description="Resolution notes"),
    resolved_by: str = Query(..., description="Person resolving the issue"),
) -> Dict[str, Any]:
    """
    Mark a failed task as resolved without retrying.

    Use when the issue is addressed manually or the form should be skipped.

    Args:
        failed_task_id: ID of the failed task
        notes: Resolution notes
        resolved_by: Name/email of person resolving

    Returns:
        Dict with resolution status

    Raises:
        HTTPException: If task not found

    Example:
        POST /api/async/failed-tasks/abc123/resolve?notes=Form+invalid&resolved_by=operator
    """
    async with get_db() as session:
        result = await session.execute(
            select(FailedTask).where(FailedTask.id == failed_task_id)
        )
        failed_task = result.scalar_one_or_none()

        if not failed_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed task {failed_task_id} not found",
            )

        failed_task.status = "resolved"
        failed_task.resolution_notes = notes
        failed_task.resolved_by = resolved_by
        failed_task.resolved_at = datetime.utcnow()

        await session.commit()

        logger.info(
            f"Resolved failed task {failed_task_id}",
            resolved_by=resolved_by,
            notes=notes,
        )

        return {
            "status": "resolved",
            "failed_task_id": failed_task_id,
            "message": "Task marked as resolved",
        }
