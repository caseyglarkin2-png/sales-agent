"""
Gamification Routes - Sales Gamification API
=============================================
REST API endpoints for badges, achievements, leaderboards, and challenges.
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..gamification import (
    GamificationService,
    get_gamification_service,
)
from ..gamification.gamification_service import (
    BadgeCategory,
    BadgeTier,
    ChallengeType,
    ChallengeStatus,
)


router = APIRouter(prefix="/gamification", tags=["Gamification"])


# Request models
class AddXPRequest(BaseModel):
    """Add XP request."""
    xp: int
    reason: Optional[str] = None


class UpdateStatRequest(BaseModel):
    """Update stat request."""
    stat_name: str
    value: int
    increment: bool = True


class AwardBadgeRequest(BaseModel):
    """Award badge request."""
    badge_id: str
    context: Optional[dict[str, Any]] = None


class CreateLeaderboardRequest(BaseModel):
    """Create leaderboard request."""
    name: str
    metric: str
    period: str
    team_id: Optional[str] = None


class UpdateLeaderboardRequest(BaseModel):
    """Update leaderboard request."""
    entries: list[dict[str, Any]]


class CreateChallengeRequest(BaseModel):
    """Create challenge request."""
    name: str
    description: str
    challenge_type: str
    metric: str
    target_value: float
    start_date: datetime
    end_date: datetime
    reward_points: int = 0


class UpdateChallengeProgressRequest(BaseModel):
    """Update challenge progress request."""
    progress: float


class CreateRewardRequest(BaseModel):
    """Create reward request."""
    name: str
    description: str
    points_cost: int
    category: str
    quantity_available: Optional[int] = None


def get_service() -> GamificationService:
    """Get gamification service instance."""
    return get_gamification_service()


# Enums
@router.get("/badge-categories")
async def list_badge_categories():
    """List badge categories."""
    return {
        "categories": [
            {"value": c.value, "name": c.name}
            for c in BadgeCategory
        ]
    }


@router.get("/badge-tiers")
async def list_badge_tiers():
    """List badge tiers."""
    return {
        "tiers": [
            {"value": t.value, "name": t.name}
            for t in BadgeTier
        ]
    }


@router.get("/challenge-types")
async def list_challenge_types():
    """List challenge types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in ChallengeType
        ]
    }


# User progress
@router.get("/users/{user_id}/progress")
async def get_user_progress(user_id: str):
    """Get user gamification progress."""
    service = get_service()
    progress = await service.get_user_progress(user_id)
    
    return {
        "user_id": progress.user_id,
        "total_points": progress.total_points,
        "level": progress.level,
        "xp": progress.xp,
        "xp_to_next_level": progress.xp_to_next_level,
        "xp_progress_percent": (progress.xp / progress.xp_to_next_level) * 100 if progress.xp_to_next_level > 0 else 100,
        "badges_earned": len(progress.badges_earned),
        "current_streak": progress.current_streak,
        "longest_streak": progress.longest_streak,
        "stats": progress.stats,
        "updated_at": progress.updated_at.isoformat(),
    }


@router.post("/users/{user_id}/xp")
async def add_xp(user_id: str, request: AddXPRequest):
    """Add XP to a user."""
    service = get_service()
    progress = await service.add_xp(user_id, request.xp, request.reason)
    
    return {
        "user_id": user_id,
        "xp_added": request.xp,
        "new_total": progress.total_points,
        "level": progress.level,
    }


@router.post("/users/{user_id}/stats")
async def update_stat(user_id: str, request: UpdateStatRequest):
    """Update a user stat."""
    service = get_service()
    progress = await service.update_stat(
        user_id=user_id,
        stat_name=request.stat_name,
        value=request.value,
        increment=request.increment,
    )
    
    return {
        "user_id": user_id,
        "stat": request.stat_name,
        "value": progress.stats.get(request.stat_name, 0),
    }


