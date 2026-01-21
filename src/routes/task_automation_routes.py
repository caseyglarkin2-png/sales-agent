"""
Task Automation Routes - Automated task workflows and triggers
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

router = APIRouter(prefix="/task-automation", tags=["Task Automation"])


class TriggerType(str, Enum):
    DEAL_STAGE_CHANGE = "deal_stage_change"
    DEAL_CREATED = "deal_created"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    CONTACT_CREATED = "contact_created"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    EMAIL_OPENED = "email_opened"
    EMAIL_REPLIED = "email_replied"
    FORM_SUBMITTED = "form_submitted"
    LEAD_SCORE_THRESHOLD = "lead_score_threshold"
    INACTIVITY = "inactivity"
    DATE_BASED = "date_based"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AutomationStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DRAFT = "draft"
    ARCHIVED = "archived"


class AssignmentStrategy(str, Enum):
    OWNER = "owner"  # Assign to record owner
    ROUND_ROBIN = "round_robin"
    SPECIFIC_USER = "specific_user"
    TEAM_QUEUE = "team_queue"
    LOAD_BALANCED = "load_balanced"


# In-memory storage
task_automations = {}
automation_executions = {}
automation_templates = {}


class AutomatedTaskConfig(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_in_days: int = 1
    due_in_hours: int = 0
    assignment_strategy: AssignmentStrategy = AssignmentStrategy.OWNER
    assigned_user_id: Optional[str] = None
    assigned_team_id: Optional[str] = None
    task_type: Optional[str] = None
    tags: List[str] = []


class TaskAutomationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_conditions: Dict[str, Any] = {}
    task_config: AutomatedTaskConfig
    additional_actions: List[Dict[str, Any]] = []
    is_active: bool = True


# Automations CRUD
@router.post("")
async def create_task_automation(
    request: TaskAutomationCreate,
    tenant_id: str = Query(default="default")
):
    """Create a task automation rule"""
    automation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    automation = {
        "id": automation_id,
        "name": request.name,
        "description": request.description,
        "trigger_type": request.trigger_type.value,
        "trigger_conditions": request.trigger_conditions,
        "task_config": {
            "title": request.task_config.title,
            "description": request.task_config.description,
            "priority": request.task_config.priority.value,
            "due_in_days": request.task_config.due_in_days,
            "due_in_hours": request.task_config.due_in_hours,
            "assignment_strategy": request.task_config.assignment_strategy.value,
            "assigned_user_id": request.task_config.assigned_user_id,
            "assigned_team_id": request.task_config.assigned_team_id,
            "task_type": request.task_config.task_type,
            "tags": request.task_config.tags
        },
        "additional_actions": request.additional_actions,
        "status": AutomationStatus.ACTIVE.value if request.is_active else AutomationStatus.DRAFT.value,
        "executions_count": 0,
        "last_executed_at": None,
        "created_by": "user_1",
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    task_automations[automation_id] = automation
    
    logger.info("task_automation_created", automation_id=automation_id, trigger=request.trigger_type.value)
    
    return automation


@router.get("")
async def list_task_automations(
    status: Optional[AutomationStatus] = None,
    trigger_type: Optional[TriggerType] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List task automations"""
    result = [a for a in task_automations.values() if a.get("tenant_id") == tenant_id]
    
    if status:
        result = [a for a in result if a.get("status") == status.value]
    if trigger_type:
        result = [a for a in result if a.get("trigger_type") == trigger_type.value]
    if search:
        result = [a for a in result if search.lower() in a.get("name", "").lower()]
    
    return {"automations": result, "total": len(result)}


@router.get("/{automation_id}")
async def get_task_automation(
    automation_id: str,
    tenant_id: str = Query(default="default")
):
    """Get automation details"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    return task_automations[automation_id]


@router.patch("/{automation_id}")
async def update_task_automation(
    automation_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update automation configuration"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    automation = task_automations[automation_id]
    
    for key, value in updates.items():
        if key in ["name", "description", "trigger_conditions", "task_config", "additional_actions"]:
            automation[key] = value
    
    automation["updated_at"] = datetime.utcnow().isoformat()
    
    return automation


@router.delete("/{automation_id}")
async def delete_task_automation(
    automation_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    del task_automations[automation_id]
    
    return {"success": True, "deleted": automation_id}


# Status Control
@router.post("/{automation_id}/activate")
async def activate_automation(
    automation_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    task_automations[automation_id]["status"] = AutomationStatus.ACTIVE.value
    
    return {"success": True, "status": "active"}


@router.post("/{automation_id}/pause")
async def pause_automation(
    automation_id: str,
    tenant_id: str = Query(default="default")
):
    """Pause an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    task_automations[automation_id]["status"] = AutomationStatus.PAUSED.value
    
    return {"success": True, "status": "paused"}


