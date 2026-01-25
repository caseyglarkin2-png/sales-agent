"""
Sales Playbooks V2 Routes - Advanced sales playbook management
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

router = APIRouter(prefix="/playbooks-v2", tags=["Sales Playbooks V2"])


class PlaybookType(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"
    EXPANSION = "expansion"
    RENEWAL = "renewal"
    COMPETITIVE = "competitive"
    OBJECTION_HANDLING = "objection_handling"
    DEMO = "demo"
    ONBOARDING = "onboarding"


class PlaybookStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(str, Enum):
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    TASK = "task"
    LINKEDIN = "linkedin"
    DELAY = "delay"
    BRANCH = "branch"
    AI_INSIGHT = "ai_insight"


class PlaybookMetric(str, Enum):
    RESPONSE_RATE = "response_rate"
    MEETING_RATE = "meeting_rate"
    CONVERSION_RATE = "conversion_rate"
    WIN_RATE = "win_rate"
    CYCLE_TIME = "cycle_time"


# In-memory storage
playbooks = {}
playbook_steps = {}
playbook_enrollments = {}
playbook_analytics = {}


class PlaybookCreate(BaseModel):
    name: str
    type: PlaybookType
    description: Optional[str] = None
    target_persona: Optional[str] = None
    target_industry: Optional[str] = None
    entry_criteria: Optional[Dict[str, Any]] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    owner_id: Optional[str] = None


class PlaybookStepCreate(BaseModel):
    playbook_id: str
    step_type: StepType
    order: int
    title: str
    content: Optional[str] = None
    template_id: Optional[str] = None
    delay_days: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None


class EnrollmentCreate(BaseModel):
    playbook_id: str
    prospect_id: str
    prospect_data: Optional[Dict[str, Any]] = None


# Playbooks
@router.post("/playbooks")
async def create_playbook(
    request: PlaybookCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new playbook"""
    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    playbook = {
        "id": playbook_id,
        "name": request.name,
        "type": request.type.value,
        "description": request.description,
        "target_persona": request.target_persona,
        "target_industry": request.target_industry,
        "entry_criteria": request.entry_criteria or {},
        "exit_criteria": request.exit_criteria or {},
        "owner_id": request.owner_id,
        "status": PlaybookStatus.DRAFT.value,
        "steps_count": 0,
        "enrollments_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    playbooks[playbook_id] = playbook
    
    return playbook


@router.get("/playbooks")
async def list_playbooks(
    type: Optional[PlaybookType] = None,
    status: Optional[PlaybookStatus] = None,
    owner_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List playbooks"""
    result = [p for p in playbooks.values() if p.get("tenant_id") == tenant_id]
    
    if type:
        result = [p for p in result if p.get("type") == type.value]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if owner_id:
        result = [p for p in result if p.get("owner_id") == owner_id]
    
    return {"playbooks": result, "total": len(result)}


@router.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str):
    """Get playbook with steps"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    playbook = playbooks[playbook_id].copy()
    
    # Add steps
    steps = [s for s in playbook_steps.values() if s.get("playbook_id") == playbook_id]
    steps.sort(key=lambda x: x.get("order", 0))
    playbook["steps"] = steps
    
    # Add analytics
    playbook["analytics"] = {
        "total_enrollments": random.randint(50, 500),
        "active_enrollments": random.randint(10, 100),
        "completed": random.randint(30, 300),
        "response_rate": round(random.uniform(0.15, 0.45), 3),
        "meeting_rate": round(random.uniform(0.05, 0.25), 3),
        "avg_completion_days": random.randint(7, 30)
    }
    
    return playbook


@router.put("/playbooks/{playbook_id}")
async def update_playbook(
    playbook_id: str,
    request: PlaybookCreate
):
    """Update a playbook"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    playbook = playbooks[playbook_id]
    playbook.update({
        "name": request.name,
        "type": request.type.value,
        "description": request.description,
        "target_persona": request.target_persona,
        "target_industry": request.target_industry,
        "entry_criteria": request.entry_criteria or {},
        "exit_criteria": request.exit_criteria or {},
        "owner_id": request.owner_id,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return playbook


@router.post("/playbooks/{playbook_id}/publish")
async def publish_playbook(playbook_id: str):
    """Publish a playbook"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    playbook = playbooks[playbook_id]
    playbook["status"] = PlaybookStatus.PUBLISHED.value
    playbook["published_at"] = datetime.utcnow().isoformat()
    
    return playbook


@router.post("/playbooks/{playbook_id}/clone")
async def clone_playbook(
    playbook_id: str,
    new_name: str = Query(...)
):
    """Clone a playbook"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    original = playbooks[playbook_id]
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    cloned = original.copy()
    cloned.update({
        "id": new_id,
        "name": new_name,
        "status": PlaybookStatus.DRAFT.value,
        "enrollments_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "cloned_from": playbook_id
    })
    
    playbooks[new_id] = cloned
    
    # Clone steps too
    for step in playbook_steps.values():
        if step.get("playbook_id") == playbook_id:
            new_step = step.copy()
            new_step["id"] = str(uuid.uuid4())
            new_step["playbook_id"] = new_id
            playbook_steps[new_step["id"]] = new_step
    
    return cloned


# Steps
@router.post("/steps")
async def create_step(
    request: PlaybookStepCreate,
    tenant_id: str = Query(default="default")
):
    """Add a step to a playbook"""
    step_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    step = {
        "id": step_id,
        "playbook_id": request.playbook_id,
        "step_type": request.step_type.value,
        "order": request.order,
        "title": request.title,
        "content": request.content,
        "template_id": request.template_id,
        "delay_days": request.delay_days,
        "conditions": request.conditions or {},
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    playbook_steps[step_id] = step
    
    # Update playbook step count
    if request.playbook_id in playbooks:
        playbooks[request.playbook_id]["steps_count"] = len(
            [s for s in playbook_steps.values() if s.get("playbook_id") == request.playbook_id]
        )
    
    return step


@router.get("/playbooks/{playbook_id}/steps")
async def list_playbook_steps(playbook_id: str):
    """List steps for a playbook"""
    steps = [s for s in playbook_steps.values() if s.get("playbook_id") == playbook_id]
    steps.sort(key=lambda x: x.get("order", 0))
    return {"steps": steps, "total": len(steps)}


@router.put("/steps/{step_id}")
async def update_step(
    step_id: str,
    request: PlaybookStepCreate
):
    """Update a step"""
    if step_id not in playbook_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    step = playbook_steps[step_id]
    step.update({
        "step_type": request.step_type.value,
        "order": request.order,
        "title": request.title,
        "content": request.content,
        "template_id": request.template_id,
        "delay_days": request.delay_days,
        "conditions": request.conditions or {},
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return step


@router.delete("/steps/{step_id}")
async def delete_step(step_id: str):
    """Delete a step"""
    if step_id not in playbook_steps:
        raise HTTPException(status_code=404, detail="Step not found")
    
    del playbook_steps[step_id]
    return {"status": "deleted", "id": step_id}


@router.put("/playbooks/{playbook_id}/reorder-steps")
async def reorder_steps(
    playbook_id: str,
    step_order: List[str] = Query(...)
):
    """Reorder playbook steps"""
    for i, step_id in enumerate(step_order):
        if step_id in playbook_steps:
            playbook_steps[step_id]["order"] = i + 1
    
    return {"status": "reordered", "playbook_id": playbook_id}


# Enrollments
@router.post("/enrollments")
async def enroll_prospect(
    request: EnrollmentCreate,
    tenant_id: str = Query(default="default")
):
    """Enroll a prospect in a playbook"""
    enrollment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    enrollment = {
        "id": enrollment_id,
        "playbook_id": request.playbook_id,
        "prospect_id": request.prospect_id,
        "prospect_data": request.prospect_data or {},
        "status": "active",
        "current_step": 1,
        "steps_completed": 0,
        "started_at": now.isoformat(),
        "last_activity": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    playbook_enrollments[enrollment_id] = enrollment
    
    # Update playbook enrollment count
    if request.playbook_id in playbooks:
        playbooks[request.playbook_id]["enrollments_count"] = len(
            [e for e in playbook_enrollments.values() if e.get("playbook_id") == request.playbook_id]
        )
    
    return enrollment


@router.get("/playbooks/{playbook_id}/enrollments")
async def list_playbook_enrollments(
    playbook_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """List enrollments for a playbook"""
    result = [e for e in playbook_enrollments.values() if e.get("playbook_id") == playbook_id]
    
    if status:
        result = [e for e in result if e.get("status") == status]
    
    result.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"enrollments": result[:limit], "total": len(result)}


@router.put("/enrollments/{enrollment_id}/advance")
async def advance_enrollment(enrollment_id: str):
    """Advance enrollment to next step"""
    if enrollment_id not in playbook_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = playbook_enrollments[enrollment_id]
    enrollment["current_step"] += 1
    enrollment["steps_completed"] += 1
    enrollment["last_activity"] = datetime.utcnow().isoformat()
    
    return enrollment


@router.put("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str):
    """Pause an enrollment"""
    if enrollment_id not in playbook_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = playbook_enrollments[enrollment_id]
    enrollment["status"] = "paused"
    enrollment["paused_at"] = datetime.utcnow().isoformat()
    
    return enrollment


@router.put("/enrollments/{enrollment_id}/complete")
async def complete_enrollment(
    enrollment_id: str,
    outcome: str = Query(...)
):
    """Complete an enrollment"""
    if enrollment_id not in playbook_enrollments:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment = playbook_enrollments[enrollment_id]
    enrollment["status"] = "completed"
    enrollment["completed_at"] = datetime.utcnow().isoformat()
    enrollment["outcome"] = outcome
    
    return enrollment


# Templates
@router.get("/templates")
async def list_playbook_templates(
    type: Optional[PlaybookType] = None,
    tenant_id: str = Query(default="default")
):
    """List playbook templates"""
    templates = [
        {
            "id": "tpl_outbound_basic",
            "name": "Basic Outbound Sequence",
            "type": "outbound",
            "description": "5-touch outbound sequence for cold prospects",
            "steps_count": 5,
            "avg_performance": {"response_rate": 0.18, "meeting_rate": 0.08}
        },
        {
            "id": "tpl_enterprise_outreach",
            "name": "Enterprise Multi-Threading",
            "type": "outbound",
            "description": "10-touch multi-stakeholder enterprise sequence",
            "steps_count": 10,
            "avg_performance": {"response_rate": 0.25, "meeting_rate": 0.12}
        },
        {
            "id": "tpl_inbound_follow",
            "name": "Inbound Lead Follow-up",
            "type": "inbound",
            "description": "Quick follow-up for inbound leads",
            "steps_count": 4,
            "avg_performance": {"response_rate": 0.45, "meeting_rate": 0.25}
        },
        {
            "id": "tpl_renewal",
            "name": "Renewal Playbook",
            "type": "renewal",
            "description": "90-day renewal sequence",
            "steps_count": 8,
            "avg_performance": {"response_rate": 0.65, "meeting_rate": 0.40}
        },
        {
            "id": "tpl_competitive",
            "name": "Competitive Displacement",
            "type": "competitive",
            "description": "Win against specific competitors",
            "steps_count": 7,
            "avg_performance": {"response_rate": 0.22, "meeting_rate": 0.10}
        }
    ]
    
    if type:
        templates = [t for t in templates if t["type"] == type.value]
    
    return {"templates": templates}


# Analytics
@router.get("/playbooks/{playbook_id}/analytics")
async def get_playbook_analytics(
    playbook_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get playbook performance analytics"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    # Step performance
    steps = [s for s in playbook_steps.values() if s.get("playbook_id") == playbook_id]
    step_analytics = []
    
    for step in sorted(steps, key=lambda x: x.get("order", 0)):
        step_analytics.append({
            "step_id": step["id"],
            "step_order": step.get("order"),
            "step_type": step.get("step_type"),
            "sent_count": random.randint(100, 500),
            "response_count": random.randint(10, 100),
            "response_rate": round(random.uniform(0.05, 0.35), 3),
            "drop_off_rate": round(random.uniform(0.05, 0.20), 3)
        })
    
    return {
        "playbook_id": playbook_id,
        "period_days": days,
        "overview": {
            "total_enrollments": random.randint(100, 1000),
            "active": random.randint(20, 200),
            "completed": random.randint(50, 500),
            "paused": random.randint(10, 50),
            "avg_time_to_complete_days": random.randint(10, 30)
        },
        "performance": {
            "response_rate": round(random.uniform(0.15, 0.40), 3),
            "meeting_rate": round(random.uniform(0.05, 0.20), 3),
            "conversion_rate": round(random.uniform(0.02, 0.15), 3)
        },
        "step_analytics": step_analytics
    }


@router.get("/analytics/comparison")
async def compare_playbooks(
    playbook_ids: List[str] = Query(...),
    metric: PlaybookMetric = Query(default=PlaybookMetric.RESPONSE_RATE)
):
    """Compare multiple playbooks"""
    comparison = []
    
    for pid in playbook_ids:
        if pid in playbooks:
            comparison.append({
                "playbook_id": pid,
                "playbook_name": playbooks[pid].get("name"),
                "metric_value": round(random.uniform(0.1, 0.5), 3),
                "enrollments": random.randint(50, 500),
                "trend": random.choice(["up", "down", "stable"])
            })
    
    comparison.sort(key=lambda x: x["metric_value"], reverse=True)
    
    return {
        "metric": metric.value,
        "comparison": comparison,
        "best_performing": comparison[0]["playbook_id"] if comparison else None
    }


@router.get("/analytics/overview")
async def get_playbooks_overview(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get overview analytics for all playbooks"""
    return {
        "period_days": days,
        "summary": {
            "total_playbooks": len([p for p in playbooks.values() if p.get("tenant_id") == tenant_id]),
            "active_playbooks": len([p for p in playbooks.values() if p.get("status") == "published" and p.get("tenant_id") == tenant_id]),
            "total_enrollments": random.randint(500, 5000),
            "active_enrollments": random.randint(100, 1000)
        },
        "top_performers": [
            {"playbook": "Enterprise Outbound", "response_rate": round(random.uniform(0.20, 0.35), 3)},
            {"playbook": "Inbound Follow-up", "response_rate": round(random.uniform(0.35, 0.50), 3)},
            {"playbook": "Renewal Sequence", "response_rate": round(random.uniform(0.50, 0.70), 3)}
        ],
        "conversion_funnel": {
            "enrolled": 1000,
            "responded": random.randint(150, 300),
            "meetings": random.randint(50, 150),
            "opportunities": random.randint(20, 80),
            "won": random.randint(5, 30)
        }
    }
