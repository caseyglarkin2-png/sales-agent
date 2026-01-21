"""
User Service - User and Team Management
========================================
User accounts, teams, and permission management.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_REP = "sales_rep"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class UserPreferences:
    """User preferences and settings."""
    timezone: str = "UTC"
    locale: str = "en-US"
    email_notifications: bool = True
    browser_notifications: bool = True
    daily_digest: bool = True
    weekly_report: bool = True
    theme: str = "light"
    dashboard_layout: Optional[dict] = None


@dataclass
class User:
    """User entity."""
    id: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    
    # Profile
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    
    # Team
    team_id: Optional[str] = None
    manager_id: Optional[str] = None
    
    # Settings
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Activity
    last_login_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    login_count: int = 0
    
    # Stats
    contacts_owned: int = 0
    deals_owned: int = 0
    emails_sent: int = 0
    
    # Organization
    organization_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Team:
    """Team entity."""
    id: str
    name: str
    description: Optional[str] = None
    
    # Leadership
    manager_id: Optional[str] = None
    
    # Members
    member_ids: list[str] = field(default_factory=list)
    
    # Hierarchy
    parent_team_id: Optional[str] = None
    child_team_ids: list[str] = field(default_factory=list)
    
    # Goals
    monthly_quota: Optional[float] = None
    quarterly_quota: Optional[float] = None
    annual_quota: Optional[float] = None
    
    # Organization
    organization_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Invitation:
    """User invitation."""
    id: str
    email: str
    role: UserRole
    team_id: Optional[str]
    invited_by: str
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class UserService:
    """Service for user and team management."""
    
    def __init__(self):
        self.users: dict[str, User] = {}
        self.teams: dict[str, Team] = {}
        self.invitations: dict[str, Invitation] = {}
        self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample users and teams for demo."""
        # Create teams
        sales_team = Team(
            id="team_sales",
            name="Sales Team",
            description="Main sales team",
            monthly_quota=500000,
            quarterly_quota=1500000
        )
        
        enterprise_team = Team(
            id="team_enterprise",
            name="Enterprise Sales",
            description="Enterprise accounts team",
            parent_team_id="team_sales",
            monthly_quota=1000000
        )
        
        self.teams["team_sales"] = sales_team
        self.teams["team_enterprise"] = enterprise_team
        sales_team.child_team_ids.append("team_enterprise")
        
        # Create users
        admin = User(
            id="user_admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            title="System Administrator",
            login_count=150,
            last_login_at=datetime.utcnow() - timedelta(hours=2)
        )
        
        manager = User(
            id="user_manager",
            email="manager@example.com",
            first_name="Sales",
            last_name="Manager",
            role=UserRole.MANAGER,
            title="Sales Manager",
            team_id="team_sales",
            contacts_owned=50,
            deals_owned=15,
            emails_sent=500,
            login_count=89,
            last_login_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        rep1 = User(
            id="user_rep1",
            email="rep1@example.com",
            first_name="Alex",
            last_name="Johnson",
            role=UserRole.SALES_REP,
            title="Account Executive",
            team_id="team_sales",
            manager_id="user_manager",
            contacts_owned=120,
            deals_owned=25,
            emails_sent=1500,
            login_count=200,
            last_login_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        rep2 = User(
            id="user_rep2",
            email="rep2@example.com",
            first_name="Sarah",
            last_name="Williams",
            role=UserRole.SALES_REP,
            title="Account Executive",
            team_id="team_enterprise",
            manager_id="user_manager",
            contacts_owned=80,
            deals_owned=18,
            emails_sent=1200,
            login_count=175,
            last_login_at=datetime.utcnow() - timedelta(hours=3)
        )
        
        self.users["user_admin"] = admin
        self.users["user_manager"] = manager
        self.users["user_rep1"] = rep1
        self.users["user_rep2"] = rep2
        
        # Add members to teams
        sales_team.member_ids = ["user_manager", "user_rep1"]
        sales_team.manager_id = "user_manager"
        enterprise_team.member_ids = ["user_rep2"]
    
    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        role: UserRole,
        team_id: Optional[str] = None,
        manager_id: Optional[str] = None,
        title: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> User:
        """Create a new user."""
        # Check if email already exists
        for user in self.users.values():
            if user.email.lower() == email.lower():
                raise ValueError(f"User with email {email} already exists")
        
        user_id = f"user_{uuid4().hex[:8]}"
        
        user = User(
            id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            team_id=team_id,
            manager_id=manager_id,
            title=title,
            organization_id=organization_id
        )
        
        self.users[user_id] = user
        
        # Add to team if specified
        if team_id and team_id in self.teams:
            self.teams[team_id].member_ids.append(user_id)
        
        logger.info(f"Created user: {email} ({user_id})")
        
        return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.users.get(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None
    
    async def update_user(
        self,
        user_id: str,
        updates: dict[str, Any]
    ) -> Optional[User]:
        """Update a user."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        allowed_fields = [
            "first_name", "last_name", "email", "phone", "title",
            "avatar_url", "team_id", "manager_id", "role", "status"
        ]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        
        logger.info(f"Updated user: {user_id}")
        
        return user
    
    async def update_preferences(
        self,
        user_id: str,
        preferences: dict
    ) -> Optional[User]:
        """Update user preferences."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        for key, value in preferences.items():
            if hasattr(user.preferences, key):
                setattr(user.preferences, key, value)
        
        user.updated_at = datetime.utcnow()
        
        return user
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        # Remove from team
        if user.team_id and user.team_id in self.teams:
            team = self.teams[user.team_id]
            if user_id in team.member_ids:
                team.member_ids.remove(user_id)
        
        del self.users[user_id]
        
        logger.info(f"Deleted user: {user_id}")
        
        return True
    
    async def list_users(
        self,
        role: Optional[UserRole] = None,
        team_id: Optional[str] = None,
        status: Optional[UserStatus] = None,
        manager_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[User]:
        """List users with filters."""
        results = list(self.users.values())
        
        if role:
            results = [u for u in results if u.role == role]
        
        if team_id:
            results = [u for u in results if u.team_id == team_id]
        
        if status:
            results = [u for u in results if u.status == status]
        
        if manager_id:
            results = [u for u in results if u.manager_id == manager_id]
        
        # Sort by name
        results.sort(key=lambda u: u.full_name)
        
        return results[offset:offset + limit]
    
    async def search_users(
        self,
        query: str,
        limit: int = 20
    ) -> list[User]:
        """Search users by name or email."""
        query = query.lower()
        
        results = [
            u for u in self.users.values()
            if query in u.email.lower()
            or query in u.first_name.lower()
            or query in u.last_name.lower()
            or query in u.full_name.lower()
        ]
        
        return results[:limit]
    
    async def record_login(self, user_id: str) -> Optional[User]:
        """Record a user login."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        user.last_login_at = datetime.utcnow()
        user.login_count += 1
        
        return user
    
    async def record_activity(self, user_id: str) -> Optional[User]:
        """Record user activity."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        user.last_activity_at = datetime.utcnow()
        
        return user
    
    # Team methods
    
    async def create_team(
        self,
        name: str,
        description: Optional[str] = None,
        manager_id: Optional[str] = None,
        parent_team_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Team:
        """Create a new team."""
        team_id = f"team_{uuid4().hex[:8]}"
        
        team = Team(
            id=team_id,
            name=name,
            description=description,
            manager_id=manager_id,
            parent_team_id=parent_team_id,
            organization_id=organization_id
        )
        
        self.teams[team_id] = team
        
        # Add to parent team's children
        if parent_team_id and parent_team_id in self.teams:
            self.teams[parent_team_id].child_team_ids.append(team_id)
        
        logger.info(f"Created team: {name} ({team_id})")
        
        return team
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team by ID."""
        return self.teams.get(team_id)
    
    async def update_team(
        self,
        team_id: str,
        updates: dict[str, Any]
    ) -> Optional[Team]:
        """Update a team."""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        allowed_fields = [
            "name", "description", "manager_id",
            "monthly_quota", "quarterly_quota", "annual_quota"
        ]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(team, key, value)
        
        team.updated_at = datetime.utcnow()
        
        logger.info(f"Updated team: {team_id}")
        
        return team
    
    async def delete_team(self, team_id: str) -> bool:
        """Delete a team."""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        # Remove users from team
        for user in self.users.values():
            if user.team_id == team_id:
                user.team_id = None
        
        # Remove from parent
        if team.parent_team_id and team.parent_team_id in self.teams:
            parent = self.teams[team.parent_team_id]
            if team_id in parent.child_team_ids:
                parent.child_team_ids.remove(team_id)
        
        del self.teams[team_id]
        
        logger.info(f"Deleted team: {team_id}")
        
        return True
    
    async def list_teams(
        self,
        parent_team_id: Optional[str] = None,
        manager_id: Optional[str] = None
    ) -> list[Team]:
        """List teams with filters."""
        results = list(self.teams.values())
        
        if parent_team_id:
            results = [t for t in results if t.parent_team_id == parent_team_id]
        
        if manager_id:
            results = [t for t in results if t.manager_id == manager_id]
        
        return results
    
    async def add_user_to_team(
        self,
        user_id: str,
        team_id: str
    ) -> bool:
        """Add a user to a team."""
        user = self.users.get(user_id)
        team = self.teams.get(team_id)
        
        if not user or not team:
            return False
        
        # Remove from old team
        if user.team_id and user.team_id in self.teams:
            old_team = self.teams[user.team_id]
            if user_id in old_team.member_ids:
                old_team.member_ids.remove(user_id)
        
        # Add to new team
        user.team_id = team_id
        if user_id not in team.member_ids:
            team.member_ids.append(user_id)
        
        logger.info(f"Added user {user_id} to team {team_id}")
        
        return True
    
    async def remove_user_from_team(
        self,
        user_id: str,
        team_id: str
    ) -> bool:
        """Remove a user from a team."""
        user = self.users.get(user_id)
        team = self.teams.get(team_id)
        
        if not user or not team:
            return False
        
        if user.team_id == team_id:
            user.team_id = None
        
        if user_id in team.member_ids:
            team.member_ids.remove(user_id)
        
        logger.info(f"Removed user {user_id} from team {team_id}")
        
        return True
    
    async def get_team_members(self, team_id: str) -> list[User]:
        """Get all members of a team."""
        team = self.teams.get(team_id)
        if not team:
            return []
        
        return [
            self.users[uid] for uid in team.member_ids
            if uid in self.users
        ]
    
    async def get_team_hierarchy(self, team_id: str) -> dict:
        """Get team hierarchy."""
        team = self.teams.get(team_id)
        if not team:
            return {}
        
        result = {
            "team": team,
            "parent": None,
            "children": [],
            "members": []
        }
        
        # Get parent
        if team.parent_team_id:
            result["parent"] = self.teams.get(team.parent_team_id)
        
        # Get children
        for child_id in team.child_team_ids:
            child = self.teams.get(child_id)
            if child:
                result["children"].append(child)
        
        # Get members
        result["members"] = await self.get_team_members(team_id)
        
        return result
    
    # Invitation methods
    
    async def create_invitation(
        self,
        email: str,
        role: UserRole,
        invited_by: str,
        team_id: Optional[str] = None,
        expires_in_days: int = 7
    ) -> Invitation:
        """Create a user invitation."""
        invitation_id = f"inv_{uuid4().hex[:12]}"
        token = uuid4().hex
        
        invitation = Invitation(
            id=invitation_id,
            email=email,
            role=role,
            team_id=team_id,
            invited_by=invited_by,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        
        self.invitations[invitation_id] = invitation
        
        logger.info(f"Created invitation for: {email}")
        
        return invitation
    
    async def accept_invitation(
        self,
        token: str,
        first_name: str,
        last_name: str
    ) -> Optional[User]:
        """Accept an invitation and create user."""
        # Find invitation by token
        invitation = None
        for inv in self.invitations.values():
            if inv.token == token:
                invitation = inv
                break
        
        if not invitation:
            return None
        
        # Check expiration
        if datetime.utcnow() > invitation.expires_at:
            return None
        
        # Check if already accepted
        if invitation.accepted_at:
            return None
        
        # Create user
        user = await self.create_user(
            email=invitation.email,
            first_name=first_name,
            last_name=last_name,
            role=invitation.role,
            team_id=invitation.team_id
        )
        
        invitation.accepted_at = datetime.utcnow()
        
        return user
    
    async def get_stats(self) -> dict:
        """Get user/team statistics."""
        users = list(self.users.values())
        teams = list(self.teams.values())
        
        # Role distribution
        role_dist = {}
        for role in UserRole:
            role_dist[role.value] = len([u for u in users if u.role == role])
        
        # Status distribution
        status_dist = {}
        for status in UserStatus:
            status_dist[status.value] = len([u for u in users if u.status == status])
        
        # Active users (logged in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users = len([
            u for u in users
            if u.last_login_at and u.last_login_at > week_ago
        ])
        
        return {
            "total_users": len(users),
            "total_teams": len(teams),
            "active_users_7d": active_users,
            "pending_invitations": len([
                i for i in self.invitations.values()
                if not i.accepted_at and datetime.utcnow() < i.expires_at
            ]),
            "role_distribution": role_dist,
            "status_distribution": status_dist,
            "average_logins_per_user": sum(u.login_count for u in users) / len(users) if users else 0
        }


# Global service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get or create the user service singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
