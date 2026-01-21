"""
Customer Success Routes - Customer health, retention, and expansion management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/customer-success", tags=["Customer Success"])


class HealthScore(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class LifecycleStage(str, Enum):
    ONBOARDING = "onboarding"
    ADOPTION = "adoption"
    GROWING = "growing"
    RENEWING = "renewing"
    CHURNED = "churned"


class TaskType(str, Enum):
    ONBOARDING = "onboarding"
    CHECK_IN = "check_in"
    QBR = "qbr"
    ESCALATION = "escalation"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    TRAINING = "training"


class RiskType(str, Enum):
    CHURN = "churn"
    DOWNGRADE = "downgrade"
    LOW_USAGE = "low_usage"
    SUPPORT_ESCALATION = "support_escalation"
    PAYMENT_ISSUE = "payment_issue"


class PlaybookType(str, Enum):
    ONBOARDING = "onboarding"
    ADOPTION = "adoption"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    SAVE = "save"
    REACTIVATION = "reactivation"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    lifecycle_stage: Optional[LifecycleStage] = None
    csm_id: Optional[str] = None
    contract_end_date: Optional[str] = None
    arr: Optional[float] = None
    notes: Optional[str] = None


class SuccessTaskCreate(BaseModel):
    customer_id: str
    task_type: TaskType
    title: str
    description: Optional[str] = None
    due_date: str
    assignee_id: Optional[str] = None
    priority: str = "medium"


class PlaybookCreate(BaseModel):
    name: str
    playbook_type: PlaybookType
    description: Optional[str] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]]
    is_active: bool = True


class HealthOverride(BaseModel):
    customer_id: str
    new_score: HealthScore
    reason: str


# In-memory storage
customers = {}
success_tasks = {}
playbooks = {}
risk_alerts = {}
customer_notes = {}
health_history = {}


# Customer Health
@router.get("/customers")
async def list_customers(
    health_score: Optional[HealthScore] = None,
    lifecycle_stage: Optional[LifecycleStage] = None,
    csm_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List customers with health scores"""
    result = [c for c in customers.values() if c.get("tenant_id") == tenant_id]
    
    if health_score:
        result = [c for c in result if c.get("health_score") == health_score.value]
    if lifecycle_stage:
        result = [c for c in result if c.get("lifecycle_stage") == lifecycle_stage.value]
    if csm_id:
        result = [c for c in result if c.get("csm_id") == csm_id]
    
    # Sort by health score (critical first)
    health_order = {"critical": 0, "at_risk": 1, "good": 2, "excellent": 3}
    result.sort(key=lambda x: health_order.get(x.get("health_score", "good"), 2))
    
    return {
        "customers": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.post("/customers")
async def create_customer(
    account_id: str,
    name: str,
    arr: float = 0,
    contract_start: Optional[str] = None,
    contract_end: Optional[str] = None,
    csm_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a new customer for success tracking"""
    customer_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    customer = {
        "id": customer_id,
        "account_id": account_id,
        "name": name,
        "arr": arr,
        "health_score": HealthScore.GOOD.value,
        "health_score_value": 75,
        "lifecycle_stage": LifecycleStage.ONBOARDING.value,
        "csm_id": csm_id,
        "contract_start_date": contract_start,
        "contract_end_date": contract_end,
        "days_until_renewal": 365,
        "usage_metrics": {
            "dau": 0,
            "mau": 0,
            "feature_adoption": 0,
            "login_frequency": 0
        },
        "nps_score": None,
        "csat_score": None,
        "support_tickets_open": 0,
        "last_contact_date": now.isoformat(),
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    customers[customer_id] = customer
    
    logger.info("customer_created", customer_id=customer_id, name=name)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get customer details with health metrics"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customers[customer_id]


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, request: CustomerUpdate):
    """Update customer details"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = customers[customer_id]
    
    if request.name is not None:
        customer["name"] = request.name
    if request.lifecycle_stage is not None:
        customer["lifecycle_stage"] = request.lifecycle_stage.value
    if request.csm_id is not None:
        customer["csm_id"] = request.csm_id
    if request.contract_end_date is not None:
        customer["contract_end_date"] = request.contract_end_date
    if request.arr is not None:
        customer["arr"] = request.arr
    if request.notes is not None:
        customer["notes"] = request.notes
    
    customer["updated_at"] = datetime.utcnow().isoformat()
    
    return customer


@router.get("/customers/{customer_id}/health")
async def get_customer_health(customer_id: str):
    """Get detailed health breakdown for a customer"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = customers[customer_id]
    
    # Generate detailed health analysis
    return {
        "customer_id": customer_id,
        "overall_score": customer.get("health_score_value", 75),
        "health_status": customer.get("health_score", "good"),
        "factors": {
            "product_usage": {
                "score": random.randint(50, 100),
                "weight": 0.30,
                "details": {
                    "dau_vs_licenses": 0.65,
                    "feature_adoption": 0.72,
                    "depth_of_use": 0.58
                }
            },
            "engagement": {
                "score": random.randint(50, 100),
                "weight": 0.25,
                "details": {
                    "meetings_attended": 8,
                    "emails_responded": 0.85,
                    "training_completed": 0.60
                }
            },
            "support": {
                "score": random.randint(50, 100),
                "weight": 0.20,
                "details": {
                    "open_tickets": customer.get("support_tickets_open", 0),
                    "avg_resolution_time": "4.2 hours",
                    "escalations": 1
                }
            },
            "satisfaction": {
                "score": random.randint(50, 100),
                "weight": 0.15,
                "details": {
                    "nps": customer.get("nps_score"),
                    "csat": customer.get("csat_score"),
                    "last_survey": (datetime.utcnow() - timedelta(days=30)).isoformat()
                }
            },
            "relationship": {
                "score": random.randint(50, 100),
                "weight": 0.10,
                "details": {
                    "stakeholder_coverage": 0.80,
                    "executive_sponsor": True,
                    "champion_strength": "strong"
                }
            }
        },
        "trend": random.choice(["improving", "stable", "declining"]),
        "risks": [
            {"type": "low_usage", "severity": "medium", "detail": "Feature X adoption below benchmark"}
        ],
        "opportunities": [
            {"type": "expansion", "product": "Premium Add-on", "likelihood": 0.65}
        ],
        "last_calculated": datetime.utcnow().isoformat()
    }


@router.get("/customers/{customer_id}/health/history")
async def get_health_history(
    customer_id: str,
    days: int = Query(default=90, ge=7, le=365)
):
    """Get health score history"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Generate mock history
    history = []
    for i in range(days, -1, -7):
        history.append({
            "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
            "score": random.randint(60, 95),
            "status": random.choice(["excellent", "good", "at_risk"])
        })
    
    return {
        "customer_id": customer_id,
        "history": history,
        "period_days": days
    }


@router.post("/customers/{customer_id}/health/override")
async def override_health_score(
    customer_id: str,
    request: HealthOverride,
    user_id: str = Query(default="default")
):
    """Manually override health score"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = customers[customer_id]
    old_score = customer.get("health_score")
    
    customer["health_score"] = request.new_score.value
    customer["health_override"] = {
        "previous_score": old_score,
        "reason": request.reason,
        "overridden_by": user_id,
        "overridden_at": datetime.utcnow().isoformat()
    }
    customer["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("health_score_overridden", customer_id=customer_id, new_score=request.new_score.value)
    return customer


# Success Tasks
@router.post("/tasks")
async def create_success_task(
    request: SuccessTaskCreate,
    tenant_id: str = Query(default="default")
):
    """Create a CS task"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    task = {
        "id": task_id,
        "customer_id": request.customer_id,
        "task_type": request.task_type.value,
        "title": request.title,
        "description": request.description,
        "due_date": request.due_date,
        "assignee_id": request.assignee_id,
        "priority": request.priority,
        "status": "pending",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    success_tasks[task_id] = task
    
    logger.info("success_task_created", task_id=task_id, task_type=request.task_type.value)
    return task


@router.get("/tasks")
async def list_success_tasks(
    customer_id: Optional[str] = None,
    task_type: Optional[TaskType] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    due_before: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List CS tasks"""
    result = [t for t in success_tasks.values() if t.get("tenant_id") == tenant_id]
    
    if customer_id:
        result = [t for t in result if t.get("customer_id") == customer_id]
    if task_type:
        result = [t for t in result if t.get("task_type") == task_type.value]
    if assignee_id:
        result = [t for t in result if t.get("assignee_id") == assignee_id]
    if status:
        result = [t for t in result if t.get("status") == status]
    
    result.sort(key=lambda x: x.get("due_date", ""))
    
    return {
        "tasks": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/tasks/{task_id}")
async def get_success_task(task_id: str):
    """Get task details"""
    if task_id not in success_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return success_tasks[task_id]


@router.put("/tasks/{task_id}")
async def update_success_task(
    task_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    assignee_id: Optional[str] = None
):
    """Update task"""
    if task_id not in success_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = success_tasks[task_id]
    
    if status:
        task["status"] = status
    if notes:
        task["notes"] = notes
    if assignee_id:
        task["assignee_id"] = assignee_id
    
    task["updated_at"] = datetime.utcnow().isoformat()
    
    if status == "completed":
        task["completed_at"] = datetime.utcnow().isoformat()
    
    return task


@router.delete("/tasks/{task_id}")
async def delete_success_task(task_id: str):
    """Delete task"""
    if task_id not in success_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    del success_tasks[task_id]
    return {"status": "deleted", "task_id": task_id}


# Playbooks
@router.post("/playbooks")
async def create_playbook(
    request: PlaybookCreate,
    tenant_id: str = Query(default="default")
):
    """Create a CS playbook"""
    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    playbook = {
        "id": playbook_id,
        "name": request.name,
        "playbook_type": request.playbook_type.value,
        "description": request.description,
        "trigger_conditions": request.trigger_conditions or {},
        "steps": request.steps,
        "is_active": request.is_active,
        "times_triggered": 0,
        "success_rate": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    playbooks[playbook_id] = playbook
    
    logger.info("playbook_created", playbook_id=playbook_id, name=request.name)
    return playbook


@router.get("/playbooks")
async def list_playbooks(
    playbook_type: Optional[PlaybookType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List playbooks"""
    result = [p for p in playbooks.values() if p.get("tenant_id") == tenant_id]
    
    if playbook_type:
        result = [p for p in result if p.get("playbook_type") == playbook_type.value]
    if is_active is not None:
        result = [p for p in result if p.get("is_active") == is_active]
    
    return {"playbooks": result, "total": len(result)}


@router.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str):
    """Get playbook details"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbooks[playbook_id]


@router.post("/playbooks/{playbook_id}/trigger")
async def trigger_playbook(
    playbook_id: str,
    customer_id: str
):
    """Trigger a playbook for a customer"""
    if playbook_id not in playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    playbook = playbooks[playbook_id]
    execution_id = str(uuid.uuid4())
    
    # Create tasks from playbook steps
    tasks_created = []
    for i, step in enumerate(playbook.get("steps", [])):
        task_id = str(uuid.uuid4())
        due_offset = step.get("due_days_offset", i * 7)
        
        task = {
            "id": task_id,
            "customer_id": customer_id,
            "playbook_id": playbook_id,
            "execution_id": execution_id,
            "task_type": step.get("task_type", "check_in"),
            "title": step.get("title"),
            "description": step.get("description"),
            "due_date": (datetime.utcnow() + timedelta(days=due_offset)).strftime("%Y-%m-%d"),
            "status": "pending",
            "step_order": i + 1,
            "created_at": datetime.utcnow().isoformat()
        }
        success_tasks[task_id] = task
        tasks_created.append(task_id)
    
    playbook["times_triggered"] = playbook.get("times_triggered", 0) + 1
    
    logger.info("playbook_triggered", playbook_id=playbook_id, customer_id=customer_id, tasks=len(tasks_created))
    return {
        "execution_id": execution_id,
        "playbook_id": playbook_id,
        "customer_id": customer_id,
        "tasks_created": tasks_created
    }


# Risk Management
@router.get("/risks")
async def get_risk_alerts(
    risk_type: Optional[RiskType] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get customer risk alerts"""
    # Generate mock risk alerts
    mock_risks = [
        {
            "id": str(uuid.uuid4()),
            "customer_id": "cust_123",
            "customer_name": "Acme Corp",
            "risk_type": RiskType.CHURN.value,
            "severity": "high",
            "score": 85,
            "indicators": ["Usage dropped 40%", "No login in 14 days", "Support ticket escalated"],
            "recommended_actions": ["Schedule emergency call", "Offer training session"],
            "detected_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": "cust_456",
            "customer_name": "TechStart Inc",
            "risk_type": RiskType.LOW_USAGE.value,
            "severity": "medium",
            "score": 65,
            "indicators": ["DAU below 50% of licenses", "Key feature unused"],
            "recommended_actions": ["Send usage tips email", "Schedule adoption review"],
            "detected_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "customer_id": "cust_789",
            "customer_name": "Global Industries",
            "risk_type": RiskType.DOWNGRADE.value,
            "severity": "medium",
            "score": 55,
            "indicators": ["Asked about smaller plan", "Budget cut mentioned"],
            "recommended_actions": ["Review value delivered", "Prepare ROI deck"],
            "detected_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }
    ]
    
    if risk_type:
        mock_risks = [r for r in mock_risks if r["risk_type"] == risk_type.value]
    if severity:
        mock_risks = [r for r in mock_risks if r["severity"] == severity]
    
    return {
        "risks": mock_risks[:limit],
        "total": len(mock_risks),
        "high_count": len([r for r in mock_risks if r["severity"] == "high"]),
        "medium_count": len([r for r in mock_risks if r["severity"] == "medium"])
    }


@router.post("/risks/{risk_id}/dismiss")
async def dismiss_risk(
    risk_id: str,
    reason: str,
    user_id: str = Query(default="default")
):
    """Dismiss a risk alert"""
    return {
        "risk_id": risk_id,
        "status": "dismissed",
        "reason": reason,
        "dismissed_by": user_id,
        "dismissed_at": datetime.utcnow().isoformat()
    }


# Renewals
@router.get("/renewals")
async def get_upcoming_renewals(
    days_ahead: int = Query(default=90, ge=30, le=365),
    health_score: Optional[HealthScore] = None,
    tenant_id: str = Query(default="default")
):
    """Get upcoming renewals"""
    tenant_customers = [c for c in customers.values() if c.get("tenant_id") == tenant_id]
    
    renewals = []
    for customer in tenant_customers:
        if customer.get("contract_end_date"):
            renewals.append({
                "customer_id": customer["id"],
                "customer_name": customer["name"],
                "arr": customer.get("arr", 0),
                "contract_end_date": customer["contract_end_date"],
                "days_until_renewal": customer.get("days_until_renewal", 365),
                "health_score": customer.get("health_score"),
                "csm_id": customer.get("csm_id"),
                "risk_level": "low" if customer.get("health_score") in ["excellent", "good"] else "high",
                "expansion_opportunity": random.choice([True, False])
            })
    
    if health_score:
        renewals = [r for r in renewals if r.get("health_score") == health_score.value]
    
    renewals.sort(key=lambda x: x.get("days_until_renewal", 999))
    
    return {
        "renewals": renewals,
        "total": len(renewals),
        "total_arr_at_risk": sum(r["arr"] for r in renewals if r.get("risk_level") == "high")
    }


# Notes
@router.post("/customers/{customer_id}/notes")
async def add_customer_note(
    customer_id: str,
    content: str,
    note_type: str = "general",
    user_id: str = Query(default="default")
):
    """Add a note to a customer"""
    if customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    note_id = str(uuid.uuid4())
    
    note = {
        "id": note_id,
        "customer_id": customer_id,
        "content": content,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if customer_id not in customer_notes:
        customer_notes[customer_id] = []
    customer_notes[customer_id].append(note)
    
    return note


@router.get("/customers/{customer_id}/notes")
async def get_customer_notes(customer_id: str):
    """Get notes for a customer"""
    notes = customer_notes.get(customer_id, [])
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"notes": notes, "total": len(notes)}


# Dashboard
@router.get("/dashboard")
async def get_cs_dashboard(
    tenant_id: str = Query(default="default")
):
    """Get customer success dashboard metrics"""
    tenant_customers = [c for c in customers.values() if c.get("tenant_id") == tenant_id]
    
    return {
        "customer_count": len(tenant_customers),
        "total_arr": sum(c.get("arr", 0) for c in tenant_customers),
        "health_distribution": {
            HealthScore.EXCELLENT.value: len([c for c in tenant_customers if c.get("health_score") == "excellent"]),
            HealthScore.GOOD.value: len([c for c in tenant_customers if c.get("health_score") == "good"]),
            HealthScore.AT_RISK.value: len([c for c in tenant_customers if c.get("health_score") == "at_risk"]),
            HealthScore.CRITICAL.value: len([c for c in tenant_customers if c.get("health_score") == "critical"])
        },
        "lifecycle_distribution": {
            stage.value: len([c for c in tenant_customers if c.get("lifecycle_stage") == stage.value])
            for stage in LifecycleStage
        },
        "tasks": {
            "open": len([t for t in success_tasks.values() if t.get("status") == "pending"]),
            "overdue": len([t for t in success_tasks.values() if t.get("status") == "pending" and t.get("due_date", "9999") < datetime.utcnow().strftime("%Y-%m-%d")]),
            "completed_this_week": len([t for t in success_tasks.values() if t.get("status") == "completed"])
        },
        "renewals_next_90_days": len([c for c in tenant_customers if c.get("days_until_renewal", 999) <= 90]),
        "arr_at_risk": sum(c.get("arr", 0) for c in tenant_customers if c.get("health_score") in ["at_risk", "critical"]),
        "nps_average": 45,
        "csat_average": 4.2,
        "expansion_opportunities": 12,
        "generated_at": datetime.utcnow().isoformat()
    }


# Segments
@router.get("/segments")
async def get_customer_segments(tenant_id: str = Query(default="default")):
    """Get customer segments"""
    return {
        "segments": [
            {"name": "Enterprise", "count": 25, "arr": 2500000, "avg_health": 78},
            {"name": "Mid-Market", "count": 85, "arr": 1700000, "avg_health": 72},
            {"name": "SMB", "count": 250, "arr": 800000, "avg_health": 68},
            {"name": "At Risk", "count": 18, "arr": 450000, "avg_health": 35},
            {"name": "Champions", "count": 45, "arr": 1200000, "avg_health": 92}
        ]
    }
