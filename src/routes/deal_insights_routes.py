"""
Deal Insights Routes - AI-powered deal analysis and recommendations
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

router = APIRouter(prefix="/deal-insights", tags=["Deal Insights"])


class InsightType(str, Enum):
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    ACTION = "action"
    TREND = "trend"
    ANOMALY = "anomaly"


class InsightPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DealHealth(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class SignalType(str, Enum):
    ENGAGEMENT = "engagement"
    STAKEHOLDER = "stakeholder"
    COMPETITION = "competition"
    TIMELINE = "timeline"
    BUDGET = "budget"
    CHAMPION = "champion"


# In-memory storage
deal_insights = {}
insight_actions = {}
deal_health_scores = {}


class InsightFeedbackRequest(BaseModel):
    insight_id: str
    is_helpful: bool
    feedback_text: Optional[str] = None


# Deal Analysis
@router.get("/analyze/{deal_id}")
async def analyze_deal(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get comprehensive AI analysis of a deal"""
    now = datetime.utcnow()
    
    health = random.choice(list(DealHealth))
    health_score = random.randint(60, 95) if health in [DealHealth.EXCELLENT, DealHealth.GOOD] else random.randint(30, 60)
    
    analysis = {
        "deal_id": deal_id,
        "analyzed_at": now.isoformat(),
        "health": {
            "status": health.value,
            "score": health_score,
            "trend": random.choice(["improving", "stable", "declining"]),
            "change_vs_last_week": random.randint(-10, 15)
        },
        "win_probability": {
            "current": round(random.uniform(0.4, 0.85), 2),
            "change_7d": round(random.uniform(-0.1, 0.15), 2),
            "factors": [
                {"name": "Engagement Level", "score": random.randint(60, 95), "impact": "positive"},
                {"name": "Decision Timeline", "score": random.randint(40, 80), "impact": "neutral"},
                {"name": "Competitive Position", "score": random.randint(50, 90), "impact": "positive"},
                {"name": "Budget Alignment", "score": random.randint(50, 85), "impact": "neutral"}
            ]
        },
        "risk_assessment": {
            "overall_risk": random.choice(["low", "medium", "high"]),
            "risks": [
                {
                    "type": "stakeholder",
                    "description": "Key decision maker has been unresponsive for 5 days",
                    "severity": "high",
                    "mitigation": "Request introduction to alternative champion"
                },
                {
                    "type": "timeline",
                    "description": "Close date has been pushed twice",
                    "severity": "medium",
                    "mitigation": "Establish concrete next steps with firm deadlines"
                }
            ]
        },
        "opportunity_score": random.randint(65, 95),
        "recommended_actions": [
            {
                "action": "Schedule executive alignment meeting",
                "priority": "high",
                "reason": "No executive engagement in past 14 days",
                "impact": "+12% win probability"
            },
            {
                "action": "Send customized ROI analysis",
                "priority": "medium",
                "reason": "Prospect mentioned budget concerns",
                "impact": "+8% win probability"
            },
            {
                "action": "Address technical requirements document",
                "priority": "medium",
                "reason": "Open technical questions from last call",
                "impact": "+5% win probability"
            }
        ]
    }
    
    return analysis


