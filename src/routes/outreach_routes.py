"""
Outreach Routes - Multi-channel outreach campaign management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/outreach", tags=["Outreach"])


class OutreachChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    SMS = "sms"
    SOCIAL = "social"
    DIRECT_MAIL = "direct_mail"
    VIDEO = "video"


class OutreachStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TouchStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProspectStatus(str, Enum):
    ACTIVE = "active"
    ENGAGED = "engaged"
    REPLIED = "replied"
    MEETING_BOOKED = "meeting_booked"
    CONVERTED = "converted"
    OPTED_OUT = "opted_out"
    BOUNCED = "bounced"
    PAUSED = "paused"


class CadenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]  # Each step has channel, delay_days, template_id, etc.
    target_persona: Optional[str] = None
    entry_criteria: Optional[Dict[str, Any]] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class CadenceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ProspectEnroll(BaseModel):
    prospect_ids: List[str]
    cadence_id: str
    start_immediately: bool = True
    personalization: Optional[Dict[str, Any]] = None


class TouchCreate(BaseModel):
    cadence_id: str
    prospect_id: str
    step_number: int
    channel: OutreachChannel
    content: Dict[str, Any]
    scheduled_at: Optional[str] = None


class LinkedInAction(BaseModel):
    prospect_id: str
    action_type: str  # connect, message, view_profile, like_post, comment
    content: Optional[str] = None
    connection_note: Optional[str] = None


# In-memory storage
cadences = {}
enrollments = {}
touches = {}
linkedin_actions = {}
outreach_stats = {}


@router.post("/cadences")
async def create_cadence(
    request: CadenceCreate,
    tenant_id: str = Query(default="default")
):
    """Create a multi-touch outreach cadence"""
    import uuid
    
    cadence_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Validate and enhance steps
    processed_steps = []
    for idx, step in enumerate(request.steps):
        processed_steps.append({
            "step_number": idx + 1,
            "channel": step.get("channel", "email"),
            "delay_days": step.get("delay_days", 0 if idx == 0 else 3),
            "template_id": step.get("template_id"),
            "subject": step.get("subject"),
            "content": step.get("content"),
            "send_time": step.get("send_time", "09:00"),
            "skip_weekends": step.get("skip_weekends", True),
            "ab_test": step.get("ab_test"),
            "conditions": step.get("conditions", {})
        })
    
    cadence = {
        "id": cadence_id,
        "name": request.name,
        "description": request.description,
        "steps": processed_steps,
        "total_steps": len(processed_steps),
        "target_persona": request.target_persona,
        "entry_criteria": request.entry_criteria or {},
        "exit_criteria": request.exit_criteria or {},
        "settings": request.settings or {},
        "status": "active",
        "enrolled_count": 0,
        "completed_count": 0,
        "reply_rate": 0,
        "meeting_rate": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    cadences[cadence_id] = cadence
    logger.info("cadence_created", cadence_id=cadence_id, name=request.name, steps=len(processed_steps))
    return cadence


@router.get("/cadences")
async def list_cadences(
    status: Optional[str] = None,
    channel: Optional[OutreachChannel] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List outreach cadences"""
    result = [c for c in cadences.values() if c.get("tenant_id") == tenant_id]
    
    if status:
        result = [c for c in result if c.get("status") == status]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "cadences": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/cadences/{cadence_id}")
async def get_cadence(cadence_id: str):
    """Get cadence details"""
    if cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    return cadences[cadence_id]


