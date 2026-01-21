"""
Lead Routing Routes - Intelligent lead assignment and distribution
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

router = APIRouter(prefix="/lead-routing", tags=["Lead Routing"])


class RoutingMethod(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    TERRITORY = "territory"
    CAPACITY = "capacity"
    SKILLS = "skills"
    HYBRID = "hybrid"
    CUSTOM = "custom"


class LeadSource(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    REFERRAL = "referral"
    PARTNER = "partner"
    EVENT = "event"
    PAID = "paid"
    ORGANIC = "organic"


class LeadPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AssignmentStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REASSIGNED = "reassigned"
    EXPIRED = "expired"


# In-memory storage
routing_rules = {}
assignments = {}
queues = {}
rep_availability = {}


class RoutingRuleCreate(BaseModel):
    name: str
    method: RoutingMethod
    priority: int = 1
    conditions: Optional[Dict[str, Any]] = None
    assigned_reps: Optional[List[str]] = None
    territory_id: Optional[str] = None
    is_active: bool = True


class QueueCreate(BaseModel):
    name: str
    description: Optional[str] = None
    routing_method: RoutingMethod = RoutingMethod.ROUND_ROBIN
    assigned_reps: List[str] = []
    max_per_rep: Optional[int] = None
    sla_minutes: Optional[int] = None


class LeadRouteRequest(BaseModel):
    lead_id: str
    lead_data: Dict[str, Any]
    source: LeadSource
    priority: LeadPriority = LeadPriority.MEDIUM
    force_rep_id: Optional[str] = None


# Routing Rules
@router.post("/rules")
async def create_routing_rule(
    request: RoutingRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a routing rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "method": request.method.value,
        "priority": request.priority,
        "conditions": request.conditions or {},
        "assigned_reps": request.assigned_reps or [],
        "territory_id": request.territory_id,
        "is_active": request.is_active,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    routing_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_routing_rules(
    is_active: Optional[bool] = None,
    method: Optional[RoutingMethod] = None,
    tenant_id: str = Query(default="default")
):
    """List routing rules"""
    result = [r for r in routing_rules.values() if r.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    if method:
        result = [r for r in result if r.get("method") == method.value]
    
    result.sort(key=lambda x: x.get("priority", 0))
    
    return {"rules": result, "total": len(result)}


@router.get("/rules/{rule_id}")
async def get_routing_rule(rule_id: str):
    """Get a routing rule"""
    if rule_id not in routing_rules:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return routing_rules[rule_id]


@router.put("/rules/{rule_id}")
async def update_routing_rule(
    rule_id: str,
    request: RoutingRuleCreate
):
    """Update a routing rule"""
    if rule_id not in routing_rules:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    rule = routing_rules[rule_id]
    rule.update({
        "name": request.name,
        "method": request.method.value,
        "priority": request.priority,
        "conditions": request.conditions or {},
        "assigned_reps": request.assigned_reps or [],
        "territory_id": request.territory_id,
        "is_active": request.is_active,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_routing_rule(rule_id: str):
    """Delete a routing rule"""
    if rule_id not in routing_rules:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    del routing_rules[rule_id]
    return {"status": "deleted", "id": rule_id}


# Lead Assignment
@router.post("/route")
async def route_lead(
    request: LeadRouteRequest,
    tenant_id: str = Query(default="default")
):
    """Route a lead to the best rep"""
    assignment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Simulate routing logic
    if request.force_rep_id:
        assigned_rep = request.force_rep_id
        method_used = "manual"
    else:
        # Simulate finding best rep
        assigned_rep = f"rep_{random.randint(1, 10)}"
        method_used = "round_robin"
    
    assignment = {
        "id": assignment_id,
        "lead_id": request.lead_id,
        "lead_data": request.lead_data,
        "source": request.source.value,
        "priority": request.priority.value,
        "assigned_rep_id": assigned_rep,
        "status": AssignmentStatus.ASSIGNED.value,
        "method_used": method_used,
        "tenant_id": tenant_id,
        "assigned_at": now.isoformat(),
        "sla_deadline": (now + timedelta(hours=24)).isoformat()
    }
    
    assignments[assignment_id] = assignment
    
    return assignment


@router.get("/assignments")
async def list_assignments(
    rep_id: Optional[str] = None,
    status: Optional[AssignmentStatus] = None,
    priority: Optional[LeadPriority] = None,
    start_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List lead assignments"""
    result = [a for a in assignments.values() if a.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [a for a in result if a.get("assigned_rep_id") == rep_id]
    if status:
        result = [a for a in result if a.get("status") == status.value]
    if priority:
        result = [a for a in result if a.get("priority") == priority.value]
    
    result.sort(key=lambda x: x.get("assigned_at", ""), reverse=True)
    
    return {"assignments": result[:limit], "total": len(result)}


@router.post("/assignments/{assignment_id}/accept")
async def accept_assignment(assignment_id: str):
    """Rep accepts a lead assignment"""
    if assignment_id not in assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    assignment = assignments[assignment_id]
    assignment["status"] = AssignmentStatus.ACCEPTED.value
    assignment["accepted_at"] = datetime.utcnow().isoformat()
    
    return assignment


@router.post("/assignments/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    reason: str = Query(default="")
):
    """Rep rejects a lead assignment"""
    if assignment_id not in assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    assignment = assignments[assignment_id]
    assignment["status"] = AssignmentStatus.REJECTED.value
    assignment["rejected_at"] = datetime.utcnow().isoformat()
    assignment["rejection_reason"] = reason
    
    return assignment


@router.post("/assignments/{assignment_id}/reassign")
async def reassign_lead(
    assignment_id: str,
    new_rep_id: str = Query(...),
    reason: str = Query(default="")
):
    """Reassign a lead to a different rep"""
    if assignment_id not in assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    assignment = assignments[assignment_id]
    old_rep = assignment["assigned_rep_id"]
    
    assignment["previous_rep_id"] = old_rep
    assignment["assigned_rep_id"] = new_rep_id
    assignment["status"] = AssignmentStatus.REASSIGNED.value
    assignment["reassigned_at"] = datetime.utcnow().isoformat()
    assignment["reassignment_reason"] = reason
    
    return assignment


# Queues
@router.post("/queues")
async def create_queue(
    request: QueueCreate,
    tenant_id: str = Query(default="default")
):
    """Create a lead queue"""
    queue_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    queue = {
        "id": queue_id,
        "name": request.name,
        "description": request.description,
        "routing_method": request.routing_method.value,
        "assigned_reps": request.assigned_reps,
        "max_per_rep": request.max_per_rep,
        "sla_minutes": request.sla_minutes,
        "lead_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    queues[queue_id] = queue
    
    return queue


@router.get("/queues")
async def list_queues(tenant_id: str = Query(default="default")):
    """List lead queues"""
    result = [q for q in queues.values() if q.get("tenant_id") == tenant_id]
    return {"queues": result, "total": len(result)}


@router.get("/queues/{queue_id}")
async def get_queue(queue_id: str):
    """Get a queue with stats"""
    if queue_id not in queues:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    queue = queues[queue_id]
    
    # Add stats
    queue["stats"] = {
        "leads_in_queue": random.randint(0, 50),
        "avg_wait_time_minutes": random.randint(5, 60),
        "leads_assigned_today": random.randint(10, 100),
        "sla_compliance_rate": round(random.uniform(0.8, 1.0), 3)
    }
    
    return queue


# Rep Availability
@router.put("/reps/{rep_id}/availability")
async def update_rep_availability(
    rep_id: str,
    is_available: bool = Query(...),
    capacity: Optional[int] = None,
    tenant_id: str = Query(default="default")
):
    """Update rep availability for lead routing"""
    rep_availability[rep_id] = {
        "rep_id": rep_id,
        "is_available": is_available,
        "capacity": capacity,
        "current_leads": random.randint(0, capacity or 20),
        "updated_at": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id
    }
    
    return rep_availability[rep_id]


@router.get("/reps/availability")
async def get_all_rep_availability(tenant_id: str = Query(default="default")):
    """Get availability for all reps"""
    result = [r for r in rep_availability.values() if r.get("tenant_id") == tenant_id]
    
    # Add mock data if empty
    if not result:
        for i in range(5):
            result.append({
                "rep_id": f"rep_{i+1}",
                "name": f"Sales Rep {i+1}",
                "is_available": random.choice([True, True, True, False]),
                "capacity": 20,
                "current_leads": random.randint(5, 20),
                "utilization": round(random.uniform(0.4, 0.95), 2)
            })
    
    return {"reps": result}


# Analytics
@router.get("/analytics/distribution")
async def get_lead_distribution(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get lead distribution analytics"""
    reps = [f"Rep {i+1}" for i in range(8)]
    
    distribution = []
    for rep in reps:
        distribution.append({
            "rep": rep,
            "leads_assigned": random.randint(50, 200),
            "leads_accepted": random.randint(40, 180),
            "leads_converted": random.randint(10, 50),
            "avg_response_time_min": random.randint(5, 60),
            "sla_compliance": round(random.uniform(0.7, 1.0), 3)
        })
    
    return {
        "period_days": days,
        "distribution": distribution,
        "totals": {
            "total_assigned": sum(d["leads_assigned"] for d in distribution),
            "total_converted": sum(d["leads_converted"] for d in distribution),
            "avg_conversion_rate": round(random.uniform(0.15, 0.35), 3)
        }
    }


@router.get("/analytics/response-time")
async def get_response_time_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get response time analytics"""
    timeline = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()[:10]
        timeline.append({
            "date": date,
            "avg_response_time_min": random.randint(10, 45),
            "leads_within_sla": random.randint(70, 95),
            "leads_missed_sla": random.randint(5, 20)
        })
    
    return {
        "period_days": days,
        "timeline": timeline,
        "summary": {
            "avg_response_time_min": round(sum(t["avg_response_time_min"] for t in timeline) / len(timeline), 1),
            "sla_compliance_rate": round(random.uniform(0.75, 0.95), 3),
            "best_performing_rep": f"Rep {random.randint(1, 8)}",
            "improvement_trend": random.choice(["improving", "stable", "declining"])
        }
    }


@router.get("/analytics/source")
async def get_leads_by_source(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get lead routing analytics by source"""
    sources = [s.value for s in LeadSource]
    
    source_data = []
    for source in sources:
        source_data.append({
            "source": source,
            "leads": random.randint(20, 200),
            "avg_response_time_min": random.randint(10, 60),
            "conversion_rate": round(random.uniform(0.1, 0.4), 3),
            "avg_deal_value": random.randint(5000, 50000)
        })
    
    source_data.sort(key=lambda x: x["leads"], reverse=True)
    
    return {
        "period_days": days,
        "sources": source_data
    }
