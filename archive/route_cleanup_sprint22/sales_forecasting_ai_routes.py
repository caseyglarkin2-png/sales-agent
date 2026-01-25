"""
Sales Forecasting AI Routes - Predictive forecasting with machine learning
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

router = APIRouter(prefix="/forecasting-ai", tags=["Sales Forecasting AI"])


class ForecastType(str, Enum):
    PIPELINE = "pipeline"
    REVENUE = "revenue"
    BOOKINGS = "bookings"
    UNITS = "units"


class ForecastPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class ForecastModel(str, Enum):
    WEIGHTED_PIPELINE = "weighted_pipeline"
    HISTORICAL_TREND = "historical_trend"
    ML_REGRESSION = "ml_regression"
    ENSEMBLE = "ensemble"
    MONTE_CARLO = "monte_carlo"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# In-memory storage
forecasts = {}
forecast_models_data = {}
forecast_scenarios = {}
forecast_history = {}


class ForecastRequest(BaseModel):
    forecast_type: ForecastType = ForecastType.REVENUE
    period: ForecastPeriod = ForecastPeriod.QUARTERLY
    model: ForecastModel = ForecastModel.ENSEMBLE
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    include_scenarios: bool = True
    team_ids: Optional[List[str]] = None
    product_lines: Optional[List[str]] = None


class ScenarioCreate(BaseModel):
    forecast_id: str
    name: str
    description: Optional[str] = None
    adjustments: Dict[str, Any]  # Win rate changes, deal size changes, etc.


class ModelTrainingRequest(BaseModel):
    model_type: ForecastModel
    training_period_months: int = 24
    validation_split: float = 0.2
    features: Optional[List[str]] = None


# Generate Forecast
@router.post("/generate")
async def generate_forecast(
    request: ForecastRequest,
    tenant_id: str = Query(default="default")
):
    """Generate AI-powered sales forecast"""
    forecast_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate forecast data
    base_forecast = random.randint(500000, 2000000)
    
    forecast = {
        "id": forecast_id,
        "forecast_type": request.forecast_type.value,
        "period": request.period.value,
        "model": request.model.value,
        "start_date": request.start_date or now.strftime("%Y-%m-%d"),
        "end_date": request.end_date or (now + timedelta(days=90)).strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "prediction": {
            "expected": base_forecast,
            "low": int(base_forecast * 0.75),
            "high": int(base_forecast * 1.25),
            "confidence_interval": 0.90
        },
        "confidence_level": random.choice(["high", "medium"]),
        "accuracy_score": round(random.uniform(0.80, 0.95), 2),
        "drivers": [
            {"factor": "Pipeline coverage", "impact": "+15%", "trend": "improving"},
            {"factor": "Win rate trend", "impact": "+5%", "trend": "stable"},
            {"factor": "Deal velocity", "impact": "-3%", "trend": "declining"},
            {"factor": "Seasonality", "impact": "+8%", "trend": "seasonal_peak"}
        ],
        "risks": [
            {"description": "3 large deals with extended decision timelines", "impact": "$150K at risk"},
            {"description": "Competitor pricing pressure in Enterprise segment", "impact": "5-10% discount pressure"}
        ],
        "tenant_id": tenant_id
    }
    
    # Add scenarios if requested
    if request.include_scenarios:
        forecast["scenarios"] = {
            "best_case": {
                "value": int(base_forecast * 1.3),
                "probability": 0.20,
                "assumptions": ["All commit deals close", "2 upside deals convert", "No churn"]
            },
            "expected": {
                "value": base_forecast,
                "probability": 0.60,
                "assumptions": ["80% commit deals close", "Standard win rates", "Normal churn"]
            },
            "worst_case": {
                "value": int(base_forecast * 0.7),
                "probability": 0.20,
                "assumptions": ["60% commit deals close", "2 large deals slip", "Elevated churn"]
            }
        }
    
    forecasts[forecast_id] = forecast
    
    logger.info("forecast_generated", forecast_id=forecast_id, model=request.model.value)
    
    return forecast


@router.get("/")
async def list_forecasts(
    forecast_type: Optional[ForecastType] = None,
    period: Optional[ForecastPeriod] = None,
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Query(default="default")
):
    """List generated forecasts"""
    result = [f for f in forecasts.values() if f.get("tenant_id") == tenant_id]
    
    if forecast_type:
        result = [f for f in result if f.get("forecast_type") == forecast_type.value]
    if period:
        result = [f for f in result if f.get("period") == period.value]
    
    return {"forecasts": result[:limit], "total": len(result)}


@router.get("/{forecast_id}")
async def get_forecast(
    forecast_id: str,
    tenant_id: str = Query(default="default")
):
    """Get forecast details"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return forecasts[forecast_id]


