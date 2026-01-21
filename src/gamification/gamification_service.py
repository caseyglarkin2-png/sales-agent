"""
Gamification Service - Sales Team Motivation
=============================================
Handles badges, achievements, challenges, and leaderboards for sales gamification.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class BadgeCategory(str, Enum):
    """Badge categories."""
    DEALS = "deals"
    CALLS = "calls"
    EMAILS = "emails"
    MEETINGS = "meetings"
    REVENUE = "revenue"
    QUOTA = "quota"
    ACTIVITY = "activity"
    STREAK = "streak"
    MILESTONE = "milestone"
    SPECIAL = "special"


class BadgeTier(str, Enum):
    """Badge tier levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class ChallengeStatus(str, Enum):
    """Challenge status."""
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChallengeType(str, Enum):
    """Challenge types."""
    INDIVIDUAL = "individual"
    TEAM = "team"
    COMPANY_WIDE = "company_wide"
    HEAD_TO_HEAD = "head_to_head"


@dataclass
class Badge:
    """Badge definition."""
    id: str
    name: str
    description: str
    category: BadgeCategory
    tier: BadgeTier
    icon: str
    points: int
    criteria: dict[str, Any]  # e.g., {"deals_closed": 10}
    is_active: bool = True
    is_secret: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Achievement:
    """User achievement (earned badge)."""
    id: str
    user_id: str
    badge_id: str
    earned_at: datetime = field(default_factory=datetime.utcnow)
    context: dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class UserProgress:
    """User gamification progress."""
    user_id: str
    total_points: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    badges_earned: list[str] = field(default_factory=list)
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[datetime] = None
    stats: dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LeaderboardEntry:
    """Leaderboard entry."""
    user_id: str
    rank: int
    score: float
    change: int = 0  # Position change from previous period
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Leaderboard:
    """Leaderboard definition."""
    id: str
    name: str
    metric: str  # revenue, deals, calls, etc.
    period: str  # daily, weekly, monthly, quarterly, all_time
    team_id: Optional[str] = None
    entries: list[LeaderboardEntry] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Challenge:
    """Sales challenge."""
    id: str
    name: str
    description: str
    challenge_type: ChallengeType
    metric: str
    target_value: float
    start_date: datetime
    end_date: datetime
    status: ChallengeStatus = ChallengeStatus.UPCOMING
    reward_points: int = 0
    reward_badge_id: Optional[str] = None
    participants: list[str] = field(default_factory=list)
    progress: dict[str, float] = field(default_factory=dict)  # user_id -> progress
    winner_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Reward:
    """Redeemable reward."""
    id: str
    name: str
    description: str
    points_cost: int
    category: str
    quantity_available: Optional[int] = None
    quantity_redeemed: int = 0
    is_active: bool = True
    image_url: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardRedemption:
    """Reward redemption record."""
    id: str
    user_id: str
    reward_id: str
    points_spent: int
    redeemed_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, fulfilled, cancelled


