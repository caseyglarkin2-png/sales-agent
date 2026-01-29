"""Sequence API routes.

Email sequence management with database persistence.
Sprint 63: Sequence Automation
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import get_db
from src.auth.decorators import get_current_user
from src.models.user import User
from src.models.sequence import (
    Sequence,
    SequenceStep,
    SequenceEnrollment,
    SequenceStatus,
    EnrollmentStatus,
    StepChannel,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sequences", tags=["Sequences"])


# --- Request/Response Models ---

class StepCreate(BaseModel):
    """Create sequence step."""
    step_number: int
    channel: str = "email"
    delay_days: int = 0
    delay_hours: int = 0
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    task_type: Optional[str] = None
    task_description: Optional[str] = None


class SequenceCreate(BaseModel):
    """Create sequence request."""
    name: str
    description: Optional[str] = None
    target_persona: Optional[str] = None
    steps: List[StepCreate] = Field(default_factory=list)


class SequenceUpdate(BaseModel):
    """Update sequence request."""
    name: Optional[str] = None
    description: Optional[str] = None
    target_persona: Optional[str] = None
    status: Optional[str] = None


class EnrollmentCreate(BaseModel):
    """Enroll contact in sequence."""
    contact_email: str
    contact_name: Optional[str] = None
    context: Optional[dict] = None  # Personalization context


class BulkEnrollRequest(BaseModel):
    """Bulk enroll contacts."""
    contacts: List[EnrollmentCreate]


# --- Routes ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sequence(
    payload: SequenceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new sequence with steps."""
    sequence = Sequence(
        name=payload.name,
        description=payload.description,
        target_persona=payload.target_persona,
        owner_id=user.id,
        status=SequenceStatus.DRAFT.value,
    )
    db.add(sequence)
    await db.flush()
    
    # Add steps
    for step_data in payload.steps:
        step = SequenceStep(
            sequence_id=sequence.id,
            step_number=step_data.step_number,
            channel=step_data.channel,
            delay_days=step_data.delay_days,
            delay_hours=step_data.delay_hours,
            subject_template=step_data.subject_template,
            body_template=step_data.body_template,
            task_type=step_data.task_type,
            task_description=step_data.task_description,
        )
        db.add(step)
    
    await db.commit()
    await db.refresh(sequence)
    
    logger.info(f"Created sequence: {sequence.name} ({sequence.id})")
    
    return sequence.to_dict()


