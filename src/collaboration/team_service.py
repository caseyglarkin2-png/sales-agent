"""
Team Collaboration Service
===========================
Multi-user support with assignments, comments, mentions, and activity feeds.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class TeamRole(str, Enum):
    """Team member roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class ActivityType(str, Enum):
    """Types of team activities."""
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_ASSIGNED = "contact_assigned"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_REPLIED = "email_replied"
    MEETING_SCHEDULED = "meeting_scheduled"
    DEAL_CREATED = "deal_created"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    COMMENT_ADDED = "comment_added"
    MENTION = "mention"
    NOTE_ADDED = "note_added"


@dataclass
class TeamMember:
    """A team member."""
    id: str
    email: str
    name: str
    role: TeamRole = TeamRole.MEMBER
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    settings: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
        }


@dataclass
class Assignment:
    """An assignment of a record to a team member."""
    id: str
    record_type: str  # contact, company, deal
    record_id: str
    assignee_id: str
    assigned_by: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    priority: str = "normal"  # low, normal, high, urgent
    status: str = "active"  # active, completed, reassigned
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "assignee_id": self.assignee_id,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class Comment:
    """A comment on a record."""
    id: str
    record_type: str
    record_id: str
    author_id: str
    content: str
    mentions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_edited: bool = False
    parent_id: Optional[str] = None  # For threaded comments
    reactions: dict = field(default_factory=dict)  # {emoji: [user_ids]}
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "author_id": self.author_id,
            "content": self.content,
            "mentions": self.mentions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_edited": self.is_edited,
            "parent_id": self.parent_id,
            "reactions": self.reactions,
        }