class GamificationService:
    """Service for gamification features."""
    
    def __init__(self):
        """Initialize gamification service."""
        self.badges: dict[str, Badge] = {}
        self.achievements: dict[str, Achievement] = {}
        self.user_progress: dict[str, UserProgress] = {}
        self.leaderboards: dict[str, Leaderboard] = {}
        self.challenges: dict[str, Challenge] = {}
        self.rewards: dict[str, Reward] = {}
        self.redemptions: dict[str, RewardRedemption] = {}
        
        # XP level thresholds
        self._level_thresholds = [100, 250, 500, 1000, 2000, 3500, 5500, 8000, 11000, 15000]
        
        # Initialize default badges
        self._init_default_badges()
    
    def _init_default_badges(self):
        """Initialize default badges."""
        default_badges = [
            # Deals badges
            ("First Deal", "Close your first deal", BadgeCategory.DEALS, BadgeTier.BRONZE, "🎯", 50, {"deals_closed": 1}),
            ("Deal Maker", "Close 10 deals", BadgeCategory.DEALS, BadgeTier.SILVER, "💰", 100, {"deals_closed": 10}),
            ("Deal Master", "Close 50 deals", BadgeCategory.DEALS, BadgeTier.GOLD, "🏆", 250, {"deals_closed": 50}),
            ("Deal Legend", "Close 100 deals", BadgeCategory.DEALS, BadgeTier.PLATINUM, "👑", 500, {"deals_closed": 100}),
            
            # Calls badges
            ("Dialer", "Make 50 calls", BadgeCategory.CALLS, BadgeTier.BRONZE, "📞", 50, {"calls_made": 50}),
            ("Phone Pro", "Make 200 calls", BadgeCategory.CALLS, BadgeTier.SILVER, "📱", 100, {"calls_made": 200}),
            ("Call Center", "Make 500 calls", BadgeCategory.CALLS, BadgeTier.GOLD, "☎️", 250, {"calls_made": 500}),
            
            # Email badges
            ("Email Starter", "Send 100 emails", BadgeCategory.EMAILS, BadgeTier.BRONZE, "📧", 50, {"emails_sent": 100}),
            ("Email Expert", "Send 500 emails", BadgeCategory.EMAILS, BadgeTier.SILVER, "✉️", 100, {"emails_sent": 500}),
            
            # Meeting badges
            ("Meeting Scheduler", "Book 10 meetings", BadgeCategory.MEETINGS, BadgeTier.BRONZE, "📅", 50, {"meetings_booked": 10}),
            ("Meeting Master", "Book 50 meetings", BadgeCategory.MEETINGS, BadgeTier.SILVER, "🗓️", 150, {"meetings_booked": 50}),
            
            # Revenue badges
            ("$10K Club", "Close $10K in revenue", BadgeCategory.REVENUE, BadgeTier.BRONZE, "💵", 100, {"revenue": 10000}),
            ("$50K Club", "Close $50K in revenue", BadgeCategory.REVENUE, BadgeTier.SILVER, "💴", 250, {"revenue": 50000}),
            ("$100K Club", "Close $100K in revenue", BadgeCategory.REVENUE, BadgeTier.GOLD, "💎", 500, {"revenue": 100000}),
            
            # Quota badges
            ("Quota Crusher", "Hit 100% of quota", BadgeCategory.QUOTA, BadgeTier.GOLD, "🎯", 300, {"quota_percent": 100}),
            ("Overachiever", "Hit 150% of quota", BadgeCategory.QUOTA, BadgeTier.PLATINUM, "🚀", 500, {"quota_percent": 150}),
            
            # Streak badges
            ("On Fire", "7-day activity streak", BadgeCategory.STREAK, BadgeTier.BRONZE, "🔥", 75, {"streak_days": 7}),
            ("Unstoppable", "30-day activity streak", BadgeCategory.STREAK, BadgeTier.SILVER, "⚡", 200, {"streak_days": 30}),
            ("Legend", "90-day activity streak", BadgeCategory.STREAK, BadgeTier.GOLD, "🌟", 500, {"streak_days": 90}),
            
            # Special badges
            ("Early Bird", "First activity before 8 AM", BadgeCategory.SPECIAL, BadgeTier.BRONZE, "🌅", 25, {"early_bird": True}),
            ("Weekend Warrior", "Activity on a weekend", BadgeCategory.SPECIAL, BadgeTier.BRONZE, "💪", 25, {"weekend_activity": True}),
        ]
        
        for name, desc, cat, tier, icon, points, criteria in default_badges:
            badge_id = str(uuid.uuid4())
            self.badges[badge_id] = Badge(
                id=badge_id,
                name=name,
                description=desc,
                category=cat,
                tier=tier,
                icon=icon,
                points=points,
                criteria=criteria,
            )
    
    async def get_user_progress(
        self,
        user_id: str,
        create_if_missing: bool = True
    ) -> Optional[UserProgress]:
        """Get user gamification progress."""
        progress = self.user_progress.get(user_id)
        
        if not progress and create_if_missing:
            progress = UserProgress(user_id=user_id)
            self.user_progress[user_id] = progress
        
        return progress
    
    async def add_xp(
        self,
        user_id: str,
        xp: int,
        reason: Optional[str] = None
    ) -> UserProgress:
        """Add XP to a user."""
        progress = await self.get_user_progress(user_id)
        
        progress.xp += xp
        progress.total_points += xp
        
        # Check for level up
        while progress.xp >= progress.xp_to_next_level and progress.level < len(self._level_thresholds) + 1:
            progress.xp -= progress.xp_to_next_level
            progress.level += 1
            if progress.level <= len(self._level_thresholds):
                progress.xp_to_next_level = self._level_thresholds[progress.level - 1]
        
        progress.updated_at = datetime.utcnow()
        return progress
    
    async def update_stat(
        self,
        user_id: str,
        stat_name: str,
        value: int,
        increment: bool = True
    ) -> UserProgress:
        """Update a user stat and check for badges."""
        progress = await self.get_user_progress(user_id)
        
        if increment:
            progress.stats[stat_name] = progress.stats.get(stat_name, 0) + value
        else:
            progress.stats[stat_name] = value
        
        # Check for new badges
        await self._check_badges(user_id, progress)
        
        progress.updated_at = datetime.utcnow()
        return progress
    
    async def record_activity(self, user_id: str) -> UserProgress:
        """Record daily activity and update streak."""
        progress = await self.get_user_progress(user_id)
        today = datetime.utcnow().date()
        
        if progress.last_activity_date:
            last_date = progress.last_activity_date.date()
            days_diff = (today - last_date).days
            
            if days_diff == 1:
                # Consecutive day
                progress.current_streak += 1
                if progress.current_streak > progress.longest_streak:
                    progress.longest_streak = progress.current_streak
            elif days_diff > 1:
                # Streak broken
                progress.current_streak = 1
            # days_diff == 0: Same day, don't change streak
        else:
            progress.current_streak = 1
        
        progress.last_activity_date = datetime.utcnow()
        
        # Check for streak badges
        await self._check_badges(user_id, progress)
        
        progress.updated_at = datetime.utcnow()
        return progress
    
    async def _check_badges(
        self,
        user_id: str,
        progress: UserProgress
    ):
        """Check if user qualifies for any new badges."""
        for badge in self.badges.values():
            if not badge.is_active:
                continue
            if badge.id in progress.badges_earned:
                continue
            
            # Check criteria
            earned = True
            for key, required_value in badge.criteria.items():
                if key == "streak_days":
                    if progress.current_streak < required_value:
                        earned = False
                        break
                elif key in progress.stats:
                    if progress.stats[key] < required_value:
                        earned = False
                        break
                else:
                    earned = False
                    break
            
            if earned:
                await self.award_badge(user_id, badge.id)
    
    async def award_badge(
        self,
        user_id: str,
        badge_id: str,
        context: Optional[dict[str, Any]] = None
    ) -> Optional[Achievement]:
        """Award a badge to a user."""
        badge = self.badges.get(badge_id)
        if not badge:
            return None
        
        progress = await self.get_user_progress(user_id)
        
        # Check if already earned
        if badge_id in progress.badges_earned:
            return None
        
        # Create achievement
        achievement_id = str(uuid.uuid4())
        achievement = Achievement(
            id=achievement_id,
            user_id=user_id,
            badge_id=badge_id,
            context=context or {},
        )
        
        self.achievements[achievement_id] = achievement
        progress.badges_earned.append(badge_id)
        
        # Award points
        await self.add_xp(user_id, badge.points)
        
        return achievement
    
    async def get_user_badges(self, user_id: str) -> list[dict[str, Any]]:
        """Get all badges earned by a user."""
        progress = await self.get_user_progress(user_id, create_if_missing=False)
        if not progress:
            return []
        
        badges = []
        for badge_id in progress.badges_earned:
            badge = self.badges.get(badge_id)
            if badge:
                # Find achievement
                achievement = None
                for a in self.achievements.values():
                    if a.user_id == user_id and a.badge_id == badge_id:
                        achievement = a
                        break
                
                badges.append({
                    "id": badge.id,
                    "name": badge.name,
                    "description": badge.description,
                    "category": badge.category.value,
                    "tier": badge.tier.value,
                    "icon": badge.icon,
                    "points": badge.points,
                    "earned_at": achievement.earned_at.isoformat() if achievement else None,
                })
        
        return badges
    
    async def list_badges(
        self,
        category: Optional[BadgeCategory] = None,
        include_secret: bool = False
    ) -> list[Badge]:
        """List available badges."""
        badges = list(self.badges.values())
        
        if not include_secret:
            badges = [b for b in badges if not b.is_secret]
        
        if category:
            badges = [b for b in badges if b.category == category]
        
        return badges
    
    # Leaderboards
    async def update_leaderboard(
        self,
        leaderboard_id: str,
        entries: list[dict[str, Any]]
    ) -> Leaderboard:
        """Update a leaderboard."""
        lb = self.leaderboards.get(leaderboard_id)
        if not lb:
            raise ValueError("Leaderboard not found")
        
        # Calculate ranks
        sorted_entries = sorted(entries, key=lambda x: x["score"], reverse=True)
        
        lb.entries = [
            LeaderboardEntry(
                user_id=e["user_id"],
                rank=i + 1,
                score=e["score"],
                change=e.get("change", 0),
                metadata=e.get("metadata", {}),
            )
            for i, e in enumerate(sorted_entries)
        ]
        
        lb.last_updated = datetime.utcnow()
        return lb
    
    async def create_leaderboard(
        self,
        name: str,
        metric: str,
        period: str,
        team_id: Optional[str] = None,
    ) -> Leaderboard:
        """Create a new leaderboard."""
        lb_id = str(uuid.uuid4())
        
        lb = Leaderboard(
            id=lb_id,
            name=name,
            metric=metric,
            period=period,
            team_id=team_id,
        )
        
        self.leaderboards[lb_id] = lb
        return lb
    
    async def get_leaderboard(
        self,
        leaderboard_id: str
    ) -> Optional[Leaderboard]:
        """Get a leaderboard."""
        return self.leaderboards.get(leaderboard_id)
    
    async def get_user_rank(
        self,
        user_id: str,
        leaderboard_id: str
    ) -> Optional[LeaderboardEntry]:
        """Get user's rank on a leaderboard."""
        lb = self.leaderboards.get(leaderboard_id)
        if not lb:
            return None
        
        for entry in lb.entries:
            if entry.user_id == user_id:
                return entry
        
        return None
    
    # Challenges
    async def create_challenge(
        self,
        name: str,
        description: str,
        challenge_type: ChallengeType,
        metric: str,
        target_value: float,
        start_date: datetime,
        end_date: datetime,
        reward_points: int = 0,
        created_by: Optional[str] = None,
    ) -> Challenge:
        """Create a new challenge."""
        challenge_id = str(uuid.uuid4())
        
        status = ChallengeStatus.UPCOMING
        now = datetime.utcnow()
        if now >= start_date and now < end_date:
            status = ChallengeStatus.ACTIVE
        elif now >= end_date:
            status = ChallengeStatus.COMPLETED
        
        challenge = Challenge(
            id=challenge_id,
            name=name,
            description=description,
            challenge_type=challenge_type,
            metric=metric,
            target_value=target_value,
            start_date=start_date,
            end_date=end_date,
            status=status,
            reward_points=reward_points,
            created_by=created_by,
        )
        
        self.challenges[challenge_id] = challenge
        return challenge
    
    async def join_challenge(
        self,
        challenge_id: str,
        user_id: str
    ) -> bool:
        """Join a challenge."""
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return False
        
        if challenge.status != ChallengeStatus.ACTIVE:
            return False
        
        if user_id not in challenge.participants:
            challenge.participants.append(user_id)
            challenge.progress[user_id] = 0.0
        
        return True
    
    async def update_challenge_progress(
        self,
        challenge_id: str,
        user_id: str,
        progress: float
    ) -> Optional[Challenge]:
        """Update user's progress in a challenge."""
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return None
        
        if user_id not in challenge.participants:
            return None
        
        challenge.progress[user_id] = progress
        
        # Check if target reached
        if progress >= challenge.target_value and not challenge.winner_id:
            challenge.winner_id = user_id
            # Award points
            if challenge.reward_points > 0:
                await self.add_xp(user_id, challenge.reward_points, f"Challenge winner: {challenge.name}")
        
        return challenge
    
    async def list_challenges(
        self,
        status: Optional[ChallengeStatus] = None,
        user_id: Optional[str] = None
    ) -> list[Challenge]:
        """List challenges."""
        challenges = list(self.challenges.values())
        
        if status:
            challenges = [c for c in challenges if c.status == status]
        
        if user_id:
            challenges = [c for c in challenges if user_id in c.participants]
        
        return sorted(challenges, key=lambda c: c.start_date, reverse=True)
    
    # Rewards
    async def create_reward(
        self,
        name: str,
        description: str,
        points_cost: int,
        category: str,
        quantity_available: Optional[int] = None,
    ) -> Reward:
        """Create a reward."""
        reward_id = str(uuid.uuid4())
        
        reward = Reward(
            id=reward_id,
            name=name,
            description=description,
            points_cost=points_cost,
            category=category,
            quantity_available=quantity_available,
        )
        
        self.rewards[reward_id] = reward
        return reward
    
    async def list_rewards(
        self,
        category: Optional[str] = None,
        affordable_for: Optional[str] = None
    ) -> list[Reward]:
        """List available rewards."""
        rewards = [r for r in self.rewards.values() if r.is_active]
        
        if category:
            rewards = [r for r in rewards if r.category == category]
        
        if affordable_for:
            progress = await self.get_user_progress(affordable_for, create_if_missing=False)
            if progress:
                rewards = [r for r in rewards if r.points_cost <= progress.total_points]
        
        return rewards
    
    async def redeem_reward(
        self,
        user_id: str,
        reward_id: str
    ) -> Optional[RewardRedemption]:
        """Redeem a reward."""
        reward = self.rewards.get(reward_id)
        if not reward or not reward.is_active:
            return None
        
        progress = await self.get_user_progress(user_id, create_if_missing=False)
        if not progress or progress.total_points < reward.points_cost:
            return None
        
        # Check quantity
        if reward.quantity_available is not None and reward.quantity_redeemed >= reward.quantity_available:
            return None
        
        # Deduct points
        progress.total_points -= reward.points_cost
        
        # Create redemption
        redemption_id = str(uuid.uuid4())
        redemption = RewardRedemption(
            id=redemption_id,
            user_id=user_id,
            reward_id=reward_id,
            points_spent=reward.points_cost,
        )
        
        self.redemptions[redemption_id] = redemption
        reward.quantity_redeemed += 1
        
        return redemption
    
    async def get_gamification_stats(self) -> dict[str, Any]:
        """Get gamification statistics."""
        total_users = len(self.user_progress)
        total_badges_earned = sum(len(p.badges_earned) for p in self.user_progress.values())
        total_xp = sum(p.total_points for p in self.user_progress.values())
        active_challenges = len([c for c in self.challenges.values() if c.status == ChallengeStatus.ACTIVE])
        
        return {
            "total_users": total_users,
            "total_badges": len(self.badges),
            "total_badges_earned": total_badges_earned,
            "total_xp_earned": total_xp,
            "active_challenges": active_challenges,
            "leaderboards": len(self.leaderboards),
            "rewards_available": len([r for r in self.rewards.values() if r.is_active]),
            "total_redemptions": len(self.redemptions),
        }


# Singleton instance
_gamification_service: Optional[GamificationService] = None


def get_gamification_service() -> GamificationService:
    """Get gamification service singleton."""
    global _gamification_service
    if _gamification_service is None:
        _gamification_service = GamificationService()
    return _gamification_service
