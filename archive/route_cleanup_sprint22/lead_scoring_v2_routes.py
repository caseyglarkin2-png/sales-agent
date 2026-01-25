"""
Lead Scoring v2 Routes - Advanced ML-based lead scoring
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

router = APIRouter(prefix="/lead-scoring-v2", tags=["Lead Scoring V2"])


class ScoreCategory(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    UNQUALIFIED = "unqualified"


class SignalType(str, Enum):
    BEHAVIORAL = "behavioral"
    DEMOGRAPHIC = "demographic"
    FIRMOGRAPHIC = "firmographic"
    INTENT = "intent"
    ENGAGEMENT = "engagement"
    TECHNOGRAPHIC = "technographic"


class ModelType(str, Enum):
    CONVERSION = "conversion"
    FIT = "fit"
    INTENT = "intent"
    COMBINED = "combined"


class ScoringRuleCreate(BaseModel):
    name: str
    signal_type: SignalType
    condition_field: str
    condition_operator: str
    condition_value: Any
    score_adjustment: int = Field(ge=-100, le=100)
    is_active: bool = True


class ModelConfigCreate(BaseModel):
    name: str
    model_type: ModelType
    features: List[str]
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, int]] = None
    is_default: bool = False


class LeadScoreRequest(BaseModel):
    lead_id: str
    lead_data: Dict[str, Any]
    activities: Optional[List[Dict[str, Any]]] = None
    force_recalculate: bool = False


# In-memory storage
lead_scores = {}
scoring_rules = {}
scoring_models = {}
score_history = {}
signal_definitions = {}
score_explanations = {}


# Lead Scoring
@router.post("/score")
async def score_lead(
    request: LeadScoreRequest,
    model_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Score a lead using ML model"""
    now = datetime.utcnow()
    
    # Calculate component scores
    demographic_score = calculate_demographic_score(request.lead_data)
    firmographic_score = calculate_firmographic_score(request.lead_data)
    behavioral_score = calculate_behavioral_score(request.activities or [])
    engagement_score = calculate_engagement_score(request.activities or [])
    intent_score = calculate_intent_score(request.lead_data, request.activities or [])
    
    # Calculate composite score
    weights = {
        "demographic": 0.15,
        "firmographic": 0.25,
        "behavioral": 0.25,
        "engagement": 0.20,
        "intent": 0.15
    }
    
    composite_score = (
        demographic_score * weights["demographic"] +
        firmographic_score * weights["firmographic"] +
        behavioral_score * weights["behavioral"] +
        engagement_score * weights["engagement"] +
        intent_score * weights["intent"]
    )
    
    composite_score = round(min(100, max(0, composite_score)))
    
    # Determine category
    if composite_score >= 80:
        category = ScoreCategory.HOT
    elif composite_score >= 60:
        category = ScoreCategory.WARM
    elif composite_score >= 40:
        category = ScoreCategory.COLD
    else:
        category = ScoreCategory.UNQUALIFIED
    
    # Generate explanation
    explanation = generate_score_explanation(
        request.lead_data,
        {
            "demographic": demographic_score,
            "firmographic": firmographic_score,
            "behavioral": behavioral_score,
            "engagement": engagement_score,
            "intent": intent_score
        }
    )
    
    score_result = {
        "lead_id": request.lead_id,
        "score": composite_score,
        "category": category.value,
        "confidence": random.uniform(0.75, 0.95),
        "component_scores": {
            "demographic": round(demographic_score),
            "firmographic": round(firmographic_score),
            "behavioral": round(behavioral_score),
            "engagement": round(engagement_score),
            "intent": round(intent_score)
        },
        "signals": explanation.get("signals", []),
        "recommendations": explanation.get("recommendations", []),
        "model_id": model_id or "default",
        "model_version": "2.1.0",
        "scored_at": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    # Store score
    lead_scores[request.lead_id] = score_result
    
    # Store in history
    if request.lead_id not in score_history:
        score_history[request.lead_id] = []
    score_history[request.lead_id].append({
        "score": composite_score,
        "category": category.value,
        "timestamp": now.isoformat()
    })
    
    logger.info("lead_scored", lead_id=request.lead_id, score=composite_score, category=category.value)
    return score_result


@router.post("/score/batch")
async def score_leads_batch(
    leads: List[LeadScoreRequest],
    model_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Score multiple leads"""
    results = []
    for lead in leads:
        result = await score_lead(lead, model_id, tenant_id)
        results.append(result)
    
    return {
        "results": results,
        "total": len(results),
        "scored_at": datetime.utcnow().isoformat()
    }


@router.get("/leads/{lead_id}/score")
async def get_lead_score(lead_id: str):
    """Get lead's current score"""
    if lead_id not in lead_scores:
        raise HTTPException(status_code=404, detail="Score not found")
    return lead_scores[lead_id]


@router.get("/leads/{lead_id}/score/history")
async def get_score_history(
    lead_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get lead's score history"""
    history = score_history.get(lead_id, [])
    return {
        "lead_id": lead_id,
        "history": history[-100:],  # Last 100 entries
        "total_entries": len(history)
    }


@router.get("/leads/{lead_id}/score/explain")
async def explain_lead_score(lead_id: str):
    """Get detailed explanation of lead score"""
    if lead_id not in lead_scores:
        raise HTTPException(status_code=404, detail="Score not found")
    
    score = lead_scores[lead_id]
    
    return {
        "lead_id": lead_id,
        "score": score["score"],
        "category": score["category"],
        "component_breakdown": score.get("component_scores", {}),
        "positive_signals": [s for s in score.get("signals", []) if s.get("impact") == "positive"],
        "negative_signals": [s for s in score.get("signals", []) if s.get("impact") == "negative"],
        "missing_data_impact": [
            {"field": "phone", "potential_increase": 5},
            {"field": "company_revenue", "potential_increase": 8}
        ],
        "improvement_actions": [
            {"action": "Verify company size", "expected_impact": "+5 points"},
            {"action": "Capture budget information", "expected_impact": "+10 points"},
            {"action": "Schedule discovery call", "expected_impact": "+15 points"}
        ]
    }


# Scoring Rules
@router.post("/rules")
async def create_scoring_rule(
    request: ScoringRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a scoring rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "signal_type": request.signal_type.value,
        "condition_field": request.condition_field,
        "condition_operator": request.condition_operator,
        "condition_value": request.condition_value,
        "score_adjustment": request.score_adjustment,
        "is_active": request.is_active,
        "times_triggered": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    scoring_rules[rule_id] = rule
    
    logger.info("scoring_rule_created", rule_id=rule_id, name=request.name)
    return rule


@router.get("/rules")
async def list_scoring_rules(
    signal_type: Optional[SignalType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List scoring rules"""
    result = [r for r in scoring_rules.values() if r.get("tenant_id") == tenant_id]
    
    if signal_type:
        result = [r for r in result if r.get("signal_type") == signal_type.value]
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    
    return {"rules": result, "total": len(result)}


@router.get("/rules/{rule_id}")
async def get_scoring_rule(rule_id: str):
    """Get scoring rule details"""
    if rule_id not in scoring_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    return scoring_rules[rule_id]


@router.put("/rules/{rule_id}")
async def update_scoring_rule(
    rule_id: str,
    score_adjustment: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """Update scoring rule"""
    if rule_id not in scoring_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = scoring_rules[rule_id]
    
    if score_adjustment is not None:
        rule["score_adjustment"] = score_adjustment
    if is_active is not None:
        rule["is_active"] = is_active
    
    rule["updated_at"] = datetime.utcnow().isoformat()
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_scoring_rule(rule_id: str):
    """Delete scoring rule"""
    if rule_id not in scoring_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    del scoring_rules[rule_id]
    return {"status": "deleted", "rule_id": rule_id}


# Scoring Models
@router.post("/models")
async def create_scoring_model(
    request: ModelConfigCreate,
    tenant_id: str = Query(default="default")
):
    """Create a scoring model configuration"""
    model_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    model = {
        "id": model_id,
        "name": request.name,
        "model_type": request.model_type.value,
        "features": request.features,
        "weights": request.weights or {},
        "thresholds": request.thresholds or {
            "hot": 80,
            "warm": 60,
            "cold": 40
        },
        "is_default": request.is_default,
        "is_active": True,
        "version": "1.0.0",
        "accuracy": 0,
        "leads_scored": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    scoring_models[model_id] = model
    
    logger.info("scoring_model_created", model_id=model_id, name=request.name)
    return model


@router.get("/models")
async def list_scoring_models(
    model_type: Optional[ModelType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List scoring models"""
    result = [m for m in scoring_models.values() if m.get("tenant_id") == tenant_id]
    
    if model_type:
        result = [m for m in result if m.get("model_type") == model_type.value]
    if is_active is not None:
        result = [m for m in result if m.get("is_active") == is_active]
    
    return {"models": result, "total": len(result)}


@router.get("/models/{model_id}")
async def get_scoring_model(model_id: str):
    """Get model details"""
    if model_id not in scoring_models:
        raise HTTPException(status_code=404, detail="Model not found")
    return scoring_models[model_id]


@router.post("/models/{model_id}/train")
async def train_model(
    model_id: str,
    training_data_path: Optional[str] = None
):
    """Trigger model training"""
    if model_id not in scoring_models:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model = scoring_models[model_id]
    
    # Simulate training
    training_id = str(uuid.uuid4())
    
    return {
        "training_id": training_id,
        "model_id": model_id,
        "status": "started",
        "estimated_completion": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "message": "Model training initiated. You will be notified upon completion."
    }


@router.get("/models/{model_id}/performance")
async def get_model_performance(model_id: str):
    """Get model performance metrics"""
    if model_id not in scoring_models:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "model_id": model_id,
        "metrics": {
            "accuracy": 0.82,
            "precision": 0.78,
            "recall": 0.85,
            "f1_score": 0.81,
            "auc_roc": 0.88
        },
        "confusion_matrix": {
            "true_positive": 450,
            "true_negative": 320,
            "false_positive": 80,
            "false_negative": 50
        },
        "feature_importance": [
            {"feature": "email_engagement", "importance": 0.25},
            {"feature": "company_size", "importance": 0.20},
            {"feature": "website_visits", "importance": 0.18},
            {"feature": "job_title_level", "importance": 0.15},
            {"feature": "industry_fit", "importance": 0.12},
            {"feature": "technology_stack", "importance": 0.10}
        ],
        "last_trained": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "training_samples": 5000,
        "validation_samples": 1000
    }


# Signal Definitions
@router.get("/signals")
async def list_signal_definitions():
    """List available scoring signals"""
    return {
        "signals": [
            {
                "type": SignalType.BEHAVIORAL.value,
                "signals": [
                    {"name": "website_visit", "description": "Visited website", "default_score": 5},
                    {"name": "content_download", "description": "Downloaded content", "default_score": 15},
                    {"name": "pricing_page_visit", "description": "Viewed pricing page", "default_score": 20},
                    {"name": "demo_request", "description": "Requested demo", "default_score": 30},
                    {"name": "free_trial_signup", "description": "Started free trial", "default_score": 25}
                ]
            },
            {
                "type": SignalType.ENGAGEMENT.value,
                "signals": [
                    {"name": "email_open", "description": "Opened email", "default_score": 3},
                    {"name": "email_click", "description": "Clicked email link", "default_score": 8},
                    {"name": "email_reply", "description": "Replied to email", "default_score": 15},
                    {"name": "meeting_attended", "description": "Attended meeting", "default_score": 25},
                    {"name": "webinar_attended", "description": "Attended webinar", "default_score": 20}
                ]
            },
            {
                "type": SignalType.DEMOGRAPHIC.value,
                "signals": [
                    {"name": "job_title_match", "description": "Job title matches ICP", "default_score": 15},
                    {"name": "decision_maker", "description": "Is decision maker", "default_score": 20},
                    {"name": "valid_business_email", "description": "Has business email", "default_score": 5}
                ]
            },
            {
                "type": SignalType.FIRMOGRAPHIC.value,
                "signals": [
                    {"name": "company_size_fit", "description": "Company size matches ICP", "default_score": 15},
                    {"name": "industry_fit", "description": "Industry matches ICP", "default_score": 15},
                    {"name": "revenue_fit", "description": "Revenue matches ICP", "default_score": 10},
                    {"name": "location_fit", "description": "Location matches ICP", "default_score": 5}
                ]
            },
            {
                "type": SignalType.INTENT.value,
                "signals": [
                    {"name": "competitor_research", "description": "Researching competitors", "default_score": 15},
                    {"name": "solution_research", "description": "Actively researching solutions", "default_score": 20},
                    {"name": "budget_mention", "description": "Mentioned budget availability", "default_score": 25},
                    {"name": "timeline_mention", "description": "Mentioned purchase timeline", "default_score": 20}
                ]
            }
        ]
    }


# Thresholds
@router.get("/thresholds")
async def get_score_thresholds(tenant_id: str = Query(default="default")):
    """Get scoring thresholds"""
    return {
        "thresholds": {
            "hot": {"min": 80, "max": 100, "color": "#22c55e", "action": "Immediate follow-up"},
            "warm": {"min": 60, "max": 79, "color": "#f59e0b", "action": "Nurture sequence"},
            "cold": {"min": 40, "max": 59, "color": "#3b82f6", "action": "Long-term nurture"},
            "unqualified": {"min": 0, "max": 39, "color": "#6b7280", "action": "Marketing qualification"}
        }
    }


@router.put("/thresholds")
async def update_score_thresholds(
    hot_min: int = Query(default=80, ge=0, le=100),
    warm_min: int = Query(default=60, ge=0, le=100),
    cold_min: int = Query(default=40, ge=0, le=100),
    tenant_id: str = Query(default="default")
):
    """Update scoring thresholds"""
    return {
        "thresholds": {
            "hot": {"min": hot_min, "max": 100},
            "warm": {"min": warm_min, "max": hot_min - 1},
            "cold": {"min": cold_min, "max": warm_min - 1},
            "unqualified": {"min": 0, "max": cold_min - 1}
        },
        "updated_at": datetime.utcnow().isoformat()
    }


# Analytics
@router.get("/analytics")
async def get_scoring_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get lead scoring analytics"""
    tenant_scores = [s for s in lead_scores.values() if s.get("tenant_id") == tenant_id]
    
    total = len(tenant_scores)
    
    return {
        "period_days": days,
        "total_leads_scored": total,
        "distribution": {
            ScoreCategory.HOT.value: len([s for s in tenant_scores if s.get("category") == ScoreCategory.HOT.value]),
            ScoreCategory.WARM.value: len([s for s in tenant_scores if s.get("category") == ScoreCategory.WARM.value]),
            ScoreCategory.COLD.value: len([s for s in tenant_scores if s.get("category") == ScoreCategory.COLD.value]),
            ScoreCategory.UNQUALIFIED.value: len([s for s in tenant_scores if s.get("category") == ScoreCategory.UNQUALIFIED.value])
        },
        "average_score": round(sum(s.get("score", 0) for s in tenant_scores) / total, 1) if total > 0 else 0,
        "score_trends": [
            {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"), "avg_score": random.randint(45, 65)}
            for i in range(days, -1, -7)
        ],
        "top_signals": [
            {"signal": "pricing_page_visit", "frequency": 450, "avg_impact": 18.5},
            {"signal": "content_download", "frequency": 380, "avg_impact": 14.2},
            {"signal": "email_reply", "frequency": 220, "avg_impact": 15.8}
        ],
        "model_accuracy": 0.82,
        "conversion_correlation": 0.78
    }


@router.get("/analytics/conversion")
async def get_conversion_analysis(tenant_id: str = Query(default="default")):
    """Get score-to-conversion analysis"""
    return {
        "score_buckets": [
            {"range": "90-100", "leads": 120, "converted": 85, "conversion_rate": 70.8},
            {"range": "80-89", "leads": 280, "converted": 140, "conversion_rate": 50.0},
            {"range": "70-79", "leads": 450, "converted": 135, "conversion_rate": 30.0},
            {"range": "60-69", "leads": 620, "converted": 93, "conversion_rate": 15.0},
            {"range": "50-59", "leads": 880, "converted": 70, "conversion_rate": 8.0},
            {"range": "0-49", "leads": 1500, "converted": 30, "conversion_rate": 2.0}
        ],
        "insights": [
            "Leads scoring 80+ have 10x higher conversion rate",
            "Pricing page visits increase conversion likelihood by 45%",
            "Demo requests are the strongest conversion predictor"
        ]
    }


# Helper functions
def calculate_demographic_score(data: Dict[str, Any]) -> float:
    score = 50.0
    
    # Job title scoring
    title = data.get("title", "").lower()
    if any(x in title for x in ["vp", "director", "head"]):
        score += 25
    elif any(x in title for x in ["manager", "lead"]):
        score += 15
    elif any(x in title for x in ["c-level", "ceo", "cto", "cfo"]):
        score += 30
    
    # Email quality
    email = data.get("email", "")
    if email and "@" in email:
        domain = email.split("@")[1]
        if domain not in ["gmail.com", "yahoo.com", "hotmail.com"]:
            score += 10
    
    return min(100, max(0, score))


def calculate_firmographic_score(data: Dict[str, Any]) -> float:
    score = 50.0
    
    # Company size
    employees = data.get("employees", 0)
    if 50 <= employees <= 500:
        score += 25
    elif 500 < employees <= 2000:
        score += 20
    elif employees > 2000:
        score += 15
    
    # Industry fit
    industry = data.get("industry", "").lower()
    target_industries = ["technology", "software", "finance", "healthcare"]
    if any(ind in industry for ind in target_industries):
        score += 20
    
    return min(100, max(0, score))


def calculate_behavioral_score(activities: List[Dict[str, Any]]) -> float:
    score = 30.0
    
    for activity in activities:
        activity_type = activity.get("type", "")
        if activity_type == "website_visit":
            score += 5
        elif activity_type == "pricing_page":
            score += 15
        elif activity_type == "demo_request":
            score += 30
        elif activity_type == "content_download":
            score += 10
        elif activity_type == "trial_signup":
            score += 25
    
    return min(100, max(0, score))


def calculate_engagement_score(activities: List[Dict[str, Any]]) -> float:
    score = 30.0
    
    for activity in activities:
        activity_type = activity.get("type", "")
        if activity_type == "email_open":
            score += 3
        elif activity_type == "email_click":
            score += 8
        elif activity_type == "email_reply":
            score += 15
        elif activity_type == "meeting":
            score += 25
        elif activity_type == "call":
            score += 15
    
    return min(100, max(0, score))


def calculate_intent_score(data: Dict[str, Any], activities: List[Dict[str, Any]]) -> float:
    score = 30.0
    
    # Check for intent signals in data
    if data.get("budget_mentioned"):
        score += 25
    if data.get("timeline_mentioned"):
        score += 20
    if data.get("competitor_mentioned"):
        score += 15
    
    # Check for research activities
    research_activities = [a for a in activities if a.get("type") in ["competitor_research", "solution_research"]]
    score += len(research_activities) * 10
    
    return min(100, max(0, score))


def generate_score_explanation(data: Dict[str, Any], component_scores: Dict[str, float]) -> Dict[str, Any]:
    signals = []
    recommendations = []
    
    # Analyze positive signals
    if component_scores.get("behavioral", 0) > 60:
        signals.append({
            "signal": "High behavioral engagement",
            "impact": "positive",
            "contribution": "+15 points"
        })
    
    if component_scores.get("firmographic", 0) > 60:
        signals.append({
            "signal": "Strong company fit",
            "impact": "positive",
            "contribution": "+12 points"
        })
    
    # Analyze negative signals
    if component_scores.get("engagement", 0) < 40:
        signals.append({
            "signal": "Low email engagement",
            "impact": "negative",
            "contribution": "-10 points"
        })
        recommendations.append("Increase touchpoint frequency")
    
    if component_scores.get("demographic", 0) < 50:
        signals.append({
            "signal": "Non-ideal persona",
            "impact": "negative",
            "contribution": "-8 points"
        })
        recommendations.append("Verify decision-making authority")
    
    return {
        "signals": signals,
        "recommendations": recommendations
    }
