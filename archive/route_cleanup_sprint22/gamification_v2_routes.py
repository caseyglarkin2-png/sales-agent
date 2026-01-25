"""
Sales Gamification V2 Routes - Advanced contests, leaderboards, and achievements
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

router = APIRouter(prefix="/gamification-v2", tags=["Sales Gamification V2"])


class ContestType(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    HEAD_TO_HEAD = "head_to_head"
    COLLABORATIVE = "collaborative"
    BRACKET = "bracket"


class ContestStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricTracked(str, Enum):
    CALLS_MADE = "calls_made"
    EMAILS_SENT = "emails_sent"
    MEETINGS_BOOKED = "meetings_booked"
    DEMOS_COMPLETED = "demos_completed"
    OPPORTUNITIES_CREATED = "opportunities_created"
    DEALS_WON = "deals_won"
    REVENUE_CLOSED = "revenue_closed"
    PIPELINE_ADDED = "pipeline_added"
    ACTIVITIES_LOGGED = "activities_logged"
    LEADS_QUALIFIED = "leads_qualified"


class AchievementCategory(str, Enum):
    ACTIVITY = "activity"
    REVENUE = "revenue"
    CONSISTENCY = "consistency"
    MILESTONE = "milestone"
    SKILL = "skill"
    TEAMWORK = "teamwork"


class BadgeRarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class RewardType(str, Enum):
    POINTS = "points"
    CASH = "cash"
    GIFT_CARD = "gift_card"
    EXPERIENCE = "experience"
    RECOGNITION = "recognition"
    PTO = "pto"


# In-memory storage
contests_v2 = {}
leaderboards_v2 = {}
achievements_v2 = {}
user_achievements_v2 = {}
badges_v2 = {}
user_badges_v2 = {}
user_points_v2 = {}
rewards_v2 = {}
streaks_v2 = {}
levels_v2 = {}
challenges_v2 = {}
user_challenges_v2 = {}


class ContestCreate(BaseModel):
    name: str
    description: Optional[str] = None
    contest_type: ContestType
    metric: MetricTracked
    start_date: str
    end_date: str
    target_value: Optional[float] = None
    prize_pool: Optional[float] = None
    rules: Optional[Dict[str, Any]] = None


@router.post("/contests")
async def create_contest(
    request: ContestCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a contest"""
    contest_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    contest = {
        "id": contest_id,
        "name": request.name,
        "description": request.description,
        "contest_type": request.contest_type.value,
        "metric": request.metric.value,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "target_value": request.target_value,
        "prize_pool": request.prize_pool,
        "rules": request.rules or {},
        "status": ContestStatus.DRAFT.value,
        "participants": [],
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    contests_v2[contest_id] = contest
    
    logger.info("contest_v2_created", contest_id=contest_id, name=request.name)
    return contest


@router.get("/contests")
async def list_contests(
    status: Optional[ContestStatus] = None,
    contest_type: Optional[ContestType] = None,
    tenant_id: str = Query(default="default")
):
    """List contests"""
    result = [c for c in contests_v2.values() if c.get("tenant_id") == tenant_id]
    
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if contest_type:
        result = [c for c in result if c.get("contest_type") == contest_type.value]
    
    result.sort(key=lambda x: x.get("start_date", ""), reverse=True)
    
    return {"contests": result, "total": len(result)}


@router.get("/contests/{contest_id}")
async def get_contest(contest_id: str):
    """Get contest details with standings"""
    if contest_id not in contests_v2:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests_v2[contest_id]
    
    standings = []
    for i, participant in enumerate(contest.get("participants", [])):
        standings.append({
            "rank": i + 1,
            "user_id": participant,
            "user_name": f"Rep {i + 1}",
            "score": random.randint(50, 500),
            "progress_pct": random.uniform(0.3, 1.2),
            "trend": random.choice(["up", "down", "stable"])
        })
    
    standings.sort(key=lambda x: x["score"], reverse=True)
    for i, s in enumerate(standings):
        s["rank"] = i + 1
    
    return {
        **contest,
        "standings": standings,
        "days_remaining": max(0, days_until(contest.get("end_date", ""))),
        "total_activity": sum(s["score"] for s in standings)
    }


@router.post("/contests/{contest_id}/join")
async def join_contest(contest_id: str, user_id: str = Query(default="default")):
    """Join a contest"""
    if contest_id not in contests_v2:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests_v2[contest_id]
    if user_id not in contest["participants"]:
        contest["participants"].append(user_id)
    
    return {"message": "Joined contest", "contest_id": contest_id, "user_id": user_id}


@router.post("/contests/{contest_id}/start")
async def start_contest(contest_id: str):
    """Start a contest"""
    if contest_id not in contests_v2:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests_v2[contest_id]
    contest["status"] = ContestStatus.ACTIVE.value
    contest["started_at"] = datetime.utcnow().isoformat()
    
    return contest


@router.post("/contests/{contest_id}/complete")
async def complete_contest(contest_id: str):
    """Complete a contest"""
    if contest_id not in contests_v2:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    contest = contests_v2[contest_id]
    contest["status"] = ContestStatus.COMPLETED.value
    contest["completed_at"] = datetime.utcnow().isoformat()
    
    winners = []
    for i, participant in enumerate(contest.get("participants", [])[:3]):
        winners.append({
            "rank": i + 1,
            "user_id": participant,
            "score": random.randint(100, 500),
            "prize": contest.get("prize_pool", 0) / (i + 1) if contest.get("prize_pool") else None
        })
    
    contest["winners"] = winners
    return contest


# Leaderboards
@router.get("/leaderboards/{metric}")
async def get_leaderboard(
    metric: MetricTracked,
    period: str = Query(default="month"),
    team_id: Optional[str] = None,
    limit: int = Query(default=10, le=50),
    tenant_id: str = Query(default="default")
):
    """Get leaderboard for a metric"""
    entries = []
    for i in range(limit):
        entries.append({
            "rank": i + 1,
            "user_id": str(uuid.uuid4()),
            "user_name": f"Sales Rep {i + 1}",
            "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={i}",
            "score": random.randint(50, 500) - i * 10,
            "delta_from_prev": random.randint(-5, 10),
            "trend": random.choice(["up", "down", "stable"]),
            "streak_days": random.randint(0, 30)
        })
    
    entries.sort(key=lambda x: x["score"], reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1
    
    return {
        "metric": metric.value,
        "period": period,
        "entries": entries,
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/leaderboards/composite")
async def get_composite_leaderboard(
    metrics: List[MetricTracked] = Query(default=[MetricTracked.DEALS_WON, MetricTracked.REVENUE_CLOSED]),
    weights: Optional[List[float]] = None,
    period: str = Query(default="month"),
    limit: int = Query(default=10, le=50),
    tenant_id: str = Query(default="default")
):
    """Get composite leaderboard combining multiple metrics"""
    if weights is None:
        weights = [1.0] * len(metrics)
    
    entries = []
    for i in range(limit):
        scores = {}
        total = 0
        for j, metric in enumerate(metrics):
            score = random.randint(50, 500)
            scores[metric.value] = score
            total += score * weights[j]
        
        entries.append({
            "rank": i + 1,
            "user_id": str(uuid.uuid4()),
            "user_name": f"Sales Rep {i + 1}",
            "composite_score": round(total, 2),
            "metric_scores": scores,
            "trend": random.choice(["up", "down", "stable"])
        })
    
    entries.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1
    
    return {
        "metrics": [m.value for m in metrics],
        "weights": weights,
        "period": period,
        "entries": entries
    }


# Achievements
@router.post("/achievements")
async def create_achievement(
    name: str,
    description: str,
    category: AchievementCategory,
    criteria: Dict[str, Any],
    points: int = 100,
    icon: Optional[str] = None,
    secret: bool = False,
    tenant_id: str = Query(default="default")
):
    """Create an achievement definition"""
    achievement_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    achievement = {
        "id": achievement_id,
        "name": name,
        "description": description,
        "category": category.value,
        "criteria": criteria,
        "points": points,
        "icon": icon or "🏆",
        "secret": secret,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    achievements_v2[achievement_id] = achievement
    return achievement


@router.get("/achievements")
async def list_achievements(
    category: Optional[AchievementCategory] = None,
    include_secret: bool = False,
    tenant_id: str = Query(default="default")
):
    """List achievements"""
    result = [a for a in achievements_v2.values() if a.get("tenant_id") == tenant_id]
    
    if category:
        result = [a for a in result if a.get("category") == category.value]
    if not include_secret:
        result = [a for a in result if not a.get("secret")]
    
    if not result:
        result = get_default_achievements_v2()
    
    return {"achievements": result, "total": len(result)}


@router.post("/achievements/{achievement_id}/award")
async def award_achievement(achievement_id: str, user_id: str):
    """Award an achievement to a user"""
    now = datetime.utcnow()
    
    award_id = str(uuid.uuid4())
    award = {
        "id": award_id,
        "achievement_id": achievement_id,
        "user_id": user_id,
        "awarded_at": now.isoformat()
    }
    
    if user_id not in user_achievements_v2:
        user_achievements_v2[user_id] = []
    user_achievements_v2[user_id].append(award)
    
    achievement = achievements_v2.get(achievement_id, {})
    points = achievement.get("points", 100)
    
    if user_id not in user_points_v2:
        user_points_v2[user_id] = 0
    user_points_v2[user_id] += points
    
    logger.info("achievement_v2_awarded", achievement_id=achievement_id, user_id=user_id)
    return award


@router.get("/users/{user_id}/achievements")
async def get_user_achievements(user_id: str):
    """Get user's achievements"""
    awarded = user_achievements_v2.get(user_id, [])
    
    return {
        "user_id": user_id,
        "achievements": awarded,
        "total_earned": len(awarded),
        "total_points": user_points_v2.get(user_id, 0)
    }


# Badges
@router.post("/badges")
async def create_badge(
    name: str,
    description: str,
    rarity: BadgeRarity,
    icon: str,
    criteria: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Create a badge definition"""
    badge_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    badge = {
        "id": badge_id,
        "name": name,
        "description": description,
        "rarity": rarity.value,
        "icon": icon,
        "criteria": criteria,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    badges_v2[badge_id] = badge
    return badge


@router.get("/badges")
async def list_badges(
    rarity: Optional[BadgeRarity] = None,
    tenant_id: str = Query(default="default")
):
    """List badges"""
    result = [b for b in badges_v2.values() if b.get("tenant_id") == tenant_id]
    
    if rarity:
        result = [b for b in result if b.get("rarity") == rarity.value]
    
    if not result:
        result = get_default_badges_v2()
    
    return {"badges": result, "total": len(result)}


@router.post("/badges/{badge_id}/award")
async def award_badge(badge_id: str, user_id: str):
    """Award a badge to a user"""
    now = datetime.utcnow()
    
    if user_id not in user_badges_v2:
        user_badges_v2[user_id] = []
    
    user_badges_v2[user_id].append({
        "badge_id": badge_id,
        "awarded_at": now.isoformat()
    })
    
    return {"message": "Badge awarded", "badge_id": badge_id, "user_id": user_id}


@router.get("/users/{user_id}/badges")
async def get_user_badges(user_id: str):
    """Get user's badges"""
    awarded = user_badges_v2.get(user_id, [])
    return {"user_id": user_id, "badges": awarded, "total": len(awarded)}


# Streaks
@router.post("/streaks/record")
async def record_activity_for_streak(
    user_id: str,
    activity_type: str,
    tenant_id: str = Query(default="default")
):
    """Record activity for streak tracking"""
    now = datetime.utcnow()
    today = now.isoformat()[:10]
    
    key = f"{user_id}_{activity_type}"
    
    if key not in streaks_v2:
        streaks_v2[key] = {
            "user_id": user_id,
            "activity_type": activity_type,
            "current_streak": 0,
            "longest_streak": 0,
            "last_activity_date": None,
            "total_days": 0
        }
    
    streak = streaks_v2[key]
    last_date = streak.get("last_activity_date")
    
    if last_date == today:
        pass
    elif last_date == (now - timedelta(days=1)).isoformat()[:10]:
        streak["current_streak"] += 1
    else:
        streak["current_streak"] = 1
    
    streak["last_activity_date"] = today
    streak["total_days"] += 1
    
    if streak["current_streak"] > streak["longest_streak"]:
        streak["longest_streak"] = streak["current_streak"]
    
    return streak


@router.get("/streaks/{user_id}")
async def get_user_streaks(user_id: str):
    """Get user's streaks"""
    user_streaks = [s for s in streaks_v2.values() if s.get("user_id") == user_id]
    
    return {
        "user_id": user_id,
        "streaks": user_streaks,
        "active_streaks": len([s for s in user_streaks if s.get("current_streak", 0) > 0])
    }


# Points & Levels
@router.get("/users/{user_id}/points")
async def get_user_points(user_id: str):
    """Get user's points and level"""
    points = user_points_v2.get(user_id, 0)
    level_info = calculate_level_v2(points)
    
    return {
        "user_id": user_id,
        "total_points": points,
        "level": level_info["level"],
        "level_name": level_info["name"],
        "points_to_next_level": level_info["points_to_next"],
        "progress_pct": level_info["progress_pct"]
    }


@router.post("/users/{user_id}/points/add")
async def add_points(user_id: str, points: int, reason: str):
    """Add points to a user"""
    now = datetime.utcnow()
    
    if user_id not in user_points_v2:
        user_points_v2[user_id] = 0
    
    user_points_v2[user_id] += points
    
    return {
        "user_id": user_id,
        "points_added": points,
        "reason": reason,
        "new_total": user_points_v2[user_id],
        "timestamp": now.isoformat()
    }


# Challenges
@router.post("/challenges")
async def create_challenge(
    title: str,
    description: str,
    metric: MetricTracked,
    target_value: float,
    duration_days: int,
    points_reward: int,
    difficulty: str = "medium",
    tenant_id: str = Query(default="default")
):
    """Create a challenge"""
    challenge_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    challenge = {
        "id": challenge_id,
        "title": title,
        "description": description,
        "metric": metric.value,
        "target_value": target_value,
        "duration_days": duration_days,
        "points_reward": points_reward,
        "difficulty": difficulty,
        "status": "active",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    challenges_v2[challenge_id] = challenge
    return challenge


@router.get("/challenges")
async def list_challenges(
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List challenges"""
    result = [c for c in challenges_v2.values() if c.get("tenant_id") == tenant_id]
    
    if difficulty:
        result = [c for c in result if c.get("difficulty") == difficulty]
    if status:
        result = [c for c in result if c.get("status") == status]
    
    return {"challenges": result, "total": len(result)}


@router.post("/challenges/{challenge_id}/accept")
async def accept_challenge(challenge_id: str, user_id: str = Query(default="default")):
    """Accept a challenge"""
    if challenge_id not in challenges_v2:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    now = datetime.utcnow()
    challenge = challenges_v2[challenge_id]
    
    user_challenge_id = str(uuid.uuid4())
    user_challenge = {
        "id": user_challenge_id,
        "challenge_id": challenge_id,
        "user_id": user_id,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=challenge.get("duration_days", 7))).isoformat(),
        "current_value": 0,
        "target_value": challenge.get("target_value"),
        "status": "in_progress",
        "created_at": now.isoformat()
    }
    
    user_challenges_v2[user_challenge_id] = user_challenge
    return user_challenge


@router.get("/users/{user_id}/challenges")
async def get_user_challenges(user_id: str, status: Optional[str] = None):
    """Get user's challenges"""
    result = [c for c in user_challenges_v2.values() if c.get("user_id") == user_id]
    
    if status:
        result = [c for c in result if c.get("status") == status]
    
    return {"challenges": result, "total": len(result)}


# Rewards
@router.post("/rewards")
async def create_reward(
    name: str,
    description: str,
    reward_type: RewardType,
    cost_points: int,
    value: Optional[float] = None,
    quantity_available: Optional[int] = None,
    tenant_id: str = Query(default="default")
):
    """Create a reward"""
    reward_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    reward = {
        "id": reward_id,
        "name": name,
        "description": description,
        "reward_type": reward_type.value,
        "cost_points": cost_points,
        "value": value,
        "quantity_available": quantity_available,
        "quantity_claimed": 0,
        "status": "available",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    rewards_v2[reward_id] = reward
    return reward


@router.get("/rewards")
async def list_rewards(
    reward_type: Optional[RewardType] = None,
    tenant_id: str = Query(default="default")
):
    """List available rewards"""
    result = [r for r in rewards_v2.values() if r.get("tenant_id") == tenant_id and r.get("status") == "available"]
    
    if reward_type:
        result = [r for r in result if r.get("reward_type") == reward_type.value]
    
    return {"rewards": result, "total": len(result)}


@router.post("/rewards/{reward_id}/redeem")
async def redeem_reward(reward_id: str, user_id: str = Query(default="default")):
    """Redeem a reward"""
    if reward_id not in rewards_v2:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    reward = rewards_v2[reward_id]
    points = user_points_v2.get(user_id, 0)
    
    if points < reward["cost_points"]:
        raise HTTPException(status_code=400, detail="Insufficient points")
    
    if reward.get("quantity_available") is not None:
        if reward["quantity_claimed"] >= reward["quantity_available"]:
            raise HTTPException(status_code=400, detail="Reward sold out")
        reward["quantity_claimed"] += 1
    
    user_points_v2[user_id] = points - reward["cost_points"]
    
    now = datetime.utcnow()
    redemption = {
        "reward_id": reward_id,
        "user_id": user_id,
        "points_spent": reward["cost_points"],
        "redeemed_at": now.isoformat()
    }
    
    logger.info("reward_v2_redeemed", reward_id=reward_id, user_id=user_id)
    return redemption


# Activity Feed
@router.get("/feed")
async def get_activity_feed(
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get gamification activity feed"""
    activities = []
    
    activity_types = [
        ("🏆 Achievement unlocked", "achievement"),
        ("🔥 Streak extended", "streak"),
        ("🏅 Badge earned", "badge"),
        ("🎯 Challenge completed", "challenge"),
        ("📈 Leaderboard rank changed", "leaderboard"),
        ("🎁 Reward redeemed", "reward")
    ]
    
    for i in range(limit):
        activity_type = random.choice(activity_types)
        activities.append({
            "id": str(uuid.uuid4()),
            "type": activity_type[1],
            "message": activity_type[0],
            "user_id": str(uuid.uuid4()),
            "user_name": f"Rep {random.randint(1, 20)}",
            "details": {},
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat()
        })
    
    return {"activities": activities, "total": len(activities)}


# Analytics
@router.get("/analytics/engagement")
async def get_engagement_analytics(
    period: str = Query(default="month"),
    tenant_id: str = Query(default="default")
):
    """Get gamification engagement analytics"""
    return {
        "period": period,
        "active_participants": random.randint(50, 200),
        "total_participants": random.randint(100, 300),
        "engagement_rate": round(random.uniform(0.5, 0.9), 2),
        "points_distributed": random.randint(50000, 200000),
        "achievements_unlocked": random.randint(100, 500),
        "badges_awarded": random.randint(50, 200),
        "challenges_completed": random.randint(30, 100),
        "rewards_redeemed": random.randint(10, 50),
        "avg_streak_days": round(random.uniform(5, 15), 1),
        "top_activity_type": random.choice(["calls_made", "meetings_booked", "deals_won"]),
        "contest_participation_rate": round(random.uniform(0.6, 0.95), 2)
    }


@router.get("/analytics/impact")
async def get_gamification_impact(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get impact of gamification on sales performance"""
    return {
        "period": period,
        "activity_increase_pct": round(random.uniform(0.15, 0.45), 2),
        "pipeline_increase_pct": round(random.uniform(0.1, 0.3), 2),
        "revenue_increase_pct": round(random.uniform(0.08, 0.25), 2),
        "rep_retention_improvement": round(random.uniform(0.05, 0.2), 2),
        "avg_ramp_time_reduction_days": random.randint(5, 20),
        "top_performers_engaged": round(random.uniform(0.85, 0.98), 2),
        "bottom_performers_improved": round(random.uniform(0.3, 0.6), 2)
    }


# Helper functions
def days_until(date_str: str) -> int:
    """Calculate days until a date"""
    if not date_str:
        return 0
    try:
        target = datetime.fromisoformat(date_str[:10])
        now = datetime.utcnow()
        return (target - now).days
    except:
        return 0


def calculate_level_v2(points: int) -> Dict:
    """Calculate level from points"""
    level_thresholds = [
        (0, 1, "Rookie"),
        (500, 2, "Prospect"),
        (1500, 3, "Closer"),
        (3000, 4, "Crusher"),
        (5000, 5, "Champion"),
        (8000, 6, "Elite"),
        (12000, 7, "Legend"),
        (20000, 8, "Hall of Fame")
    ]
    
    current_level = 1
    current_name = "Rookie"
    current_threshold = 0
    next_threshold = 500
    
    for threshold, level, name in level_thresholds:
        if points >= threshold:
            current_level = level
            current_name = name
            current_threshold = threshold
            idx = level_thresholds.index((threshold, level, name))
            if idx < len(level_thresholds) - 1:
                next_threshold = level_thresholds[idx + 1][0]
            else:
                next_threshold = threshold
    
    points_to_next = max(0, next_threshold - points)
    progress = (points - current_threshold) / max(1, next_threshold - current_threshold)
    
    return {
        "level": current_level,
        "name": current_name,
        "points_to_next": points_to_next,
        "progress_pct": round(min(1.0, progress), 2)
    }


def get_default_achievements_v2() -> List[Dict]:
    """Get default achievement definitions"""
    return [
        {"id": "first_call", "name": "First Call", "description": "Make your first call", "category": "activity", "points": 50, "icon": "📞"},
        {"id": "first_deal", "name": "Deal Maker", "description": "Close your first deal", "category": "revenue", "points": 500, "icon": "🎉"},
        {"id": "10_calls", "name": "Dialer", "description": "Make 10 calls in a day", "category": "activity", "points": 100, "icon": "📱"},
        {"id": "5_day_streak", "name": "Consistent", "description": "Log activities 5 days in a row", "category": "consistency", "points": 200, "icon": "🔥"},
        {"id": "100k_revenue", "name": "Six Figure Closer", "description": "Close $100K in revenue", "category": "milestone", "points": 1000, "icon": "💰"}
    ]


def get_default_badges_v2() -> List[Dict]:
    """Get default badge definitions"""
    return [
        {"id": "email_warrior", "name": "Email Warrior", "description": "Send 100 emails", "rarity": "common", "icon": "✉️"},
        {"id": "meeting_master", "name": "Meeting Master", "description": "Book 50 meetings", "rarity": "uncommon", "icon": "📅"},
        {"id": "quota_crusher", "name": "Quota Crusher", "description": "Hit 150% of quota", "rarity": "rare", "icon": "🎯"},
        {"id": "deal_champion", "name": "Deal Champion", "description": "Close 10 deals in a month", "rarity": "epic", "icon": "🏆"},
        {"id": "sales_legend", "name": "Sales Legend", "description": "Top performer for 6 months", "rarity": "legendary", "icon": "👑"}
    ]
