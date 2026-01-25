"""
Team Performance Routes - Sales team performance analytics and management
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

router = APIRouter(prefix="/team-performance", tags=["Team Performance"])


class PerformanceMetric(str, Enum):
    REVENUE = "revenue"
    QUOTA_ATTAINMENT = "quota_attainment"
    WIN_RATE = "win_rate"
    DEALS_WON = "deals_won"
    PIPELINE_CREATED = "pipeline_created"
    ACTIVITIES = "activities"
    MEETINGS = "meetings"
    RESPONSE_TIME = "response_time"


class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


# In-memory storage
performance_snapshots = {}
team_goals = {}
performance_reviews = {}


class TeamGoalCreate(BaseModel):
    team_id: str
    metric: PerformanceMetric
    target_value: float
    period: TimePeriod
    start_date: str
    end_date: str


class ReviewCreate(BaseModel):
    rep_id: str
    reviewer_id: str
    period: str
    ratings: Dict[str, int]
    comments: Optional[str] = None


# Team Overview
@router.get("/teams/{team_id}/overview")
async def get_team_overview(
    team_id: str,
    period: TimePeriod = Query(default=TimePeriod.MONTHLY)
):
    """Get team performance overview"""
    now = datetime.utcnow()
    
    return {
        "team_id": team_id,
        "period": period.value,
        "performance": {
            "revenue": {
                "current": random.randint(500000, 2000000),
                "target": random.randint(700000, 2500000),
                "attainment": round(random.uniform(0.6, 1.2), 3),
                "trend": random.choice([t.value for t in TrendDirection])
            },
            "pipeline": {
                "total_value": random.randint(2000000, 8000000),
                "deals_count": random.randint(50, 200),
                "avg_deal_size": random.randint(20000, 100000),
                "velocity_days": random.randint(30, 90)
            },
            "activities": {
                "calls": random.randint(500, 2000),
                "emails": random.randint(2000, 8000),
                "meetings": random.randint(100, 500),
                "demos": random.randint(50, 200)
            },
            "win_rate": round(random.uniform(0.15, 0.35), 3),
            "avg_cycle_time_days": random.randint(30, 90)
        },
        "team_size": random.randint(5, 20),
        "calculated_at": now.isoformat()
    }


@router.get("/teams/{team_id}/members")
async def get_team_members_performance(
    team_id: str,
    period: TimePeriod = Query(default=TimePeriod.MONTHLY),
    metric: PerformanceMetric = Query(default=PerformanceMetric.REVENUE)
):
    """Get performance by team member"""
    members = []
    
    for i in range(random.randint(5, 12)):
        quota = random.randint(80000, 200000)
        attained = random.randint(int(quota * 0.5), int(quota * 1.5))
        
        members.append({
            "rep_id": f"rep_{i+1}",
            "name": f"Sales Rep {i+1}",
            "quota": quota,
            "attained": attained,
            "attainment_pct": round(attained / quota, 3),
            "deals_won": random.randint(3, 20),
            "pipeline_value": random.randint(200000, 800000),
            "win_rate": round(random.uniform(0.15, 0.40), 3),
            "activities": random.randint(100, 500),
            "rank": i + 1,
            "trend": random.choice([t.value for t in TrendDirection])
        })
    
    # Sort by metric
    if metric == PerformanceMetric.REVENUE:
        members.sort(key=lambda x: x["attained"], reverse=True)
    elif metric == PerformanceMetric.WIN_RATE:
        members.sort(key=lambda x: x["win_rate"], reverse=True)
    
    # Update ranks
    for i, m in enumerate(members):
        m["rank"] = i + 1
    
    return {
        "team_id": team_id,
        "period": period.value,
        "sort_by": metric.value,
        "members": members
    }


# Rep Performance
@router.get("/reps/{rep_id}/performance")
async def get_rep_performance(
    rep_id: str,
    period: TimePeriod = Query(default=TimePeriod.MONTHLY)
):
    """Get individual rep performance"""
    quota = random.randint(80000, 200000)
    attained = random.randint(int(quota * 0.5), int(quota * 1.3))
    
    return {
        "rep_id": rep_id,
        "period": period.value,
        "quota": {
            "target": quota,
            "attained": attained,
            "attainment_pct": round(attained / quota, 3),
            "remaining": max(0, quota - attained),
            "forecast": int(attained * 1.2)
        },
        "pipeline": {
            "total_value": random.randint(300000, 1000000),
            "deal_count": random.randint(10, 50),
            "weighted_value": random.randint(150000, 500000),
            "avg_probability": round(random.uniform(0.3, 0.6), 2)
        },
        "wins": {
            "deals_won": random.randint(3, 15),
            "revenue_won": attained,
            "avg_deal_size": int(attained / max(1, random.randint(3, 15))),
            "win_rate": round(random.uniform(0.18, 0.35), 3)
        },
        "activities": {
            "calls": random.randint(100, 400),
            "emails_sent": random.randint(500, 2000),
            "meetings": random.randint(20, 80),
            "demos": random.randint(10, 40)
        },
        "efficiency": {
            "activities_per_deal": random.randint(30, 100),
            "avg_response_time_hours": round(random.uniform(1, 8), 1),
            "email_open_rate": round(random.uniform(0.3, 0.6), 3),
            "meeting_show_rate": round(random.uniform(0.7, 0.95), 3)
        }
    }


@router.get("/reps/{rep_id}/trends")
async def get_rep_trends(
    rep_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get performance trends for a rep"""
    now = datetime.utcnow()
    
    timeline = []
    for i in range(days):
        date = (now - timedelta(days=days - i)).isoformat()[:10]
        timeline.append({
            "date": date,
            "revenue": random.randint(5000, 50000),
            "activities": random.randint(20, 100),
            "meetings": random.randint(0, 5)
        })
    
    return {
        "rep_id": rep_id,
        "period_days": days,
        "timeline": timeline,
        "summary": {
            "total_revenue": sum(t["revenue"] for t in timeline),
            "avg_daily_activities": round(sum(t["activities"] for t in timeline) / days, 1),
            "total_meetings": sum(t["meetings"] for t in timeline)
        }
    }


