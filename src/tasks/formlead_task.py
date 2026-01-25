"""Celery task for processing form lead submissions asynchronously."""
import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_session
from src.formlead_orchestrator import create_formlead_orchestrator
from src.logger import get_logger
from src.models.workflow import Workflow, WorkflowStatus, WorkflowMode

# Import Celery app from celery_app.py (the actual Celery configuration file)
from src.celery_app import celery_app as app

logger = get_logger(__name__)
settings = get_settings()


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    task_acks_late=True,
    time_limit=25 * 60,  # 25 minutes hard limit
)
def process_formlead_async(
    self, form_data: Dict[str, Any], workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process form lead submission asynchronously.

    This task:
    1. Validates form data
    2. Executes the prospecting orchestrator
    3. Persists results to database
    4. Handles retries on transient failures

    Args:
        form_data: Form submission data from webhook
        workflow_id: Optional workflow ID for tracking (creates new if not provided)

    Returns:
        Dict with workflow_id, status, and metadata

    Raises:
        Retry: On transient errors (network, DB timeout)
    """
    if not workflow_id:
        workflow_id = f"form-lead-{uuid4()}"

    logger.info(
        "Starting form lead processing task",
        task_id=self.request.id,
        workflow_id=workflow_id,
        email=form_data.get("email"),
    )

    try:
        # Run async orchestrator in sync context
        result = asyncio.run(
            _process_formlead_workflow(form_data=form_data, workflow_id=workflow_id)
        )

        logger.info(
            "Form lead processing complete",
            task_id=self.request.id,
            workflow_id=workflow_id,
            status=result.get("status"),
        )

        return result

    except Exception as exc:
        logger.exception(
            "Error processing form lead",
            task_id=self.request.id,
            workflow_id=workflow_id,
            exc_info=True,
        )

        # Retry with exponential backoff
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            retry_delay = 60 * (2 ** retry_count)  # 60s, 120s, 240s
            logger.warning(
                f"Retrying form lead processing (attempt {retry_count + 1}/{self.max_retries})",
                task_id=self.request.id,
                workflow_id=workflow_id,
                retry_delay=retry_delay,
            )
            raise self.retry(exc=exc, countdown=retry_delay)

        # Max retries exceeded - store in DLQ
        logger.error(
            "Form lead processing failed after max retries",
            task_id=self.request.id,
            workflow_id=workflow_id,
        )

        # Store failed task in database
        asyncio.run(
            _store_failed_task(
                task_id=self.request.id,
                workflow_id=workflow_id,
                form_data=form_data,
                error=str(exc),
                retry_count=retry_count,
            )
        )

        return {
            "status": "failed",
            "workflow_id": workflow_id,
            "error": str(exc),
            "task_id": self.request.id,
            "message": "Form lead processing failed after retries - stored in DLQ",
        }


async def _process_formlead_workflow(
    form_data: Dict[str, Any], workflow_id: str
) -> Dict[str, Any]:
    """
    Execute form lead workflow asynchronously with database session management.

    Args:
        form_data: Form submission data
        workflow_id: Workflow tracking ID

    Returns:
        Workflow result dict

    Raises:
        Exception: Any error during workflow execution
    """
    async with get_session() as session:
        try:
            # Create workflow record in database
            workflow = Workflow(
                id=workflow_id,
                status=WorkflowStatus.PROCESSING,
                mode=WorkflowMode.DRAFT_ONLY,
            )
            session.add(workflow)
            await session.commit()

            logger.info(f"Created workflow record: {workflow_id}")

            # Execute orchestrator
            orchestrator = create_formlead_orchestrator()
            result = await orchestrator.process_formlead(form_data)

            # Update workflow status to success
            workflow.status = WorkflowStatus.COMPLETED
            workflow.result = result
            await session.commit()

            logger.info(
                "Workflow completed successfully",
                workflow_id=workflow_id,
                final_status=result.get("final_status"),
            )

            return {
                "status": "success",
                "workflow_id": workflow_id,
                "final_status": result.get("final_status"),
                "draft_id": result.get("draft_id"),
                "metadata": result.get("metadata", {}),
            }

        except Exception as exc:
            logger.exception(
                "Workflow execution failed",
                workflow_id=workflow_id,
                exc_info=True,
            )

            # Update workflow status to error
            try:
                workflow.status = WorkflowStatus.FAILED
                workflow.error = str(exc)
                await session.commit()
            except Exception as update_exc:
                logger.warning(
                    "Failed to update workflow status to FAILED",
                    workflow_id=workflow_id,
                    exc_info=True,
                )

            raise


async def _store_failed_task(
    task_id: str,
    workflow_id: str,
    form_data: Dict[str, Any],
    error: str,
    retry_count: int,
) -> None:
    """
    Store failed task in dead letter queue for manual review.

    Args:
        task_id: Celery task ID
        workflow_id: Workflow tracking ID
        form_data: Original form data
        error: Error message
        retry_count: Number of retries attempted
    """
    from src.models.task import FailedTask

    async with get_session() as session:
        try:
            failed_task = FailedTask(
                task_id=task_id,
                workflow_id=workflow_id,
                task_type="formlead",
                payload=form_data,
                error=error,
                retry_count=retry_count,
                status="failed",
            )
            session.add(failed_task)
            await session.commit()

            logger.info(
                "Stored failed task in DLQ",
                task_id=task_id,
                workflow_id=workflow_id,
            )
        except Exception as exc:
            logger.exception(
                "Failed to store task in DLQ",
                task_id=task_id,
                workflow_id=workflow_id,
                exc_info=True,
            )