@router.get("/insights/{deal_id}")
async def get_deal_insights(
    deal_id: str,
    insight_type: Optional[InsightType] = None,
    priority: Optional[InsightPriority] = None,
    tenant_id: str = Query(default="default")
):
    """Get specific insights for a deal"""
    insights = [
        {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "type": InsightType.RISK.value,
            "priority": InsightPriority.HIGH.value,
            "title": "Champion engagement declining",
            "description": "Sarah Johnson (VP Sales) hasn't opened last 3 emails. Consider alternate approach.",
            "data": {"email_opens": 0, "days_since_response": 8},
            "recommendation": "Try phone outreach or request referral to colleague",
            "generated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "type": InsightType.OPPORTUNITY.value,
            "priority": InsightPriority.MEDIUM.value,
            "title": "Upsell opportunity detected",
            "description": "Based on usage patterns, customer may benefit from Enterprise tier",
            "data": {"current_tier": "Professional", "usage_pct": 95},
            "recommendation": "Introduce Enterprise features in next meeting",
            "generated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "type": InsightType.TREND.value,
            "priority": InsightPriority.LOW.value,
            "title": "Positive engagement trend",
            "description": "3 new stakeholders have engaged with content this week",
            "data": {"new_contacts": 3, "content_views": 12},
            "recommendation": "Map new stakeholders in buying committee",
            "generated_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "type": InsightType.ACTION.value,
            "priority": InsightPriority.CRITICAL.value,
            "title": "Follow-up overdue",
            "description": "Promised proposal was due 2 days ago",
            "data": {"days_overdue": 2, "commitment": "Send proposal by Friday"},
            "recommendation": "Send proposal immediately with apology for delay",
            "generated_at": datetime.utcnow().isoformat()
        }
    ]
    
    if insight_type:
        insights = [i for i in insights if i["type"] == insight_type.value]
    if priority:
        insights = [i for i in insights if i["priority"] == priority.value]
    
    return {"insights": insights, "total": len(insights)}


# Signals
@router.get("/signals/{deal_id}")
async def get_deal_signals(
    deal_id: str,
    signal_type: Optional[SignalType] = None,
    tenant_id: str = Query(default="default")
):
    """Get buying signals for a deal"""
    signals = [
        {
            "type": SignalType.ENGAGEMENT.value,
            "signal": "High content engagement",
            "strength": "strong",
            "details": "5 stakeholders viewed pricing page in last 3 days",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "type": SignalType.STAKEHOLDER.value,
            "signal": "New stakeholder identified",
            "strength": "medium",
            "details": "CFO added to email thread",
            "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat()
        },
        {
            "type": SignalType.CHAMPION.value,
            "signal": "Champion activity",
            "strength": "strong",
            "details": "VP Sales shared content internally 3 times",
            "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat()
        },
        {
            "type": SignalType.TIMELINE.value,
            "signal": "Urgency indicator",
            "strength": "medium",
            "details": "Mentioned Q1 budget deadline in last call",
            "timestamp": (datetime.utcnow() - timedelta(days=3)).isoformat()
        },
        {
            "type": SignalType.COMPETITION.value,
            "signal": "Competitive comparison",
            "strength": "weak",
            "details": "Prospect visited competitor comparison page",
            "timestamp": (datetime.utcnow() - timedelta(days=4)).isoformat()
        }
    ]
    
    if signal_type:
        signals = [s for s in signals if s["type"] == signal_type.value]
    
    return {"signals": signals, "overall_signal_strength": random.choice(["strong", "medium", "weak"])}


