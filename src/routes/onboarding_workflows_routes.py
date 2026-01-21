"""
Onboarding Workflows Routes - New customer and rep onboarding management
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

router = APIRouter(prefix="/onboarding", tags=["Onboarding Workflows"])


class OnboardingType(str, Enum):
    CUSTOMER = "customer"
    REP = "rep"
    PARTNER = "partner"


class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    FORM = "form"
    MEETING = "meeting"
    TRAINING = "training"
    DOCUMENT = "document"
    INTEGRATION = "integration"
    MILESTONE = "milestone"


# In-memory storage
onboarding_workflows = {}
onboarding_templates = {}
onboarding_tasks = {}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: TaskType
    assigned_to: Optional[str] = None
    due_days: int = 7  # Days from workflow start
    dependencies: List[str] = []
    is_required: bool = True


class WorkflowCreate(BaseModel):
    onboarding_type: OnboardingType
    entity_id: str  # customer_id, rep_id, or partner_id
    entity_name: str
    template_id: Optional[str] = None
    owner_id: str
    target_completion_days: int = 30


class TemplateCreate(BaseModel):
    name: str
    onboarding_type: OnboardingType
    description: Optional[str] = None
    tasks: List[TaskCreate]
    target_days: int = 30


# Dashboard
@router.get("/dashboard")
async def get_onboarding_dashboard(
    onboarding_type: Optional[OnboardingType] = None,
    tenant_id: str = Query(default="default")
):
    """Get onboarding dashboard"""
    now = datetime.utcnow()
    
    return {
        "generated_at": now.isoformat(),
        "summary": {
            "active_onboardings": random.randint(15, 50),
            "completed_this_month": random.randint(8, 25),
            "at_risk": random.randint(2, 10),
            "avg_completion_days": round(random.uniform(20, 45), 1),
            "on_time_completion_rate": round(random.uniform(0.70, 0.90), 2)
        },
        "by_type": [
            {"type": OnboardingType.CUSTOMER.value, "active": random.randint(8, 30), "completed": random.randint(5, 20)},
            {"type": OnboardingType.REP.value, "active": random.randint(3, 12), "completed": random.randint(2, 8)},
            {"type": OnboardingType.PARTNER.value, "active": random.randint(2, 8), "completed": random.randint(1, 5)}
        ],
        "by_status": [
            {"status": OnboardingStatus.IN_PROGRESS.value, "count": random.randint(12, 40)},
            {"status": OnboardingStatus.BLOCKED.value, "count": random.randint(2, 8)},
            {"status": OnboardingStatus.COMPLETED.value, "count": random.randint(8, 25)}
        ],
        "upcoming_milestones": [
            {
                "entity_name": f"Entity {i}",
                "milestone": random.choice(["Kickoff Call", "Training Complete", "Go-Live"]),
                "due_date": (now + timedelta(days=random.randint(1, 14))).isoformat(),
                "status": random.choice(["on_track", "at_risk"])
            }
            for i in range(5)
        ]
    }


# Workflow CRUD
@router.post("/workflows")
async def create_workflow(
    request: WorkflowCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new onboarding workflow"""
    workflow_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get template tasks if template provided
    tasks = []
    if request.template_id:
        template = onboarding_templates.get(request.template_id)
        if template:
            for i, task_def in enumerate(template.get("tasks", [])):
                tasks.append({
                    "id": str(uuid.uuid4()),
                    "title": task_def["title"],
                    "description": task_def.get("description"),
                    "task_type": task_def["task_type"],
                    "assigned_to": task_def.get("assigned_to"),
                    "status": TaskStatus.PENDING.value,
                    "due_date": (now + timedelta(days=task_def.get("due_days", 7))).isoformat(),
                    "is_required": task_def.get("is_required", True),
                    "order": i
                })
    
    workflow = {
        "id": workflow_id,
        "onboarding_type": request.onboarding_type.value,
        "entity_id": request.entity_id,
        "entity_name": request.entity_name,
        "template_id": request.template_id,
        "owner_id": request.owner_id,
        "status": OnboardingStatus.IN_PROGRESS.value,
        "tasks": tasks,
        "progress_pct": 0,
        "target_completion_date": (now + timedelta(days=request.target_completion_days)).isoformat(),
        "tenant_id": tenant_id,
        "started_at": now.isoformat(),
        "created_at": now.isoformat()
    }
    
    onboarding_workflows[workflow_id] = workflow
    
    return workflow


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    tenant_id: str = Query(default="default")
):
    """Get a workflow by ID"""
    workflow = onboarding_workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/workflows")