@router.post("/users/{user_id}/activity")
async def record_activity(user_id: str):
    """Record daily activity and update streak."""
    service = get_service()
    progress = await service.record_activity(user_id)
    
    return {
        "user_id": user_id,
        "current_streak": progress.current_streak,
        "longest_streak": progress.longest_streak,
    }


# Badges
@router.get("/badges")
async def list_badges(
    category: Optional[str] = None,
    include_secret: bool = False,
):
    """List available badges."""
    service = get_service()
    
    cat = None
    if category:
        try:
            cat = BadgeCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
    
    badges = await service.list_badges(cat, include_secret)
    
    return {
        "badges": [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "category": b.category.value,
                "tier": b.tier.value,
                "icon": b.icon,
                "points": b.points,
            }
            for b in badges
        ]
    }


@router.get("/users/{user_id}/badges")
async def get_user_badges(user_id: str):
    """Get badges earned by a user."""
    service = get_service()
    badges = await service.get_user_badges(user_id)
    
    return {
        "user_id": user_id,
        "badges": badges,
        "count": len(badges),
    }


@router.post("/users/{user_id}/badges")
async def award_badge(user_id: str, request: AwardBadgeRequest):
    """Award a badge to a user."""
    service = get_service()
    
    achievement = await service.award_badge(
        user_id=user_id,
        badge_id=request.badge_id,
        context=request.context,
    )
    
    if not achievement:
        raise HTTPException(status_code=400, detail="Badge not found or already earned")
    
    return {
        "achievement_id": achievement.id,
        "badge_id": achievement.badge_id,
        "earned_at": achievement.earned_at.isoformat(),
    }


# Leaderboards
@router.post("/leaderboards")
async def create_leaderboard(request: CreateLeaderboardRequest):
    """Create a new leaderboard."""
    service = get_service()
    
    lb = await service.create_leaderboard(
        name=request.name,
        metric=request.metric,
        period=request.period,
        team_id=request.team_id,
    )
    
    return {
        "id": lb.id,
        "name": lb.name,
        "metric": lb.metric,
        "period": lb.period,
    }


@router.get("/leaderboards/{leaderboard_id}")
async def get_leaderboard(leaderboard_id: str):
    """Get a leaderboard."""
    service = get_service()
    lb = await service.get_leaderboard(leaderboard_id)
    
    if not lb:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    return {
        "id": lb.id,
        "name": lb.name,
        "metric": lb.metric,
        "period": lb.period,
        "team_id": lb.team_id,
        "entries": [
            {
                "user_id": e.user_id,
                "rank": e.rank,
                "score": e.score,
                "change": e.change,
            }
            for e in lb.entries
        ],
        "last_updated": lb.last_updated.isoformat(),
    }


@router.patch("/leaderboards/{leaderboard_id}")
async def update_leaderboard(leaderboard_id: str, request: UpdateLeaderboardRequest):
    """Update a leaderboard."""
    service = get_service()
    
    try:
        lb = await service.update_leaderboard(leaderboard_id, request.entries)
    except ValueError:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    return {"success": True, "entries_count": len(lb.entries)}


@router.get("/leaderboards/{leaderboard_id}/users/{user_id}")
async def get_user_rank(leaderboard_id: str, user_id: str):
    """Get user's rank on a leaderboard."""
    service = get_service()
    entry = await service.get_user_rank(user_id, leaderboard_id)
    
    if not entry:
        return {"user_id": user_id, "rank": None}
    
    return {
        "user_id": entry.user_id,
        "rank": entry.rank,
        "score": entry.score,
        "change": entry.change,
    }


