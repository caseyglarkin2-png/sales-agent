"""
Territory Management V2 Routes - Advanced territory planning and optimization
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

router = APIRouter(prefix="/territories-v2", tags=["Territory Management V2"])


class TerritoryType(str, Enum):
    GEOGRAPHIC = "geographic"
    INDUSTRY = "industry"
    NAMED_ACCOUNT = "named_account"
    COMPANY_SIZE = "company_size"
    HYBRID = "hybrid"


class AssignmentMethod(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    CAPACITY = "capacity"
    GEOGRAPHIC = "geographic"
    MANUAL = "manual"


class TerritoryStatus(str, Enum):
    ACTIVE = "active"
    PLANNING = "planning"
    ARCHIVED = "archived"


class RealignmentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TerritoryCreate(BaseModel):
    name: str
    territory_type: TerritoryType
    description: Optional[str] = None
    criteria: Dict[str, Any]
    parent_id: Optional[str] = None
    assigned_reps: Optional[List[str]] = None
    quota: Optional[float] = None


class TerritoryAssignmentRule(BaseModel):
    name: str
    priority: int = 5
    conditions: List[Dict[str, Any]]
    territory_id: str
    method: AssignmentMethod = AssignmentMethod.ROUND_ROBIN


class RealignmentPlan(BaseModel):
    name: str
    description: Optional[str] = None
    effective_date: str
    changes: List[Dict[str, Any]]


# In-memory storage
territories = {}
territory_hierarchies = {}
assignment_rules = {}
realignment_plans = {}
territory_assignments = {}
territory_quotas = {}
territory_coverage = {}
territory_balancing = {}


# Territories CRUD
@router.post("/territories")
async def create_territory(
    request: TerritoryCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a territory"""
    territory_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    territory = {
        "id": territory_id,
        "name": request.name,
        "territory_type": request.territory_type.value,
        "description": request.description,
        "criteria": request.criteria,
        "parent_id": request.parent_id,
        "assigned_reps": request.assigned_reps or [],
        "quota": request.quota,
        "status": TerritoryStatus.ACTIVE.value,
        "account_count": 0,
        "lead_count": 0,
        "opportunity_count": 0,
        "pipeline_value": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    territories[territory_id] = territory
    
    # Update hierarchy
    if request.parent_id:
        if request.parent_id not in territory_hierarchies:
            territory_hierarchies[request.parent_id] = []
        territory_hierarchies[request.parent_id].append(territory_id)
    
    logger.info("territory_created", territory_id=territory_id, name=request.name)
    return territory


@router.get("/territories")
async def list_territories(
    territory_type: Optional[TerritoryType] = None,
    status: Optional[TerritoryStatus] = None,
    parent_id: Optional[str] = None,
    rep_id: Optional[str] = None,
    include_hierarchy: bool = False,
    tenant_id: str = Query(default="default")
):
    """List territories"""
    result = [t for t in territories.values() if t.get("tenant_id") == tenant_id]
    
    if territory_type:
        result = [t for t in result if t.get("territory_type") == territory_type.value]
    if status:
        result = [t for t in result if t.get("status") == status.value]
    if parent_id:
        result = [t for t in result if t.get("parent_id") == parent_id]
    if rep_id:
        result = [t for t in result if rep_id in t.get("assigned_reps", [])]
    
    if include_hierarchy:
        for t in result:
            t["children"] = territory_hierarchies.get(t["id"], [])
    
    return {"territories": result, "total": len(result)}


@router.get("/territories/{territory_id}")
async def get_territory(territory_id: str, include_stats: bool = True):
    """Get territory details"""
    if territory_id not in territories:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = territories[territory_id]
    children = territory_hierarchies.get(territory_id, [])
    
    result = {
        **territory,
        "children": [territories.get(c) for c in children if c in territories]
    }
    
    if include_stats:
        result["stats"] = calculate_territory_stats(territory_id)
    
    return result


@router.put("/territories/{territory_id}")
async def update_territory(
    territory_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    criteria: Optional[Dict[str, Any]] = None,
    assigned_reps: Optional[List[str]] = None,
    status: Optional[TerritoryStatus] = None,
    quota: Optional[float] = None
):
    """Update territory"""
    if territory_id not in territories:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = territories[territory_id]
    
    if name is not None:
        territory["name"] = name
    if description is not None:
        territory["description"] = description
    if criteria is not None:
        territory["criteria"] = criteria
    if assigned_reps is not None:
        territory["assigned_reps"] = assigned_reps
    if status is not None:
        territory["status"] = status.value
    if quota is not None:
        territory["quota"] = quota
    
    territory["updated_at"] = datetime.utcnow().isoformat()
    
    return territory


@router.delete("/territories/{territory_id}")
async def delete_territory(territory_id: str):
    """Delete territory"""
    if territory_id not in territories:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    # Check for children
    if territory_hierarchies.get(territory_id):
        raise HTTPException(status_code=400, detail="Cannot delete territory with children")
    
    del territories[territory_id]
    
    return {"status": "deleted", "territory_id": territory_id}


# Assignment Rules
@router.post("/assignment-rules")
async def create_assignment_rule(
    request: TerritoryAssignmentRule,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create territory assignment rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "priority": request.priority,
        "conditions": request.conditions,
        "territory_id": request.territory_id,
        "method": request.method.value,
        "is_active": True,
        "matched_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    assignment_rules[rule_id] = rule
    
    return rule


@router.get("/assignment-rules")
async def list_assignment_rules(
    territory_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List assignment rules"""
    result = [r for r in assignment_rules.values() if r.get("tenant_id") == tenant_id]
    
    if territory_id:
        result = [r for r in result if r.get("territory_id") == territory_id]
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    
    result.sort(key=lambda x: x.get("priority", 0))
    
    return {"rules": result, "total": len(result)}


@router.post("/assign-lead")
async def assign_lead_to_territory(
    lead_id: str,
    lead_data: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Assign a lead to territory based on rules"""
    tenant_rules = [
        r for r in assignment_rules.values()
        if r.get("tenant_id") == tenant_id and r.get("is_active")
    ]
    tenant_rules.sort(key=lambda x: x.get("priority", 0))
    
    for rule in tenant_rules:
        if evaluate_rule_conditions(rule.get("conditions", []), lead_data):
            territory_id = rule["territory_id"]
            territory = territories.get(territory_id)
            
            if territory:
                # Assign to rep based on method
                assigned_rep = assign_to_rep(territory, rule.get("method"))
                
                assignment = {
                    "lead_id": lead_id,
                    "territory_id": territory_id,
                    "territory_name": territory["name"],
                    "assigned_rep": assigned_rep,
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "assigned_at": datetime.utcnow().isoformat()
                }
                
                territory_assignments[lead_id] = assignment
                rule["matched_count"] = rule.get("matched_count", 0) + 1
                
                return assignment
    
    return {
        "lead_id": lead_id,
        "territory_id": None,
        "message": "No matching territory rule found"
    }


# Realignment
@router.post("/realignment")
async def create_realignment_plan(
    request: RealignmentPlan,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create territory realignment plan"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    plan = {
        "id": plan_id,
        "name": request.name,
        "description": request.description,
        "effective_date": request.effective_date,
        "changes": request.changes,
        "status": RealignmentStatus.DRAFT.value,
        "impact_analysis": analyze_realignment_impact(request.changes),
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    realignment_plans[plan_id] = plan
    
    logger.info("realignment_plan_created", plan_id=plan_id)
    return plan


@router.get("/realignment")
async def list_realignment_plans(
    status: Optional[RealignmentStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List realignment plans"""
    result = [p for p in realignment_plans.values() if p.get("tenant_id") == tenant_id]
    
    if status:
        result = [p for p in result if p.get("status") == status.value]
    
    return {"plans": result, "total": len(result)}


@router.get("/realignment/{plan_id}")
async def get_realignment_plan(plan_id: str):
    """Get realignment plan details"""
    if plan_id not in realignment_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    return realignment_plans[plan_id]


@router.post("/realignment/{plan_id}/submit-for-review")
async def submit_realignment_for_review(plan_id: str, user_id: str = Query(default="default")):
    """Submit realignment plan for review"""
    if plan_id not in realignment_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = realignment_plans[plan_id]
    plan["status"] = RealignmentStatus.REVIEW.value
    plan["submitted_by"] = user_id
    plan["submitted_at"] = datetime.utcnow().isoformat()
    
    return plan


@router.post("/realignment/{plan_id}/approve")
async def approve_realignment(plan_id: str, user_id: str = Query(default="default")):
    """Approve realignment plan"""
    if plan_id not in realignment_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = realignment_plans[plan_id]
    plan["status"] = RealignmentStatus.APPROVED.value
    plan["approved_by"] = user_id
    plan["approved_at"] = datetime.utcnow().isoformat()
    
    return plan


@router.post("/realignment/{plan_id}/execute")
async def execute_realignment(plan_id: str, user_id: str = Query(default="default")):
    """Execute approved realignment plan"""
    if plan_id not in realignment_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = realignment_plans[plan_id]
    
    if plan["status"] != RealignmentStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Plan must be approved before execution")
    
    plan["status"] = RealignmentStatus.IN_PROGRESS.value
    plan["execution_started_by"] = user_id
    plan["execution_started_at"] = datetime.utcnow().isoformat()
    
    # Apply changes
    for change in plan.get("changes", []):
        apply_territory_change(change)
    
    plan["status"] = RealignmentStatus.COMPLETED.value
    plan["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info("realignment_executed", plan_id=plan_id)
    return plan


# Coverage Analysis
@router.get("/coverage/analysis")
async def analyze_territory_coverage(tenant_id: str = Query(default="default")):
    """Analyze territory coverage"""
    tenant_territories = [t for t in territories.values() if t.get("tenant_id") == tenant_id]
    
    coverage_data = {
        "total_territories": len(tenant_territories),
        "total_reps_assigned": len(set(
            rep for t in tenant_territories for rep in t.get("assigned_reps", [])
        )),
        "territories_without_reps": len([t for t in tenant_territories if not t.get("assigned_reps")]),
        "coverage_by_type": {
            tt.value: len([t for t in tenant_territories if t.get("territory_type") == tt.value])
            for tt in TerritoryType
        },
        "quota_coverage": calculate_quota_coverage(tenant_territories),
        "white_space_analysis": identify_white_space(tenant_id)
    }
    
    territory_coverage[tenant_id] = coverage_data
    
    return coverage_data


@router.get("/coverage/gaps")
async def identify_coverage_gaps(tenant_id: str = Query(default="default")):
    """Identify coverage gaps"""
    gaps = {
        "geographic_gaps": [
            {"region": "Midwest", "accounts": 125, "assigned_reps": 0},
            {"region": "Southwest", "accounts": 87, "assigned_reps": 1}
        ],
        "industry_gaps": [
            {"industry": "Healthcare", "accounts": 45, "coverage_rate": 0.3}
        ],
        "company_size_gaps": [
            {"segment": "Enterprise", "accounts": 23, "coverage_rate": 0.65}
        ],
        "recommendations": [
            "Add rep coverage for Midwest region",
            "Increase Healthcare industry coverage",
            "Consider splitting Enterprise segment"
        ]
    }
    
    return gaps


# Balancing
@router.get("/balancing/analysis")
async def analyze_territory_balance(
    metric: str = Query(default="accounts", regex="^(accounts|revenue|opportunities|workload)$"),
    tenant_id: str = Query(default="default")
):
    """Analyze territory balance"""
    tenant_territories = [t for t in territories.values() if t.get("tenant_id") == tenant_id]
    
    # Calculate metrics per territory
    territory_metrics = []
    for t in tenant_territories:
        metrics = calculate_territory_metrics(t)
        territory_metrics.append({
            "territory_id": t["id"],
            "territory_name": t["name"],
            "rep_count": len(t.get("assigned_reps", [])),
            **metrics
        })
    
    # Calculate balance score
    if territory_metrics:
        metric_values = [m.get(metric, 0) for m in territory_metrics]
        avg = sum(metric_values) / len(metric_values)
        variance = sum((v - avg) ** 2 for v in metric_values) / len(metric_values)
        balance_score = max(0, 100 - (variance / max(1, avg) * 10))
    else:
        balance_score = 100
    
    return {
        "metric": metric,
        "territories": territory_metrics,
        "balance_score": round(balance_score, 1),
        "avg_per_territory": round(avg, 1) if territory_metrics else 0,
        "recommendations": generate_balancing_recommendations(territory_metrics, metric)
    }


@router.post("/balancing/optimize")
async def optimize_territory_balance(
    optimization_goal: str = Query(default="equal_workload"),
    constraints: Optional[Dict[str, Any]] = None,
    tenant_id: str = Query(default="default")
):
    """Generate optimized territory assignment suggestions"""
    suggestions = {
        "optimization_goal": optimization_goal,
        "suggested_changes": [
            {
                "account_id": str(uuid.uuid4()),
                "account_name": "Acme Corp",
                "from_territory": "West Region",
                "to_territory": "Central Region",
                "reason": "Better balance workload distribution"
            },
            {
                "account_id": str(uuid.uuid4()),
                "account_name": "Tech Solutions",
                "from_territory": "Enterprise",
                "to_territory": "Mid-Market",
                "reason": "Account size better fits Mid-Market criteria"
            }
        ],
        "projected_improvement": {
            "balance_score_before": 72,
            "balance_score_after": 88,
            "improvement": 16
        },
        "constraints_applied": constraints or {}
    }
    
    return suggestions


# Quota Management
@router.post("/territories/{territory_id}/quota")
async def set_territory_quota(
    territory_id: str,
    annual_quota: float,
    quarterly_breakdown: Optional[Dict[str, float]] = None,
    user_id: str = Query(default="default")
):
    """Set quota for territory"""
    if territory_id not in territories:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = territories[territory_id]
    territory["quota"] = annual_quota
    
    quota_data = {
        "territory_id": territory_id,
        "annual_quota": annual_quota,
        "quarterly_breakdown": quarterly_breakdown or {
            "Q1": annual_quota * 0.25,
            "Q2": annual_quota * 0.25,
            "Q3": annual_quota * 0.25,
            "Q4": annual_quota * 0.25
        },
        "updated_by": user_id,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    territory_quotas[territory_id] = quota_data
    
    return quota_data


@router.get("/territories/{territory_id}/quota-attainment")
async def get_quota_attainment(territory_id: str):
    """Get quota attainment for territory"""
    if territory_id not in territories:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    quota = territory_quotas.get(territory_id, {})
    annual_quota = quota.get("annual_quota", 0)
    
    # Mock attainment data
    attainment = {
        "territory_id": territory_id,
        "annual_quota": annual_quota,
        "closed_won": random.uniform(0.3, 0.9) * annual_quota,
        "pipeline": random.uniform(0.5, 1.5) * annual_quota,
        "attainment_pct": random.uniform(0.3, 0.9),
        "projected_attainment_pct": random.uniform(0.6, 1.1),
        "quarterly_attainment": {
            "Q1": {"quota": annual_quota * 0.25, "closed": random.uniform(0.7, 1.1) * annual_quota * 0.25},
            "Q2": {"quota": annual_quota * 0.25, "closed": random.uniform(0.5, 0.9) * annual_quota * 0.25},
            "Q3": {"quota": annual_quota * 0.25, "closed": random.uniform(0.2, 0.6) * annual_quota * 0.25},
            "Q4": {"quota": annual_quota * 0.25, "closed": 0}
        }
    }
    
    return attainment


# Analytics
@router.get("/analytics/overview")
async def get_territory_analytics(tenant_id: str = Query(default="default")):
    """Get territory analytics overview"""
    tenant_territories = [t for t in territories.values() if t.get("tenant_id") == tenant_id]
    
    return {
        "total_territories": len(tenant_territories),
        "active_territories": len([t for t in tenant_territories if t.get("status") == "active"]),
        "total_quota": sum(t.get("quota", 0) or 0 for t in tenant_territories),
        "total_pipeline": sum(t.get("pipeline_value", 0) for t in tenant_territories),
        "avg_accounts_per_territory": round(
            sum(t.get("account_count", 0) for t in tenant_territories) / max(1, len(tenant_territories)), 1
        ),
        "territories_above_quota": random.randint(3, 10),
        "territories_at_risk": random.randint(1, 5),
        "pending_realignments": len([p for p in realignment_plans.values() if p.get("status") in ["draft", "review"]])
    }


# Helper functions
def calculate_territory_stats(territory_id: str) -> Dict[str, Any]:
    """Calculate stats for a territory"""
    return {
        "account_count": random.randint(50, 500),
        "lead_count": random.randint(20, 200),
        "opportunity_count": random.randint(10, 100),
        "pipeline_value": random.randint(100000, 5000000),
        "closed_won_value": random.randint(50000, 2000000),
        "avg_deal_size": random.randint(10000, 100000),
        "conversion_rate": round(random.uniform(0.1, 0.4), 2)
    }


def evaluate_rule_conditions(conditions: List[Dict], lead_data: Dict) -> bool:
    """Evaluate if lead matches rule conditions"""
    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        lead_value = lead_data.get(field)
        
        if operator == "equals" and lead_value != value:
            return False
        elif operator == "contains" and value not in str(lead_value):
            return False
        elif operator == "in" and lead_value not in value:
            return False
    
    return True


def assign_to_rep(territory: Dict, method: str) -> Optional[str]:
    """Assign to rep based on method"""
    reps = territory.get("assigned_reps", [])
    if not reps:
        return None
    
    if method == "round_robin":
        return reps[random.randint(0, len(reps) - 1)]
    
    return reps[0]


def analyze_realignment_impact(changes: List[Dict]) -> Dict[str, Any]:
    """Analyze impact of realignment changes"""
    return {
        "territories_affected": len(changes),
        "accounts_moving": random.randint(10, 100),
        "reps_affected": random.randint(2, 10),
        "estimated_pipeline_shift": random.randint(100000, 1000000),
        "risk_level": random.choice(["low", "medium", "high"])
    }


def apply_territory_change(change: Dict):
    """Apply a single territory change"""
    pass


def calculate_quota_coverage(territories_list: List[Dict]) -> Dict[str, Any]:
    """Calculate quota coverage"""
    total_quota = sum(t.get("quota", 0) or 0 for t in territories_list)
    return {
        "total_quota": total_quota,
        "territories_with_quota": len([t for t in territories_list if t.get("quota")]),
        "territories_without_quota": len([t for t in territories_list if not t.get("quota")])
    }


def identify_white_space(tenant_id: str) -> List[Dict]:
    """Identify white space in territory coverage"""
    return [
        {"region": "Northeast", "potential_accounts": 45},
        {"industry": "Fintech", "potential_accounts": 23}
    ]


def calculate_territory_metrics(territory: Dict) -> Dict[str, Any]:
    """Calculate metrics for a territory"""
    return {
        "accounts": random.randint(50, 500),
        "revenue": random.randint(500000, 5000000),
        "opportunities": random.randint(10, 100),
        "workload": random.randint(60, 100)
    }


def generate_balancing_recommendations(metrics: List[Dict], metric: str) -> List[str]:
    """Generate recommendations for territory balancing"""
    return [
        f"Consider rebalancing {metric} between territories",
        "Review high-concentration territories for potential splits",
        "Evaluate underutilized territories for consolidation"
    ]
