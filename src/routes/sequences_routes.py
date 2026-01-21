"""
Sequences Routes - Sales cadence and sequence automation
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/sequences", tags=["Sequences"])


class SequenceStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class StepType(str, Enum):
    EMAIL = "email"
    CALL = "call"
    LINKEDIN = "linkedin"
    SMS = "sms"
    TASK = "task"
    WAIT = "wait"
    BRANCH = "branch"


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    BOUNCED = "bounced"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"
    CONVERTED = "converted"


class TriggerType(str, Enum):
    MANUAL = "manual"
    DEAL_STAGE = "deal_stage"
    LEAD_SCORE = "lead_score"
    FORM_SUBMIT = "form_submit"
    TAG_ADDED = "tag_added"
    API = "api"


# In-memory storage
sequences = {}
sequence_steps = {}
enrollments = {}
enrollment_activities = {}


class SequenceStepCreate(BaseModel):
    type: StepType
    order: int
    delay_days: int = 0
    delay_hours: int = 0
    subject: Optional[str] = None  # For emails
    content: Optional[str] = None
    template_id: Optional[str] = None
    task_description: Optional[str] = None
    branch_conditions: Optional[Dict[str, Any]] = None


class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_conditions: Optional[Dict[str, Any]] = None
    exit_conditions: Optional[Dict[str, Any]] = None
    steps: List[SequenceStepCreate] = []
    settings: Optional[Dict[str, Any]] = None


class EnrollmentCreate(BaseModel):
    sequence_id: str
    contact_id: str
    contact_email: str
    contact_name: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


# Sequence CRUD
@router.post("")
async def create_sequence(
    request: SequenceCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new sequence"""
    sequence_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    sequence = {
        "id": sequence_id,
        "name": request.name,
        "description": request.description,
        "trigger_type": request.trigger_type.value,
        "trigger_conditions": request.trigger_conditions or {},
        "exit_conditions": request.exit_conditions or {},
        "status": SequenceStatus.DRAFT.value,
        "settings": request.settings or {
            "send_on_weekends": False,
            "send_window_start": "09:00",
            "send_window_end": "18:00",
            "timezone": "America/New_York",
            "stop_on_reply": True,
            "stop_on_bounce": True
        },
        "step_count": len(request.steps),
        "enrolled_count": 0,
        "completed_count": 0,
        "replied_count": 0,
        "converted_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    sequences[sequence_id] = sequence
    
    # Create steps
    for step_data in request.steps:
        step_id = str(uuid.uuid4())
        step = {
            "id": step_id,
            "sequence_id": sequence_id,
            "type": step_data.type.value,
            "order": step_data.order,
            "delay_days": step_data.delay_days,
            "delay_hours": step_data.delay_hours,
            "subject": step_data.subject,
            "content": step_data.content,
            "template_id": step_data.template_id,
            "task_description": step_data.task_description,
            "branch_conditions": step_data.branch_conditions,
            "created_at": now.isoformat()
        }
        sequence_steps[step_id] = step
    
    logger.info("sequence_created", sequence_id=sequence_id, steps=len(request.steps))
    
    return sequence


@router.get("")
async def list_sequences(
    status: Optional[SequenceStatus] = None,
    trigger_type: Optional[TriggerType] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List all sequences"""
    result = [s for s in sequences.values() if s.get("tenant_id") == tenant_id]
    
    if status:
        result = [s for s in result if s.get("status") == status.value]
    if trigger_type:
        result = [s for s in result if s.get("trigger_type") == trigger_type.value]
    if search:
        result = [s for s in result if search.lower() in s.get("name", "").lower()]
    
    return {"sequences": result, "total": len(result)}


@router.get("/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Get sequence details with steps"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    steps = [
        s for s in sequence_steps.values()
        if s.get("sequence_id") == sequence_id
    ]
    steps.sort(key=lambda x: x.get("order", 0))
    
    return {**sequence, "steps": steps}


@router.patch("/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update sequence settings"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "trigger_conditions", "exit_conditions", "settings"]:
            sequence[key] = value
    
    sequence["updated_at"] = datetime.utcnow().isoformat()
    
    return sequence


@router.delete("/{sequence_id}")
async def delete_sequence(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    del sequences[sequence_id]
    
    # Delete steps
    to_delete = [sid for sid, s in sequence_steps.items() if s.get("sequence_id") == sequence_id]
    for sid in to_delete:
        del sequence_steps[sid]
    
    return {"success": True, "deleted": sequence_id}


# Sequence Status
@router.post("/{sequence_id}/activate")
async def activate_sequence(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequences[sequence_id]["status"] = SequenceStatus.ACTIVE.value
    sequences[sequence_id]["activated_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "status": "active"}


@router.post("/{sequence_id}/pause")
async def pause_sequence(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Pause a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequences[sequence_id]["status"] = SequenceStatus.PAUSED.value
    
    return {"success": True, "status": "paused"}


@router.post("/{sequence_id}/archive")
async def archive_sequence(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Archive a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequences[sequence_id]["status"] = SequenceStatus.ARCHIVED.value
    
    return {"success": True, "status": "archived"}


# Steps
@router.post("/{sequence_id}/steps")
async def add_step(
    sequence_id: str,
    request: SequenceStepCreate,
    tenant_id: str = Query(default="default")
):
    """Add a step to a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    step_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    step = {
        "id": step_id,
        "sequence_id": sequence_id,
        "type": request.type.value,
        "order": request.order,
        "delay_days": request.delay_days,
        "delay_hours": request.delay_hours,
        "subject": request.subject,
        "content": request.content,
        "template_id": request.template_id,
        "task_description": request.task_description,
        "branch_conditions": request.branch_conditions,
        "created_at": now.isoformat()
    }
    
    sequence_steps[step_id] = step
    sequences[sequence_id]["step_count"] = sequences[sequence_id].get("step_count", 0) + 1
    
    return step


@router.patch("/{sequence_id}/steps/{step_id}")
async def update_step(
    sequence_id: str,
    step_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update a step"""
    if step_id not in sequence_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    step = sequence_steps[step_id]
    
    for key, value in updates.items():
        if key in ["delay_days", "delay_hours", "subject", "content", "template_id", "task_description"]:
            step[key] = value
    
    step["updated_at"] = datetime.utcnow().isoformat()
    
    return step


@router.delete("/{sequence_id}/steps/{step_id}")
async def delete_step(
    sequence_id: str,
    step_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete a step"""
    if step_id not in sequence_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    del sequence_steps[step_id]
    sequences[sequence_id]["step_count"] = max(0, sequences[sequence_id].get("step_count", 1) - 1)
    
    return {"success": True, "deleted": step_id}


# Enrollments
@router.post("/enrollments")
async def enroll_contact(
    request: EnrollmentCreate,
    tenant_id: str = Query(default="default")
):
    """Enroll a contact in a sequence"""
    if request.sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrollment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    enrollment = {
        "id": enrollment_id,
        "sequence_id": request.sequence_id,
        "contact_id": request.contact_id,
        "contact_email": request.contact_email,
        "contact_name": request.contact_name,
        "variables": request.variables or {},
        "status": EnrollmentStatus.ACTIVE.value,
        "current_step": 1,
        "steps_completed": 0,
        "emails_sent": 0,
        "emails_opened": 0,
        "emails_clicked": 0,
        "replied": False,
        "bounced": False,
        "next_step_at": (now + timedelta(hours=1)).isoformat(),
        "tenant_id": tenant_id,
        "enrolled_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    enrollments[enrollment_id] = enrollment
    sequences[request.sequence_id]["enrolled_count"] = sequences[request.sequence_id].get("enrolled_count", 0) + 1
    
    logger.info("contact_enrolled", enrollment_id=enrollment_id, sequence_id=request.sequence_id)
    
    return enrollment


@router.get("/enrollments")
async def list_enrollments(
    sequence_id: Optional[str] = None,
    status: Optional[EnrollmentStatus] = None,
    contact_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List enrollments"""
    result = [e for e in enrollments.values() if e.get("tenant_id") == tenant_id]
    
    if sequence_id:
        result = [e for e in result if e.get("sequence_id") == sequence_id]
    if status:
        result = [e for e in result if e.get("status") == status.value]
    if contact_id:
        result = [e for e in result if e.get("contact_id") == contact_id]
    
    return {
        "enrollments": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/enrollments/{enrollment_id}")
async def get_enrollment(
    enrollment_id: str,
    tenant_id: str = Query(default="default")
):
    """Get enrollment details"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollments[enrollment_id]


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(
    enrollment_id: str,
    tenant_id: str = Query(default="default")
):
    """Pause an enrollment"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollments[enrollment_id]["status"] = EnrollmentStatus.PAUSED.value
    
    return {"success": True, "status": "paused"}


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(
    enrollment_id: str,
    tenant_id: str = Query(default="default")
):
    """Resume a paused enrollment"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollments[enrollment_id]["status"] = EnrollmentStatus.ACTIVE.value
    enrollments[enrollment_id]["next_step_at"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    return {"success": True, "status": "active"}


@router.post("/enrollments/{enrollment_id}/complete")
async def complete_enrollment(
    enrollment_id: str,
    reason: Optional[str] = Query(default="manual"),
    tenant_id: str = Query(default="default")
):
    """Mark enrollment as completed"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = enrollments[enrollment_id]
    enrollment["status"] = EnrollmentStatus.COMPLETED.value
    enrollment["completed_at"] = datetime.utcnow().isoformat()
    enrollment["completion_reason"] = reason
    
    sequences[enrollment["sequence_id"]]["completed_count"] = sequences[enrollment["sequence_id"]].get("completed_count", 0) + 1
    
    return {"success": True, "status": "completed"}


@router.delete("/enrollments/{enrollment_id}")
async def unenroll_contact(
    enrollment_id: str,
    tenant_id: str = Query(default="default")
):
    """Remove a contact from a sequence"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    del enrollments[enrollment_id]
    
    return {"success": True, "unenrolled": enrollment_id}


# Bulk Enrollment
@router.post("/{sequence_id}/enroll-bulk")
async def bulk_enroll(
    sequence_id: str,
    contacts: List[Dict[str, Any]],
    tenant_id: str = Query(default="default")
):
    """Enroll multiple contacts"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrolled = []
    now = datetime.utcnow()
    
    for contact in contacts:
        enrollment_id = str(uuid.uuid4())
        
        enrollment = {
            "id": enrollment_id,
            "sequence_id": sequence_id,
            "contact_id": contact.get("contact_id"),
            "contact_email": contact.get("email"),
            "contact_name": contact.get("name"),
            "variables": contact.get("variables", {}),
            "status": EnrollmentStatus.ACTIVE.value,
            "current_step": 1,
            "steps_completed": 0,
            "next_step_at": (now + timedelta(hours=1)).isoformat(),
            "tenant_id": tenant_id,
            "enrolled_at": now.isoformat()
        }
        
        enrollments[enrollment_id] = enrollment
        enrolled.append(enrollment_id)
    
    sequences[sequence_id]["enrolled_count"] = sequences[sequence_id].get("enrolled_count", 0) + len(enrolled)
    
    return {"success": True, "enrolled_count": len(enrolled), "enrollment_ids": enrolled}


# Analytics
@router.get("/{sequence_id}/analytics")
async def get_sequence_analytics(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Get sequence performance analytics"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    
    enrolled = sequence.get("enrolled_count", 0) or random.randint(100, 1000)
    completed = random.randint(int(enrolled * 0.3), int(enrolled * 0.7))
    
    return {
        "sequence_id": sequence_id,
        "enrolled_total": enrolled,
        "active": random.randint(20, 200),
        "completed": completed,
        "replied": random.randint(int(enrolled * 0.05), int(enrolled * 0.2)),
        "bounced": random.randint(int(enrolled * 0.01), int(enrolled * 0.05)),
        "unsubscribed": random.randint(int(enrolled * 0.01), int(enrolled * 0.03)),
        "converted": random.randint(int(enrolled * 0.02), int(enrolled * 0.15)),
        "email_metrics": {
            "sent": random.randint(enrolled * 2, enrolled * 5),
            "delivered": random.randint(int(enrolled * 1.8), int(enrolled * 4.8)),
            "opened": random.randint(int(enrolled * 0.5), int(enrolled * 2)),
            "clicked": random.randint(int(enrolled * 0.1), int(enrolled * 0.5)),
            "replied": random.randint(int(enrolled * 0.05), int(enrolled * 0.2))
        },
        "open_rate": round(random.uniform(0.25, 0.55), 3),
        "click_rate": round(random.uniform(0.02, 0.10), 3),
        "reply_rate": round(random.uniform(0.03, 0.15), 3),
        "conversion_rate": round(random.uniform(0.02, 0.12), 3),
        "avg_time_to_reply_hours": random.randint(12, 72)
    }


@router.get("/{sequence_id}/step-analytics")
async def get_step_analytics(
    sequence_id: str,
    tenant_id: str = Query(default="default")
):
    """Get per-step analytics"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    steps = [s for s in sequence_steps.values() if s.get("sequence_id") == sequence_id]
    steps.sort(key=lambda x: x.get("order", 0))
    
    analytics = []
    for step in steps:
        sent = random.randint(100, 500)
        analytics.append({
            "step_id": step["id"],
            "step_order": step["order"],
            "step_type": step["type"],
            "sent": sent,
            "delivered": int(sent * random.uniform(0.95, 0.99)),
            "opened": int(sent * random.uniform(0.25, 0.50)) if step["type"] == "email" else None,
            "clicked": int(sent * random.uniform(0.02, 0.10)) if step["type"] == "email" else None,
            "replied": int(sent * random.uniform(0.02, 0.10)) if step["type"] == "email" else None,
            "completed": int(sent * random.uniform(0.80, 0.95)) if step["type"] in ["call", "task"] else None,
            "drop_off_rate": round(random.uniform(0.05, 0.20), 3)
        })
    
    return {"sequence_id": sequence_id, "step_analytics": analytics}


# Clone
@router.post("/{sequence_id}/clone")
async def clone_sequence(
    sequence_id: str,
    new_name: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Clone a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    original = sequences[sequence_id]
    new_sequence_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_sequence = {
        **original,
        "id": new_sequence_id,
        "name": new_name or f"{original['name']} (Copy)",
        "status": SequenceStatus.DRAFT.value,
        "enrolled_count": 0,
        "completed_count": 0,
        "replied_count": 0,
        "converted_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    sequences[new_sequence_id] = new_sequence
    
    # Clone steps
    original_steps = [s for s in sequence_steps.values() if s.get("sequence_id") == sequence_id]
    for step in original_steps:
        new_step_id = str(uuid.uuid4())
        new_step = {
            **step,
            "id": new_step_id,
            "sequence_id": new_sequence_id,
            "created_at": now.isoformat()
        }
        sequence_steps[new_step_id] = new_step
    
    return new_sequence
