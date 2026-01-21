"""
Goal Tracking Service
=====================
Manages sales goals, quotas, and progress tracking.
Supports individual and team goals with periodic tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class GoalType(str, Enum):
    """Types of goals."""
    EMAILS_SENT = "emails_sent"
    EMAILS_OPENED = "emails_opened"
    REPLIES_RECEIVED = "replies_received"
    MEETINGS_BOOKED = "meetings_booked"
    MEETINGS_HELD = "meetings_held"
    CALLS_MADE = "calls_made"
    DEALS_CREATED = "deals_created"
    DEALS_WON = "deals_won"
    REVENUE = "revenue"
    PIPELINE_VALUE = "pipeline_value"
    CONTACTS_ADDED = "contacts_added"
    CONTACTS_ENGAGED = "contacts_engaged"
    RESPONSE_TIME = "response_time"
    CUSTOM = "custom"


class GoalPeriod(str, Enum):
    """Time periods for goals."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class GoalProgress:
    """Progress update for a goal."""
    id: str
    goal_id: str
    current_value: float
    previous_value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }


@dataclass
class Goal:
    """A sales goal."""
    id: str
    name: str
    goal_type: GoalType
    target_value: float
    current_value: float = 0
    period: GoalPeriod = GoalPeriod.MONTHLY
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    team_id: Optional[str] = None
    is_team_goal: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.target_value == 0:
            return 0
        return min((self.current_value / self.target_value) * 100, 100)
    
    @property
    def remaining_value(self) -> float:
        """Calculate remaining value to reach goal."""
        return max(self.target_value - self.current_value, 0)
    
    @property
    def is_completed(self) -> bool:
        """Check if goal is completed."""
        return self.current_value >= self.target_value
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining in the goal period."""
        if self.end_date:
            delta = self.end_date - datetime.utcnow()
            return max(delta.days, 0)
        return None
    
    @property
    def pace(self) -> Optional[float]:
        """Calculate if on pace to meet goal."""
        if not self.end_date:
            return None
        
        total_days = (self.end_date - self.start_date).days
        elapsed_days = (datetime.utcnow() - self.start_date).days
        
        if elapsed_days <= 0 or total_days <= 0:
            return None
        
        expected_progress = (elapsed_days / total_days) * self.target_value
        if expected_progress == 0:
            return 100
        
        return (self.current_value / expected_progress) * 100
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "goal_type": self.goal_type.value,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress_percentage": round(self.progress_percentage, 1),
            "remaining_value": self.remaining_value,
            "is_completed": self.is_completed,
            "period": self.period.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "days_remaining": self.days_remaining,
            "pace": round(self.pace, 1) if self.pace else None,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "team_id": self.team_id,
            "is_team_goal": self.is_team_goal,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GoalService:
    """
    Manages sales goals and progress tracking.
    """
    
    def __init__(self):
        self.goals: dict[str, Goal] = {}
        self.progress_history: dict[str, list[GoalProgress]] = {}  # goal_id -> progress
        self._setup_default_goals()
    
    def _setup_default_goals(self) -> None:
        """Set up default goals for demonstration."""
        now = datetime.utcnow()
        
        # Monthly goals
        month_end = datetime(now.year, now.month + 1 if now.month < 12 else 1, 1) - timedelta(days=1)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        
        self.create_goal(
            name="Monthly Emails Sent",
            goal_type=GoalType.EMAILS_SENT,
            target_value=500,
            period=GoalPeriod.MONTHLY,
            start_date=datetime(now.year, now.month, 1),
            end_date=month_end,
        )
        
        self.create_goal(
            name="Monthly Meetings Booked",
            goal_type=GoalType.MEETINGS_BOOKED,
            target_value=20,
            period=GoalPeriod.MONTHLY,
            start_date=datetime(now.year, now.month, 1),
            end_date=month_end,
        )
        
        self.create_goal(
            name="Monthly Replies",
            goal_type=GoalType.REPLIES_RECEIVED,
            target_value=50,
            period=GoalPeriod.MONTHLY,
            start_date=datetime(now.year, now.month, 1),
            end_date=month_end,
        )
        
        # Weekly goal
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        
        self.create_goal(
            name="Weekly Contacts Added",
            goal_type=GoalType.CONTACTS_ADDED,
            target_value=50,
            period=GoalPeriod.WEEKLY,
            start_date=week_start,
            end_date=week_end,
        )
        
        logger.info("default_goals_created", count=4)
    
    def create_goal(
        self,
        name: str,
        goal_type: GoalType,
        target_value: float,
        period: GoalPeriod = GoalPeriod.MONTHLY,
        start_date: datetime = None,
        end_date: datetime = None,
        owner_id: str = None,
        owner_name: str = None,
        team_id: str = None,
        is_team_goal: bool = False,
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            id=str(uuid.uuid4()),
            name=name,
            goal_type=goal_type,
            target_value=target_value,
            period=period,
            start_date=start_date or datetime.utcnow(),
            end_date=end_date,
            owner_id=owner_id,
            owner_name=owner_name,
            team_id=team_id,
            is_team_goal=is_team_goal,
        )
        
        self.goals[goal.id] = goal
        self.progress_history[goal.id] = []
        
        logger.info(
            "goal_created",
            goal_id=goal.id,
            name=name,
            target=target_value,
        )
        
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self.goals.get(goal_id)
    
    def list_goals(
        self,
        owner_id: str = None,
        team_id: str = None,
        goal_type: GoalType = None,
        period: GoalPeriod = None,
        active_only: bool = True,
    ) -> list[Goal]:
        """List goals with filters."""
        goals = list(self.goals.values())
        
        if owner_id:
            goals = [g for g in goals if g.owner_id == owner_id]
        
        if team_id:
            goals = [g for g in goals if g.team_id == team_id]
        
        if goal_type:
            goals = [g for g in goals if g.goal_type == goal_type]
        
        if period:
            goals = [g for g in goals if g.period == period]
        
        if active_only:
            goals = [g for g in goals if g.is_active]
        
        return sorted(goals, key=lambda g: g.end_date or datetime.max)
    
    def update_goal(
        self,
        goal_id: str,
        updates: dict,
    ) -> Optional[Goal]:
        """Update a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        
        for key, value in updates.items():
            if hasattr(goal, key) and key not in ["id", "created_at"]:
                setattr(goal, key, value)
        
        goal.updated_at = datetime.utcnow()
        return goal
    
    def update_progress(
        self,
        goal_id: str,
        new_value: float,
        notes: str = "",
    ) -> Optional[GoalProgress]:
        """Update progress on a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        
        progress = GoalProgress(
            id=str(uuid.uuid4()),
            goal_id=goal_id,
            current_value=new_value,
            previous_value=goal.current_value,
            notes=notes,
        )
        
        goal.current_value = new_value
        goal.updated_at = datetime.utcnow()
        
        self.progress_history[goal_id].append(progress)
        
        logger.info(
            "goal_progress_updated",
            goal_id=goal_id,
            new_value=new_value,
            progress_pct=goal.progress_percentage,
        )
        
        return progress
    
    def increment_progress(
        self,
        goal_id: str,
        increment: float = 1,
        notes: str = "",
    ) -> Optional[GoalProgress]:
        """Increment progress on a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        
        return self.update_progress(
            goal_id=goal_id,
            new_value=goal.current_value + increment,
            notes=notes,
        )
    
    def get_progress_history(
        self,
        goal_id: str,
        limit: int = 50,
    ) -> list[GoalProgress]:
        """Get progress history for a goal."""
        history = self.progress_history.get(goal_id, [])
        return sorted(history, key=lambda p: p.timestamp, reverse=True)[:limit]
    
    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        if goal_id in self.goals:
            del self.goals[goal_id]
            if goal_id in self.progress_history:
                del self.progress_history[goal_id]
            return True
        return False
    
    def get_dashboard(
        self,
        owner_id: str = None,
        team_id: str = None,
    ) -> dict:
        """Get goal dashboard summary."""
        goals = self.list_goals(
            owner_id=owner_id,
            team_id=team_id,
            active_only=True,
        )
        
        completed = [g for g in goals if g.is_completed]
        on_track = [g for g in goals if not g.is_completed and g.pace and g.pace >= 90]
        at_risk = [g for g in goals if not g.is_completed and g.pace and 70 <= g.pace < 90]
        behind = [g for g in goals if not g.is_completed and g.pace and g.pace < 70]
        
        return {
            "total_goals": len(goals),
            "completed": len(completed),
            "on_track": len(on_track),
            "at_risk": len(at_risk),
            "behind": len(behind),
            "completion_rate": (len(completed) / len(goals) * 100) if goals else 0,
            "goals": [g.to_dict() for g in goals],
        }
    
    def get_goal_by_type(
        self,
        goal_type: GoalType,
        owner_id: str = None,
        team_id: str = None,
    ) -> Optional[Goal]:
        """Get the active goal for a specific type."""
        goals = self.list_goals(
            owner_id=owner_id,
            team_id=team_id,
            goal_type=goal_type,
            active_only=True,
        )
        return goals[0] if goals else None
    
    def auto_track(
        self,
        goal_type: GoalType,
        value: float = 1,
        owner_id: str = None,
    ) -> Optional[GoalProgress]:
        """Auto-track progress for a goal type."""
        goal = self.get_goal_by_type(
            goal_type=goal_type,
            owner_id=owner_id,
        )
        
        if goal:
            return self.increment_progress(goal.id, value)
        return None
    
    def get_leaderboard(
        self,
        goal_type: GoalType = None,
        period: GoalPeriod = None,
    ) -> list[dict]:
        """Get leaderboard for goals."""
        goals = self.list_goals(
            goal_type=goal_type,
            period=period,
            active_only=True,
        )
        
        # Filter to only goals with owners
        goals = [g for g in goals if g.owner_id]
        
        # Sort by progress percentage
        goals = sorted(goals, key=lambda g: g.progress_percentage, reverse=True)
        
        return [
            {
                "rank": i + 1,
                "owner_id": g.owner_id,
                "owner_name": g.owner_name,
                "goal_name": g.name,
                "progress_percentage": round(g.progress_percentage, 1),
                "current_value": g.current_value,
                "target_value": g.target_value,
            }
            for i, g in enumerate(goals)
        ]


# Singleton instance
_service: Optional[GoalService] = None


def get_goal_service() -> GoalService:
    """Get the goal service singleton."""
    global _service
    if _service is None:
        _service = GoalService()
    return _service
