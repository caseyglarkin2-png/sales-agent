"""
Tasks API Routes
================
Endpoints for managing sales tasks and follow-ups.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import structlog

from src.tasks import (
    get_task_service,
    TaskType,
    TaskPriority,
    TaskStatus,
)
from src.tasks.task_service import RecurrencePattern

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    title: str
    task_type: str
    priority: str = "medium"
    description: str = ""
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    deal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    tags: list[str] = []


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class CompleteTaskRequest(BaseModel):
    notes: str = ""


class CreateFollowUpRequest(BaseModel):
    contact_id: str
    contact_name: str
    days_from_now: int = 3
    title: Optional[str] = None
    task_type: str = "follow_up"
    notes: str = ""


class BulkUpdateRequest(BaseModel):
    task_ids: list[str]
    updates: dict


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    contact_id: Optional[str] = None,
    company_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    overdue_only: bool = False,
    due_today: bool = False,
    due_this_week: bool = False,
    tags: Optional[str] = None,
):
    """List all tasks with optional filters."""
    service = get_task_service()
    
    # Parse enums
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    type_filter = None
    if task_type:
        try:
            type_filter = TaskType(task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")
    
    priority_filter = None
    if priority:
        try:
            priority_filter = TaskPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    
    tag_list = tags.split(",") if tags else None
    
    tasks = service.list_tasks(
        status=status_filter,
        task_type=type_filter,
        priority=priority_filter,
        assigned_to=assigned_to,
        contact_id=contact_id,
        company_id=company_id,
        deal_id=deal_id,
        overdue_only=overdue_only,
        due_today=due_today,
        due_this_week=due_this_week,
        tags=tag_list,
    )
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks),
    }


@router.post("")
async def create_task(request: CreateTaskRequest):
    """Create a new task."""
    service = get_task_service()
    
    try:
        task_type = TaskType(request.task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {request.task_type}")
    
    try:
        priority = TaskPriority(request.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")
    
    recurrence = None
    if request.recurrence_pattern:
        try:
            recurrence = RecurrencePattern(request.recurrence_pattern)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid recurrence: {request.recurrence_pattern}")
    
    task = service.create_task(
        title=request.title,
        task_type=task_type,
        priority=priority,
        description=request.description,
        due_date=request.due_date,
        due_time=request.due_time,
        contact_id=request.contact_id,
        contact_name=request.contact_name,
        company_id=request.company_id,
        company_name=request.company_name,
        deal_id=request.deal_id,
        assigned_to=request.assigned_to,
        assigned_to_name=request.assigned_to_name,
        is_recurring=request.is_recurring,
        recurrence_pattern=recurrence,
        tags=request.tags,
    )
    
    return {
        "message": "Task created",
        "task": task.to_dict(),
    }


@router.get("/stats")
async def get_task_stats(assigned_to: Optional[str] = None):
    """Get task statistics."""
    service = get_task_service()
    return service.get_task_stats(assigned_to=assigned_to)


@router.get("/reminders")
async def get_upcoming_reminders(hours: int = Query(24, ge=1, le=168)):
    """Get tasks with reminders in the next N hours."""
    service = get_task_service()
    
    tasks = service.get_upcoming_reminders(hours=hours)
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks),
    }


@router.get("/types")
async def list_task_types():
    """List available task types."""
    return {
        "types": [{"value": t.value, "name": t.name} for t in TaskType]
    }


@router.get("/priorities")
async def list_priorities():
    """List available priorities."""
    return {
        "priorities": [{"value": p.value, "name": p.name} for p in TaskPriority]
    }


@router.get("/statuses")
async def list_statuses():
    """List available statuses."""
    return {
        "statuses": [{"value": s.value, "name": s.name} for s in TaskStatus]
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a task by ID."""
    service = get_task_service()
    task = service.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"task": task.to_dict()}


@router.put("/{task_id}")
async def update_task(task_id: str, request: UpdateTaskRequest):
    """Update a task."""
    service = get_task_service()
    
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.description is not None:
        updates["description"] = request.description
    if request.due_date is not None:
        updates["due_date"] = request.due_date
    if request.due_time is not None:
        updates["due_time"] = request.due_time
    if request.assigned_to is not None:
        updates["assigned_to"] = request.assigned_to
    if request.assigned_to_name is not None:
        updates["assigned_to_name"] = request.assigned_to_name
    if request.notes is not None:
        updates["notes"] = request.notes
    if request.tags is not None:
        updates["tags"] = request.tags
    
    if request.priority is not None:
        try:
            updates["priority"] = TaskPriority(request.priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")
    
    if request.status is not None:
        try:
            updates["status"] = TaskStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    task = service.update_task(task_id, updates)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "message": "Task updated",
        "task": task.to_dict(),
    }


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, request: CompleteTaskRequest):
    """Mark a task as completed."""
    service = get_task_service()
    
    task = service.complete_task(task_id, notes=request.notes)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "message": "Task completed",
        "task": task.to_dict(),
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    service = get_task_service()
    
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted"}


@router.post("/follow-up")
async def create_follow_up(request: CreateFollowUpRequest):
    """Create a follow-up task for a contact."""
    service = get_task_service()
    
    try:
        task_type = TaskType(request.task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {request.task_type}")
    
    task = service.create_follow_up(
        contact_id=request.contact_id,
        contact_name=request.contact_name,
        days_from_now=request.days_from_now,
        title=request.title,
        task_type=task_type,
        notes=request.notes,
    )
    
    return {
        "message": "Follow-up task created",
        "task": task.to_dict(),
    }


@router.post("/bulk-update")
async def bulk_update_tasks(request: BulkUpdateRequest):
    """Bulk update multiple tasks."""
    service = get_task_service()
    
    result = service.bulk_update(
        task_ids=request.task_ids,
        updates=request.updates,
    )
    
    return {
        "message": "Bulk update completed",
        **result,
    }