# Leaderboards
@router.get("/leaderboards")
async def get_leaderboards(
    metric: PerformanceMetric = Query(default=PerformanceMetric.REVENUE),
    period: TimePeriod = Query(default=TimePeriod.MONTHLY),
    limit: int = Query(default=10, le=50),
    tenant_id: str = Query(default="default")
):
    """Get performance leaderboard"""
    leaderboard = []
    
    for i in range(limit):
        value = random.randint(50000, 300000) if metric == PerformanceMetric.REVENUE else random.randint(5, 100)
        
        leaderboard.append({
            "rank": i + 1,
            "rep_id": f"rep_{random.randint(1, 20)}",
            "name": f"Sales Rep {i+1}",
            "team": f"Team {random.choice(['A', 'B', 'C', 'D'])}",
            "value": value,
            "change_from_previous": random.randint(-3, 3),
            "streak_days": random.randint(0, 30) if random.choice([True, False]) else 0
        })
    
    leaderboard.sort(key=lambda x: x["value"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return {
        "metric": metric.value,
        "period": period.value,
        "leaderboard": leaderboard,
        "updated_at": datetime.utcnow().isoformat()
    }


# Goals
@router.post("/goals")
async def create_team_goal(
    request: TeamGoalCreate,
    tenant_id: str = Query(default="default")
):
    """Create a team goal"""
    goal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    goal = {
        "id": goal_id,
        "team_id": request.team_id,
        "metric": request.metric.value,
        "target_value": request.target_value,
        "current_value": 0,
        "period": request.period.value,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "progress": 0,
        "status": "active",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    team_goals[goal_id] = goal
    
    return goal


@router.get("/teams/{team_id}/goals")
async def list_team_goals(
    team_id: str,
    status: Optional[str] = None
):
    """List goals for a team"""
    result = [g for g in team_goals.values() if g.get("team_id") == team_id]
    
    if status:
        result = [g for g in result if g.get("status") == status]
    
    # Add progress
    for goal in result:
        goal["current_value"] = random.randint(0, int(goal["target_value"] * 1.2))
        goal["progress"] = round(goal["current_value"] / goal["target_value"], 3)
    
    return {"goals": result, "total": len(result)}


# Reviews
@router.post("/reviews")
async def create_performance_review(
    request: ReviewCreate,
    tenant_id: str = Query(default="default")
):
    """Create a performance review"""
    review_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    review = {
        "id": review_id,
        "rep_id": request.rep_id,
        "reviewer_id": request.reviewer_id,
        "period": request.period,
        "ratings": request.ratings,
        "overall_rating": round(sum(request.ratings.values()) / len(request.ratings), 1) if request.ratings else 0,
        "comments": request.comments,
        "status": "draft",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    performance_reviews[review_id] = review
    
    return review


@router.get("/reps/{rep_id}/reviews")
async def list_rep_reviews(rep_id: str):
    """List reviews for a rep"""
    result = [r for r in performance_reviews.values() if r.get("rep_id") == rep_id]
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"reviews": result, "total": len(result)}


# Comparisons
@router.get("/compare")
async def compare_performance(
    rep_ids: List[str] = Query(...),
    metric: PerformanceMetric = Query(default=PerformanceMetric.REVENUE),
    period: TimePeriod = Query(default=TimePeriod.MONTHLY)
):
    """Compare performance across reps"""
    comparison = []
    
    for rep_id in rep_ids:
        value = random.randint(50000, 300000) if metric == PerformanceMetric.REVENUE else random.randint(10, 100)
        
        comparison.append({
            "rep_id": rep_id,
            "value": value,
            "trend": random.choice([t.value for t in TrendDirection]),
            "vs_team_avg": round(random.uniform(-0.3, 0.5), 3)
        })
    
    comparison.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "metric": metric.value,
        "period": period.value,
        "comparison": comparison,
        "team_avg": round(sum(c["value"] for c in comparison) / len(comparison)) if comparison else 0
    }


# Coaching Insights
@router.get("/reps/{rep_id}/coaching-insights")
async def get_coaching_insights(rep_id: str):
    """Get AI-powered coaching insights for a rep"""
    return {
        "rep_id": rep_id,
        "strengths": [
            "Strong email engagement rates",
            "High meeting conversion",
            "Excellent demo skills"
        ],
        "areas_for_improvement": [
            "Discovery call quality",
            "Multi-threading in accounts",
            "Follow-up cadence"
        ],
        "recommendations": [
            {
                "priority": 1,
                "area": "Discovery",
                "recommendation": "Use MEDDIC framework more consistently",
                "impact": "Could improve win rate by 15%"
            },
            {
                "priority": 2,
                "area": "Multi-threading",
                "recommendation": "Engage 2-3 stakeholders per opportunity",
                "impact": "Could reduce deal slippage by 20%"
            }
        ],
        "skill_scores": {
            "prospecting": random.randint(60, 95),
            "discovery": random.randint(50, 90),
            "demo": random.randint(65, 98),
            "negotiation": random.randint(55, 85),
            "closing": random.randint(60, 90)
        }
    }


# Analytics
@router.get("/analytics/summary")
async def get_performance_summary(
    period: TimePeriod = Query(default=TimePeriod.MONTHLY),
    tenant_id: str = Query(default="default")
):
    """Get org-wide performance summary"""
    total_quota = random.randint(5000000, 15000000)
    total_attained = random.randint(int(total_quota * 0.5), int(total_quota * 1.2))
    
    return {
        "period": period.value,
        "org_performance": {
            "quota": total_quota,
            "attained": total_attained,
            "attainment_pct": round(total_attained / total_quota, 3),
            "deals_won": random.randint(50, 200),
            "pipeline_created": random.randint(10000000, 30000000)
        },
        "team_breakdown": [
            {"team": "Enterprise", "attainment": round(random.uniform(0.6, 1.3), 2)},
            {"team": "Mid-Market", "attainment": round(random.uniform(0.7, 1.2), 2)},
            {"team": "SMB", "attainment": round(random.uniform(0.5, 1.1), 2)},
            {"team": "Expansion", "attainment": round(random.uniform(0.8, 1.4), 2)}
        ],
        "top_performers": [
            {"name": "Rep A", "attainment": round(random.uniform(1.1, 1.5), 2)},
            {"name": "Rep B", "attainment": round(random.uniform(1.0, 1.4), 2)},
            {"name": "Rep C", "attainment": round(random.uniform(0.95, 1.3), 2)}
        ],
        "reps_at_risk": random.randint(2, 10),
        "reps_on_pace": random.randint(15, 40),
        "reps_exceeding": random.randint(5, 15)
    }


@router.get("/analytics/activity-metrics")
async def get_activity_metrics(
    period: TimePeriod = Query(default=TimePeriod.WEEKLY),
    tenant_id: str = Query(default="default")
):
    """Get activity metrics across the org"""
    return {
        "period": period.value,
        "activities": {
            "total_calls": random.randint(1000, 5000),
            "total_emails": random.randint(5000, 20000),
            "total_meetings": random.randint(200, 1000),
            "total_demos": random.randint(100, 500)
        },
        "averages_per_rep": {
            "calls": random.randint(50, 150),
            "emails": random.randint(200, 600),
            "meetings": random.randint(10, 40),
            "demos": random.randint(5, 20)
        },
        "conversion_rates": {
            "call_to_meeting": round(random.uniform(0.1, 0.3), 3),
            "meeting_to_opportunity": round(random.uniform(0.3, 0.6), 3),
            "demo_to_deal": round(random.uniform(0.15, 0.40), 3)
        },
        "benchmarks": {
            "top_10_pct_calls": random.randint(150, 250),
            "top_10_pct_meetings": random.randint(30, 60)
        }
    }