async def list_workflows(
    onboarding_type: Optional[OnboardingType] = None,
    status: Optional[OnboardingStatus] = None,
    owner_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List workflows"""
    result = [w for w in onboarding_workflows.values() if w.get("tenant_id") == tenant_id]
    
    if onboarding_type:
        result = [w for w in result if w.get("onboarding_type") == onboarding_type.value]
    if status:
        result = [w for w in result if w.get("status") == status.value]
    if owner_id:
        result = [w for w in result if w.get("owner_id") == owner_id]
    if entity_id:
        result = [w for w in result if w.get("entity_id") == entity_id]
    
    return {"workflows": result[:limit], "total": len(result)}


# Task Management
@router.post("/workflows/{workflow_id}/tasks")
async def add_task(
    workflow_id: str,
    request: TaskCreate,
    tenant_id: str = Query(default="default")
):
    """Add a task to a workflow"""
    workflow = onboarding_workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    now = datetime.utcnow()
    task = {
        "id": str(uuid.uuid4()),
        "title": request.title,
        "description": request.description,
        "task_type": request.task_type.value,
        "assigned_to": request.assigned_to,
        "status": TaskStatus.PENDING.value,
        "due_date": (now + timedelta(days=request.due_days)).isoformat(),
        "dependencies": request.dependencies,
        "is_required": request.is_required,
        "order": len(workflow["tasks"]),
        "created_at": now.isoformat()
    }
    
    workflow["tasks"].append(task)
    
    return task


@router.post("/workflows/{workflow_id}/tasks/{task_id}/complete")
async def complete_task(
    workflow_id: str,
    task_id: str,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Complete a task"""
    workflow = onboarding_workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    task = None
    for t in workflow["tasks"]:
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task["status"] = TaskStatus.COMPLETED.value
    task["completed_at"] = datetime.utcnow().isoformat()
    task["completion_notes"] = notes
    
    # Update workflow progress
    completed = sum(1 for t in workflow["tasks"] if t["status"] == TaskStatus.COMPLETED.value)
    workflow["progress_pct"] = int((completed / len(workflow["tasks"])) * 100) if workflow["tasks"] else 0
    
    # Check if workflow complete
    required_tasks = [t for t in workflow["tasks"] if t.get("is_required", True)]
    if all(t["status"] == TaskStatus.COMPLETED.value for t in required_tasks):
        workflow["status"] = OnboardingStatus.COMPLETED.value
        workflow["completed_at"] = datetime.utcnow().isoformat()
    
    return {
        "task_id": task_id,
        "status": task["status"],
        "workflow_progress": workflow["progress_pct"],
        "workflow_status": workflow["status"]
    }


@router.post("/workflows/{workflow_id}/tasks/{task_id}/assign")
async def assign_task(
    workflow_id: str,
    task_id: str,
    assigned_to: str,
    tenant_id: str = Query(default="default")
):
    """Assign a task to someone"""
    workflow = onboarding_workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    for task in workflow["tasks"]:
        if task["id"] == task_id:
            task["assigned_to"] = assigned_to
            task["assigned_at"] = datetime.utcnow().isoformat()
            return task
    
    raise HTTPException(status_code=404, detail="Task not found")


# Templates
@router.post("/templates")
async def create_template(
    request: TemplateCreate,
    tenant_id: str = Query(default="default")
):
    """Create an onboarding template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": request.name,
        "onboarding_type": request.onboarding_type.value,
        "description": request.description,
        "tasks": [
            {
                "title": t.title,
                "description": t.description,
                "task_type": t.task_type.value,
                "due_days": t.due_days,
                "is_required": t.is_required,
                "dependencies": t.dependencies
            }
            for t in request.tasks
        ],
        "target_days": request.target_days,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    onboarding_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_templates(
    onboarding_type: Optional[OnboardingType] = None,
    tenant_id: str = Query(default="default")
):
    """List templates"""
    result = [t for t in onboarding_templates.values() if t.get("tenant_id") == tenant_id]
    
    if onboarding_type:
        result = [t for t in result if t.get("onboarding_type") == onboarding_type.value]
    
    return {"templates": result, "total": len(result)}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    tenant_id: str = Query(default="default")
):
    """Get a template by ID"""
    template = onboarding_templates.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# Progress & Analytics
@router.get("/workflows/{workflow_id}/progress")
async def get_workflow_progress(
    workflow_id: str,
    tenant_id: str = Query(default="default")
):
    """Get detailed progress for a workflow"""
    workflow = onboarding_workflows.get(workflow_id)
    if not workflow:
        # Return mock data
        now = datetime.utcnow()
        workflow = {
            "id": workflow_id,
            "progress_pct": random.randint(20, 80),
            "status": OnboardingStatus.IN_PROGRESS.value,
            "target_completion_date": (now + timedelta(days=random.randint(5, 30))).isoformat(),
            "started_at": (now - timedelta(days=random.randint(5, 20))).isoformat()
        }
    
    now = datetime.utcnow()
    tasks = workflow.get("tasks", [])
    
    return {
        "workflow_id": workflow_id,
        "overall_progress": workflow.get("progress_pct", 0),
        "status": workflow.get("status"),
        "task_summary": {
            "total": len(tasks) or random.randint(8, 15),
            "completed": sum(1 for t in tasks if t.get("status") == TaskStatus.COMPLETED.value) or random.randint(2, 8),
            "in_progress": sum(1 for t in tasks if t.get("status") == TaskStatus.IN_PROGRESS.value) or random.randint(1, 3),
            "pending": sum(1 for t in tasks if t.get("status") == TaskStatus.PENDING.value) or random.randint(2, 6),
            "blocked": sum(1 for t in tasks if t.get("status") == TaskStatus.BLOCKED.value) or random.randint(0, 2)
        },
        "timeline": {
            "started_at": workflow.get("started_at"),
            "target_date": workflow.get("target_completion_date"),
            "days_elapsed": random.randint(5, 20),
            "days_remaining": random.randint(5, 25),
            "on_track": random.choice([True, True, False])
        },
        "milestones": [
            {"name": "Kickoff Complete", "status": "completed", "date": (now - timedelta(days=10)).isoformat()},
            {"name": "Training Complete", "status": random.choice(["completed", "in_progress"]), "date": (now - timedelta(days=3)).isoformat()},
            {"name": "Integration Setup", "status": random.choice(["in_progress", "pending"]), "date": (now + timedelta(days=5)).isoformat()},
            {"name": "Go-Live", "status": "pending", "date": (now + timedelta(days=15)).isoformat()}
        ]
    }


@router.get("/analytics")
async def get_onboarding_analytics(
    period: str = Query(default="quarter"),
    onboarding_type: Optional[OnboardingType] = None,
    tenant_id: str = Query(default="default")
):
    """Get onboarding analytics"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "completion_metrics": {
            "total_completed": random.randint(30, 100),
            "avg_completion_days": round(random.uniform(18, 35), 1),
            "median_completion_days": random.randint(15, 30),
            "on_time_rate": round(random.uniform(0.70, 0.90), 2),
            "early_completion_rate": round(random.uniform(0.10, 0.30), 2)
        },
        "task_metrics": {
            "avg_tasks_per_workflow": round(random.uniform(8, 15), 1),
            "task_completion_rate": round(random.uniform(0.85, 0.98), 2),
            "avg_days_per_task": round(random.uniform(2, 5), 1),
            "most_delayed_task_type": random.choice([t.value for t in TaskType])
        },
        "by_type": [
            {
                "type": OnboardingType.CUSTOMER.value,
                "completed": random.randint(20, 60),
                "avg_days": round(random.uniform(20, 35), 1),
                "satisfaction": round(random.uniform(4.0, 5.0), 1)
            },
            {
                "type": OnboardingType.REP.value,
                "completed": random.randint(8, 25),
                "avg_days": round(random.uniform(25, 45), 1),
                "time_to_productivity_days": random.randint(30, 90)
            },
            {
                "type": OnboardingType.PARTNER.value,
                "completed": random.randint(5, 15),
                "avg_days": round(random.uniform(25, 50), 1)
            }
        ],
        "bottlenecks": [
            {"task": "Integration Setup", "avg_delay_days": round(random.uniform(2, 7), 1), "occurrence_rate": round(random.uniform(0.20, 0.40), 2)},
            {"task": "Training Completion", "avg_delay_days": round(random.uniform(1, 4), 1), "occurrence_rate": round(random.uniform(0.15, 0.30), 2)}
        ]
    }


