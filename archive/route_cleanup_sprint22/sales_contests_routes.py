"""
Sales Contests Routes - Gamification and competition management
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

router = APIRouter(prefix="/contests", tags=["Sales Contests"])


class ContestType(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    HYBRID = "hybrid"


class ContestStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    DEALS_WON = "deals_won"
    REVENUE = "revenue"
    MEETINGS_BOOKED = "meetings_booked"
    CALLS_MADE = "calls_made"
    EMAILS_SENT = "emails_sent"
    DEMOS_COMPLETED = "demos_completed"
    PIPELINE_CREATED = "pipeline_created"
    ACTIVITIES = "activities"
    CUSTOM = "custom"


class RewardType(str, Enum):
    CASH = "cash"
    GIFT_CARD = "gift_card"
    PTO = "pto"
    EXPERIENCE = "experience"
    RECOGNITION = "recognition"
    PRIZE = "prize"
    POINTS = "points"


# In-memory storage
contests = {}
contest_participants = {}
leaderboards = {}
achievements = {}


class ContestCreate(BaseModel):
    name: str
    description: Optional[str] = None
    contest_type: ContestType = ContestType.INDIVIDUAL
    metric_type: MetricType
    metric_target: Optional[float] = None
    start_date: str
    end_date: str
    rules: Optional[Dict[str, Any]] = None
    rewards: List[Dict[str, Any]] = []
    eligible_participants: Optional[List[str]] = None  # None = all


class ParticipantJoin(BaseModel):
    user_id: str
    team_id: Optional[str] = None


class ActivitySubmission(BaseModel):
    participant_id: str
    activity_type: str
    value: float
    description: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


# Contest CRUD
@router.post("/")
async def create_contest(
    request: ContestCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new sales contest"""
    contest_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    contest = {
        "id": contest_id,
        "name": request.name,
        "description": request.description,
        "contest_type": request.contest_type.value,
        "metric_type": request.metric_type.value,
        "metric_target": request.metric_target,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "rules": request.rules or {},
        "rewards": request.rewards,
        "eligible_participants": request.eligible_participants,
        "status": ContestStatus.DRAFT.value,
        "participant_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    contests[contest_id] = contest
    leaderboards[contest_id] = []
    
    logger.info("contest_created", contest_id=contest_id, name=request.name)
    
    return contest


@router.get("/")
async def list_contests(
    status: Optional[ContestStatus] = None,
    contest_type: Optional[ContestType] = None,
    active_only: bool = False,
    tenant_id: str = Query(default="default")
):
    """List all contests"""
    result = [c for c in contests.values() if c.get("tenant_id") == tenant_id]
    
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if contest_type:
        result = [c for c in result if c.get("contest_type") == contest_type.value]
    if active_only:
        result = [c for c in result if c.get("status") == ContestStatus.ACTIVE.value]
    
    return {"contests": result, "total": len(result)}


@router.get("/{contest_id}")
async def get_contest(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Get contest details"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    return contests[contest_id]


@router.patch("/{contest_id}")
async def update_contest(
    contest_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update contest"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests[contest_id]
    
    # Only allow certain updates
    allowed_fields = ["name", "description", "rewards", "rules"]
    for key, value in updates.items():
        if key in allowed_fields:
            contest[key] = value
    
    contest["updated_at"] = datetime.utcnow().isoformat()
    
    return contest


@router.post("/{contest_id}/activate")
async def activate_contest(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate a contest"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests[contest_id]
    contest["status"] = ContestStatus.ACTIVE.value
    contest["activated_at"] = datetime.utcnow().isoformat()
    
    return {"message": "Contest activated", "contest": contest}


@router.post("/{contest_id}/pause")
async def pause_contest(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Pause a contest"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests[contest_id]
    contest["status"] = ContestStatus.PAUSED.value
    
    return {"message": "Contest paused", "contest": contest}


@router.post("/{contest_id}/complete")
async def complete_contest(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Complete a contest and finalize results"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests[contest_id]
    contest["status"] = ContestStatus.COMPLETED.value
    contest["completed_at"] = datetime.utcnow().isoformat()
    
    # Calculate final standings
    leaderboard = leaderboards.get(contest_id, [])
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x.get("score", 0), reverse=True)
    
    winners = sorted_leaderboard[:3] if len(sorted_leaderboard) >= 3 else sorted_leaderboard
    
    return {
        "message": "Contest completed",
        "contest": contest,
        "winners": winners
    }


# Participants
@router.post("/{contest_id}/join")
async def join_contest(
    contest_id: str,
    request: ParticipantJoin,
    tenant_id: str = Query(default="default")
):
    """Join a contest"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    participant_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    participant = {
        "id": participant_id,
        "contest_id": contest_id,
        "user_id": request.user_id,
        "team_id": request.team_id,
        "score": 0,
        "rank": None,
        "activities": [],
        "joined_at": now.isoformat()
    }
    
    contest_participants[participant_id] = participant
    
    # Add to leaderboard
    leaderboards[contest_id].append({
        "participant_id": participant_id,
        "user_id": request.user_id,
        "team_id": request.team_id,
        "score": 0
    })
    
    contests[contest_id]["participant_count"] += 1
    
    return participant


@router.get("/{contest_id}/participants")
async def list_participants(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """List contest participants"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    participants = [p for p in contest_participants.values() if p.get("contest_id") == contest_id]
    
    return {"participants": participants, "total": len(participants)}


# Leaderboard
@router.get("/{contest_id}/leaderboard")
async def get_leaderboard(
    contest_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Query(default="default")
):
    """Get contest leaderboard"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    leaderboard = leaderboards.get(contest_id, [])
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x.get("score", 0), reverse=True)
    
    # Add ranks
    for i, entry in enumerate(sorted_leaderboard):
        entry["rank"] = i + 1
    
    return {
        "contest_id": contest_id,
        "leaderboard": sorted_leaderboard[:limit],
        "total_participants": len(sorted_leaderboard)
    }


# Activity Tracking
@router.post("/{contest_id}/activities")
async def submit_activity(
    contest_id: str,
    request: ActivitySubmission,
    tenant_id: str = Query(default="default")
):
    """Submit an activity for contest scoring"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    now = datetime.utcnow()
    activity_id = str(uuid.uuid4())
    
    activity = {
        "id": activity_id,
        "participant_id": request.participant_id,
        "activity_type": request.activity_type,
        "value": request.value,
        "description": request.description,
        "evidence": request.evidence,
        "verified": True,  # Auto-verify for now
        "submitted_at": now.isoformat()
    }
    
    # Update participant score
    if request.participant_id in contest_participants:
        participant = contest_participants[request.participant_id]
        participant["score"] += request.value
        participant["activities"].append(activity)
        
        # Update leaderboard
        for entry in leaderboards.get(contest_id, []):
            if entry["participant_id"] == request.participant_id:
                entry["score"] += request.value
                break
    
    return activity


# Achievements & Badges
@router.get("/{contest_id}/achievements")
async def get_contest_achievements(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Get achievements earned in contest"""
    return {
        "contest_id": contest_id,
        "achievements": [
            {
                "id": "first_sale",
                "name": "First Blood",
                "description": "First to close a deal",
                "earned_by": "user_1",
                "earned_at": datetime.utcnow().isoformat()
            },
            {
                "id": "streak_3",
                "name": "Hot Streak",
                "description": "3 consecutive wins",
                "earned_by": "user_2",
                "earned_at": datetime.utcnow().isoformat()
            },
            {
                "id": "comeback",
                "name": "Comeback King",
                "description": "Rose 5+ positions in a day",
                "earned_by": "user_3",
                "earned_at": datetime.utcnow().isoformat()
            }
        ]
    }


@router.get("/user/{user_id}/achievements")
async def get_user_achievements(
    user_id: str,
    tenant_id: str = Query(default="default")
):
    """Get all achievements for a user"""
    return {
        "user_id": user_id,
        "achievements": [
            {"badge": "Top Performer", "count": 5, "last_earned": "2024-01-15"},
            {"badge": "Deal Closer", "count": 12, "last_earned": "2024-01-20"},
            {"badge": "Consistency King", "count": 3, "last_earned": "2024-01-10"}
        ],
        "total_points": random.randint(500, 5000)
    }


# Analytics
@router.get("/{contest_id}/analytics")
async def get_contest_analytics(
    contest_id: str,
    tenant_id: str = Query(default="default")
):
    """Get contest analytics"""
    if contest_id not in contests:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests[contest_id]
    
    return {
        "contest_id": contest_id,
        "participation": {
            "total_eligible": random.randint(20, 100),
            "total_joined": contest.get("participant_count", 0),
            "participation_rate": round(random.uniform(0.60, 0.95), 3),
            "active_participants": random.randint(10, 50)
        },
        "performance": {
            "total_activities": random.randint(100, 1000),
            "total_points_awarded": random.randint(5000, 50000),
            "avg_score": random.randint(100, 500),
            "top_score": random.randint(1000, 5000)
        },
        "engagement": {
            "daily_active_participants": random.randint(10, 40),
            "leaderboard_views": random.randint(100, 500),
            "achievement_unlocks": random.randint(20, 100)
        },
        "impact": {
            "revenue_generated": random.randint(50000, 500000),
            "deals_closed": random.randint(10, 100),
            "activities_increase_pct": round(random.uniform(20, 80), 1)
        }
    }


# Templates
@router.get("/templates")
async def list_contest_templates(
    tenant_id: str = Query(default="default")
):
    """List available contest templates"""
    return {
        "templates": [
            {
                "id": "weekly_blitz",
                "name": "Weekly Sales Blitz",
                "description": "One-week intensive competition focused on closing deals",
                "metric_type": "deals_won",
                "duration_days": 7,
                "recommended_rewards": ["gift_card", "recognition"]
            },
            {
                "id": "monthly_marathon",
                "name": "Monthly Marathon",
                "description": "Month-long revenue-based competition",
                "metric_type": "revenue",
                "duration_days": 30,
                "recommended_rewards": ["cash", "pto"]
            },
            {
                "id": "activity_sprint",
                "name": "Activity Sprint",
                "description": "Short burst focused on call/email activities",
                "metric_type": "activities",
                "duration_days": 3,
                "recommended_rewards": ["points", "recognition"]
            },
            {
                "id": "team_challenge",
                "name": "Team Challenge",
                "description": "Team-based competition for collaboration",
                "metric_type": "pipeline_created",
                "duration_days": 14,
                "recommended_rewards": ["experience", "prize"],
                "contest_type": "team"
            }
        ]
    }


@router.post("/templates/{template_id}/create")
async def create_from_template(
    template_id: str,
    name: str,
    start_date: str,
    end_date: str,
    tenant_id: str = Query(default="default")
):
    """Create a contest from a template"""
    templates = {
        "weekly_blitz": {
            "metric_type": MetricType.DEALS_WON,
            "contest_type": ContestType.INDIVIDUAL
        },
        "monthly_marathon": {
            "metric_type": MetricType.REVENUE,
            "contest_type": ContestType.INDIVIDUAL
        },
        "activity_sprint": {
            "metric_type": MetricType.ACTIVITIES,
            "contest_type": ContestType.INDIVIDUAL
        },
        "team_challenge": {
            "metric_type": MetricType.PIPELINE_CREATED,
            "contest_type": ContestType.TEAM
        }
    }
    
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    # Create contest with template settings
    contest_request = ContestCreate(
        name=name,
        description=f"Contest created from {template_id} template",
        contest_type=template["contest_type"],
        metric_type=template["metric_type"],
        start_date=start_date,
        end_date=end_date
    )
    
    return await create_contest(contest_request, tenant_id)


# Live Feed
@router.get("/{contest_id}/feed")
async def get_contest_feed(
    contest_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    tenant_id: str = Query(default="default")
):
    """Get live activity feed for contest"""
    return {
        "contest_id": contest_id,
        "feed": [
            {
                "type": "deal_won",
                "user": "John Smith",
                "message": "Closed a $25,000 deal!",
                "points": 250,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "achievement",
                "user": "Sarah Johnson",
                "message": "Earned 'Hot Streak' badge!",
                "points": 50,
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat()
            },
            {
                "type": "rank_change",
                "user": "Mike Brown",
                "message": "Jumped to #3 on the leaderboard!",
                "points": 0,
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            }
        ][:limit]
    }