@router.put("/cadences/{cadence_id}")
async def update_cadence(cadence_id: str, request: CadenceUpdate):
    """Update cadence"""
    if cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    cadence = cadences[cadence_id]
    
    if request.name is not None:
        cadence["name"] = request.name
    if request.description is not None:
        cadence["description"] = request.description
    if request.steps is not None:
        cadence["steps"] = request.steps
        cadence["total_steps"] = len(request.steps)
    if request.settings is not None:
        cadence["settings"] = request.settings
    if request.is_active is not None:
        cadence["status"] = "active" if request.is_active else "paused"
    
    cadence["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("cadence_updated", cadence_id=cadence_id)
    return cadence


@router.delete("/cadences/{cadence_id}")
async def delete_cadence(cadence_id: str):
    """Delete cadence"""
    if cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    del cadences[cadence_id]
    logger.info("cadence_deleted", cadence_id=cadence_id)
    return {"status": "deleted", "cadence_id": cadence_id}


@router.post("/cadences/{cadence_id}/clone")
async def clone_cadence(cadence_id: str, new_name: Optional[str] = None):
    """Clone an existing cadence"""
    if cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    import uuid
    original = cadences[cadence_id]
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    clone = {
        **original,
        "id": new_id,
        "name": new_name or f"{original['name']} (Copy)",
        "enrolled_count": 0,
        "completed_count": 0,
        "reply_rate": 0,
        "meeting_rate": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    cadences[new_id] = clone
    logger.info("cadence_cloned", original_id=cadence_id, new_id=new_id)
    return clone


@router.post("/enroll")
async def enroll_prospects(
    request: ProspectEnroll,
    tenant_id: str = Query(default="default")
):
    """Enroll prospects in a cadence"""
    if request.cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    import uuid
    now = datetime.utcnow()
    cadence = cadences[request.cadence_id]
    
    enrolled = []
    for prospect_id in request.prospect_ids:
        enrollment_id = str(uuid.uuid4())
        
        enrollment = {
            "id": enrollment_id,
            "cadence_id": request.cadence_id,
            "prospect_id": prospect_id,
            "status": ProspectStatus.ACTIVE.value,
            "current_step": 1,
            "enrolled_at": now.isoformat(),
            "next_touch_at": now.isoformat() if request.start_immediately else None,
            "personalization": request.personalization or {},
            "touches_sent": 0,
            "opens": 0,
            "clicks": 0,
            "replies": 0,
            "tenant_id": tenant_id
        }
        
        enrollments[enrollment_id] = enrollment
        enrolled.append(enrollment)
    
    # Update cadence stats
    cadence["enrolled_count"] = cadence.get("enrolled_count", 0) + len(enrolled)
    
    logger.info("prospects_enrolled", cadence_id=request.cadence_id, count=len(enrolled))
    return {
        "enrolled": enrolled,
        "count": len(enrolled),
        "cadence_id": request.cadence_id
    }


@router.get("/enrollments")
async def list_enrollments(
    cadence_id: Optional[str] = None,
    prospect_id: Optional[str] = None,
    status: Optional[ProspectStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List prospect enrollments"""
    result = [e for e in enrollments.values() if e.get("tenant_id") == tenant_id]
    
    if cadence_id:
        result = [e for e in result if e.get("cadence_id") == cadence_id]
    if prospect_id:
        result = [e for e in result if e.get("prospect_id") == prospect_id]
    if status:
        result = [e for e in result if e.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("enrolled_at", ""), reverse=True)
    
    return {
        "enrollments": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/enrollments/{enrollment_id}")
async def get_enrollment(enrollment_id: str):
    """Get enrollment details"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollments[enrollment_id]


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str, reason: Optional[str] = None):
    """Pause prospect enrollment"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = enrollments[enrollment_id]
    enrollment["status"] = ProspectStatus.PAUSED.value
    enrollment["paused_at"] = datetime.utcnow().isoformat()
    enrollment["pause_reason"] = reason
    
    logger.info("enrollment_paused", enrollment_id=enrollment_id)
    return enrollment


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(enrollment_id: str):
    """Resume paused enrollment"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = enrollments[enrollment_id]
    enrollment["status"] = ProspectStatus.ACTIVE.value
    enrollment["resumed_at"] = datetime.utcnow().isoformat()
    enrollment["next_touch_at"] = datetime.utcnow().isoformat()
    
    logger.info("enrollment_resumed", enrollment_id=enrollment_id)
    return enrollment


@router.post("/enrollments/{enrollment_id}/skip-step")
async def skip_step(enrollment_id: str, reason: Optional[str] = None):
    """Skip current step and move to next"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = enrollments[enrollment_id]
    cadence = cadences.get(enrollment["cadence_id"])
    
    if not cadence:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    current_step = enrollment.get("current_step", 1)
    total_steps = cadence.get("total_steps", 0)
    
    if current_step >= total_steps:
        enrollment["status"] = "completed"
        enrollment["completed_at"] = datetime.utcnow().isoformat()
    else:
        enrollment["current_step"] = current_step + 1
        enrollment["step_skipped"] = current_step
        enrollment["skip_reason"] = reason
    
    logger.info("step_skipped", enrollment_id=enrollment_id, step=current_step)
    return enrollment


@router.delete("/enrollments/{enrollment_id}")
async def remove_enrollment(enrollment_id: str, reason: Optional[str] = None):
    """Remove prospect from cadence"""
    if enrollment_id not in enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = enrollments[enrollment_id]
    enrollment["status"] = "removed"
    enrollment["removed_at"] = datetime.utcnow().isoformat()
    enrollment["removal_reason"] = reason
    
    logger.info("enrollment_removed", enrollment_id=enrollment_id)
    return {"status": "removed", "enrollment_id": enrollment_id}


@router.post("/touches")
async def create_touch(
    request: TouchCreate,
    tenant_id: str = Query(default="default")
):
    """Create an outreach touch"""
    import uuid
    
    touch_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    touch = {
        "id": touch_id,
        "cadence_id": request.cadence_id,
        "prospect_id": request.prospect_id,
        "step_number": request.step_number,
        "channel": request.channel.value,
        "content": request.content,
        "status": TouchStatus.PENDING.value,
        "scheduled_at": request.scheduled_at or now.isoformat(),
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    touches[touch_id] = touch
    logger.info("touch_created", touch_id=touch_id, channel=request.channel.value)
    return touch


@router.get("/touches")
async def list_touches(
    cadence_id: Optional[str] = None,
    prospect_id: Optional[str] = None,
    status: Optional[TouchStatus] = None,
    channel: Optional[OutreachChannel] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List outreach touches"""
    result = [t for t in touches.values() if t.get("tenant_id") == tenant_id]
    
    if cadence_id:
        result = [t for t in result if t.get("cadence_id") == cadence_id]
    if prospect_id:
        result = [t for t in result if t.get("prospect_id") == prospect_id]
    if status:
        result = [t for t in result if t.get("status") == status.value]
    if channel:
        result = [t for t in result if t.get("channel") == channel.value]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "touches": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.post("/touches/{touch_id}/send")
async def send_touch(touch_id: str):
    """Send/execute a touch"""
    if touch_id not in touches:
        raise HTTPException(status_code=404, detail="Touch not found")
    
    touch = touches[touch_id]
    now = datetime.utcnow()
    
    touch["status"] = TouchStatus.SENT.value
    touch["sent_at"] = now.isoformat()
    touch["message_id"] = f"msg_{touch_id[:8]}"
    
    logger.info("touch_sent", touch_id=touch_id, channel=touch.get("channel"))
    return touch


@router.post("/touches/{touch_id}/record-event")
async def record_touch_event(
    touch_id: str,
    event_type: str,  # delivered, opened, clicked, replied, bounced
    metadata: Optional[Dict[str, Any]] = None
):
    """Record engagement event for touch"""
    if touch_id not in touches:
        raise HTTPException(status_code=404, detail="Touch not found")
    
    touch = touches[touch_id]
    now = datetime.utcnow()
    
    event_status_map = {
        "delivered": TouchStatus.DELIVERED.value,
        "opened": TouchStatus.OPENED.value,
        "clicked": TouchStatus.CLICKED.value,
        "replied": TouchStatus.REPLIED.value,
        "bounced": TouchStatus.BOUNCED.value
    }
    
    if event_type in event_status_map:
        touch["status"] = event_status_map[event_type]
        touch[f"{event_type}_at"] = now.isoformat()
    
    if "events" not in touch:
        touch["events"] = []
    touch["events"].append({
        "type": event_type,
        "timestamp": now.isoformat(),
        "metadata": metadata or {}
    })
    
    logger.info("touch_event_recorded", touch_id=touch_id, event=event_type)
    return touch


@router.post("/linkedin/action")
async def perform_linkedin_action(
    request: LinkedInAction,
    tenant_id: str = Query(default="default")
):
    """Perform LinkedIn outreach action"""
    import uuid
    
    action_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    action = {
        "id": action_id,
        "prospect_id": request.prospect_id,
        "action_type": request.action_type,
        "content": request.content,
        "connection_note": request.connection_note,
        "status": "completed",
        "performed_at": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    linkedin_actions[action_id] = action
    logger.info("linkedin_action_performed", action_id=action_id, type=request.action_type)
    return action


@router.get("/linkedin/actions")
async def list_linkedin_actions(
    prospect_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List LinkedIn actions"""
    result = [a for a in linkedin_actions.values() if a.get("tenant_id") == tenant_id]
    
    if prospect_id:
        result = [a for a in result if a.get("prospect_id") == prospect_id]
    if action_type:
        result = [a for a in result if a.get("action_type") == action_type]
    
    result.sort(key=lambda x: x.get("performed_at", ""), reverse=True)
    
    return {
        "actions": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/cadences/{cadence_id}/stats")
async def get_cadence_stats(cadence_id: str):
    """Get detailed stats for a cadence"""
    if cadence_id not in cadences:
        raise HTTPException(status_code=404, detail="Cadence not found")
    
    cadence_enrollments = [e for e in enrollments.values() if e.get("cadence_id") == cadence_id]
    cadence_touches = [t for t in touches.values() if t.get("cadence_id") == cadence_id]
    
    total_enrolled = len(cadence_enrollments)
    active = len([e for e in cadence_enrollments if e.get("status") == ProspectStatus.ACTIVE.value])
    completed = len([e for e in cadence_enrollments if e.get("status") == "completed"])
    replied = len([e for e in cadence_enrollments if e.get("status") == ProspectStatus.REPLIED.value])
    meetings = len([e for e in cadence_enrollments if e.get("status") == ProspectStatus.MEETING_BOOKED.value])
    
    sent = len([t for t in cadence_touches if t.get("status") == TouchStatus.SENT.value])
    delivered = len([t for t in cadence_touches if t.get("status") == TouchStatus.DELIVERED.value])
    opened = len([t for t in cadence_touches if t.get("status") == TouchStatus.OPENED.value])
    clicked = len([t for t in cadence_touches if t.get("status") == TouchStatus.CLICKED.value])
    
    return {
        "cadence_id": cadence_id,
        "enrollments": {
            "total": total_enrolled,
            "active": active,
            "completed": completed,
            "replied": replied,
            "meetings_booked": meetings
        },
        "touches": {
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked
        },
        "rates": {
            "reply_rate": round(replied / total_enrolled * 100, 2) if total_enrolled > 0 else 0,
            "meeting_rate": round(meetings / total_enrolled * 100, 2) if total_enrolled > 0 else 0,
            "open_rate": round(opened / sent * 100, 2) if sent > 0 else 0,
            "click_rate": round(clicked / opened * 100, 2) if opened > 0 else 0
        }
    }


@router.get("/stats")
async def get_outreach_stats(
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: str = Query(default="default")
):
    """Get overall outreach statistics"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    tenant_enrollments = [e for e in enrollments.values() if e.get("tenant_id") == tenant_id]
    tenant_touches = [t for t in touches.values() if t.get("tenant_id") == tenant_id]
    tenant_cadences = [c for c in cadences.values() if c.get("tenant_id") == tenant_id]
    
    # Filter by date
    recent_touches = [t for t in tenant_touches if t.get("created_at", "") >= cutoff.isoformat()]
    
    by_channel = {}
    for t in recent_touches:
        channel = t.get("channel", "unknown")
        if channel not in by_channel:
            by_channel[channel] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}
        by_channel[channel]["sent"] += 1
        if t.get("status") in ["opened", "clicked", "replied"]:
            by_channel[channel]["opened"] += 1
        if t.get("status") in ["clicked", "replied"]:
            by_channel[channel]["clicked"] += 1
        if t.get("status") == "replied":
            by_channel[channel]["replied"] += 1
    
    return {
        "period_days": days,
        "total_cadences": len(tenant_cadences),
        "active_cadences": len([c for c in tenant_cadences if c.get("status") == "active"]),
        "total_enrollments": len(tenant_enrollments),
        "total_touches": len(tenant_touches),
        "recent_touches": len(recent_touches),
        "by_channel": by_channel
    }