# Stakeholder Analysis
@router.get("/stakeholders/{deal_id}")
async def analyze_stakeholders(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Analyze stakeholder engagement and influence"""
    return {
        "deal_id": deal_id,
        "stakeholder_count": random.randint(3, 8),
        "engagement_score": random.randint(60, 95),
        "stakeholders": [
            {
                "name": "Sarah Johnson",
                "title": "VP of Sales",
                "role": "Champion",
                "influence": "high",
                "sentiment": "positive",
                "engagement_score": random.randint(70, 95),
                "last_interaction": (datetime.utcnow() - timedelta(days=random.randint(1, 7))).isoformat(),
                "insights": ["Strong advocate", "Needs ROI data for CFO"]
            },
            {
                "name": "Mike Chen",
                "title": "CFO",
                "role": "Economic Buyer",
                "influence": "high",
                "sentiment": "neutral",
                "engagement_score": random.randint(40, 70),
                "last_interaction": (datetime.utcnow() - timedelta(days=random.randint(7, 14))).isoformat(),
                "insights": ["Budget holder", "Risk-averse", "Needs business case"]
            },
            {
                "name": "Lisa Park",
                "title": "Sales Operations Manager",
                "role": "Technical Evaluator",
                "influence": "medium",
                "sentiment": "positive",
                "engagement_score": random.randint(60, 85),
                "last_interaction": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat(),
                "insights": ["Highly technical", "Loves automation features"]
            }
        ],
        "gaps": [
            {"type": "missing_role", "description": "No IT/Security stakeholder identified"},
            {"type": "low_engagement", "description": "CFO engagement below threshold"}
        ],
        "recommendations": [
            "Request introduction to IT stakeholder",
            "Schedule CFO-focused ROI presentation"
        ]
    }


# Competitive Analysis
@router.get("/competitive/{deal_id}")
async def get_competitive_analysis(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get competitive intelligence for a deal"""
    return {
        "deal_id": deal_id,
        "competitive_situation": random.choice(["head_to_head", "preferred", "underdog", "sole_source"]),
        "known_competitors": [
            {
                "name": "CompetitorA",
                "likelihood": "high",
                "strengths": ["Lower price point", "Existing relationship"],
                "weaknesses": ["Limited features", "Poor support reputation"],
                "counter_strategy": "Emphasize total cost of ownership and support quality"
            },
            {
                "name": "CompetitorB",
                "likelihood": "medium",
                "strengths": ["Strong brand", "Enterprise features"],
                "weaknesses": ["Complex implementation", "Long contracts"],
                "counter_strategy": "Highlight quick time-to-value and flexibility"
            }
        ],
        "win_against_competitors": {
            "CompetitorA": {"wins": 12, "losses": 5, "win_rate": 0.71},
            "CompetitorB": {"wins": 8, "losses": 6, "win_rate": 0.57}
        },
        "recommended_battlecards": [
            {"title": "CompetitorA Displacement", "last_updated": "2024-01-10"},
            {"title": "Enterprise Feature Comparison", "last_updated": "2024-01-15"}
        ]
    }


# Timeline Analysis
@router.get("/timeline/{deal_id}")
async def analyze_timeline(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Analyze deal timeline and velocity"""
    return {
        "deal_id": deal_id,
        "current_stage": "Proposal",
        "days_in_current_stage": random.randint(5, 20),
        "average_for_stage": random.randint(10, 15),
        "velocity_status": random.choice(["on_track", "behind", "ahead"]),
        "timeline": {
            "created": (datetime.utcnow() - timedelta(days=45)).isoformat(),
            "expected_close": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "predicted_close": (datetime.utcnow() + timedelta(days=random.randint(25, 45))).isoformat(),
            "close_date_changes": 2
        },
        "stage_history": [
            {"stage": "Qualification", "entered": (datetime.utcnow() - timedelta(days=45)).isoformat(), "days": 8},
            {"stage": "Discovery", "entered": (datetime.utcnow() - timedelta(days=37)).isoformat(), "days": 12},
            {"stage": "Demo", "entered": (datetime.utcnow() - timedelta(days=25)).isoformat(), "days": 10},
            {"stage": "Proposal", "entered": (datetime.utcnow() - timedelta(days=15)).isoformat(), "days": 15}
        ],
        "next_steps": [
            {"action": "Proposal review call", "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat()},
            {"action": "Contract negotiation", "due_date": (datetime.utcnow() + timedelta(days=10)).isoformat()},
            {"action": "Final approval", "due_date": (datetime.utcnow() + timedelta(days=20)).isoformat()}
        ]
    }


# Recommendations
@router.get("/recommendations/{deal_id}")
async def get_recommendations(
    deal_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    tenant_id: str = Query(default="default")
):
    """Get AI-powered recommendations for a deal"""
    recommendations = [
        {
            "id": str(uuid.uuid4()),
            "type": "action",
            "priority": "high",
            "title": "Schedule executive sponsor call",
            "description": "Executive engagement has been low. Schedule call with VP Sales to reinforce partnership value.",
            "expected_impact": "+15% win probability",
            "effort": "low",
            "deadline": (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
        },
        {
            "id": str(uuid.uuid4()),
            "type": "content",
            "priority": "medium",
            "title": "Share relevant case study",
            "description": "Similar company in same industry achieved 40% productivity gain. Share case study.",
            "expected_impact": "+8% win probability",
            "effort": "low",
            "content_id": "case_study_123"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "stakeholder",
            "priority": "high",
            "title": "Expand buying committee map",
            "description": "Only 3 stakeholders identified. Typical deals this size have 5-7 stakeholders.",
            "expected_impact": "+10% win probability",
            "effort": "medium"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "competitive",
            "priority": "medium",
            "title": "Address competitive threat",
            "description": "Prospect visited CompetitorA comparison page. Proactively share differentiation.",
            "expected_impact": "+12% win probability",
            "effort": "low",
            "content_id": "battlecard_456"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "timing",
            "priority": "critical",
            "title": "Accelerate timeline",
            "description": "Q1 budget cycle ends in 3 weeks. Push for decision before deadline.",
            "expected_impact": "+20% close this quarter",
            "effort": "high"
        }
    ]
    
    return {"recommendations": recommendations[:limit], "total": len(recommendations)}


# Feedback
@router.post("/feedback")
async def submit_insight_feedback(
    request: InsightFeedbackRequest,
    tenant_id: str = Query(default="default")
):
    """Submit feedback on an insight"""
    return {
        "insight_id": request.insight_id,
        "feedback_recorded": True,
        "message": "Thank you for your feedback. This helps improve our AI recommendations."
    }


# Similar Deals
@router.get("/similar/{deal_id}")
async def find_similar_deals(
    deal_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    tenant_id: str = Query(default="default")
):
    """Find similar deals for pattern matching"""
    return {
        "deal_id": deal_id,
        "similar_deals": [
            {
                "deal_id": f"deal_{random.randint(100, 999)}",
                "company": f"Similar Company {i + 1}",
                "industry": random.choice(["Technology", "Healthcare", "Finance"]),
                "deal_value": random.randint(50000, 300000),
                "outcome": random.choice(["won", "lost"]),
                "similarity_score": round(random.uniform(0.75, 0.95), 2),
                "key_similarities": random.sample([
                    "Same industry",
                    "Similar company size",
                    "Same use case",
                    "Similar buying process",
                    "Same competitor involved"
                ], k=3),
                "lessons_learned": "Won by focusing on quick implementation and dedicated support"
            }
            for i in range(limit)
        ]
    }


# Health Score Breakdown
@router.get("/health/{deal_id}")
async def get_health_breakdown(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get detailed health score breakdown"""
    return {
        "deal_id": deal_id,
        "overall_score": random.randint(60, 95),
        "components": [
            {
                "name": "Engagement",
                "score": random.randint(50, 100),
                "weight": 0.25,
                "trend": random.choice(["up", "down", "stable"]),
                "factors": ["Email opens", "Meeting attendance", "Content views"]
            },
            {
                "name": "Stakeholder Coverage",
                "score": random.randint(50, 100),
                "weight": 0.20,
                "trend": random.choice(["up", "down", "stable"]),
                "factors": ["Number of contacts", "Roles covered", "Seniority mix"]
            },
            {
                "name": "Activity Momentum",
                "score": random.randint(50, 100),
                "weight": 0.20,
                "trend": random.choice(["up", "down", "stable"]),
                "factors": ["Meeting frequency", "Email cadence", "Response times"]
            },
            {
                "name": "Sales Process",
                "score": random.randint(50, 100),
                "weight": 0.20,
                "trend": random.choice(["up", "down", "stable"]),
                "factors": ["Stage progression", "MEDDIC completion", "Next steps defined"]
            },
            {
                "name": "Competitive Position",
                "score": random.randint(50, 100),
                "weight": 0.15,
                "trend": random.choice(["up", "down", "stable"]),
                "factors": ["Win rate vs competitors", "Differentiation clarity", "Proof points"]
            }
        ]
    }
