"""API routes for workflow automation."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.workflows import (
    get_workflow_engine,
    StepType,
    TriggerType,
    ExecutionStatus,
)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    triggers: list[dict] = []


class AddStepRequest(BaseModel):
    name: str
    step_type: str
    config: dict = {}
    after_step_id: Optional[str] = None


class TriggerWorkflowRequest(BaseModel):
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    context: dict = {}


class ProcessEventRequest(BaseModel):
    type: str
    data: dict = {}


@router.get("/")
async def list_workflows(active_only: bool = True):
    """List all workflows."""
    engine = get_workflow_engine()
    workflows = engine.list_workflows(active_only=active_only)
    return {
        "workflows": [w.to_dict() for w in workflows],
        "total": len(workflows),
    }


@router.post("/")
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new workflow."""
    engine = get_workflow_engine()
    
    workflow = engine.create_workflow(
        name=request.name,
        description=request.description,
        triggers=request.triggers,
    )
    
    return {
        "message": "Workflow created",
        "workflow": workflow.to_dict(),
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow.to_dict()


@router.post("/{workflow_id}/steps")
async def add_step(workflow_id: str, request: AddStepRequest):
    """Add a step to a workflow."""
    engine = get_workflow_engine()
    
    try:
        step_type = StepType(request.step_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step type. Valid types: {[s.value for s in StepType]}"
        )
    
    try:
        step = engine.add_step_to_workflow(
            workflow_id=workflow_id,
            name=request.name,
            step_type=step_type,
            config=request.config,
            after_step_id=request.after_step_id,
        )
        
        return {
            "message": "Step added",
            "step": step.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workflow_id}/trigger")
async def trigger_workflow(workflow_id: str, request: TriggerWorkflowRequest):
    """Manually trigger a workflow."""
    engine = get_workflow_engine()
    
    try:
        execution = await engine.trigger_workflow(
            workflow_id=workflow_id,
            contact_id=request.contact_id,
            company_id=request.company_id,
            context=request.context,
        )
        
        return {
            "message": "Workflow triggered",
            "execution": execution.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    """Activate a workflow."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow.is_active = True
    return {"message": "Workflow activated", "workflow_id": workflow_id}


@router.post("/{workflow_id}/deactivate")
async def deactivate_workflow(workflow_id: str):
    """Deactivate a workflow."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow.is_active = False
    return {"message": "Workflow deactivated", "workflow_id": workflow_id}


@router.get("/executions/")
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    contact_id: Optional[str] = None,
):
    """List workflow executions."""
    engine = get_workflow_engine()
    
    exec_status = None
    if status:
        try:
            exec_status = ExecutionStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid: {[s.value for s in ExecutionStatus]}"
            )
    
    executions = engine.list_executions(
        workflow_id=workflow_id,
        status=exec_status,
        contact_id=contact_id,
    )
    
    return {
        "executions": [e.to_dict() for e in executions[:100]],  # Limit to 100
        "total": len(executions),
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get a specific execution."""
    engine = get_workflow_engine()
    execution = engine.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution.to_dict()


@router.post("/executions/{execution_id}/pause")
async def pause_execution(execution_id: str):
    """Pause an execution."""
    engine = get_workflow_engine()
    execution = engine.pause_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {"message": "Execution paused", "execution": execution.to_dict()}


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel an execution."""
    engine = get_workflow_engine()
    execution = engine.cancel_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {"message": "Execution cancelled", "execution": execution.to_dict()}


@router.post("/events")
async def process_event(request: ProcessEventRequest):
    """Process an event and trigger matching workflows."""
    engine = get_workflow_engine()
    
    event = {
        "type": request.type,
        "data": request.data,
    }
    
    executions = await engine.process_event(event)
    
    return {
        "message": f"Event processed, triggered {len(executions)} workflow(s)",
        "executions": [e.to_dict() for e in executions],
    }


@router.post("/resume-waiting")
async def resume_waiting_executions():
    """Resume executions that are past their wait time."""
    engine = get_workflow_engine()
    resumed = await engine.resume_waiting_executions()
    
    return {
        "message": f"Resumed {len(resumed)} execution(s)",
        "executions": [e.to_dict() for e in resumed],
    }


@router.get("/step-types")
async def list_step_types():
    """List available step types."""
    return {
        "step_types": [
            {
                "type": s.value,
                "name": s.name.replace("_", " ").title(),
            }
            for s in StepType
        ]
    }


@router.get("/trigger-types")
async def list_trigger_types():
    """List available trigger types."""
    return {
        "trigger_types": [
            {
                "type": t.value,
                "name": t.name.replace("_", " ").title(),
            }
            for t in TriggerType
        ]
    }
