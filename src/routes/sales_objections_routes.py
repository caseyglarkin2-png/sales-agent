"""
Sales Objections Routes - Objection handling and response management
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

router = APIRouter(prefix="/objections", tags=["Sales Objections"])


class ObjectionCategory(str, Enum):
    PRICE = "price"
    BUDGET = "budget"
    TIMING = "timing"
    COMPETITION = "competition"
    NEED = "need"
    AUTHORITY = "authority"
    TRUST = "trust"
    IMPLEMENTATION = "implementation"
    INTEGRATION = "integration"
    FEATURES = "features"
    SUPPORT = "support"
    OTHER = "other"


class ObjectionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DEAL_BREAKER = "deal_breaker"


class ObjectionStatus(str, Enum):
    NEW = "new"
    ADDRESSED = "addressed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    UNRESOLVED = "unresolved"


# In-memory storage
objection_library = {}
deal_objections = {}
objection_responses = {}
objection_analytics_data = {}


class ObjectionLibraryCreate(BaseModel):
    category: ObjectionCategory
    objection_text: str
    severity: ObjectionSeverity = ObjectionSeverity.MEDIUM
    common_responses: List[str] = []
    supporting_content: List[str] = []  # Content IDs, case studies, etc.
    keywords: List[str] = []
    industry_specific: Optional[List[str]] = None


class DealObjectionCreate(BaseModel):
    deal_id: str
    category: ObjectionCategory
    objection_text: str
    severity: ObjectionSeverity = ObjectionSeverity.MEDIUM
    raised_by: Optional[str] = None
    raised_at: Optional[str] = None
    context: Optional[str] = None


class ObjectionResponseCreate(BaseModel):
    objection_id: str
    response_text: str
    response_type: str = "verbal"  # verbal, email, document
    outcome: Optional[str] = None  # resolved, partially_resolved, not_resolved


# Objection Library
@router.post("/library")
async def add_to_library(
    request: ObjectionLibraryCreate,
    tenant_id: str = Query(default="default")
):
    """Add objection to library"""
    objection_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    objection = {
        "id": objection_id,
        "category": request.category.value,
        "objection_text": request.objection_text,
        "severity": request.severity.value,
        "common_responses": request.common_responses,
        "supporting_content": request.supporting_content,
        "keywords": request.keywords,
        "industry_specific": request.industry_specific,
        "times_encountered": 0,
        "times_resolved": 0,
        "avg_resolution_score": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    objection_library[objection_id] = objection
    
    return objection


@router.get("/library")
async def list_library_objections(
    category: Optional[ObjectionCategory] = None,
    severity: Optional[ObjectionSeverity] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List objections from library"""
    result = [o for o in objection_library.values() if o.get("tenant_id") == tenant_id]
    
    if category:
        result = [o for o in result if o.get("category") == category.value]
    if severity:
        result = [o for o in result if o.get("severity") == severity.value]
    if search:
        result = [o for o in result if search.lower() in o.get("objection_text", "").lower()]
    
    return {"objections": result, "total": len(result)}


@router.get("/library/{objection_id}")
async def get_library_objection(
    objection_id: str,
    tenant_id: str = Query(default="default")
):
    """Get objection from library with responses"""
    if objection_id not in objection_library:
        raise HTTPException(status_code=404, detail="Objection not found")
    return objection_library[objection_id]


