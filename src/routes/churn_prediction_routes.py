"""
Churn Prediction Routes - AI-powered churn risk analysis and prevention
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

router = APIRouter(prefix="/churn-prediction", tags=["Churn Prediction"])


class ChurnRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChurnReason(str, Enum):
    POOR_ADOPTION = "poor_adoption"
    SUPPORT_ISSUES = "support_issues"
    COMPETITOR = "competitor"
    BUDGET_CUTS = "budget_cuts"
    CHAMPION_LEFT = "champion_left"
    PRODUCT_GAP = "product_gap"
    PRICE = "price"
    IMPLEMENTATION = "implementation"
    NO_VALUE = "no_value"


class InterventionType(str, Enum):
    EXECUTIVE_OUTREACH = "executive_outreach"
    SUCCESS_CALL = "success_call"
    TRAINING = "training"
    FEATURE_DEMO = "feature_demo"
    DISCOUNT_OFFER = "discount_offer"
    ROADMAP_PREVIEW = "roadmap_preview"
    ESCALATION = "escalation"


class InterventionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"


# In-memory storage
churn_predictions = {}
churn_interventions = {}
churn_signals = {}


class InterventionCreate(BaseModel):
    account_id: str
    intervention_type: InterventionType
    assigned_to: str
    due_date: datetime
    notes: Optional[str] = None


class SignalCreate(BaseModel):
    account_id: str
    signal_type: str
    severity: ChurnRisk
    description: str


# Dashboard
@router.get("/dashboard")
async def get_churn_dashboard(
    tenant_id: str = Query(default="default")
):
    """Get churn prediction dashboard"""
    now = datetime.utcnow()
    
    return {
        "generated_at": now.isoformat(),
        "summary": {
            "total_accounts": random.randint(200, 500),
            "at_risk_accounts": random.randint(15, 50),
            "critical_risk_accounts": random.randint(3, 12),
            "high_risk_accounts": random.randint(5, 20),
            "medium_risk_accounts": random.randint(10, 30),
            "revenue_at_risk": random.randint(500000, 2000000),
            "churn_rate_current": round(random.uniform(0.02, 0.08), 3),
            "churn_rate_previous": round(random.uniform(0.02, 0.08), 3),
            "prediction_accuracy": round(random.uniform(0.80, 0.92), 2)
        },
        "risk_distribution": [
            {"risk_level": ChurnRisk.CRITICAL.value, "count": random.randint(3, 10), "arr": random.randint(150000, 500000)},
            {"risk_level": ChurnRisk.HIGH.value, "count": random.randint(5, 15), "arr": random.randint(200000, 600000)},
            {"risk_level": ChurnRisk.MEDIUM.value, "count": random.randint(10, 25), "arr": random.randint(300000, 800000)},
            {"risk_level": ChurnRisk.LOW.value, "count": random.randint(150, 400), "arr": random.randint(3000000, 10000000)}
        ],
        "top_risk_factors": [
            {"factor": ChurnReason.POOR_ADOPTION.value, "occurrence_rate": round(random.uniform(0.25, 0.40), 2)},
            {"factor": ChurnReason.SUPPORT_ISSUES.value, "occurrence_rate": round(random.uniform(0.15, 0.30), 2)},
            {"factor": ChurnReason.CHAMPION_LEFT.value, "occurrence_rate": round(random.uniform(0.10, 0.25), 2)},
            {"factor": ChurnReason.COMPETITOR.value, "occurrence_rate": round(random.uniform(0.08, 0.20), 2)}
        ],
        "intervention_stats": {
            "active_interventions": random.randint(10, 30),
            "successful_saves_mtd": random.randint(3, 12),
            "saved_revenue_mtd": random.randint(100000, 500000)
        }
    }


# Risk Scoring
@router.get("/accounts/{account_id}/risk")
async def get_account_churn_risk(
    account_id: str,
    tenant_id: str = Query(default="default")
):
    """Get churn risk prediction for an account"""
    now = datetime.utcnow()
    
    risk_score = random.randint(15, 85)
    if risk_score >= 70:
        risk_level = ChurnRisk.CRITICAL
    elif risk_score >= 50:
        risk_level = ChurnRisk.HIGH
    elif risk_score >= 30:
        risk_level = ChurnRisk.MEDIUM
    else:
        risk_level = ChurnRisk.LOW
    
    return {
        "account_id": account_id,
        "risk_score": risk_score,
        "risk_level": risk_level.value,
        "predicted_at": now.isoformat(),
        "model_version": "v2.1",
        "confidence": round(random.uniform(0.75, 0.95), 2),
        "risk_factors": [
            {
                "factor": ChurnReason.POOR_ADOPTION.value,
                "weight": round(random.uniform(0.15, 0.35), 2),
                "details": "Login frequency down 40% in last 30 days",
                "trend": "declining"
            },
            {
                "factor": ChurnReason.SUPPORT_ISSUES.value,
                "weight": round(random.uniform(0.10, 0.25), 2),
                "details": "3 escalated tickets in last 60 days",
                "trend": "stable"
            },
            {
                "factor": ChurnReason.CHAMPION_LEFT.value,
                "weight": round(random.uniform(0.05, 0.20), 2),
                "details": "Primary contact changed 2 weeks ago",
                "trend": "new_factor"
            }
        ],
        "health_indicators": {
            "product_adoption": random.randint(30, 90),
            "engagement_score": random.randint(40, 95),
            "support_satisfaction": round(random.uniform(2.5, 5.0), 1),
            "nps_score": random.randint(-20, 80),
            "feature_utilization": round(random.uniform(0.20, 0.80), 2),
            "days_since_last_login": random.randint(1, 45)
        },
        "contract_context": {
            "days_until_renewal": random.randint(-30, 180),
            "contract_value": random.randint(20000, 200000),
            "tenure_months": random.randint(3, 48)
        },
        "recommended_actions": [
            {
                "action": "Schedule executive business review",
                "priority": "high",
                "expected_impact": "Reduce risk by 15-20%"
            },
            {
                "action": "Conduct product training session",
                "priority": "high",
                "expected_impact": "Improve adoption by 25%"
            },
            {
                "action": "Introduce new primary contact to customer success",
                "priority": "medium",
                "expected_impact": "Build relationship with new champion"
            }
        ]
    }


@router.get("/at-risk")
async def get_at_risk_accounts(
    risk_level: Optional[ChurnRisk] = None,
    min_arr: Optional[float] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get list of at-risk accounts"""
    accounts = []
    
    for i in range(random.randint(15, 40)):
        risk_score = random.randint(30, 95)
        if risk_score >= 70:
            level = ChurnRisk.CRITICAL
        elif risk_score >= 50:
            level = ChurnRisk.HIGH
        else:
            level = ChurnRisk.MEDIUM
        
        arr = random.randint(15000, 300000)
        
        if risk_level and level != risk_level:
            continue
        if min_arr and arr < min_arr:
            continue
        
        accounts.append({
            "account_id": str(uuid.uuid4()),
            "account_name": f"Account {i + 1}",
            "risk_score": risk_score,
            "risk_level": level.value,
            "arr": arr,
            "primary_risk_factor": random.choice([r.value for r in ChurnReason]),
            "days_until_renewal": random.randint(-30, 180),
            "has_active_intervention": random.choice([True, False]),
            "last_engagement": (datetime.utcnow() - timedelta(days=random.randint(1, 60))).isoformat()
        })
    
    accounts.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "at_risk_accounts": accounts[:limit],
        "total": len(accounts),
        "total_arr_at_risk": sum(a["arr"] for a in accounts)
    }


