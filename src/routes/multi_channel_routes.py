"""
Multi-Channel Outreach Routes - Coordinated outreach across channels
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

router = APIRouter(prefix="/multi-channel", tags=["Multi-Channel Outreach"])


class ChannelType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"
    VIDEO = "video"
    SOCIAL = "social"
    CHAT = "chat"


class SequenceStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProspectStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REPLIED = "replied"
    MEETING_BOOKED = "meeting_booked"
    OPTED_OUT = "opted_out"
    BOUNCED = "bounced"


class StepType(str, Enum):
    SEND = "send"
    CALL = "call"
    TASK = "task"
    WAIT = "wait"
    CONDITION = "condition"
    LINKEDIN_CONNECT = "linkedin_connect"
    LINKEDIN_MESSAGE = "linkedin_message"


class TriggerType(str, Enum):
    IMMEDIATE = "immediate"
    DELAY = "delay"
    SCHEDULE = "schedule"
    EVENT = "event"
    REPLY = "reply"
    NO_REPLY = "no_reply"


# In-memory storage
sequences = {}
sequence_steps = {}
sequence_enrollments = {}
channel_templates = {}
outreach_tasks = {}
channel_analytics = {}
ab_tests = {}
throttle_settings = {}


class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    channels: List[ChannelType]
    goal: Optional[str] = None
    tags: Optional[List[str]] = None


class StepCreate(BaseModel):
    sequence_id: str
    step_type: StepType
    channel: Optional[ChannelType] = None
    template_id: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    delay_days: int = 0
    delay_hours: int = 0
    conditions: Optional[Dict[str, Any]] = None
    position: Optional[int] = None


# Sequences
@router.post("/sequences")
async def create_sequence(
    request: SequenceCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a multi-channel sequence"""
    sequence_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    sequence = {
        "id": sequence_id,
        "name": request.name,
        "description": request.description,
        "channels": [c.value for c in request.channels],
        "goal": request.goal,
        "tags": request.tags or [],
        "status": SequenceStatus.DRAFT.value,
        "step_count": 0,
        "enrolled_count": 0,
        "completed_count": 0,
        "reply_rate": 0,
        "meeting_rate": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    sequences[sequence_id] = sequence
    
    logger.info("sequence_created", sequence_id=sequence_id, channels=request.channels)
    return sequence


@router.get("/sequences")
async def list_sequences(
    status: Optional[SequenceStatus] = None,
    channel: Optional[ChannelType] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List sequences"""
    result = [s for s in sequences.values() if s.get("tenant_id") == tenant_id]
    
    if status:
        result = [s for s in result if s.get("status") == status.value]
    if channel:
        result = [s for s in result if channel.value in s.get("channels", [])]
    if search:
        search_lower = search.lower()
        result = [s for s in result if search_lower in s.get("name", "").lower()]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"sequences": result, "total": len(result)}


@router.get("/sequences/{sequence_id}")
async def get_sequence(sequence_id: str):
    """Get sequence details"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    steps = [s for s in sequence_steps.values() if s.get("sequence_id") == sequence_id]
    steps.sort(key=lambda x: x.get("position", 0))
    
    enrollments = [e for e in sequence_enrollments.values() if e.get("sequence_id") == sequence_id]
    
    return {
        **sequence,
        "steps": steps,
        "enrollments_summary": {
            "total": len(enrollments),
            "in_progress": len([e for e in enrollments if e.get("status") == "in_progress"]),
            "completed": len([e for e in enrollments if e.get("status") == "completed"]),
            "replied": len([e for e in enrollments if e.get("status") == "replied"])
        }
    }


@router.put("/sequences/{sequence_id}/status")
async def update_sequence_status(
    sequence_id: str,
    status: SequenceStatus
):
    """Update sequence status"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    sequence["status"] = status.value
    sequence["updated_at"] = datetime.utcnow().isoformat()
    
    if status == SequenceStatus.ACTIVE:
        sequence["activated_at"] = datetime.utcnow().isoformat()
    
    return sequence


# Steps
@router.post("/steps")
async def create_step(
    request: StepCreate,
    user_id: str = Query(default="default")
):
    """Add a step to a sequence"""
    if request.sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    step_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Calculate position
    existing_steps = [s for s in sequence_steps.values() if s.get("sequence_id") == request.sequence_id]
    position = request.position if request.position is not None else len(existing_steps) + 1
    
    step = {
        "id": step_id,
        "sequence_id": request.sequence_id,
        "step_type": request.step_type.value,
        "channel": request.channel.value if request.channel else None,
        "template_id": request.template_id,
        "content": request.content,
        "subject": request.subject,
        "delay_days": request.delay_days,
        "delay_hours": request.delay_hours,
        "conditions": request.conditions or {},
        "position": position,
        "created_by": user_id,
        "created_at": now.isoformat()
    }
    
    sequence_steps[step_id] = step
    
    # Update step count
    sequences[request.sequence_id]["step_count"] = len(existing_steps) + 1
    
    return step


@router.get("/sequences/{sequence_id}/steps")
async def get_sequence_steps(sequence_id: str):
    """Get all steps in a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    steps = [s for s in sequence_steps.values() if s.get("sequence_id") == sequence_id]
    steps.sort(key=lambda x: x.get("position", 0))
    
    return {"steps": steps, "total": len(steps)}


@router.put("/steps/{step_id}")
async def update_step(
    step_id: str,
    content: Optional[str] = None,
    subject: Optional[str] = None,
    delay_days: Optional[int] = None,
    delay_hours: Optional[int] = None,
    position: Optional[int] = None
):
    """Update a step"""
    if step_id not in sequence_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    step = sequence_steps[step_id]
    
    if content is not None:
        step["content"] = content
    if subject is not None:
        step["subject"] = subject
    if delay_days is not None:
        step["delay_days"] = delay_days
    if delay_hours is not None:
        step["delay_hours"] = delay_hours
    if position is not None:
        step["position"] = position
    
    step["updated_at"] = datetime.utcnow().isoformat()
    
    return step


@router.delete("/steps/{step_id}")
async def delete_step(step_id: str):
    """Delete a step"""
    if step_id not in sequence_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    step = sequence_steps.pop(step_id)
    
    return {"message": "Step deleted", "step_id": step_id}


# Enrollments
@router.post("/sequences/{sequence_id}/enroll")
async def enroll_prospect(
    sequence_id: str,
    prospect_id: str,
    prospect_email: str,
    prospect_name: Optional[str] = None,
    prospect_data: Optional[Dict[str, Any]] = None,
    user_id: str = Query(default="default")
):
    """Enroll a prospect in a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrollment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    enrollment = {
        "id": enrollment_id,
        "sequence_id": sequence_id,
        "prospect_id": prospect_id,
        "prospect_email": prospect_email,
        "prospect_name": prospect_name,
        "prospect_data": prospect_data or {},
        "status": ProspectStatus.NOT_STARTED.value,
        "current_step": 1,
        "next_step_at": now.isoformat(),
        "steps_completed": 0,
        "enrolled_by": user_id,
        "enrolled_at": now.isoformat()
    }
    
    sequence_enrollments[enrollment_id] = enrollment
    
    # Update sequence counts
    sequences[sequence_id]["enrolled_count"] = sequences[sequence_id].get("enrolled_count", 0) + 1
    
    logger.info("prospect_enrolled", enrollment_id=enrollment_id, sequence_id=sequence_id)
    return enrollment


@router.post("/sequences/{sequence_id}/enroll-bulk")
async def bulk_enroll_prospects(
    sequence_id: str,
    prospects: List[Dict[str, Any]],
    user_id: str = Query(default="default")
):
    """Bulk enroll prospects in a sequence"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrolled = []
    failed = []
    
    for prospect in prospects:
        try:
            enrollment = await enroll_prospect(
                sequence_id=sequence_id,
                prospect_id=prospect.get("id", str(uuid.uuid4())),
                prospect_email=prospect.get("email"),
                prospect_name=prospect.get("name"),
                prospect_data=prospect.get("data"),
                user_id=user_id
            )
            enrolled.append(enrollment)
        except Exception as e:
            failed.append({"prospect": prospect, "error": str(e)})
    
    return {
        "enrolled_count": len(enrolled),
        "failed_count": len(failed),
        "enrollments": enrolled,
        "failures": failed
    }


@router.get("/sequences/{sequence_id}/enrollments")
async def get_sequence_enrollments(
    sequence_id: str,
    status: Optional[ProspectStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    """Get sequence enrollments"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrollments = [e for e in sequence_enrollments.values() if e.get("sequence_id") == sequence_id]
    
    if status:
        enrollments = [e for e in enrollments if e.get("status") == status.value]
    
    enrollments.sort(key=lambda x: x.get("enrolled_at", ""), reverse=True)
    
    return {
        "enrollments": enrollments[offset:offset + limit],
        "total": len(enrollments),
        "limit": limit,
        "offset": offset
    }


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str):
    """Pause an enrollment"""
    if enrollment_id not in sequence_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = sequence_enrollments[enrollment_id]
    enrollment["paused"] = True
    enrollment["paused_at"] = datetime.utcnow().isoformat()
    
    return enrollment


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(enrollment_id: str):
    """Resume a paused enrollment"""
    if enrollment_id not in sequence_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = sequence_enrollments[enrollment_id]
    enrollment["paused"] = False
    enrollment["resumed_at"] = datetime.utcnow().isoformat()
    
    return enrollment


@router.post("/enrollments/{enrollment_id}/complete")
async def complete_enrollment(
    enrollment_id: str,
    outcome: str,
    notes: Optional[str] = None
):
    """Mark enrollment as complete"""
    if enrollment_id not in sequence_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = sequence_enrollments[enrollment_id]
    now = datetime.utcnow()
    
    enrollment["status"] = ProspectStatus.COMPLETED.value
    enrollment["outcome"] = outcome
    enrollment["notes"] = notes
    enrollment["completed_at"] = now.isoformat()
    
    # Update sequence counts
    sequence_id = enrollment["sequence_id"]
    if sequence_id in sequences:
        sequences[sequence_id]["completed_count"] = sequences[sequence_id].get("completed_count", 0) + 1
    
    return enrollment


# Channel Templates
@router.post("/templates")
async def create_channel_template(
    name: str,
    channel: ChannelType,
    subject: Optional[str] = None,
    content: str = "",
    variables: Optional[List[str]] = None,
    tenant_id: str = Query(default="default")
):
    """Create a channel template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": name,
        "channel": channel.value,
        "subject": subject,
        "content": content,
        "variables": variables or [],
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    channel_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_channel_templates(
    channel: Optional[ChannelType] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List channel templates"""
    result = [t for t in channel_templates.values() if t.get("tenant_id") == tenant_id]
    
    if channel:
        result = [t for t in result if t.get("channel") == channel.value]
    if search:
        search_lower = search.lower()
        result = [t for t in result if search_lower in t.get("name", "").lower()]
    
    return {"templates": result, "total": len(result)}


# Tasks
@router.get("/tasks")
async def get_outreach_tasks(
    user_id: Optional[str] = None,
    channel: Optional[ChannelType] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get outreach tasks"""
    tasks = list(outreach_tasks.values())
    
    if user_id:
        tasks = [t for t in tasks if t.get("assigned_to") == user_id]
    if channel:
        tasks = [t for t in tasks if t.get("channel") == channel.value]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if due_date:
        tasks = [t for t in tasks if t.get("due_date", "")[:10] == due_date]
    
    tasks.sort(key=lambda x: x.get("due_date", "9999"))
    
    return {"tasks": tasks, "total": len(tasks)}


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    outcome: str,
    notes: Optional[str] = None
):
    """Complete an outreach task"""
    if task_id not in outreach_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = outreach_tasks[task_id]
    now = datetime.utcnow()
    
    task["status"] = "completed"
    task["outcome"] = outcome
    task["notes"] = notes
    task["completed_at"] = now.isoformat()
    
    return task


# A/B Testing
@router.post("/sequences/{sequence_id}/ab-test")
async def create_ab_test(
    sequence_id: str,
    step_position: int,
    variant_b_content: str,
    variant_b_subject: Optional[str] = None,
    split_percentage: int = 50
):
    """Create A/B test for a sequence step"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    test_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    test = {
        "id": test_id,
        "sequence_id": sequence_id,
        "step_position": step_position,
        "variant_a": "original",
        "variant_b_content": variant_b_content,
        "variant_b_subject": variant_b_subject,
        "split_percentage": split_percentage,
        "status": "active",
        "variant_a_sent": 0,
        "variant_a_opens": 0,
        "variant_a_replies": 0,
        "variant_b_sent": 0,
        "variant_b_opens": 0,
        "variant_b_replies": 0,
        "created_at": now.isoformat()
    }
    
    ab_tests[test_id] = test
    
    return test


@router.get("/sequences/{sequence_id}/ab-tests")
async def get_ab_tests(sequence_id: str):
    """Get A/B tests for a sequence"""
    tests = [t for t in ab_tests.values() if t.get("sequence_id") == sequence_id]
    
    # Calculate results
    for test in tests:
        test["variant_a_open_rate"] = test["variant_a_opens"] / max(1, test["variant_a_sent"])
        test["variant_a_reply_rate"] = test["variant_a_replies"] / max(1, test["variant_a_sent"])
        test["variant_b_open_rate"] = test["variant_b_opens"] / max(1, test["variant_b_sent"])
        test["variant_b_reply_rate"] = test["variant_b_replies"] / max(1, test["variant_b_sent"])
        test["winner"] = "variant_a" if test["variant_a_reply_rate"] > test["variant_b_reply_rate"] else "variant_b"
    
    return {"ab_tests": tests, "total": len(tests)}


# Throttling
@router.post("/throttle-settings")
async def set_throttle_settings(
    channel: ChannelType,
    max_per_day: int,
    max_per_hour: Optional[int] = None,
    send_window_start: Optional[str] = None,
    send_window_end: Optional[str] = None,
    timezone: str = "UTC",
    tenant_id: str = Query(default="default")
):
    """Set channel throttling settings"""
    setting_id = f"{tenant_id}_{channel.value}"
    
    setting = {
        "id": setting_id,
        "channel": channel.value,
        "max_per_day": max_per_day,
        "max_per_hour": max_per_hour,
        "send_window_start": send_window_start,
        "send_window_end": send_window_end,
        "timezone": timezone,
        "tenant_id": tenant_id,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    throttle_settings[setting_id] = setting
    
    return setting


@router.get("/throttle-settings")
async def get_throttle_settings(
    channel: Optional[ChannelType] = None,
    tenant_id: str = Query(default="default")
):
    """Get throttle settings"""
    result = [s for s in throttle_settings.values() if s.get("tenant_id") == tenant_id]
    
    if channel:
        result = [s for s in result if s.get("channel") == channel.value]
    
    return {"settings": result}


# Analytics
@router.get("/analytics/sequences/{sequence_id}")
async def get_sequence_analytics(sequence_id: str):
    """Get detailed sequence analytics"""
    if sequence_id not in sequences:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    sequence = sequences[sequence_id]
    enrollments = [e for e in sequence_enrollments.values() if e.get("sequence_id") == sequence_id]
    steps = [s for s in sequence_steps.values() if s.get("sequence_id") == sequence_id]
    
    # Generate step performance
    step_performance = []
    for step in sorted(steps, key=lambda x: x.get("position", 0)):
        step_performance.append({
            "step": step["position"],
            "channel": step.get("channel"),
            "type": step["step_type"],
            "sent": random.randint(50, 200),
            "opened": random.randint(20, 100),
            "clicked": random.randint(5, 40),
            "replied": random.randint(2, 20),
            "meetings": random.randint(0, 5)
        })
    
    return {
        "sequence_id": sequence_id,
        "sequence_name": sequence["name"],
        "total_enrolled": len(enrollments),
        "in_progress": len([e for e in enrollments if e.get("status") == "in_progress"]),
        "completed": len([e for e in enrollments if e.get("status") == "completed"]),
        "replied": len([e for e in enrollments if e.get("status") == "replied"]),
        "meetings_booked": len([e for e in enrollments if e.get("status") == "meeting_booked"]),
        "opted_out": len([e for e in enrollments if e.get("status") == "opted_out"]),
        "reply_rate": round(random.uniform(0.05, 0.25), 3),
        "meeting_rate": round(random.uniform(0.02, 0.1), 3),
        "avg_days_to_reply": round(random.uniform(2, 7), 1),
        "step_performance": step_performance
    }


@router.get("/analytics/channels")
async def get_channel_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get multi-channel analytics"""
    channels = {}
    
    for channel in ChannelType:
        channels[channel.value] = {
            "sent": random.randint(500, 5000),
            "delivered": random.randint(450, 4800),
            "opened": random.randint(200, 2000),
            "clicked": random.randint(50, 500),
            "replied": random.randint(20, 200),
            "meetings": random.randint(5, 50),
            "open_rate": round(random.uniform(0.2, 0.6), 3),
            "reply_rate": round(random.uniform(0.02, 0.15), 3),
            "meeting_rate": round(random.uniform(0.01, 0.05), 3)
        }
    
    return {
        "channels": channels,
        "period": {"start_date": start_date, "end_date": end_date},
        "best_performing_channel": max(channels.items(), key=lambda x: x[1]["reply_rate"])[0],
        "total_outreach": sum(c["sent"] for c in channels.values())
    }


@router.get("/analytics/optimal-times")
async def get_optimal_send_times(
    channel: Optional[ChannelType] = None,
    tenant_id: str = Query(default="default")
):
    """Get optimal send times by channel"""
    times = {}
    
    channels_to_analyze = [channel] if channel else list(ChannelType)
    
    for ch in channels_to_analyze:
        ch_value = ch.value if isinstance(ch, ChannelType) else ch
        times[ch_value] = {
            "best_days": random.sample(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], k=3),
            "best_hours": random.sample(["9:00", "10:00", "11:00", "14:00", "15:00", "16:00"], k=3),
            "worst_times": ["Monday 8:00", "Friday 17:00"],
            "timezone_note": "Based on recipient local time"
        }
    
    return {
        "optimal_times": times,
        "recommendation": "Send emails Tuesday-Thursday between 9-11am local time for best results"
    }
