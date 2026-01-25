"""Celery task queue configuration and workflow tasks."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from celery import Celery
from celery.exceptions import Retry

from src.config import get_settings
from src.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

app = Celery(__name__)

# Configure Celery
app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_workflow_task(self, form_submission_id: str) -> dict:
    """
    Process workflow asynchronously using FormLeadOrchestrator.
    
    Args:
        form_submission_id: UUID of form_submission record
        
    Returns:
        Dict with workflow_id, status, and metadata
        
    Raises:
        Retry: If transient error encountered
    """
    from src.models.form_submission import FormSubmission
    from src.models.workflow import Workflow, WorkflowStatus, WorkflowMode
    from src.formlead_orchestrator import create_formlead_orchestrator
    from src.db import get_session
    from sqlalchemy import select
    
    logger.info(
        f"Processing workflow task",
        extra={"form_submission_id": form_submission_id, "task_id": self.request.id}
    )
    
    try:
        # Get form submission from database
        async def get_submission():
            async with get_session() as session:
                result = await session.execute(
                    select(FormSubmission).where(FormSubmission.id == UUID(form_submission_id))
                )
                return result.scalar_one_or_none()
        
        import asyncio
        submission = asyncio.run(get_submission())
        
        if not submission:
            logger.error(f"Form submission not found: {form_submission_id}")
            return {
                "status": "error",
                "error": f"Form submission {form_submission_id} not found"
            }
        
        if submission.is_processed:
            logger.warning(f"Form submission already processed: {form_submission_id}")
            return {
                "status": "skipped",
                "message": "Already processed",
                "workflow_id": None
            }
        
        # Create workflow record
        async def create_workflow():
            async with get_session() as session:
                workflow = Workflow(
                    form_submission_id=UUID(form_submission_id),
                    status=WorkflowStatus.PROCESSING,
                    mode=WorkflowMode.DRAFT_ONLY,
                    started_at=datetime.utcnow()
                )
                session.add(workflow)
                await session.commit()
                await session.refresh(workflow)
                return workflow
        
        workflow = asyncio.run(create_workflow())
        
        logger.info(
            f"Workflow created",
            extra={"workflow_id": str(workflow.id), "submission_id": form_submission_id}
        )
        
        # Execute orchestrator
        try:
            orchestrator = create_formlead_orchestrator()
            
            # Convert submission to form_data format
            form_data = {
                "portalId": submission.portal_id,
                "formId": submission.form_id,
                "formSubmissionId": submission.form_submission_id,
                "email": submission.prospect_email,
                "firstName": submission.prospect_full_name.split()[0] if submission.prospect_full_name else "",
                "lastName": " ".join(submission.prospect_full_name.split()[1:]) if submission.prospect_full_name and len(submission.prospect_full_name.split()) > 1 else "",
                "company": submission.prospect_company or "",
                "fieldValues": [{"name": k, "value": v} for k, v in (submission.raw_fields or {}).items()]
            }
            
            result = asyncio.run(orchestrator.process_formlead(form_data))
            
            # Update workflow status
            async def update_workflow_success():
                async with get_session() as session:
                    workflow_update = await session.get(Workflow, workflow.id)
                    workflow_update.status = WorkflowStatus.COMPLETED
                    workflow_update.completed_at = datetime.utcnow()
                    workflow_update.final_status = result.get("final_status", "completed")
                    await session.commit()
                    
                    # Mark submission as processed
                    submission_update = await session.get(FormSubmission, UUID(form_submission_id))
                    submission_update.is_processed = True
                    submission_update.is_pending = False
                    submission_update.processed_at = datetime.utcnow()
                    await session.commit()
            
            asyncio.run(update_workflow_success())
            
            logger.info(
                f"Workflow completed successfully",
                extra={
                    "workflow_id": str(workflow.id),
                    "final_status": result.get("final_status")
                }
            )
            
            return {
                "status": "completed",
                "workflow_id": str(workflow.id),
                "final_status": result.get("final_status"),
                "draft_id": result.get("draft_id")
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            
            # Update workflow status to failed
            async def update_workflow_failed():
                async with get_session() as session:
                    from src.models.workflow import WorkflowError
                    
                    workflow_update = await session.get(Workflow, workflow.id)
                    workflow_update.status = WorkflowStatus.FAILED
                    workflow_update.completed_at = datetime.utcnow()
                    workflow_update.final_status = "failed"
                    await session.commit()
                    
                    # Store error
                    error = WorkflowError(
                        workflow_id=workflow.id,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        occurred_at=datetime.utcnow()
                    )
                    session.add(error)
                    await session.commit()
                    
                    # Mark submission as failed
                    submission_update = await session.get(FormSubmission, UUID(form_submission_id))
                    submission_update.is_failed = True
                    submission_update.is_pending = False
                    await session.commit()
            
            asyncio.run(update_workflow_failed())
            
            # Retry on transient errors
            if "rate limit" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"Transient error detected, retrying: {e}")
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            
            raise e
            
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise


def queue_workflow_processing(form_submission_id: str) -> str:
    """
    Queue workflow processing task.
    
    Args:
        form_submission_id: UUID of form_submission record
        
    Returns:
        Celery task ID
    """
    task = process_workflow_task.delay(form_submission_id)
    logger.info(
        f"Workflow queued",
        extra={"form_submission_id": form_submission_id, "task_id": task.id}
    )
    return task.id

