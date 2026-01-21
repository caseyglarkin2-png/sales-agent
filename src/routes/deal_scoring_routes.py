"""
Deal Scoring Routes - AI-powered deal scoring and prioritization
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

router = APIRouter(prefix="/deal-scoring", tags=["Deal Scoring"])


class ScoreCategory(str, Enum):
    ENGAGEMENT = "engagement"
    FIT = "fit"
    TIMING = "timing"
    CHAMPION = "champion"
    BUDGET = "budget"
    AUTHORITY = "authority"
    NEED = "need"
    COMPETITION = "competition"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScoreChange(str, Enum):
    INCREASED = "increased"
    DECREASED = "decreased"
    STABLE = "stable"


# In-memory storage
deal_scores = {}
scoring_models = {}
score_history = {}
scoring_rules = {}
score_alerts = {}


class ScoringModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weights: Dict[str, float]
    thresholds: Dict[str, int]


class ScoringRuleCreate(BaseModel):
    name: str
    category: ScoreCategory
    condition: str
    score_impact: int
    description: Optional[str] = None


# Deal Scores
@router.get("/deals/{deal_id}/score")
async def get_deal_score(deal_id: str):
    """Get deal score with breakdown"""
    if deal_id not in deal_scores:
        # Generate score
        deal_scores[deal_id] = generate_deal_score(deal_id)
    
    return deal_scores[deal_id]


@router.post("/deals/{deal_id}/score/refresh")
async def refresh_deal_score(deal_id: str):
    """Refresh deal score"""
    deal_scores[deal_id] = generate_deal_score(deal_id)
    
    # Record in history
    history_id = str(uuid.uuid4())
    score_history[history_id] = {
        "id": history_id,
        "deal_id": deal_id,
        "score": deal_scores[deal_id]["overall_score"],
        "recorded_at": datetime.utcnow().isoformat()
    }
    
    return deal_scores[deal_id]


@router.get("/deals/{deal_id}/score/history")
async def get_score_history(
    deal_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get deal score history"""
    history = [h for h in score_history.values() if h.get("deal_id") == deal_id]
    history.sort(key=lambda x: x.get("recorded_at", ""))
    
    # Generate simulated history if empty
    if not history:
        base_score = random.randint(50, 80)
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()
            variation = random.randint(-5, 5)
            history.append({
                "date": date[:10],
                "score": min(100, max(0, base_score + variation + i // 5))
            })
    
    return {"deal_id": deal_id, "history": history}


@router.get("/deals/{deal_id}/score/factors")
async def get_score_factors(deal_id: str):
    """Get detailed scoring factors"""
    factors = []
    
    positive_factors = [
        "Executive sponsor identified",
        "Budget confirmed",
        "Clear timeline established",
        "Technical evaluation completed",
        "Multiple stakeholders engaged",
        "Strong product fit",
        "Competitor displaced"
    ]
    
    negative_factors = [
        "No recent activity",
        "Close date pushed multiple times",
        "Key stakeholder unresponsive",
        "Budget constraints mentioned",
        "Competitor actively involved",
        "Long sales cycle"
    ]
    
    # Add positive factors
    for factor in random.sample(positive_factors, k=random.randint(2, 4)):
        factors.append({
            "factor": factor,
            "impact": "positive",
            "score_contribution": random.randint(5, 15)
        })
    
    # Add negative factors
    for factor in random.sample(negative_factors, k=random.randint(1, 3)):
        factors.append({
            "factor": factor,
            "impact": "negative",
            "score_contribution": -random.randint(5, 15)
        })
    
    return {
        "deal_id": deal_id,
        "factors": factors,
        "net_impact": sum(f["score_contribution"] for f in factors)
    }


@router.get("/deals/{deal_id}/recommendations")
async def get_deal_recommendations(deal_id: str):
    """Get AI recommendations to improve deal score"""
    recommendations = [
        {
            "priority": "high",
            "action": "Schedule executive alignment meeting",
            "potential_impact": "+10 points",
            "reasoning": "No executive sponsor identified yet"
        },
        {
            "priority": "high",
            "action": "Request budget confirmation",
            "potential_impact": "+15 points",
            "reasoning": "Budget not yet confirmed"
        },
        {
            "priority": "medium",
            "action": "Send ROI analysis",
            "potential_impact": "+8 points",
            "reasoning": "Strengthen business case"
        },
        {
            "priority": "medium",
            "action": "Introduce customer reference",
            "potential_impact": "+7 points",
            "reasoning": "Social proof in similar industry"
        },
        {
            "priority": "low",
            "action": "Document technical requirements",
            "potential_impact": "+5 points",
            "reasoning": "Accelerate evaluation phase"
        }
    ]
    
    return {
        "deal_id": deal_id,
        "recommendations": random.sample(recommendations, k=random.randint(3, 5)),
        "projected_score_improvement": random.randint(15, 35)
    }


# Bulk Scoring
@router.post("/deals/score/bulk")
async def bulk_score_deals(deal_ids: List[str]):
    """Score multiple deals"""
    results = []
    
    for deal_id in deal_ids:
        if deal_id not in deal_scores:
            deal_scores[deal_id] = generate_deal_score(deal_id)
        results.append({
            "deal_id": deal_id,
            "overall_score": deal_scores[deal_id]["overall_score"],
            "risk_level": deal_scores[deal_id]["risk_level"]
        })
    
    return {"scores": results}


@router.get("/deals/ranked")
async def get_ranked_deals(
    limit: int = Query(default=20, le=50),
    min_score: Optional[int] = None,
    risk_level: Optional[RiskLevel] = None,
    tenant_id: str = Query(default="default")
):
    """Get deals ranked by score"""
    # Simulate ranked deals
    deals = []
    for i in range(limit):
        score = random.randint(30, 95)
        if min_score and score < min_score:
            continue
        
        risk = "low" if score >= 70 else "medium" if score >= 50 else "high" if score >= 30 else "critical"
        
        if risk_level and risk != risk_level.value:
            continue
        
        deals.append({
            "deal_id": str(uuid.uuid4()),
            "name": f"Deal {i+1}",
            "amount": round(random.uniform(20000, 500000), 2),
            "overall_score": score,
            "risk_level": risk,
            "score_change": random.choice([c.value for c in ScoreChange]),
            "days_in_stage": random.randint(5, 45)
        })
    
    deals.sort(key=lambda x: x["overall_score"], reverse=True)
    
    return {"deals": deals, "total": len(deals)}


# Scoring Models
@router.post("/models")
async def create_scoring_model(
    request: ScoringModelCreate,
    tenant_id: str = Query(default="default")
):
    """Create a custom scoring model"""
    model_id = str(uuid.uuid4())
    
    model = {
        "id": model_id,
        "name": request.name,
        "description": request.description,
        "weights": request.weights,
        "thresholds": request.thresholds,
        "is_active": False,
        "deals_scored": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    scoring_models[model_id] = model
    
    return model


@router.get("/models")
async def list_scoring_models(tenant_id: str = Query(default="default")):
    """List scoring models"""
    models = [m for m in scoring_models.values() if m.get("tenant_id") == tenant_id]
    
    # Add default model if none exist
    if not models:
        models = [{
            "id": "default",
            "name": "Default Model",
            "description": "Standard deal scoring model",
            "weights": {
                "engagement": 0.25,
                "fit": 0.20,
                "timing": 0.15,
                "champion": 0.15,
                "budget": 0.15,
                "authority": 0.10
            },
            "thresholds": {
                "high": 70,
                "medium": 50,
                "low": 30
            },
            "is_active": True
        }]
    
    return {"models": models, "total": len(models)}


@router.put("/models/{model_id}/activate")
async def activate_model(model_id: str):
    """Activate a scoring model"""
    if model_id not in scoring_models:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Deactivate other models
    for m in scoring_models.values():
        m["is_active"] = False
    
    scoring_models[model_id]["is_active"] = True
    
    return scoring_models[model_id]


# Scoring Rules
@router.post("/rules")
async def create_scoring_rule(
    request: ScoringRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a scoring rule"""
    rule_id = str(uuid.uuid4())
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "category": request.category.value,
        "condition": request.condition,
        "score_impact": request.score_impact,
        "description": request.description,
        "is_active": True,
        "matches": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    scoring_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_scoring_rules(
    category: Optional[ScoreCategory] = None,
    tenant_id: str = Query(default="default")
):
    """List scoring rules"""
    rules = [r for r in scoring_rules.values() if r.get("tenant_id") == tenant_id]
    
    if category:
        rules = [r for r in rules if r.get("category") == category.value]
    
    return {"rules": rules, "total": len(rules)}


@router.put("/rules/{rule_id}")
async def update_scoring_rule(
    rule_id: str,
    condition: Optional[str] = None,
    score_impact: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """Update a scoring rule"""
    if rule_id not in scoring_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = scoring_rules[rule_id]
    
    if condition:
        rule["condition"] = condition
    if score_impact is not None:
        rule["score_impact"] = score_impact
    if is_active is not None:
        rule["is_active"] = is_active
    
    rule["updated_at"] = datetime.utcnow().isoformat()
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_scoring_rule(rule_id: str):
    """Delete a scoring rule"""
    if rule_id not in scoring_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    scoring_rules.pop(rule_id)
    
    return {"message": "Rule deleted"}


# Alerts
@router.get("/alerts")
async def list_score_alerts(
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """List score change alerts"""
    alerts = [a for a in score_alerts.values() if a.get("tenant_id") == tenant_id]
    alerts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"alerts": alerts[:limit], "total": len(alerts)}


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    """Dismiss an alert"""
    if alert_id not in score_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    score_alerts[alert_id]["dismissed"] = True
    score_alerts[alert_id]["dismissed_at"] = datetime.utcnow().isoformat()
    
    return score_alerts[alert_id]


# Analytics
@router.get("/analytics")
async def get_scoring_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get scoring analytics"""
    return {
        "deals_scored": random.randint(100, 500),
        "avg_score": round(random.uniform(50, 70), 1),
        "score_distribution": {
            "high": random.randint(20, 40),
            "medium": random.randint(30, 50),
            "low": random.randint(10, 30),
            "critical": random.randint(5, 15)
        },
        "score_accuracy": round(random.uniform(0.7, 0.9), 3),
        "correlation_with_wins": round(random.uniform(0.6, 0.85), 3),
        "top_predictive_factors": [
            {"factor": "Executive sponsor", "correlation": round(random.uniform(0.7, 0.9), 2)},
            {"factor": "Budget confirmed", "correlation": round(random.uniform(0.65, 0.85), 2)},
            {"factor": "Recent engagement", "correlation": round(random.uniform(0.6, 0.8), 2)}
        ],
        "score_trends": {
            "improving": random.randint(30, 60),
            "stable": random.randint(20, 40),
            "declining": random.randint(10, 30)
        }
    }


# Helper functions
def generate_deal_score(deal_id: str) -> Dict:
    """Generate a deal score"""
    category_scores = {}
    
    for category in ScoreCategory:
        category_scores[category.value] = random.randint(30, 95)
    
    overall = int(sum(category_scores.values()) / len(category_scores))
    
    risk_level = "low" if overall >= 70 else "medium" if overall >= 50 else "high" if overall >= 30 else "critical"
    
    return {
        "deal_id": deal_id,
        "overall_score": overall,
        "category_scores": category_scores,
        "risk_level": risk_level,
        "confidence": round(random.uniform(0.7, 0.95), 2),
        "last_updated": datetime.utcnow().isoformat()
    }