@router.patch("/library/{objection_id}")
async def update_library_objection(
    objection_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update library objection"""
    if objection_id not in objection_library:
        raise HTTPException(status_code=404, detail="Objection not found")
    
    objection = objection_library[objection_id]
    
    for key, value in updates.items():
        if key in ["common_responses", "supporting_content", "keywords", "severity"]:
            objection[key] = value
    
    objection["updated_at"] = datetime.utcnow().isoformat()
    
    return objection


@router.post("/library/{objection_id}/responses")
async def add_response_to_library(
    objection_id: str,
    response_text: str,
    effectiveness_score: Optional[float] = None,
    tenant_id: str = Query(default="default")
):
    """Add a response to library objection"""
    if objection_id not in objection_library:
        raise HTTPException(status_code=404, detail="Objection not found")
    
    objection = objection_library[objection_id]
    if "common_responses" not in objection:
        objection["common_responses"] = []
    
    objection["common_responses"].append({
        "text": response_text,
        "effectiveness_score": effectiveness_score,
        "added_at": datetime.utcnow().isoformat()
    })
    
    return objection


# Deal Objections
@router.post("/deals")
async def log_deal_objection(
    request: DealObjectionCreate,
    tenant_id: str = Query(default="default")
):
    """Log an objection on a deal"""
    objection_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    objection = {
        "id": objection_id,
        "deal_id": request.deal_id,
        "category": request.category.value,
        "objection_text": request.objection_text,
        "severity": request.severity.value,
        "raised_by": request.raised_by,
        "raised_at": request.raised_at or now.isoformat(),
        "context": request.context,
        "status": ObjectionStatus.NEW.value,
        "responses": [],
        "resolved_at": None,
        "resolution_notes": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    deal_objections[objection_id] = objection
    
    logger.info("deal_objection_logged", objection_id=objection_id, deal_id=request.deal_id)
    
    return objection


@router.get("/deals")
async def list_deal_objections(
    deal_id: Optional[str] = None,
    category: Optional[ObjectionCategory] = None,
    status: Optional[ObjectionStatus] = None,
    severity: Optional[ObjectionSeverity] = None,
    tenant_id: str = Query(default="default")
):
    """List deal objections"""
    result = [o for o in deal_objections.values() if o.get("tenant_id") == tenant_id]
    
    if deal_id:
        result = [o for o in result if o.get("deal_id") == deal_id]
    if category:
        result = [o for o in result if o.get("category") == category.value]
    if status:
        result = [o for o in result if o.get("status") == status.value]
    if severity:
        result = [o for o in result if o.get("severity") == severity.value]
    
    return {"objections": result, "total": len(result)}


@router.get("/deals/{objection_id}")
async def get_deal_objection(
    objection_id: str,
    tenant_id: str = Query(default="default")
):
    """Get deal objection details"""
    if objection_id not in deal_objections:
        raise HTTPException(status_code=404, detail="Objection not found")
    return deal_objections[objection_id]


@router.post("/deals/{objection_id}/respond")
async def respond_to_objection(
    objection_id: str,
    request: ObjectionResponseCreate,
    tenant_id: str = Query(default="default")
):
    """Add response to a deal objection"""
    if objection_id not in deal_objections:
        raise HTTPException(status_code=404, detail="Objection not found")
    
    objection = deal_objections[objection_id]
    now = datetime.utcnow()
    
    response = {
        "id": str(uuid.uuid4()),
        "response_text": request.response_text,
        "response_type": request.response_type,
        "outcome": request.outcome,
        "responded_by": "user_1",
        "responded_at": now.isoformat()
    }
    
    if "responses" not in objection:
        objection["responses"] = []
    
    objection["responses"].append(response)
    objection["status"] = ObjectionStatus.ADDRESSED.value
    
    return objection


@router.post("/deals/{objection_id}/resolve")
async def resolve_objection(
    objection_id: str,
    resolution_notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Mark objection as resolved"""
    if objection_id not in deal_objections:
        raise HTTPException(status_code=404, detail="Objection not found")
    
    objection = deal_objections[objection_id]
    objection["status"] = ObjectionStatus.RESOLVED.value
    objection["resolved_at"] = datetime.utcnow().isoformat()
    objection["resolution_notes"] = resolution_notes
    
    return objection


@router.post("/deals/{objection_id}/escalate")
async def escalate_objection(
    objection_id: str,
    escalate_to: str,
    reason: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Escalate objection to manager/specialist"""
    if objection_id not in deal_objections:
        raise HTTPException(status_code=404, detail="Objection not found")
    
    objection = deal_objections[objection_id]
    objection["status"] = ObjectionStatus.ESCALATED.value
    objection["escalated_to"] = escalate_to
    objection["escalation_reason"] = reason
    objection["escalated_at"] = datetime.utcnow().isoformat()
    
    return objection


# AI Suggestions
@router.post("/suggest-response")
async def suggest_objection_response(
    objection_text: str,
    category: Optional[ObjectionCategory] = None,
    deal_context: Optional[Dict[str, Any]] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-suggested responses for an objection"""
    suggestions = [
        {
            "response": "I understand your concern about pricing. Many of our customers initially felt the same way. Let me share how companies like yours typically see ROI within the first 6 months...",
            "confidence": 0.92,
            "category": "value_justification"
        },
        {
            "response": "That's a valid point. Rather than comparing just the price, let's look at the total cost of ownership including time saved and productivity gains...",
            "confidence": 0.88,
            "category": "tco_comparison"
        },
        {
            "response": "I hear you. We offer flexible payment terms that can help with budget constraints. Would quarterly billing work better for your organization?",
            "confidence": 0.85,
            "category": "payment_flexibility"
        }
    ]
    
    return {
        "objection_text": objection_text,
        "detected_category": category.value if category else "price",
        "suggestions": suggestions,
        "supporting_content": [
            {"type": "case_study", "title": "How Acme Corp achieved 300% ROI"},
            {"type": "calculator", "title": "ROI Calculator"},
            {"type": "comparison", "title": "Total Cost Comparison Sheet"}
        ]
    }


@router.get("/suggest-preemptive")
async def suggest_preemptive_handling(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get suggestions for preemptively addressing likely objections"""
    return {
        "deal_id": deal_id,
        "predicted_objections": [
            {
                "category": "price",
                "likelihood": 0.85,
                "reason": "Similar deals in this industry often raise pricing concerns",
                "preemptive_strategy": "Lead with ROI and customer success stories before discussing pricing"
            },
            {
                "category": "integration",
                "likelihood": 0.70,
                "reason": "Customer uses legacy systems that typically require custom integration",
                "preemptive_strategy": "Proactively discuss integration options and past successful integrations"
            },
            {
                "category": "timing",
                "likelihood": 0.55,
                "reason": "End of fiscal year approaching",
                "preemptive_strategy": "Offer implementation flexibility and phased rollout options"
            }
        ]
    }


# Analytics
@router.get("/analytics")
async def get_objection_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get objection analytics"""
    return {
        "period_days": days,
        "summary": {
            "total_objections": random.randint(50, 200),
            "resolved": random.randint(30, 150),
            "unresolved": random.randint(5, 30),
            "resolution_rate": round(random.uniform(0.70, 0.90), 3)
        },
        "by_category": {
            "price": random.randint(20, 80),
            "timing": random.randint(10, 40),
            "competition": random.randint(10, 35),
            "features": random.randint(5, 25),
            "implementation": random.randint(5, 20)
        },
        "by_severity": {
            "low": random.randint(15, 50),
            "medium": random.randint(20, 80),
            "high": random.randint(10, 40),
            "deal_breaker": random.randint(2, 15)
        },
        "avg_resolution_time_hours": random.randint(24, 96),
        "most_effective_responses": [
            {"category": "price", "response_type": "ROI calculation", "success_rate": 0.82},
            {"category": "timing", "response_type": "Phased implementation", "success_rate": 0.78},
            {"category": "competition", "response_type": "Feature comparison", "success_rate": 0.75}
        ],
        "impact_on_deals": {
            "deals_with_objections": random.randint(30, 100),
            "deals_won_after_objection": random.randint(15, 60),
            "win_rate_after_resolution": round(random.uniform(0.45, 0.65), 3)
        }
    }


@router.get("/analytics/by-rep")
async def get_objection_analytics_by_rep(
    tenant_id: str = Query(default="default")
):
    """Get objection handling analytics by sales rep"""
    return {
        "reps": [
            {
                "rep_id": f"user_{i}",
                "name": f"Sales Rep {i + 1}",
                "objections_handled": random.randint(10, 50),
                "resolution_rate": round(random.uniform(0.60, 0.95), 3),
                "avg_resolution_time_hours": random.randint(12, 72),
                "top_category": random.choice(["price", "timing", "features"])
            }
            for i in range(5)
        ]
    }


# Training Content
@router.get("/training/{category}")
async def get_objection_training(
    category: ObjectionCategory,
    tenant_id: str = Query(default="default")
):
    """Get training materials for handling specific objection category"""
    return {
        "category": category.value,
        "overview": f"Best practices for handling {category.value} objections",
        "key_principles": [
            "Acknowledge the concern genuinely",
            "Ask clarifying questions",
            "Provide relevant evidence",
            "Check for understanding"
        ],
        "example_scenarios": [
            {
                "scenario": f"Customer says '{category.value} is their main concern'",
                "recommended_response": "Acknowledge, empathize, then redirect to value...",
                "common_mistakes": ["Getting defensive", "Offering discounts too quickly"]
            }
        ],
        "resources": [
            {"type": "video", "title": f"Mastering {category.value} objections", "duration_minutes": 15},
            {"type": "script", "title": f"{category.value} handling script"},
            {"type": "battle_card", "title": f"{category.value} battle card"}
        ]
    }
