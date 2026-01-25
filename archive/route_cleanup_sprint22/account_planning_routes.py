"""
Account Planning Routes - Strategic account management and planning
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

router = APIRouter(prefix="/account-planning", tags=["Account Planning"])


class AccountTier(str, Enum):
    STRATEGIC = "strategic"
    ENTERPRISE = "enterprise"
    MID_MARKET = "mid_market"
    SMB = "smb"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ObjectiveStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class RelationshipStrength(str, Enum):
    WEAK = "weak"
    DEVELOPING = "developing"
    STRONG = "strong"
    CHAMPION = "champion"


# In-memory storage
account_plans = {}
objectives = {}
stakeholders = {}
action_items = {}
whitespace_opportunities = {}


class AccountPlanCreate(BaseModel):
    account_id: str
    account_name: str
    tier: AccountTier
    fiscal_year: int
    owner_id: str
    team_ids: Optional[List[str]] = None
    vision: Optional[str] = None
    executive_summary: Optional[str] = None


class ObjectiveCreate(BaseModel):
    plan_id: str
    title: str
    description: Optional[str] = None
    target_value: Optional[float] = None
    target_date: Optional[str] = None
    owner_id: Optional[str] = None


class StakeholderCreate(BaseModel):
    plan_id: str
    contact_id: str
    name: str
    title: str
    role: str
    relationship_strength: RelationshipStrength = RelationshipStrength.DEVELOPING
    influence_level: int = Field(ge=1, le=10, default=5)
    notes: Optional[str] = None


class ActionItemCreate(BaseModel):
    plan_id: str
    objective_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    owner_id: str
    due_date: str
    priority: int = Field(ge=1, le=5, default=3)


# Account Plans
@router.post("/plans")
async def create_account_plan(
    request: AccountPlanCreate,
    tenant_id: str = Query(default="default")
):
    """Create an account plan"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    plan = {
        "id": plan_id,
        "account_id": request.account_id,
        "account_name": request.account_name,
        "tier": request.tier.value,
        "fiscal_year": request.fiscal_year,
        "owner_id": request.owner_id,
        "team_ids": request.team_ids or [],
        "vision": request.vision,
        "executive_summary": request.executive_summary,
        "status": PlanStatus.DRAFT.value,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    account_plans[plan_id] = plan
    
    return plan


@router.get("/plans")
async def list_account_plans(
    tier: Optional[AccountTier] = None,
    status: Optional[PlanStatus] = None,
    owner_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    tenant_id: str = Query(default="default")
):
    """List account plans"""
    result = [p for p in account_plans.values() if p.get("tenant_id") == tenant_id]
    
    if tier:
        result = [p for p in result if p.get("tier") == tier.value]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    if owner_id:
        result = [p for p in result if p.get("owner_id") == owner_id]
    if fiscal_year:
        result = [p for p in result if p.get("fiscal_year") == fiscal_year]
    
    return {"plans": result, "total": len(result)}


@router.get("/plans/{plan_id}")
async def get_account_plan(plan_id: str):
    """Get an account plan with full details"""
    if plan_id not in account_plans:
        raise HTTPException(status_code=404, detail="Account plan not found")
    
    plan = account_plans[plan_id].copy()
    
    # Add related data
    plan["objectives"] = [o for o in objectives.values() if o.get("plan_id") == plan_id]
    plan["stakeholders"] = [s for s in stakeholders.values() if s.get("plan_id") == plan_id]
    plan["action_items"] = [a for a in action_items.values() if a.get("plan_id") == plan_id]
    
    # Add summary stats
    plan["stats"] = {
        "objectives_count": len(plan["objectives"]),
        "objectives_completed": len([o for o in plan["objectives"] if o.get("status") == "completed"]),
        "stakeholders_count": len(plan["stakeholders"]),
        "champions_count": len([s for s in plan["stakeholders"] if s.get("relationship_strength") == "champion"]),
        "action_items_pending": len([a for a in plan["action_items"] if a.get("status") != "completed"]),
        "health_score": random.randint(60, 100)
    }
    
    return plan