@router.get("")
async def list_sequences(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List sequences."""
    query = (
        select(Sequence)
        .options(selectinload(Sequence.steps))
        .where(Sequence.owner_id == user.id)
    )
    
    if status:
        query = query.where(Sequence.status == status)
    
    query = query.order_by(Sequence.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    sequences = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Sequence.id)).where(Sequence.owner_id == user.id)
    if status:
        count_query = count_query.where(Sequence.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "sequences": [
            {
                **s.to_dict(),
                "steps": [st.to_dict() for st in s.steps],
            }
            for s in sequences
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get sequence with steps and enrollments."""
    query = (
        select(Sequence)
        .options(
            selectinload(Sequence.steps),
            selectinload(Sequence.enrollments),
        )
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    seq_dict = sequence.to_dict()
    seq_dict["steps"] = [s.to_dict() for s in sequence.steps]
    seq_dict["enrollments"] = [e.to_dict() for e in sequence.enrollments[:50]]  # Limit
    
    return seq_dict


@router.patch("/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    payload: SequenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Update sequence."""
    query = (
        select(Sequence)
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if payload.name is not None:
        sequence.name = payload.name
    if payload.description is not None:
        sequence.description = payload.description
    if payload.target_persona is not None:
        sequence.target_persona = payload.target_persona
    if payload.status is not None:
        sequence.status = payload.status
    
    await db.commit()
    await db.refresh(sequence)
    
    return sequence.to_dict()


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete sequence."""
    query = (
        select(Sequence)
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    await db.delete(sequence)
    await db.commit()


@router.post("/{sequence_id}/steps")
async def add_step(
    sequence_id: str,
    payload: StepCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Add step to sequence."""
    query = (
        select(Sequence)
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    step = SequenceStep(
        sequence_id=sequence.id,
        step_number=payload.step_number,
        channel=payload.channel,
        delay_days=payload.delay_days,
        delay_hours=payload.delay_hours,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
        task_type=payload.task_type,
        task_description=payload.task_description,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    
    return step.to_dict()


@router.post("/{sequence_id}/activate")
async def activate_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Activate sequence."""
    query = (
        select(Sequence)
        .options(selectinload(Sequence.steps))
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if not sequence.steps:
        raise HTTPException(status_code=400, detail="Sequence has no steps")
    
    sequence.status = SequenceStatus.ACTIVE.value
    await db.commit()
    
    return {"status": sequence.status}


@router.post("/{sequence_id}/pause")
async def pause_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Pause sequence."""
    query = (
        select(Sequence)
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence.status = SequenceStatus.PAUSED.value
    await db.commit()
    
    return {"status": sequence.status}


@router.post("/{sequence_id}/enroll")
async def enroll_contact(
    sequence_id: str,
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Enroll a contact in a sequence."""
    query = (
        select(Sequence)
        .options(selectinload(Sequence.steps))
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if sequence.status != SequenceStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Sequence is not active")
    
    # Check if already enrolled
    existing_query = (
        select(SequenceEnrollment)
        .where(SequenceEnrollment.sequence_id == uuid.UUID(sequence_id))
        .where(SequenceEnrollment.contact_email == payload.contact_email)
        .where(SequenceEnrollment.status == EnrollmentStatus.ACTIVE.value)
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Contact already enrolled in this sequence")
    
    # Calculate first step timing
    first_step = min(sequence.steps, key=lambda s: s.step_number) if sequence.steps else None
    if first_step:
        next_step_at = datetime.utcnow() + timedelta(
            days=first_step.delay_days,
            hours=first_step.delay_hours,
        )
    else:
        next_step_at = datetime.utcnow()
    
    enrollment = SequenceEnrollment(
        sequence_id=sequence.id,
        contact_email=payload.contact_email,
        contact_name=payload.contact_name,
        context=payload.context,
        current_step=0,
        status=EnrollmentStatus.ACTIVE.value,
        next_step_at=next_step_at,
        step_history=[],
    )
    db.add(enrollment)
    
    # Update sequence metrics
    sequence.total_enrollments += 1
    sequence.active_enrollments += 1
    
    await db.commit()
    await db.refresh(enrollment)
    
    logger.info(f"Enrolled {payload.contact_email} in sequence {sequence.name}")
    
    return enrollment.to_dict()


@router.post("/{sequence_id}/enroll/bulk")
async def bulk_enroll(
    sequence_id: str,
    payload: BulkEnrollRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Bulk enroll contacts in a sequence."""
    query = (
        select(Sequence)
        .options(selectinload(Sequence.steps))
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    sequence = result.scalar_one_or_none()
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if sequence.status != SequenceStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Sequence is not active")
    
    # Get existing enrollments
    existing_query = (
        select(SequenceEnrollment.contact_email)
        .where(SequenceEnrollment.sequence_id == uuid.UUID(sequence_id))
        .where(SequenceEnrollment.status == EnrollmentStatus.ACTIVE.value)
    )
    existing_result = await db.execute(existing_query)
    existing_emails = {r[0] for r in existing_result.all()}
    
    # Calculate first step timing
    first_step = min(sequence.steps, key=lambda s: s.step_number) if sequence.steps else None
    base_next_step = datetime.utcnow()
    if first_step:
        base_next_step += timedelta(days=first_step.delay_days, hours=first_step.delay_hours)
    
    enrolled = 0
    skipped = 0
    
    for contact in payload.contacts:
        if contact.contact_email in existing_emails:
            skipped += 1
            continue
        
        enrollment = SequenceEnrollment(
            sequence_id=sequence.id,
            contact_email=contact.contact_email,
            contact_name=contact.contact_name,
            context=contact.context,
            current_step=0,
            status=EnrollmentStatus.ACTIVE.value,
            next_step_at=base_next_step,
            step_history=[],
        )
        db.add(enrollment)
        enrolled += 1
        existing_emails.add(contact.contact_email)
    
    # Update sequence metrics
    sequence.total_enrollments += enrolled
    sequence.active_enrollments += enrolled
    
    await db.commit()
    
    logger.info(f"Bulk enrolled {enrolled} contacts in sequence {sequence.name}, skipped {skipped}")
    
    return {
        "enrolled": enrolled,
        "skipped": skipped,
        "total_enrollments": sequence.total_enrollments,
    }


@router.get("/{sequence_id}/enrollments")
async def list_enrollments(
    sequence_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List enrollments for a sequence."""
    # Verify ownership
    seq_query = (
        select(Sequence)
        .where(Sequence.id == uuid.UUID(sequence_id))
        .where(Sequence.owner_id == user.id)
    )
    seq_result = await db.execute(seq_query)
    if not seq_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    query = (
        select(SequenceEnrollment)
        .where(SequenceEnrollment.sequence_id == uuid.UUID(sequence_id))
    )
    
    if status:
        query = query.where(SequenceEnrollment.status == status)
    
    query = query.order_by(SequenceEnrollment.enrolled_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    enrollments = result.scalars().all()
    
    # Get total count
    count_query = (
        select(func.count(SequenceEnrollment.id))
        .where(SequenceEnrollment.sequence_id == uuid.UUID(sequence_id))
    )
    if status:
        count_query = count_query.where(SequenceEnrollment.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "enrollments": [e.to_dict() for e in enrollments],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Pause an enrollment."""
    query = (
        select(SequenceEnrollment)
        .join(Sequence)
        .where(SequenceEnrollment.id == uuid.UUID(enrollment_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment.status = EnrollmentStatus.PAUSED.value
    enrollment.paused_at = datetime.utcnow()
    
    # Update sequence metrics
    sequence_query = select(Sequence).where(Sequence.id == enrollment.sequence_id)
    seq_result = await db.execute(sequence_query)
    sequence = seq_result.scalar_one()
    sequence.active_enrollments = max(0, sequence.active_enrollments - 1)
    
    await db.commit()
    
    return enrollment.to_dict()


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Resume a paused enrollment."""
    query = (
        select(SequenceEnrollment)
        .join(Sequence)
        .where(SequenceEnrollment.id == uuid.UUID(enrollment_id))
        .where(Sequence.owner_id == user.id)
    )
    result = await db.execute(query)
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    if enrollment.status != EnrollmentStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Enrollment is not paused")
    
    enrollment.status = EnrollmentStatus.ACTIVE.value
    enrollment.paused_at = None
    enrollment.next_step_at = datetime.utcnow()  # Resume immediately
    
    # Update sequence metrics
    sequence_query = select(Sequence).where(Sequence.id == enrollment.sequence_id)
    seq_result = await db.execute(sequence_query)
    sequence = seq_result.scalar_one()
    sequence.active_enrollments += 1
    
    await db.commit()
    
    return enrollment.to_dict()