# Challenges
@router.post("/challenges")
async def create_challenge(request: CreateChallengeRequest):
    """Create a new challenge."""
    service = get_service()
    
    try:
        challenge_type = ChallengeType(request.challenge_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge type")
    
    challenge = await service.create_challenge(
        name=request.name,
        description=request.description,
        challenge_type=challenge_type,
        metric=request.metric,
        target_value=request.target_value,
        start_date=request.start_date,
        end_date=request.end_date,
        reward_points=request.reward_points,
    )
    
    return {
        "id": challenge.id,
        "name": challenge.name,
        "status": challenge.status.value,
    }


@router.get("/challenges")
async def list_challenges(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """List challenges."""
    service = get_service()
    
    stat = None
    if status:
        try:
            stat = ChallengeStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    challenges = await service.list_challenges(stat, user_id)
    
    return {
        "challenges": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "challenge_type": c.challenge_type.value,
                "metric": c.metric,
                "target_value": c.target_value,
                "status": c.status.value,
                "participants_count": len(c.participants),
                "reward_points": c.reward_points,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
            }
            for c in challenges
        ]
    }


@router.get("/challenges/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get challenge details."""
    service = get_service()
    challenge = service.challenges.get(challenge_id)
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return {
        "id": challenge.id,
        "name": challenge.name,
        "description": challenge.description,
        "challenge_type": challenge.challenge_type.value,
        "metric": challenge.metric,
        "target_value": challenge.target_value,
        "status": challenge.status.value,
        "participants": challenge.participants,
        "progress": challenge.progress,
        "winner_id": challenge.winner_id,
        "reward_points": challenge.reward_points,
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat(),
    }


@router.post("/challenges/{challenge_id}/join")
async def join_challenge(challenge_id: str, user_id: str):
    """Join a challenge."""
    service = get_service()
    
    if not await service.join_challenge(challenge_id, user_id):
        raise HTTPException(status_code=400, detail="Cannot join challenge")
    
    return {"success": True}


@router.patch("/challenges/{challenge_id}/users/{user_id}")
async def update_challenge_progress(
    challenge_id: str,
    user_id: str,
    request: UpdateChallengeProgressRequest
):
    """Update user's challenge progress."""
    service = get_service()
    
    challenge = await service.update_challenge_progress(
        challenge_id=challenge_id,
        user_id=user_id,
        progress=request.progress,
    )
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge or participant not found")
    
    return {
        "challenge_id": challenge_id,
        "user_id": user_id,
        "progress": challenge.progress.get(user_id),
        "target": challenge.target_value,
    }


# Rewards
@router.post("/rewards")
async def create_reward(request: CreateRewardRequest):
    """Create a reward."""
    service = get_service()
    
    reward = await service.create_reward(
        name=request.name,
        description=request.description,
        points_cost=request.points_cost,
        category=request.category,
        quantity_available=request.quantity_available,
    )
    
    return {
        "id": reward.id,
        "name": reward.name,
        "points_cost": reward.points_cost,
    }


@router.get("/rewards")
async def list_rewards(
    category: Optional[str] = None,
    affordable_for: Optional[str] = None,
):
    """List available rewards."""
    service = get_service()
    rewards = await service.list_rewards(category, affordable_for)
    
    return {
        "rewards": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "points_cost": r.points_cost,
                "category": r.category,
                "quantity_available": r.quantity_available,
                "quantity_redeemed": r.quantity_redeemed,
            }
            for r in rewards
        ]
    }


@router.post("/rewards/{reward_id}/redeem")
async def redeem_reward(reward_id: str, user_id: str):
    """Redeem a reward."""
    service = get_service()
    
    redemption = await service.redeem_reward(user_id, reward_id)
    
    if not redemption:
        raise HTTPException(status_code=400, detail="Cannot redeem reward (not found, insufficient points, or out of stock)")
    
    return {
        "redemption_id": redemption.id,
        "reward_id": redemption.reward_id,
        "points_spent": redemption.points_spent,
        "status": redemption.status,
    }


# Stats
@router.get("/stats")
async def get_gamification_stats():
    """Get gamification statistics."""
    service = get_service()
    return await service.get_gamification_stats()