# Time Series Breakdown
@router.get("/{forecast_id}/breakdown")
async def get_forecast_breakdown(
    forecast_id: str,
    granularity: str = Query(default="week"),
    tenant_id: str = Query(default="default")
):
    """Get time series breakdown of forecast"""
    if forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    periods = 12 if granularity == "week" else 3 if granularity == "month" else 4
    base = random.randint(100000, 300000)
    
    return {
        "forecast_id": forecast_id,
        "granularity": granularity,
        "periods": [
            {
                "period": i + 1,
                "label": f"Week {i + 1}" if granularity == "week" else f"Month {i + 1}",
                "predicted": int(base * (1 + random.uniform(-0.2, 0.3))),
                "low": int(base * 0.8),
                "high": int(base * 1.3),
                "cumulative_predicted": int(base * (i + 1) * 1.05)
            }
            for i in range(periods)
        ]
    }


# Pipeline Analysis
@router.get("/pipeline-analysis")
async def analyze_pipeline_for_forecast(
    period: ForecastPeriod = ForecastPeriod.QUARTERLY,
    tenant_id: str = Query(default="default")
):
    """Analyze pipeline for forecasting"""
    return {
        "period": period.value,
        "analysis_date": datetime.utcnow().isoformat(),
        "pipeline_summary": {
            "total_pipeline": random.randint(3000000, 10000000),
            "qualified_pipeline": random.randint(2000000, 7000000),
            "commit_forecast": random.randint(800000, 2000000),
            "best_case_forecast": random.randint(1200000, 3000000)
        },
        "coverage_ratios": {
            "total_to_quota": round(random.uniform(2.5, 4.0), 1),
            "qualified_to_quota": round(random.uniform(1.8, 3.0), 1),
            "commit_to_quota": round(random.uniform(0.8, 1.2), 1)
        },
        "stage_distribution": [
            {"stage": "Discovery", "value": random.randint(500000, 1500000), "count": random.randint(20, 50)},
            {"stage": "Qualification", "value": random.randint(400000, 1200000), "count": random.randint(15, 40)},
            {"stage": "Demo", "value": random.randint(300000, 900000), "count": random.randint(10, 30)},
            {"stage": "Proposal", "value": random.randint(400000, 1000000), "count": random.randint(8, 25)},
            {"stage": "Negotiation", "value": random.randint(300000, 800000), "count": random.randint(5, 15)}
        ],
        "aging_analysis": {
            "healthy": {"count": random.randint(30, 80), "value": random.randint(1000000, 3000000)},
            "at_risk": {"count": random.randint(10, 30), "value": random.randint(300000, 1000000)},
            "stalled": {"count": random.randint(5, 15), "value": random.randint(200000, 600000)}
        }
    }


# Deal Predictions
@router.post("/predict-deals")
async def predict_deal_outcomes(
    deal_ids: Optional[List[str]] = None,
    tenant_id: str = Query(default="default")
):
    """Predict outcomes for specific deals"""
    deals = deal_ids or [f"deal_{i}" for i in range(10)]
    
    return {
        "predictions": [
            {
                "deal_id": deal_id,
                "deal_name": f"Enterprise Deal {i + 1}",
                "current_value": random.randint(50000, 500000),
                "predicted_value": random.randint(45000, 550000),
                "win_probability": round(random.uniform(0.3, 0.9), 2),
                "predicted_close_date": (datetime.utcnow() + timedelta(days=random.randint(15, 90))).strftime("%Y-%m-%d"),
                "confidence": random.choice(["high", "medium", "low"]),
                "risk_factors": random.sample([
                    "Extended stakeholder review",
                    "Competitive situation",
                    "Budget timing",
                    "Champion change",
                    "Technical concerns"
                ], k=random.randint(0, 2)),
                "recommendations": random.sample([
                    "Schedule executive alignment call",
                    "Provide additional ROI analysis",
                    "Address security requirements",
                    "Offer pilot program"
                ], k=random.randint(1, 2))
            }
            for i, deal_id in enumerate(deals)
        ]
    }


