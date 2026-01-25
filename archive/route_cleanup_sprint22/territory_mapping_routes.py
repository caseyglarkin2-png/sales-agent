"""
Territory Mapping Routes - Geographic and account territory management
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

router = APIRouter(prefix="/territory-mapping", tags=["Territory Mapping"])


class TerritoryType(str, Enum):
    GEOGRAPHIC = "geographic"
    NAMED_ACCOUNTS = "named_accounts"
    INDUSTRY = "industry"
    COMPANY_SIZE = "company_size"
    HYBRID = "hybrid"


class AssignmentStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    BALANCED_WORKLOAD = "balanced_workload"
    PERFORMANCE_BASED = "performance_based"
    MANUAL = "manual"
    WEIGHTED = "weighted"


class TerritoryStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"


# In-memory storage
territory_maps = {}
territory_rules = {}
territory_assignments = {}
coverage_gaps = {}


class TerritoryMapCreate(BaseModel):
    name: str
    description: Optional[str] = None
    territory_type: TerritoryType
    assignment_strategy: AssignmentStrategy = AssignmentStrategy.BALANCED_WORKLOAD
    regions: Optional[List[Dict[str, Any]]] = None
    criteria: Optional[Dict[str, Any]] = None  # Rules for assignment


class TerritoryRuleCreate(BaseModel):
    map_id: str
    rule_name: str
    rule_type: str  # geographic, firmographic, custom
    conditions: Dict[str, Any]
    priority: int = 1
    assign_to: Optional[str] = None  # Rep or team ID


class TerritoryAssignmentCreate(BaseModel):
    map_id: str
    account_id: str
    rep_id: Optional[str] = None
    override_reason: Optional[str] = None


# Territory Maps
@router.post("/maps")
async def create_territory_map(
    request: TerritoryMapCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new territory map"""
    map_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    territory_map = {
        "id": map_id,
        "name": request.name,
        "description": request.description,
        "territory_type": request.territory_type.value,
        "assignment_strategy": request.assignment_strategy.value,
        "regions": request.regions or [],
        "criteria": request.criteria or {},
        "status": TerritoryStatus.ACTIVE.value,
        "total_accounts": 0,
        "assigned_reps": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    territory_maps[map_id] = territory_map
    
    logger.info("territory_map_created", map_id=map_id, name=request.name)
    
    return territory_map


@router.get("/maps")
async def list_territory_maps(
    territory_type: Optional[TerritoryType] = None,
    status: Optional[TerritoryStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List all territory maps"""
    result = [m for m in territory_maps.values() if m.get("tenant_id") == tenant_id]
    
    if territory_type:
        result = [m for m in result if m.get("territory_type") == territory_type.value]
    if status:
        result = [m for m in result if m.get("status") == status.value]
    
    return {"maps": result, "total": len(result)}


@router.get("/maps/{map_id}")
async def get_territory_map(
    map_id: str,
    tenant_id: str = Query(default="default")
):
    """Get territory map details"""
    if map_id not in territory_maps:
        raise HTTPException(status_code=404, detail="Territory map not found")
    return territory_maps[map_id]


@router.patch("/maps/{map_id}")
async def update_territory_map(
    map_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update territory map"""
    if map_id not in territory_maps:
        raise HTTPException(status_code=404, detail="Territory map not found")
    
    territory_map = territory_maps[map_id]
    
    allowed_fields = ["name", "description", "regions", "criteria", "assignment_strategy", "status"]
    for key, value in updates.items():
        if key in allowed_fields:
            territory_map[key] = value
    
    territory_map["updated_at"] = datetime.utcnow().isoformat()
    
    return territory_map


@router.delete("/maps/{map_id}")
async def delete_territory_map(
    map_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete territory map"""
    if map_id not in territory_maps:
        raise HTTPException(status_code=404, detail="Territory map not found")
    
    del territory_maps[map_id]
    
    return {"message": "Territory map deleted"}


# Territory Rules
@router.post("/rules")
async def create_territory_rule(
    request: TerritoryRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create territory assignment rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "map_id": request.map_id,
        "rule_name": request.rule_name,
        "rule_type": request.rule_type,
        "conditions": request.conditions,
        "priority": request.priority,
        "assign_to": request.assign_to,
        "is_active": True,
        "matches_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    territory_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_territory_rules(
    map_id: Optional[str] = None,
    rule_type: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List territory rules"""
    result = [r for r in territory_rules.values() if r.get("tenant_id") == tenant_id]
    
    if map_id:
        result = [r for r in result if r.get("map_id") == map_id]
    if rule_type:
        result = [r for r in result if r.get("rule_type") == rule_type]
    
    # Sort by priority
    result = sorted(result, key=lambda x: x.get("priority", 0))
    
    return {"rules": result, "total": len(result)}


@router.patch("/rules/{rule_id}")
async def update_territory_rule(
    rule_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update territory rule"""
    if rule_id not in territory_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = territory_rules[rule_id]
    
    for key, value in updates.items():
        if key in ["rule_name", "conditions", "priority", "assign_to", "is_active"]:
            rule[key] = value
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_territory_rule(
    rule_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete territory rule"""
    if rule_id not in territory_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    del territory_rules[rule_id]
    
    return {"message": "Rule deleted"}


# Account Assignments
@router.post("/assignments")
async def assign_account(
    request: TerritoryAssignmentCreate,
    tenant_id: str = Query(default="default")
):
    """Manually assign account to territory/rep"""
    assignment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    assignment = {
        "id": assignment_id,
        "map_id": request.map_id,
        "account_id": request.account_id,
        "rep_id": request.rep_id,
        "override_reason": request.override_reason,
        "assignment_type": "manual" if request.override_reason else "automatic",
        "previous_rep_id": None,
        "tenant_id": tenant_id,
        "assigned_at": now.isoformat()
    }
    
    territory_assignments[assignment_id] = assignment
    
    return assignment


@router.get("/assignments")
async def list_assignments(
    map_id: Optional[str] = None,
    rep_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List territory assignments"""
    result = [a for a in territory_assignments.values() if a.get("tenant_id") == tenant_id]
    
    if map_id:
        result = [a for a in result if a.get("map_id") == map_id]
    if rep_id:
        result = [a for a in result if a.get("rep_id") == rep_id]
    
    return {"assignments": result, "total": len(result)}


@router.post("/assignments/bulk-reassign")
async def bulk_reassign(
    from_rep_id: str,
    to_rep_id: str,
    account_ids: Optional[List[str]] = None,
    reason: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Bulk reassign accounts from one rep to another"""
    reassigned = 0
    now = datetime.utcnow()
    
    for assignment in territory_assignments.values():
        if assignment.get("rep_id") == from_rep_id:
            if account_ids is None or assignment.get("account_id") in account_ids:
                assignment["previous_rep_id"] = from_rep_id
                assignment["rep_id"] = to_rep_id
                assignment["override_reason"] = reason or "Bulk reassignment"
                assignment["assigned_at"] = now.isoformat()
                reassigned += 1
    
    return {"message": f"Reassigned {reassigned} accounts", "from": from_rep_id, "to": to_rep_id}


# Auto-Assignment
@router.post("/auto-assign")
async def auto_assign_accounts(
    map_id: str,
    account_ids: Optional[List[str]] = None,
    dry_run: bool = True,
    tenant_id: str = Query(default="default")
):
    """Auto-assign accounts based on territory rules"""
    assignments = []
    
    # Simulate auto-assignment
    sample_accounts = account_ids or [f"account_{i}" for i in range(10)]
    sample_reps = [f"rep_{i}" for i in range(5)]
    
    for account in sample_accounts:
        assignments.append({
            "account_id": account,
            "assigned_to": random.choice(sample_reps),
            "matched_rule": f"rule_{random.randint(1, 5)}",
            "confidence": round(random.uniform(0.7, 1.0), 2)
        })
    
    if not dry_run:
        # Actually create assignments
        for a in assignments:
            await assign_account(
                TerritoryAssignmentCreate(
                    map_id=map_id,
                    account_id=a["account_id"],
                    rep_id=a["assigned_to"]
                ),
                tenant_id=tenant_id
            )
    
    return {
        "dry_run": dry_run,
        "assignments": assignments,
        "total": len(assignments)
    }


# Coverage Analysis
@router.get("/coverage/{map_id}")
async def get_coverage_analysis(
    map_id: str,
    tenant_id: str = Query(default="default")
):
    """Analyze territory coverage"""
    return {
        "map_id": map_id,
        "coverage_summary": {
            "total_accounts": random.randint(500, 2000),
            "assigned_accounts": random.randint(400, 1800),
            "unassigned_accounts": random.randint(50, 200),
            "coverage_rate": round(random.uniform(0.85, 0.98), 3)
        },
        "by_region": [
            {
                "region": region,
                "accounts": random.randint(50, 300),
                "assigned": random.randint(40, 280),
                "reps": random.randint(1, 5),
                "coverage_rate": round(random.uniform(0.80, 1.0), 3)
            }
            for region in ["Northeast", "Southeast", "Midwest", "West", "Southwest"]
        ],
        "gaps": [
            {
                "region": "Northwest",
                "unassigned_accounts": random.randint(10, 50),
                "potential_revenue": random.randint(100000, 500000)
            },
            {
                "region": "Southeast - Healthcare",
                "unassigned_accounts": random.randint(5, 25),
                "potential_revenue": random.randint(50000, 200000)
            }
        ]
    }


# Workload Balance
@router.get("/balance/{map_id}")
async def get_workload_balance(
    map_id: str,
    tenant_id: str = Query(default="default")
):
    """Analyze workload balance across reps"""
    return {
        "map_id": map_id,
        "balance_score": round(random.uniform(0.70, 0.95), 2),
        "reps": [
            {
                "rep_id": f"rep_{i}",
                "name": f"Sales Rep {i + 1}",
                "accounts": random.randint(20, 80),
                "total_revenue": random.randint(500000, 3000000),
                "active_deals": random.randint(5, 25),
                "workload_score": round(random.uniform(0.5, 1.5), 2),
                "capacity": "over" if random.random() > 0.7 else "optimal" if random.random() > 0.3 else "under"
            }
            for i in range(6)
        ],
        "recommendations": [
            {
                "type": "rebalance",
                "from_rep": "rep_3",
                "to_rep": "rep_1",
                "accounts": 5,
                "reason": "Rep 3 is over capacity, Rep 1 has bandwidth"
            },
            {
                "type": "new_hire",
                "region": "West",
                "reason": "Region is understaffed for growth targets"
            }
        ]
    }


# Visualization Data
@router.get("/maps/{map_id}/visualization")
async def get_map_visualization(
    map_id: str,
    tenant_id: str = Query(default="default")
):
    """Get data for territory map visualization"""
    return {
        "map_id": map_id,
        "type": "geographic",
        "regions": [
            {
                "id": f"region_{i}",
                "name": name,
                "bounds": {
                    "north": 40 + random.uniform(-5, 10),
                    "south": 35 + random.uniform(-5, 5),
                    "east": -80 + random.uniform(-10, 10),
                    "west": -90 + random.uniform(-10, 10)
                },
                "color": f"#{random.randint(100000, 999999)}",
                "rep_id": f"rep_{i}",
                "accounts": random.randint(30, 100),
                "revenue": random.randint(500000, 2000000)
            }
            for i, name in enumerate(["Northeast", "Southeast", "Midwest", "West", "Southwest"])
        ],
        "account_markers": [
            {
                "account_id": f"account_{i}",
                "lat": 35 + random.uniform(-10, 15),
                "lng": -80 + random.uniform(-30, 10),
                "size": random.choice(["small", "medium", "large"]),
                "value": random.randint(10000, 500000)
            }
            for i in range(20)
        ]
    }


# Conflict Detection
@router.get("/conflicts")
async def detect_conflicts(
    map_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Detect territory conflicts and overlaps"""
    return {
        "conflicts": [
            {
                "type": "overlap",
                "account_id": f"account_{random.randint(1, 100)}",
                "rep_1": "rep_1",
                "rep_2": "rep_3",
                "rule_1": "Geographic - West",
                "rule_2": "Named Accounts - Enterprise",
                "recommendation": "Assign to rep_1 (geographic takes precedence)"
            },
            {
                "type": "gap",
                "description": "No assignment rule for accounts in Vermont",
                "affected_accounts": random.randint(5, 20),
                "recommendation": "Add Vermont to Northeast region rule"
            }
        ],
        "total_conflicts": 2
    }


# History
@router.get("/history/{account_id}")
async def get_assignment_history(
    account_id: str,
    tenant_id: str = Query(default="default")
):
    """Get territory assignment history for an account"""
    return {
        "account_id": account_id,
        "history": [
            {
                "rep_id": f"rep_{random.randint(1, 5)}",
                "from_date": (datetime.utcnow() - timedelta(days=random.randint(180, 365))).isoformat(),
                "to_date": (datetime.utcnow() - timedelta(days=random.randint(90, 179))).isoformat(),
                "reason": "Initial assignment"
            },
            {
                "rep_id": f"rep_{random.randint(1, 5)}",
                "from_date": (datetime.utcnow() - timedelta(days=random.randint(30, 89))).isoformat(),
                "to_date": None,
                "reason": "Territory rebalancing"
            }
        ]
    }