@dataclass
class Activity:
    """A team activity entry."""
    id: str
    activity_type: ActivityType
    actor_id: str
    record_type: Optional[str] = None
    record_id: Optional[str] = None
    description: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "activity_type": self.activity_type.value,
            "actor_id": self.actor_id,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class TeamService:
    """
    Manages team collaboration features.
    """
    
    def __init__(self):
        self.members: dict[str, TeamMember] = {}
        self.assignments: dict[str, Assignment] = {}
        self.comments: dict[str, Comment] = {}
        self.activities: list[Activity] = []
    
    # Team Member Management
    
    def add_member(
        self,
        email: str,
        name: str,
        role: TeamRole = TeamRole.MEMBER,
    ) -> TeamMember:
        """Add a team member."""
        member = TeamMember(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            role=role,
        )
        
        self.members[member.id] = member
        
        logger.info("team_member_added", member_id=member.id, email=email)
        
        return member
    
    def get_member(self, member_id: str) -> Optional[TeamMember]:
        """Get a team member by ID."""
        return self.members.get(member_id)
    
    def get_member_by_email(self, email: str) -> Optional[TeamMember]:
        """Get a team member by email."""
        for member in self.members.values():
            if member.email == email:
                return member
        return None
    
    def list_members(
        self,
        role: TeamRole = None,
        active_only: bool = True,
    ) -> list[TeamMember]:
        """List team members."""
        members = list(self.members.values())
        
        if active_only:
            members = [m for m in members if m.is_active]
        if role:
            members = [m for m in members if m.role == role]
        
        return sorted(members, key=lambda m: m.name)
    
    def update_member(
        self,
        member_id: str,
        updates: dict,
    ) -> Optional[TeamMember]:
        """Update a team member."""
        member = self.members.get(member_id)
        if not member:
            return None
        
        for key, value in updates.items():
            if hasattr(member, key):
                if key == "role":
                    value = TeamRole(value)
                setattr(member, key, value)
        
        return member
    
    def deactivate_member(self, member_id: str) -> bool:
        """Deactivate a team member."""
        member = self.members.get(member_id)
        if member:
            member.is_active = False
            return True
        return False
    
    # Assignments
    
    def assign_record(
        self,
        record_type: str,
        record_id: str,
        assignee_id: str,
        assigned_by: str,
        due_date: datetime = None,
        priority: str = "normal",
        notes: str = "",
    ) -> Assignment:
        """Assign a record to a team member."""
        # Check for existing assignment
        existing = self.get_assignment(record_type, record_id)
        if existing:
            existing.status = "reassigned"
        
        assignment = Assignment(
            id=str(uuid.uuid4()),
            record_type=record_type,
            record_id=record_id,
            assignee_id=assignee_id,
            assigned_by=assigned_by,
            due_date=due_date,
            priority=priority,
            notes=notes,
        )
        
        self.assignments[assignment.id] = assignment
        
        # Log activity
        self._log_activity(
            ActivityType.CONTACT_ASSIGNED,
            actor_id=assigned_by,
            record_type=record_type,
            record_id=record_id,
            description=f"Assigned to {self.members.get(assignee_id, {}).get('name', assignee_id)}",
            metadata={"assignee_id": assignee_id},
        )
        
        logger.info(
            "record_assigned",
            record_type=record_type,
            record_id=record_id,
            assignee_id=assignee_id,
        )
        
        return assignment
    
    def get_assignment(
        self,
        record_type: str,
        record_id: str,
    ) -> Optional[Assignment]:
        """Get active assignment for a record."""
        for assignment in self.assignments.values():
            if (assignment.record_type == record_type and 
                assignment.record_id == record_id and 
                assignment.status == "active"):
                return assignment
        return None
    
    def get_assignments_for_member(
        self,
        member_id: str,
        status: str = "active",
    ) -> list[Assignment]:
        """Get assignments for a team member."""
        return [
            a for a in self.assignments.values()
            if a.assignee_id == member_id and (not status or a.status == status)
        ]
    
    def complete_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Mark an assignment as completed."""
        assignment = self.assignments.get(assignment_id)
        if assignment:
            assignment.status = "completed"
            
            self._log_activity(
                ActivityType.TASK_COMPLETED,
                actor_id=assignment.assignee_id,
                record_type=assignment.record_type,
                record_id=assignment.record_id,
                description="Assignment completed",
            )
        return assignment
    
    # Comments
    
    def add_comment(
        self,
        record_type: str,
        record_id: str,
        author_id: str,
        content: str,
        parent_id: str = None,
    ) -> Comment:
        """Add a comment to a record."""
        # Extract mentions
        import re
        mentions = re.findall(r'@(\w+)', content)
        
        comment = Comment(
            id=str(uuid.uuid4()),
            record_type=record_type,
            record_id=record_id,
            author_id=author_id,
            content=content,
            mentions=mentions,
            parent_id=parent_id,
        )
        
        self.comments[comment.id] = comment
        
        # Log activity
        self._log_activity(
            ActivityType.COMMENT_ADDED,
            actor_id=author_id,
            record_type=record_type,
            record_id=record_id,
            description="Added a comment",
        )
        
        # Create mention activities
        for mention in mentions:
            member = self.get_member_by_email(f"{mention}@company.com") or \
                     self.get_member(mention)
            if member:
                self._log_activity(
                    ActivityType.MENTION,
                    actor_id=author_id,
                    record_type=record_type,
                    record_id=record_id,
                    description=f"Mentioned {member.name}",
                    metadata={"mentioned_id": member.id},
                )
        
        return comment
    
    def get_comments(
        self,
        record_type: str,
        record_id: str,
    ) -> list[Comment]:
        """Get comments for a record."""
        comments = [
            c for c in self.comments.values()
            if c.record_type == record_type and c.record_id == record_id
        ]
        return sorted(comments, key=lambda c: c.created_at)
    
    def edit_comment(
        self,
        comment_id: str,
        new_content: str,
        editor_id: str,
    ) -> Optional[Comment]:
        """Edit a comment."""
        comment = self.comments.get(comment_id)
        if comment and comment.author_id == editor_id:
            comment.content = new_content
            comment.updated_at = datetime.utcnow()
            comment.is_edited = True
            return comment
        return None
    
    def delete_comment(self, comment_id: str, deleter_id: str) -> bool:
        """Delete a comment."""
        comment = self.comments.get(comment_id)
        if comment and comment.author_id == deleter_id:
            del self.comments[comment_id]
            return True
        return False
    
    def add_reaction(
        self,
        comment_id: str,
        user_id: str,
        emoji: str,
    ) -> Optional[Comment]:
        """Add a reaction to a comment."""
        comment = self.comments.get(comment_id)
        if comment:
            if emoji not in comment.reactions:
                comment.reactions[emoji] = []
            if user_id not in comment.reactions[emoji]:
                comment.reactions[emoji].append(user_id)
        return comment
    
    # Activity Feed
    
    def _log_activity(
        self,
        activity_type: ActivityType,
        actor_id: str,
        record_type: str = None,
        record_id: str = None,
        description: str = "",
        metadata: dict = None,
    ) -> Activity:
        """Log an activity."""
        activity = Activity(
            id=str(uuid.uuid4()),
            activity_type=activity_type,
            actor_id=actor_id,
            record_type=record_type,
            record_id=record_id,
            description=description,
            metadata=metadata or {},
        )
        
        self.activities.append(activity)
        
        # Keep last 1000 activities
        if len(self.activities) > 1000:
            self.activities = self.activities[-1000:]
        
        return activity
    
    def log_activity(
        self,
        activity_type: str,
        actor_id: str,
        record_type: str = None,
        record_id: str = None,
        description: str = "",
        metadata: dict = None,
    ) -> Activity:
        """Public method to log an activity."""
        try:
            act_type = ActivityType(activity_type)
        except ValueError:
            act_type = ActivityType.NOTE_ADDED
        
        return self._log_activity(
            act_type, actor_id, record_type, record_id, description, metadata
        )
    
    def get_activity_feed(
        self,
        limit: int = 50,
        actor_id: str = None,
        record_type: str = None,
        record_id: str = None,
        activity_types: list[ActivityType] = None,
    ) -> list[Activity]:
        """Get activity feed."""
        activities = self.activities.copy()
        
        if actor_id:
            activities = [a for a in activities if a.actor_id == actor_id]
        if record_type:
            activities = [a for a in activities if a.record_type == record_type]
        if record_id:
            activities = [a for a in activities if a.record_id == record_id]
        if activity_types:
            activities = [a for a in activities if a.activity_type in activity_types]
        
        # Sort by most recent first
        activities.sort(key=lambda a: a.created_at, reverse=True)
        
        return activities[:limit]
    
    def get_mentions_for_member(self, member_id: str) -> list[Activity]:
        """Get mentions for a team member."""
        return [
            a for a in self.activities
            if a.activity_type == ActivityType.MENTION and
            a.metadata.get("mentioned_id") == member_id
        ]
    
    # Team Stats
    
    def get_team_stats(self) -> dict:
        """Get team statistics."""
        members = list(self.members.values())
        active_members = [m for m in members if m.is_active]
        
        assignments = list(self.assignments.values())
        active_assignments = [a for a in assignments if a.status == "active"]
        
        return {
            "total_members": len(members),
            "active_members": len(active_members),
            "by_role": {
                role.value: len([m for m in active_members if m.role == role])
                for role in TeamRole
            },
            "total_assignments": len(assignments),
            "active_assignments": len(active_assignments),
            "assignments_by_priority": {
                priority: len([a for a in active_assignments if a.priority == priority])
                for priority in ["low", "normal", "high", "urgent"]
            },
            "total_comments": len(self.comments),
            "recent_activities": len([
                a for a in self.activities
                if (datetime.utcnow() - a.created_at).days < 1
            ]),
        }


# Singleton instance
_service: Optional[TeamService] = None


def get_team_service() -> TeamService:
    """Get the team service singleton."""
    global _service
    if _service is None:
        _service = TeamService()
    return _service