# Checklist for Customer
@router.get("/workflows/{workflow_id}/checklist")
async def get_customer_checklist(
    workflow_id: str,
    tenant_id: str = Query(default="default")
):
    """Get customer-facing onboarding checklist"""
    return {
        "workflow_id": workflow_id,
        "overall_progress": random.randint(30, 75),
        "checklist": [
            {
                "category": "Getting Started",
                "items": [
                    {"title": "Complete kickoff call", "completed": True, "required": True},
                    {"title": "Review welcome documentation", "completed": True, "required": True},
                    {"title": "Set up user accounts", "completed": random.choice([True, False]), "required": True}
                ]
            },
            {
                "category": "Configuration",
                "items": [
                    {"title": "Connect integrations", "completed": random.choice([True, False]), "required": True},
                    {"title": "Import existing data", "completed": random.choice([True, False]), "required": False},
                    {"title": "Configure settings", "completed": False, "required": True}
                ]
            },
            {
                "category": "Training",
                "items": [
                    {"title": "Complete admin training", "completed": random.choice([True, False]), "required": True},
                    {"title": "Complete user training", "completed": False, "required": True},
                    {"title": "Review best practices", "completed": False, "required": False}
                ]
            },
            {
                "category": "Go-Live",
                "items": [
                    {"title": "Final configuration review", "completed": False, "required": True},
                    {"title": "Launch to team", "completed": False, "required": True},
                    {"title": "Schedule success check-in", "completed": False, "required": True}
                ]
            }
        ],
        "next_steps": [
            "Complete user account setup",
            "Schedule training session",
            "Connect CRM integration"
        ],
        "resources": [
            {"title": "Getting Started Guide", "url": "https://docs.example.com/getting-started", "type": "documentation"},
            {"title": "Video Tutorials", "url": "https://videos.example.com/onboarding", "type": "video"},
            {"title": "Contact Support", "url": "https://support.example.com", "type": "support"}
        ]
    }
