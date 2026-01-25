"""
Workflow Automation V2 Routes - Advanced workflow builder and automation engine
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

router = APIRouter(prefix="/workflows-v2", tags=["Workflow Automation V2"])


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


class TriggerType(str, Enum):
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    FIELD_CHANGED = "field_changed"
    STAGE_CHANGED = "stage_changed"
    DATE_REACHED = "date_reached"
    TIME_BASED = "time_based"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    API_CALL = "api_call"
    FORM_SUBMISSION = "form_submission"
    EMAIL_EVENT = "email_event"


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    CREATE_TASK = "create_task"
    UPDATE_RECORD = "update_record"
    CREATE_RECORD = "create_record"
    DELETE_RECORD = "delete_record"
    ASSIGN_RECORD = "assign_record"
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    SEND_NOTIFICATION = "send_notification"
    CALL_WEBHOOK = "call_webhook"
    WAIT = "wait"
    CONDITION = "condition"
    SPLIT = "split"
    MERGE = "merge"
    LOOP = "loop"
    RUN_SCRIPT = "run_script"
    ENROLL_SEQUENCE = "enroll_sequence"
    SLACK_MESSAGE = "slack_message"


class ConditionOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class RecordType(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    LEAD = "lead"
    OPPORTUNITY = "opportunity"
    TASK = "task"
    DEAL = "deal"
    TICKET = "ticket"


# In-memory storage
workflows = {}
workflow_triggers = {}
workflow_actions = {}
workflow_executions = {}
execution_logs = {}
workflow_versions = {}
workflow_templates = {}
workflow_analytics = {}


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    object_type: RecordType
    is_template: bool = False
    tags: Optional[List[str]] = None


class TriggerCreate(BaseModel):
    workflow_id: str
    trigger_type: TriggerType
    conditions: Optional[List[Dict[str, Any]]] = None
    schedule: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class ActionCreate(BaseModel):
    workflow_id: str
    action_type: ActionType
    position: int
    config: Dict[str, Any]
    conditions: Optional[List[Dict[str, Any]]] = None
    parent_action_id: Optional[str] = None
    branch: Optional[str] = None


# Workflows
@router.post("/workflows")
async def create_workflow(
    request: WorkflowCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a workflow"""
    workflow_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    workflow = {
        "id": workflow_id,
        "name": request.name,
        "description": request.description,
        "object_type": request.object_type.value,
        "status": WorkflowStatus.DRAFT.value,
        "is_template": request.is_template,
        "tags": request.tags or [],
        "trigger_count": 0,
        "action_count": 0,
        "execution_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "version": 1,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    workflows[workflow_id] = workflow
    
    logger.info("workflow_created", workflow_id=workflow_id, name=request.name)
    return workflow


@router.get("/workflows")
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    object_type: Optional[RecordType] = None,
    is_template: Optional[bool] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List workflows"""
    result = [w for w in workflows.values() if w.get("tenant_id") == tenant_id]
    
    if status:
        result = [w for w in result if w.get("status") == status.value]
    if object_type:
        result = [w for w in result if w.get("object_type") == object_type.value]
    if is_template is not None:
        result = [w for w in result if w.get("is_template") == is_template]
    if search:
        search_lower = search.lower()
        result = [w for w in result if search_lower in w.get("name", "").lower()]
    
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return {"workflows": result, "total": len(result)}


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    triggers = [t for t in workflow_triggers.values() if t.get("workflow_id") == workflow_id]
    actions = [a for a in workflow_actions.values() if a.get("workflow_id") == workflow_id]
    actions.sort(key=lambda x: x.get("position", 0))
    
    return {
        **workflow,
        "triggers": triggers,
        "actions": actions,
        "flow": build_flow_structure(actions)
    }


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[WorkflowStatus] = None,
    tags: Optional[List[str]] = None
):
    """Update workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    now = datetime.utcnow()
    
    if name is not None:
        workflow["name"] = name
    if description is not None:
        workflow["description"] = description
    if status is not None:
        workflow["status"] = status.value
        if status == WorkflowStatus.ACTIVE:
            workflow["activated_at"] = now.isoformat()
    if tags is not None:
        workflow["tags"] = tags
    
    workflow["updated_at"] = now.isoformat()
    
    return workflow


@router.post("/workflows/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    """Activate a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    now = datetime.utcnow()
    
    # Validate workflow has at least one trigger and action
    triggers = [t for t in workflow_triggers.values() if t.get("workflow_id") == workflow_id]
    actions = [a for a in workflow_actions.values() if a.get("workflow_id") == workflow_id]
    
    if not triggers:
        raise HTTPException(status_code=400, detail="Workflow must have at least one trigger")
    if not actions:
        raise HTTPException(status_code=400, detail="Workflow must have at least one action")
    
    workflow["status"] = WorkflowStatus.ACTIVE.value
    workflow["activated_at"] = now.isoformat()
    workflow["updated_at"] = now.isoformat()
    
    return workflow


@router.post("/workflows/{workflow_id}/deactivate")
async def deactivate_workflow(workflow_id: str):
    """Deactivate a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    workflow["status"] = WorkflowStatus.PAUSED.value
    workflow["updated_at"] = datetime.utcnow().isoformat()
    
    return workflow


@router.post("/workflows/{workflow_id}/clone")
async def clone_workflow(
    workflow_id: str,
    new_name: str,
    user_id: str = Query(default="default")
):
    """Clone a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    source = workflows[workflow_id]
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    cloned = {
        **source,
        "id": new_id,
        "name": new_name,
        "status": WorkflowStatus.DRAFT.value,
        "execution_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "version": 1,
        "cloned_from": workflow_id,
        "created_by": user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    workflows[new_id] = cloned
    
    # Clone triggers
    for trigger in workflow_triggers.values():
        if trigger.get("workflow_id") == workflow_id:
            new_trigger_id = str(uuid.uuid4())
            workflow_triggers[new_trigger_id] = {
                **trigger,
                "id": new_trigger_id,
                "workflow_id": new_id
            }
    
    # Clone actions
    for action in workflow_actions.values():
        if action.get("workflow_id") == workflow_id:
            new_action_id = str(uuid.uuid4())
            workflow_actions[new_action_id] = {
                **action,
                "id": new_action_id,
                "workflow_id": new_id
            }
    
    return cloned


# Triggers
@router.post("/triggers")
async def create_trigger(request: TriggerCreate):
    """Add a trigger to a workflow"""
    if request.workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    trigger_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    trigger = {
        "id": trigger_id,
        "workflow_id": request.workflow_id,
        "trigger_type": request.trigger_type.value,
        "conditions": request.conditions or [],
        "schedule": request.schedule,
        "settings": request.settings or {},
        "created_at": now.isoformat()
    }
    
    workflow_triggers[trigger_id] = trigger
    
    # Update workflow trigger count
    workflows[request.workflow_id]["trigger_count"] = len([
        t for t in workflow_triggers.values() if t.get("workflow_id") == request.workflow_id
    ])
    
    return trigger


@router.get("/workflows/{workflow_id}/triggers")
async def get_workflow_triggers(workflow_id: str):
    """Get triggers for a workflow"""
    triggers = [t for t in workflow_triggers.values() if t.get("workflow_id") == workflow_id]
    return {"triggers": triggers, "total": len(triggers)}


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str):
    """Delete a trigger"""
    if trigger_id not in workflow_triggers:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    trigger = workflow_triggers.pop(trigger_id)
    
    return {"message": "Trigger deleted", "trigger_id": trigger_id}


# Actions
@router.post("/actions")
async def create_action(request: ActionCreate):
    """Add an action to a workflow"""
    if request.workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    action_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    action = {
        "id": action_id,
        "workflow_id": request.workflow_id,
        "action_type": request.action_type.value,
        "position": request.position,
        "config": request.config,
        "conditions": request.conditions or [],
        "parent_action_id": request.parent_action_id,
        "branch": request.branch,
        "created_at": now.isoformat()
    }
    
    workflow_actions[action_id] = action
    
    # Update workflow action count
    workflows[request.workflow_id]["action_count"] = len([
        a for a in workflow_actions.values() if a.get("workflow_id") == request.workflow_id
    ])
    
    return action


@router.get("/workflows/{workflow_id}/actions")
async def get_workflow_actions(workflow_id: str):
    """Get actions for a workflow"""
    actions = [a for a in workflow_actions.values() if a.get("workflow_id") == workflow_id]
    actions.sort(key=lambda x: x.get("position", 0))
    return {"actions": actions, "total": len(actions)}


@router.put("/actions/{action_id}")
async def update_action(
    action_id: str,
    config: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    position: Optional[int] = None
):
    """Update an action"""
    if action_id not in workflow_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action = workflow_actions[action_id]
    
    if config is not None:
        action["config"] = config
    if conditions is not None:
        action["conditions"] = conditions
    if position is not None:
        action["position"] = position
    
    action["updated_at"] = datetime.utcnow().isoformat()
    
    return action


@router.delete("/actions/{action_id}")
async def delete_action(action_id: str):
    """Delete an action"""
    if action_id not in workflow_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    
    workflow_actions.pop(action_id)
    
    return {"message": "Action deleted", "action_id": action_id}


# Executions
@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    record_id: str,
    record_data: Optional[Dict[str, Any]] = None,
    user_id: str = Query(default="default")
):
    """Manually execute a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    execution_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    execution = {
        "id": execution_id,
        "workflow_id": workflow_id,
        "record_id": record_id,
        "record_data": record_data or {},
        "status": ExecutionStatus.RUNNING.value,
        "triggered_by": "manual",
        "triggered_by_user": user_id,
        "current_action": 1,
        "actions_completed": 0,
        "actions_failed": 0,
        "started_at": now.isoformat(),
        "completed_at": None
    }
    
    workflow_executions[execution_id] = execution
    
    # Simulate execution
    await simulate_workflow_execution(execution_id, workflow_id)
    
    return workflow_executions[execution_id]


@router.get("/workflows/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: str,
    status: Optional[ExecutionStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    """Get workflow executions"""
    executions = [e for e in workflow_executions.values() if e.get("workflow_id") == workflow_id]
    
    if status:
        executions = [e for e in executions if e.get("status") == status.value]
    
    executions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {
        "executions": executions[offset:offset + limit],
        "total": len(executions),
        "limit": limit,
        "offset": offset
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details"""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = workflow_executions[execution_id]
    logs = [l for l in execution_logs.values() if l.get("execution_id") == execution_id]
    logs.sort(key=lambda x: x.get("timestamp", ""))
    
    return {
        **execution,
        "logs": logs
    }


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel a running execution"""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = workflow_executions[execution_id]
    execution["status"] = ExecutionStatus.CANCELLED.value
    execution["cancelled_at"] = datetime.utcnow().isoformat()
    
    return execution


@router.post("/executions/{execution_id}/retry")
async def retry_execution(execution_id: str):
    """Retry a failed execution"""
    if execution_id not in workflow_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    old_execution = workflow_executions[execution_id]
    
    # Create new execution
    return await execute_workflow(
        workflow_id=old_execution["workflow_id"],
        record_id=old_execution["record_id"],
        record_data=old_execution.get("record_data")
    )


# Templates
@router.get("/templates")
async def list_workflow_templates(
    category: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List workflow templates"""
    # Return built-in templates + user templates
    templates = get_builtin_templates()
    
    user_templates = [
        w for w in workflows.values() 
        if w.get("tenant_id") == tenant_id and w.get("is_template")
    ]
    
    templates.extend(user_templates)
    
    if category:
        templates = [t for t in templates if t.get("category") == category]
    
    return {"templates": templates, "total": len(templates)}


@router.post("/templates/{template_id}/use")
async def create_from_template(
    template_id: str,
    name: str,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a workflow from a template"""
    # Find template
    template = None
    for t in get_builtin_templates():
        if t.get("id") == template_id:
            template = t
            break
    
    if not template:
        if template_id in workflows:
            template = workflows[template_id]
        else:
            raise HTTPException(status_code=404, detail="Template not found")
    
    # Create workflow from template
    workflow_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    workflow = {
        "id": workflow_id,
        "name": name,
        "description": template.get("description"),
        "object_type": template.get("object_type"),
        "status": WorkflowStatus.DRAFT.value,
        "is_template": False,
        "from_template": template_id,
        "tags": template.get("tags", []),
        "trigger_count": 0,
        "action_count": 0,
        "execution_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "version": 1,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    workflows[workflow_id] = workflow
    
    return workflow


# Analytics
@router.get("/analytics/overview")
async def get_workflow_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get workflow analytics overview"""
    tenant_workflows = [w for w in workflows.values() if w.get("tenant_id") == tenant_id]
    all_executions = list(workflow_executions.values())
    
    return {
        "total_workflows": len(tenant_workflows),
        "active_workflows": len([w for w in tenant_workflows if w.get("status") == "active"]),
        "total_executions": len(all_executions),
        "successful_executions": len([e for e in all_executions if e.get("status") == "completed"]),
        "failed_executions": len([e for e in all_executions if e.get("status") == "failed"]),
        "success_rate": round(random.uniform(0.85, 0.98), 3),
        "avg_execution_time_ms": random.randint(100, 5000),
        "actions_executed_today": random.randint(100, 1000),
        "most_used_actions": [
            {"action": "send_email", "count": random.randint(100, 500)},
            {"action": "create_task", "count": random.randint(50, 300)},
            {"action": "update_record", "count": random.randint(30, 200)}
        ]
    }


@router.get("/analytics/workflows/{workflow_id}")
async def get_single_workflow_analytics(workflow_id: str):
    """Get analytics for a specific workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    executions = [e for e in workflow_executions.values() if e.get("workflow_id") == workflow_id]
    
    return {
        "workflow_id": workflow_id,
        "workflow_name": workflow["name"],
        "total_executions": len(executions),
        "successful": len([e for e in executions if e.get("status") == "completed"]),
        "failed": len([e for e in executions if e.get("status") == "failed"]),
        "success_rate": round(random.uniform(0.8, 0.99), 3),
        "avg_duration_ms": random.randint(500, 3000),
        "executions_by_day": [
            {"date": (datetime.utcnow() - timedelta(days=i)).isoformat()[:10], "count": random.randint(10, 100)}
            for i in range(7)
        ],
        "failure_reasons": [
            {"reason": "Timeout", "count": random.randint(1, 10)},
            {"reason": "Invalid data", "count": random.randint(1, 5)},
            {"reason": "API error", "count": random.randint(1, 3)}
        ]
    }


# Helper functions
def build_flow_structure(actions: List[Dict]) -> Dict:
    """Build visual flow structure from actions"""
    flow = {
        "nodes": [],
        "edges": []
    }
    
    for action in actions:
        flow["nodes"].append({
            "id": action["id"],
            "type": action["action_type"],
            "position": action["position"],
            "data": action.get("config", {})
        })
        
        if action.get("parent_action_id"):
            flow["edges"].append({
                "source": action["parent_action_id"],
                "target": action["id"],
                "branch": action.get("branch")
            })
    
    return flow


async def simulate_workflow_execution(execution_id: str, workflow_id: str):
    """Simulate workflow execution"""
    execution = workflow_executions[execution_id]
    actions = [a for a in workflow_actions.values() if a.get("workflow_id") == workflow_id]
    
    now = datetime.utcnow()
    
    for i, action in enumerate(sorted(actions, key=lambda x: x.get("position", 0))):
        log_id = str(uuid.uuid4())
        success = random.random() > 0.05
        
        execution_logs[log_id] = {
            "id": log_id,
            "execution_id": execution_id,
            "action_id": action["id"],
            "action_type": action["action_type"],
            "status": "completed" if success else "failed",
            "output": {"result": "success"} if success else {"error": "Simulated error"},
            "timestamp": (now + timedelta(seconds=i)).isoformat()
        }
        
        if success:
            execution["actions_completed"] += 1
        else:
            execution["actions_failed"] += 1
            execution["status"] = ExecutionStatus.FAILED.value
            break
    
    if execution["status"] != ExecutionStatus.FAILED.value:
        execution["status"] = ExecutionStatus.COMPLETED.value
    
    execution["completed_at"] = datetime.utcnow().isoformat()
    
    # Update workflow stats
    workflow = workflows[workflow_id]
    workflow["execution_count"] = workflow.get("execution_count", 0) + 1
    if execution["status"] == ExecutionStatus.COMPLETED.value:
        workflow["success_count"] = workflow.get("success_count", 0) + 1
    else:
        workflow["failure_count"] = workflow.get("failure_count", 0) + 1


def get_builtin_templates() -> List[Dict]:
    """Get built-in workflow templates"""
    return [
        {
            "id": "lead_nurture",
            "name": "Lead Nurturing Workflow",
            "description": "Automatically nurture new leads with a series of emails",
            "category": "sales",
            "object_type": "lead",
            "tags": ["nurturing", "email"]
        },
        {
            "id": "deal_stage_notifications",
            "name": "Deal Stage Notifications",
            "description": "Notify team when deals move to certain stages",
            "category": "sales",
            "object_type": "opportunity",
            "tags": ["notifications", "deals"]
        },
        {
            "id": "task_reminder",
            "name": "Task Reminder Workflow",
            "description": "Send reminders for overdue tasks",
            "category": "productivity",
            "object_type": "task",
            "tags": ["reminders", "tasks"]
        },
        {
            "id": "welcome_sequence",
            "name": "Welcome Sequence",
            "description": "Welcome new customers with onboarding emails",
            "category": "customer_success",
            "object_type": "contact",
            "tags": ["onboarding", "welcome"]
        },
        {
            "id": "churn_prevention",
            "name": "Churn Prevention",
            "description": "Alert CSM when customer health drops",
            "category": "customer_success",
            "object_type": "account",
            "tags": ["churn", "health"]
        }
    ]
