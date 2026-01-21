"""
Team Service - Sales Team Management
=====================================
Handles team creation, hierarchy, membership, and performance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class TeamType(str, Enum):
    """Types of teams."""
    SALES = "sales"
    SDR = "sdr"
    ACCOUNT_MANAGEMENT = "account_management"
    CUSTOMER_SUCCESS = "customer_success"
    ENTERPRISE = "enterprise"
    SMB = "smb"
    MID_MARKET = "mid_market"
    PARTNERSHIPS = "partnerships"
    CHANNEL = "channel"
    REGIONAL = "regional"
    VIRTUAL = "virtual"


class TeamRole(str, Enum):
    """Roles within a team."""
    LEADER = "leader"
    MANAGER = "manager"
    MEMBER = "member"
    ADMIN = "admin"


@dataclass
class TeamMember:
    """Team member model."""
    id: str
    team_id: str
    user_id: str
    role: TeamRole
    title: Optional[str] = None
    quota: Optional[float] = None
    commission_rate: Optional[float] = None
    is_active: bool = True
    joined_at: datetime = field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamGoal:
    """Team goal/target."""
    id: str
    team_id: str
    name: str
    target_type: str  # revenue, deals, meetings, etc.
    target_value: float
    current_value: float = 0.0
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: Optional[datetime] = None
    is_achieved: bool = False
    achieved_at: Optional[datetime] = None


@dataclass
class TeamPerformance:
    """Team performance metrics."""
    team_id: str
    period: str
    total_revenue: float = 0.0
    total_deals: int = 0
    deals_won: int = 0
    deals_lost: int = 0
    pipeline_value: float = 0.0
    avg_deal_size: float = 0.0
    win_rate: float = 0.0
    quota_attainment: float = 0.0
    activities_count: int = 0
    meetings_count: int = 0
    calls_count: int = 0
    emails_sent: int = 0


@dataclass
class Team:
    """Team model."""
    id: str
    name: str
    type: TeamType
    description: Optional[str] = None
    parent_team_id: Optional[str] = None
    territory_id: Optional[str] = None
    manager_user_id: Optional[str] = None
    quota: Optional[float] = None
    is_active: bool = True
    members: list[TeamMember] = field(default_factory=list)
    child_teams: list[str] = field(default_factory=list)  # Team IDs
    goals: list[TeamGoal] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TeamService:
    """Service for team management."""
    
    def __init__(self):
        """Initialize team service."""
        self.teams: dict[str, Team] = {}
        self.members: dict[str, TeamMember] = {}
        self.goals: dict[str, TeamGoal] = {}
        self.performance: dict[str, TeamPerformance] = {}
    
    async def create_team(
        self,
        name: str,
        team_type: TeamType,
        description: Optional[str] = None,
        parent_team_id: Optional[str] = None,
        territory_id: Optional[str] = None,
        manager_user_id: Optional[str] = None,
        quota: Optional[float] = None,
        created_by: Optional[str] = None,
    ) -> Team:
        """Create a new team."""
        team_id = str(uuid.uuid4())
        
        team = Team(
            id=team_id,
            name=name,
            type=team_type,
            description=description,
            parent_team_id=parent_team_id,
            territory_id=territory_id,
            manager_user_id=manager_user_id,
            quota=quota,
            created_by=created_by,
        )
        
        self.teams[team_id] = team
        
        # Add to parent's child list
        if parent_team_id and parent_team_id in self.teams:
            self.teams[parent_team_id].child_teams.append(team_id)
        
        return team
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        return self.teams.get(team_id)
    
    async def update_team(
        self,
        team_id: str,
        updates: dict[str, Any]
    ) -> Optional[Team]:
        """Update team."""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        for key, value in updates.items():
            if hasattr(team, key) and key not in ['id', 'created_at']:
                setattr(team, key, value)
        
        team.updated_at = datetime.utcnow()
        return team
    
    async def delete_team(self, team_id: str) -> bool:
        """Delete team (soft delete)."""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        team.is_active = False
        team.updated_at = datetime.utcnow()
        return True
    
    async def list_teams(
        self,
        team_type: Optional[TeamType] = None,
        parent_team_id: Optional[str] = None,
        active_only: bool = True,
        include_children: bool = False,
    ) -> list[Team]:
        """List teams with filters."""
        teams = list(self.teams.values())
        
        if active_only:
            teams = [t for t in teams if t.is_active]
        
        if team_type:
            teams = [t for t in teams if t.type == team_type]
        
        if parent_team_id is not None:
            teams = [t for t in teams if t.parent_team_id == parent_team_id]
        
        return teams
    
    async def get_team_hierarchy(self, team_id: str) -> dict[str, Any]:
        """Get team hierarchy (ancestors and descendants)."""
        team = self.teams.get(team_id)
        if not team:
            return {}
        
        # Get ancestors
        ancestors = []
        current = team
        while current.parent_team_id:
            parent = self.teams.get(current.parent_team_id)
            if parent:
                ancestors.append({
                    "id": parent.id,
                    "name": parent.name,
                    "type": parent.type.value,
                })
                current = parent
            else:
                break
        
        # Get descendants
        def get_children(tid: str) -> list[dict]:
            t = self.teams.get(tid)
            if not t:
                return []
            
            return [
                {
                    "id": child_id,
                    "name": self.teams[child_id].name if child_id in self.teams else "Unknown",
                    "type": self.teams[child_id].type.value if child_id in self.teams else "Unknown",
                    "children": get_children(child_id),
                }
                for child_id in t.child_teams
                if child_id in self.teams
            ]
        
        descendants = get_children(team_id)
        
        return {
            "team": {
                "id": team.id,
                "name": team.name,
                "type": team.type.value,
            },
            "ancestors": list(reversed(ancestors)),
            "descendants": descendants,
        }
    
    # Member management
    async def add_member(
        self,
        team_id: str,
        user_id: str,
        role: TeamRole = TeamRole.MEMBER,
        title: Optional[str] = None,
        quota: Optional[float] = None,
        commission_rate: Optional[float] = None,
    ) -> Optional[TeamMember]:
        """Add member to team."""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        member_id = str(uuid.uuid4())
        
        member = TeamMember(
            id=member_id,
            team_id=team_id,
            user_id=user_id,
            role=role,
            title=title,
            quota=quota,
            commission_rate=commission_rate,
        )
        
        self.members[member_id] = member
        team.members.append(member)
        
        return member
    
    async def remove_member(
        self,
        team_id: str,
        user_id: str
    ) -> bool:
        """Remove member from team."""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        for member in team.members:
            if member.user_id == user_id and member.is_active:
                member.is_active = False
                member.left_at = datetime.utcnow()
                return True
        
        return False
    
    async def update_member(
        self,
        member_id: str,
        updates: dict[str, Any]
    ) -> Optional[TeamMember]:
        """Update team member."""
        member = self.members.get(member_id)
        if not member:
            return None
        
        for key, value in updates.items():
            if hasattr(member, key) and key not in ['id', 'team_id', 'user_id', 'joined_at']:
                setattr(member, key, value)
        
        return member
    
    async def get_team_members(
        self,
        team_id: str,
        include_inactive: bool = False
    ) -> list[TeamMember]:
        """Get all members of a team."""
        team = self.teams.get(team_id)
        if not team:
            return []
        
        if include_inactive:
            return team.members
        
        return [m for m in team.members if m.is_active]
    
    async def get_user_teams(
        self,
        user_id: str,
        active_only: bool = True
    ) -> list[Team]:
        """Get all teams a user belongs to."""
        user_teams = []
        
        for team in self.teams.values():
            if not team.is_active and active_only:
                continue
            
            for member in team.members:
                if member.user_id == user_id and (not active_only or member.is_active):
                    user_teams.append(team)
                    break
        
        return user_teams
    
    async def change_member_role(
        self,
        team_id: str,
        user_id: str,
        new_role: TeamRole
    ) -> Optional[TeamMember]:
        """Change a member's role in the team."""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        for member in team.members:
            if member.user_id == user_id and member.is_active:
                member.role = new_role
                return member
        
        return None
    
    # Goals management
    async def set_goal(
        self,
        team_id: str,
        name: str,
        target_type: str,
        target_value: float,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Optional[TeamGoal]:
        """Set a goal for the team."""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        goal_id = str(uuid.uuid4())
        
        goal = TeamGoal(
            id=goal_id,
            team_id=team_id,
            name=name,
            target_type=target_type,
            target_value=target_value,
            period_start=period_start or datetime.utcnow(),
            period_end=period_end,
        )
        
        self.goals[goal_id] = goal
        team.goals.append(goal)
        
        return goal
    
    async def update_goal_progress(
        self,
        goal_id: str,
        current_value: float
    ) -> Optional[TeamGoal]:
        """Update goal progress."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        
        goal.current_value = current_value
        
        if current_value >= goal.target_value and not goal.is_achieved:
            goal.is_achieved = True
            goal.achieved_at = datetime.utcnow()
        
        return goal
    
    async def get_team_goals(
        self,
        team_id: str,
        active_only: bool = True
    ) -> list[TeamGoal]:
        """Get team goals."""
        team = self.teams.get(team_id)
        if not team:
            return []
        
        goals = team.goals
        
        if active_only:
            now = datetime.utcnow()
            goals = [
                g for g in goals
                if not g.period_end or g.period_end > now
            ]
        
        return goals
    
    # Performance tracking
    async def record_performance(
        self,
        team_id: str,
        period: str,
        metrics: dict[str, Any]
    ) -> TeamPerformance:
        """Record team performance metrics."""
        key = f"{team_id}:{period}"
        
        perf = TeamPerformance(
            team_id=team_id,
            period=period,
            **metrics
        )
        
        self.performance[key] = perf
        return perf
    
    async def get_performance(
        self,
        team_id: str,
        period: str
    ) -> Optional[TeamPerformance]:
        """Get team performance for a period."""
        key = f"{team_id}:{period}"
        return self.performance.get(key)
    
    async def get_leaderboard(
        self,
        team_id: str,
        metric: str = "revenue",
        period: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get team member leaderboard."""
        team = self.teams.get(team_id)
        if not team:
            return []
        
        # In production, this would calculate from actual data
        leaderboard = []
        for i, member in enumerate(team.members):
            if member.is_active:
                leaderboard.append({
                    "rank": i + 1,
                    "user_id": member.user_id,
                    "title": member.title,
                    "value": 50000 - (i * 5000),  # Mock data
                    "quota_attainment": 0.85 - (i * 0.1),
                })
        
        return sorted(leaderboard, key=lambda x: x["value"], reverse=True)
    
    async def get_team_stats(self, team_id: str) -> dict[str, Any]:
        """Get team statistics."""
        team = self.teams.get(team_id)
        if not team:
            return {}
        
        active_members = [m for m in team.members if m.is_active]
        total_quota = sum(m.quota or 0 for m in active_members)
        
        return {
            "team_id": team_id,
            "name": team.name,
            "type": team.type.value,
            "member_count": len(active_members),
            "total_quota": total_quota,
            "team_quota": team.quota,
            "active_goals": len([g for g in team.goals if not g.is_achieved]),
            "achieved_goals": len([g for g in team.goals if g.is_achieved]),
            "child_teams_count": len(team.child_teams),
        }


# Singleton instance
_team_service: Optional[TeamService] = None


def get_team_service() -> TeamService:
    """Get team service singleton."""
    global _team_service
    if _team_service is None:
        _team_service = TeamService()
    return _team_service
