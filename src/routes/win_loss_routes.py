"""
Win/Loss Analysis Routes - Analyze deal outcomes and competitive insights
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

router = APIRouter(prefix="/win-loss", tags=["Win/Loss Analysis"])


class DealOutcome(str, Enum):
    WON = "won"
    LOST = "lost"
    NO_DECISION = "no_decision"


class LossReason(str, Enum):
    PRICE = "price"
    FEATURE_GAP = "feature_gap"
    COMPETITOR = "competitor"
    TIMING = "timing"
    BUDGET = "budget"
    CHAMPION_LEFT = "champion_left"
    INTERNAL_POLITICS = "internal_politics"
    POOR_FIT = "poor_fit"
    NO_DECISION = "no_decision"
    OTHER = "other"


class WinFactor(str, Enum):
    PRODUCT_FIT = "product_fit"
    RELATIONSHIP = "relationship"
    PRICE_VALUE = "price_value"
    IMPLEMENTATION = "implementation"
    SUPPORT = "support"
    BRAND_TRUST = "brand_trust"
    INTEGRATION = "integration"
    CHAMPION = "champion"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# In-memory storage
win_loss_analyses = {}
deal_patterns = {}
competitive_intel = {}


class WinLossAnalysisCreate(BaseModel):
    deal_id: str
    deal_name: str
    outcome: DealOutcome
    deal_value: float
    sales_cycle_days: int
    primary_competitor: Optional[str] = None
    loss_reasons: Optional[List[LossReason]] = []
    win_factors: Optional[List[WinFactor]] = []
    customer_feedback: Optional[str] = None


class InterviewCreate(BaseModel):
    analysis_id: str
    contact_name: str
    contact_title: str
    interview_notes: str
    key_insights: List[str]
    decision_factors: List[str]


# Dashboard
@router.get("/dashboard")
async def get_win_loss_dashboard(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get win/loss analysis dashboard"""
    now = datetime.utcnow()
    
    return {
        "period": period,
        "generated_at": now.isoformat(),
        "summary": {
            "total_deals_analyzed": random.randint(50, 150),
            "wins": random.randint(25, 60),
            "losses": random.randint(15, 50),
            "no_decisions": random.randint(5, 20),
            "win_rate": round(random.uniform(0.25, 0.45), 2),
            "competitive_win_rate": round(random.uniform(0.30, 0.50), 2)
        },
        "win_factors_ranking": [
            {"factor": WinFactor.PRODUCT_FIT.value, "mentions": random.randint(30, 60), "impact_score": round(random.uniform(4.0, 5.0), 1)},
            {"factor": WinFactor.RELATIONSHIP.value, "mentions": random.randint(25, 50), "impact_score": round(random.uniform(3.5, 4.8), 1)},
            {"factor": WinFactor.CHAMPION.value, "mentions": random.randint(20, 45), "impact_score": round(random.uniform(3.5, 4.5), 1)},
            {"factor": WinFactor.PRICE_VALUE.value, "mentions": random.randint(15, 35), "impact_score": round(random.uniform(3.0, 4.2), 1)}
        ],
        "loss_reasons_ranking": [
            {"reason": LossReason.PRICE.value, "mentions": random.randint(15, 35), "impact_score": round(random.uniform(3.5, 4.5), 1)},
            {"reason": LossReason.FEATURE_GAP.value, "mentions": random.randint(12, 30), "impact_score": round(random.uniform(3.0, 4.2), 1)},
            {"reason": LossReason.COMPETITOR.value, "mentions": random.randint(10, 25), "impact_score": round(random.uniform(3.0, 4.0), 1)},
            {"reason": LossReason.NO_DECISION.value, "mentions": random.randint(8, 20), "impact_score": round(random.uniform(2.5, 3.5), 1)}
        ],
        "trends": {
            "win_rate_vs_last_period": round(random.uniform(-0.05, 0.10), 2),
            "avg_deal_size_change": round(random.uniform(-10, 20), 1),
            "sales_cycle_change_days": random.randint(-10, 10)
        }
    }


