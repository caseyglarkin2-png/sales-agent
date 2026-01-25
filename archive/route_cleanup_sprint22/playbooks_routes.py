"""
Playbook Routes - Playbook API Endpoints
=========================================
RESTful API for sales playbook management.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.playbooks import PlaybookService, get_playbook_service


router = APIRouter(prefix="/playbooks", tags=["Playbooks"])


# Request/Response Models
class CreatePlaybookRequest(BaseModel):
    name: str
    description: str
    category: str = "general"
    deal_stages: list[str] = []
    segments: list[str] = []
    industries: list[str] = []
    trigger_type: str = "manual"
    estimated_duration_days: int = 7
    owner_id: Optional[str] = None


class UpdatePlaybookRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    deal_stages: Optional[list[str]] = None
    segments: Optional[list[str]] = None
    industries: Optional[list[str]] = None
    estimated_duration_days: Optional[int] = None


class AddStepRequest(BaseModel):
    name: str
    description: str
    step_type: str
    order: Optional[int] = None
    instructions: str = ""
    delay_days: int = 0
    due_in_days: int = 1
    outcomes: list[str] = []
    required: bool = True
    email_template_id: Optional[str] = None


class UpdateStepRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    delay_days: Optional[int] = None
    due_in_days: Optional[int] = None
    outcomes: Optional[list[str]] = None


class ReorderStepsRequest(BaseModel):
    step_order: list[str]


class StartExecutionRequest(BaseModel):
    playbook_id: str
    deal_id: str
    user_id: str


class CompleteStepRequest(BaseModel):
    step_id: str
    outcome: Optional[str] = None
    notes: str = ""


class SkipStepRequest(BaseModel):
    step_id: str
    reason: str = ""


class AbandonExecutionRequest(BaseModel):
    reason: str = ""


# Helper
def get_service() -> PlaybookService:
    return get_playbook_service()


# Playbook CRUD endpoints
@router.post("")
async def create_playbook(request: CreatePlaybookRequest):
    """Create a playbook."""
    service = get_service()
    from src.playbooks.playbook_service import TriggerType
    
    playbook = await service.create_playbook(
        name=request.name,
        description=request.description,
        category=request.category,
        deal_stages=request.deal_stages,
        segments=request.segments,
        industries=request.industries,
        trigger_type=TriggerType(request.trigger_type),
        estimated_duration_days=request.estimated_duration_days,
        owner_id=request.owner_id,
    )
    
    return {"playbook": playbook}


@router.get("")
async def list_playbooks(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    deal_stage: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List playbooks."""
    service = get_service()
    from src.playbooks.playbook_service import PlaybookStatus
    
    status_enum = PlaybookStatus(status) if status else None
    playbooks = await service.list_playbooks(
        category=category,
        status=status_enum,
        deal_stage=deal_stage,
        limit=limit,
    )
    
    return {"playbooks": playbooks, "count": len(playbooks)}


@router.get("/recommended")
async def get_recommended(
    deal_stage: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    limit: int = Query(5, le=20)
):
    """Get recommended playbooks."""
    service = get_service()
    playbooks = await service.get_recommended_playbooks(
        deal_stage=deal_stage,
        industry=industry,
        segment=segment,
        limit=limit,
    )
    
    return {"playbooks": playbooks, "count": len(playbooks)}


@router.get("/{playbook_id}")
async def get_playbook(playbook_id: str):
    """Get a playbook."""
    service = get_service()
    playbook = await service.get_playbook(playbook_id)
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return {"playbook": playbook}


