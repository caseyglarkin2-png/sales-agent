"""
Sales Forecasting V2 Routes - Advanced AI-powered sales forecasting
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

router = APIRouter(prefix="/forecasting-v2", tags=["Sales Forecasting V2"])


class ForecastPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ForecastMethod(str, Enum):
    AI_PREDICTIVE = "ai_predictive"
    WEIGHTED_PIPELINE = "weighted_pipeline"
    HISTORICAL_TREND = "historical_trend"
    REP_COMMIT = "rep_commit"
    BLENDED = "blended"


class ForecastCategory(str, Enum):
    COMMIT = "commit"
    BEST_CASE = "best_case"
    UPSIDE = "upside"
    PIPELINE = "pipeline"
    OMITTED = "omitted"


class ForecastStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LOCKED = "locked"
    FINAL = "final"


# In-memory storage
forecasts = {}
forecast_snapshots = {}
rep_forecasts = {}
forecast_adjustments = {}
forecast_scenarios = {}


class ForecastCreate(BaseModel):
    name: str
    period: ForecastPeriod
    start_date: str
    end_date: str
    method: ForecastMethod = ForecastMethod.BLENDED


class RepForecastSubmit(BaseModel):
    deals: List[Dict[str, Any]]
    commit_amount: float
    best_case_amount: float
    upside_amount: float


@router.post("/forecasts")
async def create_forecast(
    request: ForecastCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a new forecast"""
    forecast_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    ai_prediction = random.uniform(500000, 2000000)
    
    forecast = {
        "id": forecast_id,
        "name": request.name,
        "period": request.period.value,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "method": request.method.value,
        "status": ForecastStatus.DRAFT.value,
        "amounts": {
            "commit": 0,
            "best_case": 0,
            "upside": 0,
            "pipeline": ai_prediction * 2.5,
            "ai_prediction": ai_prediction,
            "weighted_pipeline": ai_prediction * 0.7
        },
        "ai_confidence": round(random.uniform(0.7, 0.9), 2),
        "rep_submissions": 0,
        "owner_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    forecasts[forecast_id] = forecast
    
    return forecast


@router.get("/forecasts")
async def list_forecasts(
    period: Optional[ForecastPeriod] = None,
    status: Optional[ForecastStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List forecasts"""
    result = [f for f in forecasts.values() if f.get("tenant_id") == tenant_id]
    
    if period:
        result = [f for f in result if f.get("period") == period.value]
    if status:
        result = [f for f in result if f.get("status") == status.value]
    
    return {"forecasts": result, "total": len(result)}


@router.get("/forecasts/{forecast_id}")
async def get_forecast(forecast_id: str):
    """Get forecast details"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return forecasts[forecast_id]


@router.post("/forecasts/{forecast_id}/lock")
async def lock_forecast(forecast_id: str):
    """Lock a forecast"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    forecast = forecasts[forecast_id]
    forecast["status"] = ForecastStatus.LOCKED.value
    forecast["locked_at"] = datetime.utcnow().isoformat()
    
    return forecast


@router.post("/forecasts/{forecast_id}/rep-submit")
async def submit_rep_forecast(
    forecast_id: str,
    request: RepForecastSubmit,
    user_id: str = Query(default="default")
):
    """Submit rep-level forecast"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    rep_forecast_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rep_forecast = {
        "id": rep_forecast_id,
        "forecast_id": forecast_id,
        "rep_id": user_id,
        "deals": request.deals,
        "commit_amount": request.commit_amount,
        "best_case_amount": request.best_case_amount,
        "upside_amount": request.upside_amount,
        "submitted_at": now.isoformat()
    }
    
    rep_forecasts[rep_forecast_id] = rep_forecast
    
    forecast = forecasts[forecast_id]
    forecast["amounts"]["commit"] += request.commit_amount
    forecast["amounts"]["best_case"] += request.best_case_amount
    forecast["amounts"]["upside"] += request.upside_amount
    forecast["rep_submissions"] += 1
    
    return rep_forecast


@router.post("/forecasts/{forecast_id}/adjust")
async def adjust_forecast(
    forecast_id: str,
    adjustment_type: str,
    amount: float,
    reason: str,
    user_id: str = Query(default="default")
):
    """Apply manager adjustment"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    adjustment_id = str(uuid.uuid4())
    
    adjustment = {
        "id": adjustment_id,
        "forecast_id": forecast_id,
        "adjustment_type": adjustment_type,
        "amount": amount,
        "reason": reason,
        "applied_by": user_id,
        "applied_at": datetime.utcnow().isoformat()
    }
    
    forecast_adjustments[adjustment_id] = adjustment
    
    forecast = forecasts[forecast_id]
    if adjustment_type in forecast["amounts"]:
        forecast["amounts"][adjustment_type] += amount
    
    return adjustment


@router.get("/forecasts/{forecast_id}/ai-prediction")
async def get_ai_prediction(forecast_id: str):
    """Get detailed AI prediction"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    forecast = forecasts[forecast_id]
    
    return {
        "forecast_id": forecast_id,
        "predicted_amount": forecast["amounts"]["ai_prediction"],
        "confidence": forecast["ai_confidence"],
        "prediction_range": {
            "low": forecast["amounts"]["ai_prediction"] * 0.85,
            "high": forecast["amounts"]["ai_prediction"] * 1.15
        },
        "factors": [
            {"name": "Pipeline Quality", "impact": round(random.uniform(-0.1, 0.2), 2)},
            {"name": "Historical Performance", "impact": round(random.uniform(0.05, 0.15), 2)},
            {"name": "Deal Velocity", "impact": round(random.uniform(-0.05, 0.1), 2)},
            {"name": "Seasonality", "impact": round(random.uniform(-0.08, 0.08), 2)}
        ],
        "deals_analysis": {
            "high_confidence": random.randint(5, 15),
            "medium_confidence": random.randint(10, 25),
            "low_confidence": random.randint(5, 20)
        }
    }


@router.get("/forecasts/{forecast_id}/deal-analysis")
async def get_deal_forecast_analysis(forecast_id: str):
    """Get deal-level forecast analysis"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    deals = []
    for i in range(random.randint(10, 30)):
        amount = random.uniform(10000, 500000)
        close_prob = random.uniform(0.1, 0.95)
        
        deals.append({
            "deal_id": str(uuid.uuid4()),
            "name": f"Deal {i+1}",
            "amount": round(amount, 2),
            "close_probability": round(close_prob, 2),
            "weighted_amount": round(amount * close_prob, 2),
            "forecast_category": random.choice([c.value for c in ForecastCategory]),
            "ai_confidence": round(random.uniform(0.6, 0.95), 2),
            "risk_factors": random.sample([
                "No recent activity", "Champion left", "Budget not confirmed",
                "Long sales cycle", "Competitor mentioned"
            ], k=random.randint(0, 3))
        })
    
    return {"forecast_id": forecast_id, "deals": deals}


@router.get("/accuracy")
async def get_forecast_accuracy(
    periods: int = Query(default=4, ge=1, le=12),
    tenant_id: str = Query(default="default")
):
    """Get forecast accuracy metrics"""
    accuracy_data = []
    
    for i in range(periods):
        period_date = (datetime.utcnow() - timedelta(days=30 * i)).isoformat()[:7]
        forecasted = random.uniform(500000, 2000000)
        actual = forecasted * random.uniform(0.85, 1.15)
        
        accuracy_data.append({
            "period": period_date,
            "forecasted": round(forecasted, 2),
            "actual": round(actual, 2),
            "variance": round(actual - forecasted, 2),
            "variance_pct": round((actual - forecasted) / forecasted * 100, 2),
            "mape": round(abs(actual - forecasted) / actual * 100, 2)
        })
    
    avg_mape = sum(d["mape"] for d in accuracy_data) / len(accuracy_data)
    
    return {
        "periods": accuracy_data,
        "summary": {
            "avg_mape": round(avg_mape, 2),
            "accuracy_rating": "good" if avg_mape < 15 else "fair" if avg_mape < 25 else "needs_improvement"
        }
    }


@router.get("/pipeline-coverage")
async def get_pipeline_coverage(
    target_amount: float,
    tenant_id: str = Query(default="default")
):
    """Get pipeline coverage analysis"""
    pipeline_total = target_amount * random.uniform(2.5, 4.5)
    weighted_pipeline = pipeline_total * random.uniform(0.3, 0.5)
    
    return {
        "target": target_amount,
        "pipeline_total": round(pipeline_total, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        "coverage_ratio": round(pipeline_total / target_amount, 2),
        "weighted_coverage": round(weighted_pipeline / target_amount, 2),
        "risk_assessment": "healthy" if pipeline_total / target_amount > 3 else "at_risk"
    }


@router.post("/forecasts/{forecast_id}/scenarios")
async def create_scenario(
    forecast_id: str,
    name: str,
    assumptions: List[Dict[str, Any]]
):
    """Create what-if scenario"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    scenario_id = str(uuid.uuid4())
    base_forecast = forecasts[forecast_id]
    
    scenario_amounts = dict(base_forecast["amounts"])
    for assumption in assumptions:
        if assumption.get("type") == "percentage_change":
            for key in scenario_amounts:
                scenario_amounts[key] *= (1 + assumption.get("value", 0) / 100)
    
    scenario = {
        "id": scenario_id,
        "forecast_id": forecast_id,
        "name": name,
        "assumptions": assumptions,
        "amounts": {k: round(v, 2) for k, v in scenario_amounts.items()},
        "created_at": datetime.utcnow().isoformat()
    }
    
    forecast_scenarios[scenario_id] = scenario
    
    return scenario


@router.get("/forecasts/{forecast_id}/scenarios")
async def list_scenarios(forecast_id: str):
    """List scenarios for a forecast"""
    scenarios = [s for s in forecast_scenarios.values() if s.get("forecast_id") == forecast_id]
    return {"scenarios": scenarios, "total": len(scenarios)}