# Analysis CRUD
@router.post("/analysis")
async def create_analysis(
    request: WinLossAnalysisCreate,
    tenant_id: str = Query(default="default")
):
    """Create a win/loss analysis for a deal"""
    analysis_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    analysis = {
        "id": analysis_id,
        "deal_id": request.deal_id,
        "deal_name": request.deal_name,
        "outcome": request.outcome.value,
        "deal_value": request.deal_value,
        "sales_cycle_days": request.sales_cycle_days,
        "primary_competitor": request.primary_competitor,
        "loss_reasons": [r.value for r in (request.loss_reasons or [])],
        "win_factors": [f.value for f in (request.win_factors or [])],
        "customer_feedback": request.customer_feedback,
        "status": AnalysisStatus.PENDING.value,
        "interviews": [],
        "insights": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    win_loss_analyses[analysis_id] = analysis
    
    return analysis


@router.get("/analysis/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    tenant_id: str = Query(default="default")
):
    """Get a specific analysis"""
    analysis = win_loss_analyses.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/analysis")
async def list_analyses(
    outcome: Optional[DealOutcome] = None,
    status: Optional[AnalysisStatus] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List win/loss analyses"""
    result = [a for a in win_loss_analyses.values() if a.get("tenant_id") == tenant_id]
    
    if outcome:
        result = [a for a in result if a.get("outcome") == outcome.value]
    if status:
        result = [a for a in result if a.get("status") == status.value]
    
    return {"analyses": result[:limit], "total": len(result)}


@router.post("/analysis/{analysis_id}/interview")
async def add_interview(
    analysis_id: str,
    request: InterviewCreate,
    tenant_id: str = Query(default="default")
):
    """Add interview to analysis"""
    analysis = win_loss_analyses.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    interview = {
        "id": str(uuid.uuid4()),
        "contact_name": request.contact_name,
        "contact_title": request.contact_title,
        "interview_notes": request.interview_notes,
        "key_insights": request.key_insights,
        "decision_factors": request.decision_factors,
        "conducted_at": datetime.utcnow().isoformat()
    }
    
    analysis["interviews"].append(interview)
    analysis["updated_at"] = datetime.utcnow().isoformat()
    
    return interview


# Competitive Analysis
@router.get("/competitive")
async def get_competitive_analysis(
    competitor: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get competitive win/loss analysis"""
    competitors = [
        {
            "name": "Competitor A",
            "deals_competed": random.randint(20, 50),
            "wins_against": random.randint(8, 25),
            "losses_to": random.randint(10, 25),
            "win_rate_against": round(random.uniform(0.35, 0.55), 2),
            "avg_deal_size_won": random.randint(40000, 80000),
            "avg_deal_size_lost": random.randint(60000, 120000),
            "top_win_factors": [WinFactor.PRODUCT_FIT.value, WinFactor.RELATIONSHIP.value],
            "top_loss_reasons": [LossReason.PRICE.value, LossReason.FEATURE_GAP.value]
        },
        {
            "name": "Competitor B",
            "deals_competed": random.randint(15, 40),
            "wins_against": random.randint(6, 20),
            "losses_to": random.randint(8, 20),
            "win_rate_against": round(random.uniform(0.30, 0.50), 2),
            "avg_deal_size_won": random.randint(35000, 70000),
            "avg_deal_size_lost": random.randint(50000, 100000),
            "top_win_factors": [WinFactor.INTEGRATION.value, WinFactor.SUPPORT.value],
            "top_loss_reasons": [LossReason.FEATURE_GAP.value, LossReason.COMPETITOR.value]
        },
        {
            "name": "Competitor C",
            "deals_competed": random.randint(10, 30),
            "wins_against": random.randint(5, 15),
            "losses_to": random.randint(4, 15),
            "win_rate_against": round(random.uniform(0.40, 0.60), 2),
            "avg_deal_size_won": random.randint(45000, 90000),
            "avg_deal_size_lost": random.randint(55000, 110000),
            "top_win_factors": [WinFactor.CHAMPION.value, WinFactor.BRAND_TRUST.value],
            "top_loss_reasons": [LossReason.PRICE.value, LossReason.TIMING.value]
        }
    ]
    
    if competitor:
        competitors = [c for c in competitors if competitor.lower() in c["name"].lower()]
    
    return {
        "competitors": competitors,
        "overall_competitive_win_rate": round(random.uniform(0.38, 0.52), 2),
        "most_threatening_competitor": "Competitor A",
        "strongest_against": "Competitor C"
    }


# Pattern Detection
@router.get("/patterns")
async def get_deal_patterns(
    outcome: Optional[DealOutcome] = None,
    tenant_id: str = Query(default="default")
):
    """Get patterns in won and lost deals"""
    return {
        "win_patterns": [
            {
                "pattern": "Executive sponsor identified early",
                "correlation": round(random.uniform(0.70, 0.90), 2),
                "deals_with_pattern": random.randint(40, 80),
                "win_rate_with_pattern": round(random.uniform(0.55, 0.75), 2)
            },
            {
                "pattern": "Technical evaluation completed",
                "correlation": round(random.uniform(0.65, 0.85), 2),
                "deals_with_pattern": random.randint(35, 70),
                "win_rate_with_pattern": round(random.uniform(0.50, 0.70), 2)
            },
            {
                "pattern": "Multi-threaded deal (3+ contacts)",
                "correlation": round(random.uniform(0.60, 0.80), 2),
                "deals_with_pattern": random.randint(30, 60),
                "win_rate_with_pattern": round(random.uniform(0.45, 0.65), 2)
            }
        ],
        "loss_patterns": [
            {
                "pattern": "Single-threaded deal",
                "correlation": round(random.uniform(0.65, 0.80), 2),
                "deals_with_pattern": random.randint(25, 50),
                "loss_rate_with_pattern": round(random.uniform(0.60, 0.80), 2)
            },
            {
                "pattern": "No discovery call completed",
                "correlation": round(random.uniform(0.70, 0.85), 2),
                "deals_with_pattern": random.randint(20, 45),
                "loss_rate_with_pattern": round(random.uniform(0.65, 0.85), 2)
            },
            {
                "pattern": "Price discussed before value established",
                "correlation": round(random.uniform(0.55, 0.75), 2),
                "deals_with_pattern": random.randint(15, 40),
                "loss_rate_with_pattern": round(random.uniform(0.55, 0.75), 2)
            }
        ],
        "no_decision_patterns": [
            {
                "pattern": "Budget not confirmed",
                "correlation": round(random.uniform(0.70, 0.85), 2),
                "deals_with_pattern": random.randint(15, 35)
            },
            {
                "pattern": "Unclear decision process",
                "correlation": round(random.uniform(0.65, 0.80), 2),
                "deals_with_pattern": random.randint(12, 30)
            }
        ]
    }


# Segmented Analysis
@router.get("/segmented")
async def get_segmented_analysis(
    segment_by: str = Query(default="industry"),
    tenant_id: str = Query(default="default")
):
    """Get win/loss analysis by segment"""
    segments = {
        "industry": [
            {"segment": "Technology", "deals": random.randint(30, 60), "win_rate": round(random.uniform(0.35, 0.55), 2), "avg_deal_size": random.randint(50000, 100000)},
            {"segment": "Healthcare", "deals": random.randint(20, 45), "win_rate": round(random.uniform(0.30, 0.50), 2), "avg_deal_size": random.randint(45000, 90000)},
            {"segment": "Financial Services", "deals": random.randint(25, 50), "win_rate": round(random.uniform(0.35, 0.55), 2), "avg_deal_size": random.randint(60000, 120000)},
            {"segment": "Retail", "deals": random.randint(15, 35), "win_rate": round(random.uniform(0.25, 0.45), 2), "avg_deal_size": random.randint(35000, 70000)}
        ],
        "deal_size": [
            {"segment": "Enterprise ($100K+)", "deals": random.randint(15, 35), "win_rate": round(random.uniform(0.25, 0.40), 2), "avg_cycle_days": random.randint(80, 150)},
            {"segment": "Mid-Market ($50K-$100K)", "deals": random.randint(25, 50), "win_rate": round(random.uniform(0.30, 0.45), 2), "avg_cycle_days": random.randint(50, 90)},
            {"segment": "SMB (<$50K)", "deals": random.randint(40, 80), "win_rate": round(random.uniform(0.40, 0.55), 2), "avg_cycle_days": random.randint(20, 50)}
        ],
        "source": [
            {"segment": "Inbound", "deals": random.randint(35, 70), "win_rate": round(random.uniform(0.35, 0.50), 2), "avg_deal_size": random.randint(40000, 80000)},
            {"segment": "Outbound", "deals": random.randint(25, 55), "win_rate": round(random.uniform(0.25, 0.40), 2), "avg_deal_size": random.randint(55000, 100000)},
            {"segment": "Partner", "deals": random.randint(15, 40), "win_rate": round(random.uniform(0.40, 0.55), 2), "avg_deal_size": random.randint(50000, 90000)}
        ]
    }
    
    return {
        "segment_by": segment_by,
        "segments": segments.get(segment_by, segments["industry"]),
        "insights": [
            f"Highest win rate in {random.choice(['Technology', 'Financial Services'])} segment",
            "Larger deals have longer sales cycles but lower win rates",
            "Partner-sourced deals show highest win rate"
        ]
    }


# AI Insights
@router.get("/ai-insights")
async def get_ai_insights(
    focus_area: str = Query(default="all"),
    tenant_id: str = Query(default="default")
):
    """Get AI-generated insights from win/loss analysis"""
    return {
        "focus_area": focus_area,
        "generated_at": datetime.utcnow().isoformat(),
        "key_insights": [
            {
                "insight": "Deals with executive sponsorship have 2.3x higher win rate",
                "confidence": round(random.uniform(0.85, 0.95), 2),
                "supporting_data": {"deals_analyzed": random.randint(100, 200), "correlation": 0.78},
                "recommendation": "Prioritize executive engagement in qualification stage"
            },
            {
                "insight": "Pricing objections are most common in financial services deals",
                "confidence": round(random.uniform(0.80, 0.92), 2),
                "supporting_data": {"deals_analyzed": random.randint(50, 100), "mention_rate": 0.45},
                "recommendation": "Develop ROI-focused value messaging for FinServ"
            },
            {
                "insight": "Technical validation increases win rate by 35%",
                "confidence": round(random.uniform(0.82, 0.93), 2),
                "supporting_data": {"deals_analyzed": random.randint(80, 150), "lift": 0.35},
                "recommendation": "Mandate POC/pilot for deals over $75K"
            }
        ],
        "action_items": [
            {"priority": "high", "action": "Create executive briefing program", "expected_impact": "15% win rate improvement"},
            {"priority": "medium", "action": "Update competitive battlecards for Competitor A", "expected_impact": "10% improvement against competitor"},
            {"priority": "medium", "action": "Develop feature comparison matrix", "expected_impact": "Reduce feature gap objections by 25%"}
        ]
    }


# Recommendations
@router.get("/recommendations/{deal_id}")
async def get_deal_recommendations(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get AI recommendations for improving deal outcome based on historical patterns"""
    return {
        "deal_id": deal_id,
        "current_win_probability": round(random.uniform(0.30, 0.65), 2),
        "recommendations": [
            {
                "action": "Identify and engage executive sponsor",
                "impact": "High",
                "rationale": "Deals with exec sponsors have 2.3x higher win rate",
                "priority": 1
            },
            {
                "action": "Schedule technical validation session",
                "impact": "High",
                "rationale": "Technical POCs increase win rate by 35%",
                "priority": 2
            },
            {
                "action": "Multi-thread with 2+ additional stakeholders",
                "impact": "Medium",
                "rationale": "Single-threaded deals have 65% loss rate",
                "priority": 3
            },
            {
                "action": "Address potential price objection proactively",
                "impact": "Medium",
                "rationale": "Industry segment shows 45% price objection rate",
                "priority": 4
            }
        ],
        "similar_won_deals": [
            {"deal_name": "TechCorp Enterprise", "value": random.randint(80000, 150000), "similarity_score": round(random.uniform(0.75, 0.90), 2)},
            {"deal_name": "GlobalFinance Suite", "value": random.randint(90000, 180000), "similarity_score": round(random.uniform(0.70, 0.85), 2)}
        ],
        "similar_lost_deals": [
            {"deal_name": "MedTech Solutions", "value": random.randint(70000, 140000), "loss_reason": LossReason.PRICE.value, "similarity_score": round(random.uniform(0.65, 0.80), 2)}
        ]
    }