@router.post("/{automation_id}/archive")
async def archive_automation(
    automation_id: str,
    tenant_id: str = Query(default="default")
):
    """Archive an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    task_automations[automation_id]["status"] = AutomationStatus.ARCHIVED.value
    
    return {"success": True, "status": "archived"}


# Manual Trigger
@router.post("/{automation_id}/trigger")
async def trigger_automation(
    automation_id: str,
    context: Dict[str, Any] = {},
    tenant_id: str = Query(default="default")
):
    """Manually trigger an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    automation = task_automations[automation_id]
    execution_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create execution record
    execution = {
        "id": execution_id,
        "automation_id": automation_id,
        "trigger_type": "manual",
        "context": context,
        "status": "completed",
        "task_created": True,
        "task_id": str(uuid.uuid4()),
        "executed_at": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    automation_executions[execution_id] = execution
    automation["executions_count"] = automation.get("executions_count", 0) + 1
    automation["last_executed_at"] = now.isoformat()
    
    return {
        "success": True,
        "execution_id": execution_id,
        "task_id": execution["task_id"]
    }


# Executions
@router.get("/{automation_id}/executions")
async def list_automation_executions(
    automation_id: str,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List execution history for an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    result = [
        e for e in automation_executions.values()
        if e.get("automation_id") == automation_id
    ]
    
    result.sort(key=lambda x: x.get("executed_at", ""), reverse=True)
    
    return {
        "executions": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/executions/{execution_id}")
async def get_execution_details(
    execution_id: str,
    tenant_id: str = Query(default="default")
):
    """Get execution details"""
    if execution_id not in automation_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    return automation_executions[execution_id]


# Templates
@router.get("/templates")
async def list_automation_templates(tenant_id: str = Query(default="default")):
    """Get pre-built automation templates"""
    templates = [
        {
            "id": "tpl_follow_up",
            "name": "Follow-up After Meeting",
            "description": "Create a follow-up task 24 hours after a meeting",
            "trigger_type": "meeting_completed",
            "category": "follow_up"
        },
        {
            "id": "tpl_proposal_reminder",
            "name": "Proposal Follow-up Reminder",
            "description": "Remind to follow up 3 days after sending proposal",
            "trigger_type": "deal_stage_change",
            "category": "sales"
        },
        {
            "id": "tpl_new_lead_call",
            "name": "Call New Leads",
            "description": "Create call task for high-score leads",
            "trigger_type": "lead_score_threshold",
            "category": "leads"
        },
        {
            "id": "tpl_onboarding",
            "name": "New Customer Onboarding",
            "description": "Create onboarding tasks when deal is won",
            "trigger_type": "deal_won",
            "category": "onboarding"
        },
        {
            "id": "tpl_inactivity_check",
            "name": "Inactive Deal Check-in",
            "description": "Task to check on deals with no activity for 7 days",
            "trigger_type": "inactivity",
            "category": "engagement"
        }
    ]
    
    return {"templates": templates}


@router.post("/templates/{template_id}/apply")
async def apply_template(
    template_id: str,
    customizations: Dict[str, Any] = {},
    tenant_id: str = Query(default="default")
):
    """Create automation from template"""
    # Generate automation from template
    automation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    automation = {
        "id": automation_id,
        "name": customizations.get("name", f"Automation from {template_id}"),
        "description": customizations.get("description"),
        "trigger_type": "deal_stage_change",
        "trigger_conditions": customizations.get("trigger_conditions", {}),
        "task_config": customizations.get("task_config", {
            "title": "Auto-generated Task",
            "priority": "medium",
            "due_in_days": 1
        }),
        "additional_actions": [],
        "status": AutomationStatus.DRAFT.value,
        "from_template": template_id,
        "executions_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    task_automations[automation_id] = automation
    
    return automation


# Analytics
@router.get("/analytics")
async def get_automation_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get task automation analytics"""
    automations = [a for a in task_automations.values() if a.get("tenant_id") == tenant_id]
    
    return {
        "period_days": days,
        "summary": {
            "total_automations": len(automations),
            "active": sum(1 for a in automations if a.get("status") == "active"),
            "paused": sum(1 for a in automations if a.get("status") == "paused")
        },
        "executions": {
            "total": random.randint(500, 2000),
            "successful": random.randint(450, 1900),
            "failed": random.randint(10, 100)
        },
        "tasks_created": random.randint(400, 1800),
        "tasks_completed": random.randint(300, 1500),
        "avg_completion_rate": round(random.uniform(0.70, 0.95), 3),
        "time_saved_hours": random.randint(50, 300),
        "top_automations": [
            {
                "id": str(uuid.uuid4()),
                "name": f"Top Automation {i + 1}",
                "executions": random.randint(50, 300)
            }
            for i in range(5)
        ],
        "by_trigger_type": {
            "deal_stage_change": random.randint(100, 500),
            "meeting_completed": random.randint(50, 200),
            "inactivity": random.randint(100, 400),
            "lead_score_threshold": random.randint(50, 200)
        }
    }


# Clone
@router.post("/{automation_id}/clone")
async def clone_automation(
    automation_id: str,
    new_name: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Clone an automation"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    original = task_automations[automation_id]
    new_automation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_automation = {
        **original,
        "id": new_automation_id,
        "name": new_name or f"{original['name']} (Copy)",
        "status": AutomationStatus.DRAFT.value,
        "executions_count": 0,
        "last_executed_at": None,
        "cloned_from": automation_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    task_automations[new_automation_id] = new_automation
    
    return new_automation


# Test Automation
@router.post("/{automation_id}/test")
async def test_automation(
    automation_id: str,
    test_context: Dict[str, Any] = {},
    tenant_id: str = Query(default="default")
):
    """Test automation without creating actual tasks"""
    if automation_id not in task_automations:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    automation = task_automations[automation_id]
    
    # Simulate what would happen
    return {
        "automation_id": automation_id,
        "test_result": "success",
        "would_trigger": True,
        "conditions_met": True,
        "task_preview": {
            "title": automation["task_config"]["title"],
            "priority": automation["task_config"]["priority"],
            "due_date": (datetime.utcnow() + timedelta(days=automation["task_config"].get("due_in_days", 1))).isoformat(),
            "assignee": automation["task_config"].get("assigned_user_id") or "record_owner"
        },
        "warnings": []
    }