@router.put("/{playbook_id}")
async def update_playbook(playbook_id: str, request: UpdatePlaybookRequest):
    """Update a playbook."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    playbook = await service.update_playbook(playbook_id, updates)
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return {"playbook": playbook}


@router.delete("/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a playbook."""
    service = get_service()
    success = await service.delete_playbook(playbook_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return {"deleted": True}


@router.post("/{playbook_id}/publish")
async def publish_playbook(playbook_id: str):
    """Publish a playbook."""
    service = get_service()
    success = await service.publish_playbook(playbook_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot publish playbook")
    
    playbook = await service.get_playbook(playbook_id)
    return {"playbook": playbook}


@router.post("/{playbook_id}/archive")
async def archive_playbook(playbook_id: str):
    """Archive a playbook."""
    service = get_service()
    success = await service.archive_playbook(playbook_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot archive playbook")
    
    playbook = await service.get_playbook(playbook_id)
    return {"playbook": playbook}


# Step endpoints
@router.post("/{playbook_id}/steps")
async def add_step(playbook_id: str, request: AddStepRequest):
    """Add a step to a playbook."""
    service = get_service()
    from src.playbooks.playbook_service import StepType
    
    step = await service.add_step(
        playbook_id=playbook_id,
        name=request.name,
        description=request.description,
        step_type=StepType(request.step_type),
        order=request.order,
        instructions=request.instructions,
        delay_days=request.delay_days,
        due_in_days=request.due_in_days,
        outcomes=request.outcomes,
        required=request.required,
        email_template_id=request.email_template_id,
    )
    
    if not step:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return {"step": step}


@router.put("/{playbook_id}/steps/{step_id}")
async def update_step(playbook_id: str, step_id: str, request: UpdateStepRequest):
    """Update a step."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    step = await service.update_step(playbook_id, step_id, updates)
    
    if not step:
        raise HTTPException(status_code=404, detail="Playbook or step not found")
    
    return {"step": step}


@router.delete("/{playbook_id}/steps/{step_id}")
async def remove_step(playbook_id: str, step_id: str):
    """Remove a step from a playbook."""
    service = get_service()
    success = await service.remove_step(playbook_id, step_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Playbook or step not found")
    
    return {"deleted": True}


@router.post("/{playbook_id}/steps/reorder")
async def reorder_steps(playbook_id: str, request: ReorderStepsRequest):
    """Reorder playbook steps."""
    service = get_service()
    success = await service.reorder_steps(playbook_id, request.step_order)
    
    if not success:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    playbook = await service.get_playbook(playbook_id)
    return {"playbook": playbook}


# Execution endpoints
@router.post("/executions")
async def start_execution(request: StartExecutionRequest):
    """Start a playbook execution."""
    service = get_service()
    execution = await service.start_execution(
        playbook_id=request.playbook_id,
        deal_id=request.deal_id,
        user_id=request.user_id,
    )
    
    if not execution:
        raise HTTPException(status_code=400, detail="Cannot start execution")
    
    return {"execution": execution}


@router.get("/executions")
async def list_executions(
    playbook_id: Optional[str] = Query(None),
    deal_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List executions."""
    service = get_service()
    executions = await service.list_executions(
        playbook_id=playbook_id,
        deal_id=deal_id,
        user_id=user_id,
        status=status,
        limit=limit,
    )
    
    return {"executions": executions, "count": len(executions)}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get an execution."""
    service = get_service()
    execution = await service.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {"execution": execution}


@router.post("/executions/{execution_id}/complete-step")
async def complete_step(execution_id: str, request: CompleteStepRequest):
    """Complete a step in an execution."""
    service = get_service()
    success = await service.complete_step(
        execution_id=execution_id,
        step_id=request.step_id,
        outcome=request.outcome,
        notes=request.notes,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot complete step")
    
    execution = await service.get_execution(execution_id)
    return {"execution": execution}


@router.post("/executions/{execution_id}/skip-step")
async def skip_step(execution_id: str, request: SkipStepRequest):
    """Skip a step in an execution."""
    service = get_service()
    success = await service.skip_step(
        execution_id=execution_id,
        step_id=request.step_id,
        reason=request.reason,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot skip step")
    
    execution = await service.get_execution(execution_id)
    return {"execution": execution}


@router.post("/executions/{execution_id}/pause")
async def pause_execution(execution_id: str):
    """Pause an execution."""
    service = get_service()
    success = await service.pause_execution(execution_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause execution")
    
    execution = await service.get_execution(execution_id)
    return {"execution": execution}


@router.post("/executions/{execution_id}/resume")
async def resume_execution(execution_id: str):
    """Resume a paused execution."""
    service = get_service()
    success = await service.resume_execution(execution_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume execution")
    
    execution = await service.get_execution(execution_id)
    return {"execution": execution}


@router.post("/executions/{execution_id}/abandon")
async def abandon_execution(execution_id: str, request: AbandonExecutionRequest):
    """Abandon an execution."""
    service = get_service()
    success = await service.abandon_execution(
        execution_id=execution_id,
        reason=request.reason,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot abandon execution")
    
    execution = await service.get_execution(execution_id)
    return {"execution": execution}


# Analytics
@router.get("/{playbook_id}/analytics")
async def get_playbook_analytics(playbook_id: str):
    """Get playbook analytics."""
    service = get_service()
    analytics = await service.get_playbook_analytics(playbook_id)
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return analytics