@router.put("/plans/{plan_id}")
async def update_account_plan(
    plan_id: str,
    request: AccountPlanCreate
):
    """Update an account plan"""
    if plan_id not in account_plans:
        raise HTTPException(status_code=404, detail="Account plan not found")
    
    plan = account_plans[plan_id]
    plan.update({
        "account_name": request.account_name,
        "tier": request.tier.value,
        "fiscal_year": request.fiscal_year,
        "owner_id": request.owner_id,
        "team_ids": request.team_ids or [],
        "vision": request.vision,
        "executive_summary": request.executive_summary,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return plan


@router.put("/plans/{plan_id}/status")
async def update_plan_status(
    plan_id: str,
    status: PlanStatus = Query(...)
):
    """Update plan status"""
    if plan_id not in account_plans:
        raise HTTPException(status_code=404, detail="Account plan not found")
    
    plan = account_plans[plan_id]
    plan["status"] = status.value
    plan["updated_at"] = datetime.utcnow().isoformat()
    
    return plan


# Objectives
@router.post("/objectives")
async def create_objective(
    request: ObjectiveCreate,
    tenant_id: str = Query(default="default")
):
    """Create a plan objective"""
    objective_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    objective = {
        "id": objective_id,
        "plan_id": request.plan_id,
        "title": request.title,
        "description": request.description,
        "target_value": request.target_value,
        "current_value": 0,
        "target_date": request.target_date,
        "owner_id": request.owner_id,
        "status": ObjectiveStatus.NOT_STARTED.value,
        "progress": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    objectives[objective_id] = objective
    
    return objective


@router.get("/plans/{plan_id}/objectives")
async def list_plan_objectives(plan_id: str):
    """List objectives for a plan"""
    result = [o for o in objectives.values() if o.get("plan_id") == plan_id]
    return {"objectives": result, "total": len(result)}


@router.put("/objectives/{objective_id}")
async def update_objective(
    objective_id: str,
    status: Optional[ObjectiveStatus] = None,
    current_value: Optional[float] = None,
    progress: Optional[int] = None
):
    """Update an objective"""
    if objective_id not in objectives:
        raise HTTPException(status_code=404, detail="Objective not found")
    
    obj = objectives[objective_id]
    
    if status:
        obj["status"] = status.value
    if current_value is not None:
        obj["current_value"] = current_value
    if progress is not None:
        obj["progress"] = progress
    
    obj["updated_at"] = datetime.utcnow().isoformat()
    
    return obj


# Stakeholders
@router.post("/stakeholders")
async def add_stakeholder(
    request: StakeholderCreate,
    tenant_id: str = Query(default="default")
):
    """Add a stakeholder to a plan"""
    stakeholder_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    stakeholder = {
        "id": stakeholder_id,
        "plan_id": request.plan_id,
        "contact_id": request.contact_id,
        "name": request.name,
        "title": request.title,
        "role": request.role,
        "relationship_strength": request.relationship_strength.value,
        "influence_level": request.influence_level,
        "notes": request.notes,
        "last_contact": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    stakeholders[stakeholder_id] = stakeholder
    
    return stakeholder


@router.get("/plans/{plan_id}/stakeholders")
async def list_plan_stakeholders(plan_id: str):
    """List stakeholders for a plan"""
    result = [s for s in stakeholders.values() if s.get("plan_id") == plan_id]
    
    # Sort by influence
    result.sort(key=lambda x: x.get("influence_level", 0), reverse=True)
    
    return {"stakeholders": result, "total": len(result)}


@router.put("/stakeholders/{stakeholder_id}")
async def update_stakeholder(
    stakeholder_id: str,
    relationship_strength: Optional[RelationshipStrength] = None,
    influence_level: Optional[int] = None,
    notes: Optional[str] = None
):
    """Update a stakeholder"""
    if stakeholder_id not in stakeholders:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    
    sh = stakeholders[stakeholder_id]
    
    if relationship_strength:
        sh["relationship_strength"] = relationship_strength.value
    if influence_level is not None:
        sh["influence_level"] = influence_level
    if notes:
        sh["notes"] = notes
    
    sh["updated_at"] = datetime.utcnow().isoformat()
    
    return sh


@router.post("/stakeholders/{stakeholder_id}/contact")
async def log_stakeholder_contact(
    stakeholder_id: str,
    contact_type: str = Query(...),
    notes: str = Query(default="")
):
    """Log contact with a stakeholder"""
    if stakeholder_id not in stakeholders:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    
    sh = stakeholders[stakeholder_id]
    sh["last_contact"] = datetime.utcnow().isoformat()
    sh["last_contact_type"] = contact_type
    
    return sh


# Action Items
@router.post("/action-items")
async def create_action_item(
    request: ActionItemCreate,
    tenant_id: str = Query(default="default")
):
    """Create an action item"""
    item_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    item = {
        "id": item_id,
        "plan_id": request.plan_id,
        "objective_id": request.objective_id,
        "title": request.title,
        "description": request.description,
        "owner_id": request.owner_id,
        "due_date": request.due_date,
        "priority": request.priority,
        "status": "pending",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    action_items[item_id] = item
    
    return item


@router.get("/plans/{plan_id}/action-items")
async def list_plan_action_items(
    plan_id: str,
    status: Optional[str] = None,
    owner_id: Optional[str] = None
):
    """List action items for a plan"""
    result = [a for a in action_items.values() if a.get("plan_id") == plan_id]
    
    if status:
        result = [a for a in result if a.get("status") == status]
    if owner_id:
        result = [a for a in result if a.get("owner_id") == owner_id]
    
    result.sort(key=lambda x: (x.get("due_date", ""), -x.get("priority", 0)))
    
    return {"action_items": result, "total": len(result)}


@router.put("/action-items/{item_id}/complete")
async def complete_action_item(item_id: str):
    """Mark action item as complete"""
    if item_id not in action_items:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    item = action_items[item_id]
    item["status"] = "completed"
    item["completed_at"] = datetime.utcnow().isoformat()
    
    return item


# Whitespace Analysis
@router.get("/plans/{plan_id}/whitespace")
async def get_whitespace_opportunities(plan_id: str):
    """Get whitespace opportunities for an account"""
    products = ["Product A", "Product B", "Product C", "Add-on X", "Add-on Y", "Service Z"]
    
    opportunities = []
    for product in products:
        opportunities.append({
            "product": product,
            "current_usage": random.choice([True, False]),
            "potential_value": random.randint(10000, 100000),
            "fit_score": random.randint(50, 100),
            "competition": random.choice(["None", "Competitor A", "Competitor B"]),
            "recommended_approach": random.choice(["Cross-sell", "Upsell", "Expansion"])
        })
    
    opportunities.sort(key=lambda x: x["potential_value"], reverse=True)
    
    return {
        "plan_id": plan_id,
        "opportunities": opportunities,
        "total_potential_value": sum(o["potential_value"] for o in opportunities if not o["current_usage"])
    }


# Org Chart
@router.get("/plans/{plan_id}/org-chart")
async def get_account_org_chart(plan_id: str):
    """Get organization chart for account"""
    plan_stakeholders = [s for s in stakeholders.values() if s.get("plan_id") == plan_id]
    
    # Build hierarchical org chart
    org_chart = {
        "account_name": account_plans.get(plan_id, {}).get("account_name", "Account"),
        "stakeholders": plan_stakeholders,
        "coverage": {
            "executive": len([s for s in plan_stakeholders if "executive" in s.get("role", "").lower()]),
            "decision_makers": len([s for s in plan_stakeholders if s.get("influence_level", 0) >= 8]),
            "champions": len([s for s in plan_stakeholders if s.get("relationship_strength") == "champion"]),
            "total_contacts": len(plan_stakeholders)
        },
        "gaps": [
            "Need more executive sponsors",
            "Finance stakeholder missing"
        ] if random.choice([True, False]) else []
    }
    
    return org_chart


# Analytics
@router.get("/analytics/health")
async def get_plans_health(tenant_id: str = Query(default="default")):
    """Get health scores across all account plans"""
    plans = [p for p in account_plans.values() if p.get("tenant_id") == tenant_id]
    
    health_data = []
    for plan in plans:
        health_data.append({
            "plan_id": plan["id"],
            "account_name": plan.get("account_name"),
            "tier": plan.get("tier"),
            "health_score": random.randint(50, 100),
            "trend": random.choice(["improving", "stable", "declining"]),
            "objectives_progress": random.randint(20, 90),
            "stakeholder_engagement": random.randint(30, 95)
        })
    
    health_data.sort(key=lambda x: x["health_score"])
    
    return {
        "plans": health_data,
        "at_risk_count": len([h for h in health_data if h["health_score"] < 70])
    }