# Signals
@router.post("/signals")
async def record_churn_signal(
    request: SignalCreate,
    tenant_id: str = Query(default="default")
):
    """Record a churn signal"""
    signal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    signal = {
        "id": signal_id,
        "account_id": request.account_id,
        "signal_type": request.signal_type,
        "severity": request.severity.value,
        "description": request.description,
        "tenant_id": tenant_id,
        "detected_at": now.isoformat(),
        "status": "active"
    }
    
    churn_signals[signal_id] = signal
    
    return signal


@router.get("/signals/{account_id}")
async def get_account_signals(
    account_id: str,
    tenant_id: str = Query(default="default")
):
    """Get churn signals for an account"""
    signals = [
        {
            "id": str(uuid.uuid4()),
            "signal_type": "usage_decline",
            "severity": ChurnRisk.HIGH.value,
            "description": "Weekly active users down 35%",
            "detected_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "signal_type": "support_escalation",
            "severity": ChurnRisk.MEDIUM.value,
            "description": "Critical support ticket opened",
            "detected_at": (datetime.utcnow() - timedelta(days=7)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "signal_type": "stakeholder_change",
            "severity": ChurnRisk.MEDIUM.value,
            "description": "Primary champion changed roles",
            "detected_at": (datetime.utcnow() - timedelta(days=14)).isoformat()
        }
    ]
    
    return {"account_id": account_id, "signals": signals}


# Interventions
@router.post("/interventions")
async def create_intervention(
    request: InterventionCreate,
    tenant_id: str = Query(default="default")
):
    """Create a churn intervention"""
    intervention_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    intervention = {
        "id": intervention_id,
        "account_id": request.account_id,
        "intervention_type": request.intervention_type.value,
        "assigned_to": request.assigned_to,
        "status": InterventionStatus.PLANNED.value,
        "due_date": request.due_date.isoformat(),
        "notes": request.notes,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    churn_interventions[intervention_id] = intervention
    
    return intervention


@router.get("/interventions")
async def list_interventions(
    account_id: Optional[str] = None,
    status: Optional[InterventionStatus] = None,
    assigned_to: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List interventions"""
    result = [i for i in churn_interventions.values() if i.get("tenant_id") == tenant_id]
    
    if account_id:
        result = [i for i in result if i.get("account_id") == account_id]
    if status:
        result = [i for i in result if i.get("status") == status.value]
    if assigned_to:
        result = [i for i in result if i.get("assigned_to") == assigned_to]
    
    return {"interventions": result, "total": len(result)}


@router.post("/interventions/{intervention_id}/complete")
async def complete_intervention(
    intervention_id: str,
    outcome: str,
    successful: bool,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Complete an intervention"""
    intervention = churn_interventions.get(intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    intervention["status"] = InterventionStatus.SUCCESSFUL.value if successful else InterventionStatus.UNSUCCESSFUL.value
    intervention["outcome"] = outcome
    intervention["outcome_notes"] = notes
    intervention["completed_at"] = datetime.utcnow().isoformat()
    
    return intervention


# AI Recommendations
@router.get("/recommendations/{account_id}")
async def get_intervention_recommendations(
    account_id: str,
    tenant_id: str = Query(default="default")
):
    """Get AI-recommended interventions for an account"""
    return {
        "account_id": account_id,
        "generated_at": datetime.utcnow().isoformat(),
        "recommendations": [
            {
                "intervention_type": InterventionType.EXECUTIVE_OUTREACH.value,
                "priority": "high",
                "rationale": "Account shows declining engagement and renewal is in 45 days",
                "expected_impact": "25% reduction in churn risk",
                "suggested_timing": "This week",
                "talking_points": [
                    "Discuss ROI and value realized",
                    "Understand current priorities and challenges",
                    "Preview upcoming product roadmap"
                ]
            },
            {
                "intervention_type": InterventionType.TRAINING.value,
                "priority": "high",
                "rationale": "Feature utilization is at 35%, below healthy threshold",
                "expected_impact": "40% improvement in adoption",
                "suggested_timing": "Within 2 weeks",
                "focus_areas": ["Advanced reporting", "Automation features", "Integrations"]
            },
            {
                "intervention_type": InterventionType.SUCCESS_CALL.value,
                "priority": "medium",
                "rationale": "New stakeholder needs relationship building",
                "expected_impact": "Establish champion relationship",
                "suggested_timing": "Within 1 week",
                "topics": ["Introduction to success team", "Review account goals", "Gather feedback"]
            }
        ],
        "success_playbook": {
            "playbook_name": "At-Risk Account Recovery",
            "suggested_cadence": "weekly touchpoints for 4 weeks",
            "escalation_threshold": "No improvement in 2 weeks"
        }
    }


# Cohort Analysis
@router.get("/cohorts")
async def get_churn_cohort_analysis(
    segment_by: str = Query(default="industry"),
    tenant_id: str = Query(default="default")
):
    """Get churn analysis by cohort"""
    cohorts = {
        "industry": [
            {"cohort": "Technology", "accounts": random.randint(50, 100), "churn_rate": round(random.uniform(0.03, 0.08), 3), "at_risk": random.randint(3, 10)},
            {"cohort": "Healthcare", "accounts": random.randint(30, 70), "churn_rate": round(random.uniform(0.02, 0.06), 3), "at_risk": random.randint(2, 8)},
            {"cohort": "Financial Services", "accounts": random.randint(40, 80), "churn_rate": round(random.uniform(0.02, 0.05), 3), "at_risk": random.randint(2, 6)},
            {"cohort": "Retail", "accounts": random.randint(25, 60), "churn_rate": round(random.uniform(0.04, 0.10), 3), "at_risk": random.randint(3, 12)}
        ],
        "tenure": [
            {"cohort": "0-6 months", "accounts": random.randint(40, 80), "churn_rate": round(random.uniform(0.08, 0.15), 3), "at_risk": random.randint(5, 15)},
            {"cohort": "6-12 months", "accounts": random.randint(50, 100), "churn_rate": round(random.uniform(0.04, 0.08), 3), "at_risk": random.randint(3, 10)},
            {"cohort": "1-2 years", "accounts": random.randint(60, 120), "churn_rate": round(random.uniform(0.02, 0.05), 3), "at_risk": random.randint(2, 8)},
            {"cohort": "2+ years", "accounts": random.randint(40, 90), "churn_rate": round(random.uniform(0.01, 0.03), 3), "at_risk": random.randint(1, 4)}
        ],
        "deal_size": [
            {"cohort": "Enterprise ($100K+)", "accounts": random.randint(20, 40), "churn_rate": round(random.uniform(0.01, 0.04), 3), "at_risk": random.randint(1, 3)},
            {"cohort": "Mid-Market ($25K-$100K)", "accounts": random.randint(60, 120), "churn_rate": round(random.uniform(0.03, 0.06), 3), "at_risk": random.randint(3, 8)},
            {"cohort": "SMB (<$25K)", "accounts": random.randint(80, 200), "churn_rate": round(random.uniform(0.05, 0.12), 3), "at_risk": random.randint(8, 20)}
        ]
    }
    
    return {
        "segment_by": segment_by,
        "cohorts": cohorts.get(segment_by, cohorts["industry"]),
        "insights": [
            "New customers (0-6 months) have highest churn risk",
            "Enterprise accounts show best retention",
            "Retail industry needs focused attention"
        ]
    }


# Trends
@router.get("/trends")
async def get_churn_trends(
    periods: int = Query(default=6, ge=3, le=12),
    tenant_id: str = Query(default="default")
):
    """Get churn trends over time"""
    now = datetime.utcnow()
    trends = []
    
    for i in range(periods):
        period_date = now - timedelta(days=30 * i)
        trends.append({
            "period": period_date.strftime("%Y-%m"),
            "churn_rate": round(random.uniform(0.02, 0.08), 3),
            "churned_accounts": random.randint(2, 15),
            "churned_arr": random.randint(50000, 300000),
            "saved_accounts": random.randint(1, 8),
            "saved_arr": random.randint(25000, 150000)
        })
    
    return {
        "trends": list(reversed(trends)),
        "overall_trend": random.choice(["improving", "stable", "worsening"]),
        "prediction_next_month": {
            "expected_churn_rate": round(random.uniform(0.02, 0.06), 3),
            "expected_churned_arr": random.randint(50000, 200000),
            "confidence": round(random.uniform(0.75, 0.90), 2)
        }
    }