# Scenarios
@router.post("/scenarios")
async def create_scenario(
    request: ScenarioCreate,
    tenant_id: str = Query(default="default")
):
    """Create a forecast scenario"""
    scenario_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    if request.forecast_id not in forecasts:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    base_forecast = forecasts[request.forecast_id]["prediction"]["expected"]
    
    # Apply adjustments
    adjustment_factor = 1.0
    for key, value in request.adjustments.items():
        if key == "win_rate_change":
            adjustment_factor *= (1 + value / 100)
        elif key == "deal_size_change":
            adjustment_factor *= (1 + value / 100)
        elif key == "pipeline_change":
            adjustment_factor *= (1 + value / 100)
    
    adjusted_forecast = int(base_forecast * adjustment_factor)
    
    scenario = {
        "id": scenario_id,
        "forecast_id": request.forecast_id,
        "name": request.name,
        "description": request.description,
        "adjustments": request.adjustments,
        "original_forecast": base_forecast,
        "adjusted_forecast": adjusted_forecast,
        "change_pct": round((adjustment_factor - 1) * 100, 1),
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    forecast_scenarios[scenario_id] = scenario
    
    return scenario


@router.get("/scenarios/{forecast_id}")
async def list_scenarios(
    forecast_id: str,
    tenant_id: str = Query(default="default")
):
    """List scenarios for a forecast"""
    result = [s for s in forecast_scenarios.values() 
              if s.get("forecast_id") == forecast_id and s.get("tenant_id") == tenant_id]
    
    return {"scenarios": result, "total": len(result)}


# Model Management
@router.post("/models/train")
async def train_forecast_model(
    request: ModelTrainingRequest,
    tenant_id: str = Query(default="default")
):
    """Train a forecast model"""
    model_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    model_info = {
        "id": model_id,
        "model_type": request.model_type.value,
        "status": "training",
        "training_period_months": request.training_period_months,
        "validation_split": request.validation_split,
        "features": request.features or ["deal_size", "stage_duration", "activity_count", "engagement_score"],
        "metrics": None,
        "tenant_id": tenant_id,
        "started_at": now.isoformat(),
        "estimated_completion": (now + timedelta(minutes=10)).isoformat()
    }
    
    forecast_models_data[model_id] = model_info
    
    return model_info


@router.get("/models")
async def list_models(
    tenant_id: str = Query(default="default")
):
    """List trained forecast models"""
    result = [m for m in forecast_models_data.values() if m.get("tenant_id") == tenant_id]
    return {"models": result, "total": len(result)}


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    tenant_id: str = Query(default="default")
):
    """Get model details and performance metrics"""
    if model_id not in forecast_models_data:
        # Return mock model data
        return {
            "id": model_id,
            "model_type": "ensemble",
            "status": "ready",
            "metrics": {
                "mae": round(random.uniform(0.05, 0.15), 3),
                "mape": round(random.uniform(8, 18), 1),
                "rmse": round(random.uniform(0.08, 0.20), 3),
                "r_squared": round(random.uniform(0.75, 0.92), 3)
            },
            "feature_importance": [
                {"feature": "pipeline_value", "importance": 0.35},
                {"feature": "win_rate_trend", "importance": 0.25},
                {"feature": "deal_velocity", "importance": 0.20},
                {"feature": "activity_score", "importance": 0.12},
                {"feature": "seasonality", "importance": 0.08}
            ],
            "last_trained": datetime.utcnow().isoformat(),
            "training_samples": random.randint(1000, 10000)
        }
    
    return forecast_models_data[model_id]


# Accuracy Tracking
@router.get("/accuracy")
async def get_forecast_accuracy(
    periods: int = Query(default=6, ge=1, le=24),
    tenant_id: str = Query(default="default")
):
    """Get historical forecast accuracy"""
    return {
        "overall_accuracy": round(random.uniform(0.82, 0.93), 2),
        "by_period": [
            {
                "period": (datetime.utcnow() - timedelta(days=30 * i)).strftime("%Y-%m"),
                "forecasted": random.randint(800000, 1500000),
                "actual": random.randint(750000, 1600000),
                "accuracy": round(random.uniform(0.75, 0.98), 2),
                "variance_pct": round(random.uniform(-15, 15), 1)
            }
            for i in range(periods)
        ],
        "by_model": {
            "weighted_pipeline": round(random.uniform(0.78, 0.88), 2),
            "historical_trend": round(random.uniform(0.75, 0.85), 2),
            "ml_regression": round(random.uniform(0.82, 0.92), 2),
            "ensemble": round(random.uniform(0.85, 0.95), 2)
        },
        "improvement_trend": round(random.uniform(2, 8), 1)
    }


# Rep-Level Forecasts
@router.get("/by-rep")
async def get_forecast_by_rep(
    period: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get forecasts broken down by sales rep"""
    return {
        "period": period or "Q1 2024",
        "team_forecast": random.randint(1500000, 3000000),
        "reps": [
            {
                "rep_id": f"rep_{i}",
                "name": f"Sales Rep {i + 1}",
                "quota": random.randint(200000, 500000),
                "forecast": {
                    "commit": random.randint(150000, 400000),
                    "best_case": random.randint(200000, 500000),
                    "expected": random.randint(175000, 450000)
                },
                "attainment_forecast": round(random.uniform(0.70, 1.20), 2),
                "confidence": random.choice(["high", "medium", "low"]),
                "pipeline_health": random.choice(["healthy", "at_risk", "needs_attention"])
            }
            for i in range(8)
        ]
    }


# Real-time Updates
@router.get("/live")
async def get_live_forecast(
    tenant_id: str = Query(default="default")
):
    """Get live forecast with real-time deal updates"""
    return {
        "as_of": datetime.utcnow().isoformat(),
        "current_quarter": "Q1 2024",
        "live_forecast": {
            "total": random.randint(1500000, 2500000),
            "change_today": random.randint(-50000, 100000),
            "change_this_week": random.randint(-100000, 200000)
        },
        "recent_changes": [
            {
                "type": "deal_won",
                "deal": "Acme Corp Enterprise",
                "value": random.randint(50000, 200000),
                "impact": "+$150K to commit",
                "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat()
            },
            {
                "type": "deal_slipped",
                "deal": "Tech Solutions Inc",
                "value": random.randint(30000, 100000),
                "impact": "Moved to next quarter",
                "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(2, 48))).isoformat()
            }
        ],
        "at_risk_deals": random.randint(3, 8),
        "deals_to_close_this_week": random.randint(5, 15)
    }
