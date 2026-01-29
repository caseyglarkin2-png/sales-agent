"""Sequence Step Executor Celery Task.

Processes due sequence steps and queues emails for sending.
Sprint 63: Sequence Automation
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.db import get_session
from src.models.sequence import (
    Sequence,
    SequenceStep,
    SequenceEnrollment,
    SequenceStatus,
    EnrollmentStatus,
    StepChannel,
)
from src.models.command_queue import CommandQueueItem, QueueItemStatus

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context for Celery."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    name="src.tasks.sequence_executor.execute_due_steps",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def execute_due_steps(self):
    """Execute all due sequence steps.
    
    Runs every 15 minutes via Celery beat.
    Finds enrollments with next_step_at <= now and processes them.
    """
    return _run_async(_execute_due_steps_async())


async def _execute_due_steps_async():
    """Async implementation of step execution."""
    now = datetime.utcnow()
    processed = 0
    errors = 0
    
    async with get_session() as db:
        # Find all active enrollments with due steps
        query = (
            select(SequenceEnrollment)
            .options(selectinload(SequenceEnrollment.sequence).selectinload(Sequence.steps))
            .where(
                and_(
                    SequenceEnrollment.status == EnrollmentStatus.ACTIVE.value,
                    SequenceEnrollment.next_step_at <= now,
                )
            )
            .limit(100)  # Process in batches
        )
        
        result = await db.execute(query)
        enrollments = result.scalars().all()
        
        logger.info(f"Found {len(enrollments)} enrollments with due steps")
        
        for enrollment in enrollments:
            try:
                await _process_enrollment_step(db, enrollment, now)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing enrollment {enrollment.id}: {e}")
                errors += 1
        
        await db.commit()
    
    logger.info(f"Sequence executor completed: {processed} processed, {errors} errors")
    return {"processed": processed, "errors": errors}


async def _process_enrollment_step(db, enrollment: SequenceEnrollment, now: datetime):
    """Process a single enrollment step."""
    sequence = enrollment.sequence
    
    if not sequence or sequence.status != SequenceStatus.ACTIVE.value:
        # Sequence was deactivated, pause enrollment
        enrollment.status = EnrollmentStatus.PAUSED.value
        enrollment.paused_at = now
        logger.info(f"Paused enrollment {enrollment.id} - sequence not active")
        return
    
    # Get current step
    current_step_num = enrollment.current_step + 1
    steps_by_num = {s.step_number: s for s in sequence.steps}
    
    if current_step_num not in steps_by_num:
        # No more steps, mark complete
        enrollment.status = EnrollmentStatus.COMPLETED.value
        enrollment.completed_at = now
        enrollment.next_step_at = None
        
        # Update sequence metrics
        sequence.active_enrollments = max(0, sequence.active_enrollments - 1)
        sequence.completed_enrollments += 1
        
        logger.info(f"Completed enrollment {enrollment.id} - no more steps")
        return
    
    step = steps_by_num[current_step_num]
    
    # Process based on channel
    if step.channel == StepChannel.EMAIL.value:
        await _queue_email_step(db, enrollment, step)
    elif step.channel == StepChannel.TASK.value:
        await _create_task_step(db, enrollment, step)
    # LinkedIn and Call steps would create tasks for manual action
    
    # Update enrollment
    enrollment.current_step = current_step_num
    
    # Record in history
    history = enrollment.step_history or []
    history.append({
        "step": current_step_num,
        "channel": step.channel,
        "executed_at": now.isoformat(),
        "status": "queued" if step.channel == StepChannel.EMAIL.value else "created",
    })
    enrollment.step_history = history
    
    # Calculate next step timing
    next_step_num = current_step_num + 1
    if next_step_num in steps_by_num:
        next_step = steps_by_num[next_step_num]
        enrollment.next_step_at = now + timedelta(
            days=next_step.delay_days,
            hours=next_step.delay_hours,
        )
    else:
        # This was the last step
        enrollment.status = EnrollmentStatus.COMPLETED.value
        enrollment.completed_at = now
        enrollment.next_step_at = None
        sequence.active_enrollments = max(0, sequence.active_enrollments - 1)
        sequence.completed_enrollments += 1
    
    logger.info(f"Processed step {current_step_num} for enrollment {enrollment.id}")


async def _queue_email_step(db, enrollment: SequenceEnrollment, step: SequenceStep):
    """Queue an email step for operator approval."""
    # Personalize templates
    context = enrollment.context or {}
    
    subject = _personalize_template(step.subject_template or "", context, enrollment)
    body = _personalize_template(step.body_template or "", context, enrollment)
    
    # Create queue item
    queue_item = CommandQueueItem(
        action_type="send_email",
        priority=40,  # Medium-low for sequences
        recipient=enrollment.contact_email,
        subject=subject,
        body=body,
        status=QueueItemStatus.PENDING.value,
        metadata={
            "sequence_id": str(enrollment.sequence_id),
            "enrollment_id": str(enrollment.id),
            "step_number": step.step_number,
            "contact_name": enrollment.contact_name,
        },
    )
    db.add(queue_item)
    
    logger.info(f"Queued email for enrollment {enrollment.id}, step {step.step_number}")


async def _create_task_step(db, enrollment: SequenceEnrollment, step: SequenceStep):
    """Create a task for manual action (call, LinkedIn, etc.)."""
    # For now, just log it - could create actual Task model
    logger.info(
        f"Task step for enrollment {enrollment.id}: "
        f"{step.task_type} - {step.task_description}"
    )


def _personalize_template(template: str, context: dict, enrollment: SequenceEnrollment) -> str:
    """Replace template placeholders with context values."""
    if not template:
        return template
    
    # Build replacement dict
    replacements = {
        "{{first_name}}": context.get("first_name", enrollment.contact_name or "there"),
        "{{last_name}}": context.get("last_name", ""),
        "{{company}}": context.get("company", context.get("company_name", "")),
        "{{title}}": context.get("title", ""),
        "{{email}}": enrollment.contact_email,
        "{{contact_name}}": enrollment.contact_name or "",
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, str(value))
    
    return result


@celery_app.task(
    name="src.tasks.sequence_executor.mark_replied",
    bind=True,
)
def mark_replied(self, contact_email: str, thread_id: Optional[str] = None):
    """Mark enrollment as replied when we detect a response.
    
    Called by reply detection webhook/polling.
    """
    return _run_async(_mark_replied_async(contact_email, thread_id))


async def _mark_replied_async(contact_email: str, thread_id: Optional[str]):
    """Mark all active enrollments for this contact as replied."""
    async with get_session() as db:
        query = (
            select(SequenceEnrollment)
            .options(selectinload(SequenceEnrollment.sequence))
            .where(
                and_(
                    SequenceEnrollment.contact_email == contact_email,
                    SequenceEnrollment.status == EnrollmentStatus.ACTIVE.value,
                )
            )
        )
        
        result = await db.execute(query)
        enrollments = result.scalars().all()
        
        count = 0
        for enrollment in enrollments:
            enrollment.status = EnrollmentStatus.REPLIED.value
            enrollment.next_step_at = None
            
            # Update sequence metrics
            if enrollment.sequence:
                enrollment.sequence.active_enrollments = max(0, enrollment.sequence.active_enrollments - 1)
                enrollment.sequence.replied_enrollments += 1
            
            count += 1
        
        await db.commit()
        
        logger.info(f"Marked {count} enrollments as replied for {contact_email}")
        return {"marked_replied": count}
