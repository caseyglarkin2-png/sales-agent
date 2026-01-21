"""
Task Management Service
=======================
Manages sales tasks, follow-ups, and reminders.
Supports recurring tasks, dependencies, and assignments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    """Types of tasks."""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    RESEARCH = "research"
    PROPOSAL = "proposal"
    DEMO = "demo"
    LINKEDIN = "linkedin"
    REVIEW = "review"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    """Task priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task status."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecurrencePattern(str, Enum):
    """Recurrence patterns for tasks."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class Task:
    """A sales task."""
    id: str
    title: str
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    description: str = ""
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None  # HH:MM format
    reminder_at: Optional[datetime] = None
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    deal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_end_date: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        if self.due_date:
            return datetime.utcnow() > self.due_date
        return False
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until due."""
        if self.due_date:
            delta = self.due_date - datetime.utcnow()
            return delta.days
        return None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time,
            "reminder_at": self.reminder_at.isoformat() if self.reminder_at else None,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "deal_id": self.deal_id,
            "assigned_to": self.assigned_to,
            "assigned_to_name": self.assigned_to_name,
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern.value if self.recurrence_pattern else None,
            "parent_task_id": self.parent_task_id,
            "depends_on": self.depends_on,
            "tags": self.tags,
            "notes": self.notes,
            "is_overdue": self.is_overdue,
            "days_until_due": self.days_until_due,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TaskService:
    """
    Manages sales tasks and follow-ups.
    """
    
    def __init__(self):
        self.tasks: dict[str, Task] = {}
    
    def create_task(
        self,
        title: str,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        description: str = "",
        due_date: datetime = None,
        due_time: str = None,
        contact_id: str = None,
        contact_name: str = None,
        company_id: str = None,
        company_name: str = None,
        deal_id: str = None,
        assigned_to: str = None,
        assigned_to_name: str = None,
        created_by: str = None,
        is_recurring: bool = False,
        recurrence_pattern: RecurrencePattern = None,
        tags: list[str] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            task_type=task_type,
            priority=priority,
            description=description,
            due_date=due_date,
            due_time=due_time,
            contact_id=contact_id,
            contact_name=contact_name,
            company_id=company_id,
            company_name=company_name,
            deal_id=deal_id,
            assigned_to=assigned_to,
            assigned_to_name=assigned_to_name,
            created_by=created_by,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            tags=tags or [],
        )
        
        self.tasks[task.id] = task
        
        logger.info(
            "task_created",
            task_id=task.id,
            title=title,
            type=task_type.value,
        )
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        status: TaskStatus = None,
        task_type: TaskType = None,
        priority: TaskPriority = None,
        assigned_to: str = None,
        contact_id: str = None,
        company_id: str = None,
        deal_id: str = None,
        overdue_only: bool = False,
        due_today: bool = False,
        due_this_week: bool = False,
        tags: list[str] = None,
    ) -> list[Task]:
        """List tasks with filters."""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        if contact_id:
            tasks = [t for t in tasks if t.contact_id == contact_id]
        
        if company_id:
            tasks = [t for t in tasks if t.company_id == company_id]
        
        if deal_id:
            tasks = [t for t in tasks if t.deal_id == deal_id]
        
        if overdue_only:
            tasks = [t for t in tasks if t.is_overdue]
        
        if due_today:
            today = datetime.utcnow().date()
            tasks = [t for t in tasks if t.due_date and t.due_date.date() == today]
        
        if due_this_week:
            today = datetime.utcnow().date()
            week_end = today + timedelta(days=(6 - today.weekday()))
            tasks = [
                t for t in tasks
                if t.due_date and today <= t.due_date.date() <= week_end
            ]
        
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        
        # Sort by priority and due date
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        
        return sorted(
            tasks,
            key=lambda t: (
                priority_order.get(t.priority, 99),
                t.due_date or datetime.max,
            ),
        )
    
    def update_task(
        self,
        task_id: str,
        updates: dict,
    ) -> Optional[Task]:
        """Update a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        for key, value in updates.items():
            if hasattr(task, key) and key not in ["id", "created_at"]:
                setattr(task, key, value)
        
        task.updated_at = datetime.utcnow()
        return task
    
    def complete_task(
        self,
        task_id: str,
        notes: str = "",
    ) -> Optional[Task]:
        """Mark a task as completed."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        
        if notes:
            task.notes = f"{task.notes}\n\nCompletion notes: {notes}".strip()
        
        # Create next occurrence for recurring tasks
        if task.is_recurring and task.recurrence_pattern:
            self._create_next_occurrence(task)
        
        logger.info("task_completed", task_id=task_id)
        
        return task
    
    def _create_next_occurrence(self, task: Task) -> Optional[Task]:
        """Create the next occurrence of a recurring task."""
        if not task.due_date or not task.recurrence_pattern:
            return None
        
        # Check if past end date
        if task.recurrence_end_date and datetime.utcnow() > task.recurrence_end_date:
            return None
        
        # Calculate next due date
        next_due = task.due_date
        if task.recurrence_pattern == RecurrencePattern.DAILY:
            next_due += timedelta(days=1)
        elif task.recurrence_pattern == RecurrencePattern.WEEKLY:
            next_due += timedelta(weeks=1)
        elif task.recurrence_pattern == RecurrencePattern.BIWEEKLY:
            next_due += timedelta(weeks=2)
        elif task.recurrence_pattern == RecurrencePattern.MONTHLY:
            next_due += timedelta(days=30)
        elif task.recurrence_pattern == RecurrencePattern.QUARTERLY:
            next_due += timedelta(days=90)
        
        # Create new task
        new_task = self.create_task(
            title=task.title,
            task_type=task.task_type,
            priority=task.priority,
            description=task.description,
            due_date=next_due,
            due_time=task.due_time,
            contact_id=task.contact_id,
            contact_name=task.contact_name,
            company_id=task.company_id,
            company_name=task.company_name,
            deal_id=task.deal_id,
            assigned_to=task.assigned_to,
            assigned_to_name=task.assigned_to_name,
            is_recurring=True,
            recurrence_pattern=task.recurrence_pattern,
            tags=task.tags,
        )
        new_task.parent_task_id = task.id
        new_task.recurrence_end_date = task.recurrence_end_date
        
        return new_task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def get_task_stats(
        self,
        assigned_to: str = None,
    ) -> dict:
        """Get task statistics."""
        tasks = list(self.tasks.values())
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        total = len(tasks)
        by_status = {}
        by_type = {}
        by_priority = {}
        
        for task in tasks:
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            by_type[task.task_type.value] = by_type.get(task.task_type.value, 0) + 1
            by_priority[task.priority.value] = by_priority.get(task.priority.value, 0) + 1
        
        overdue = len([t for t in tasks if t.is_overdue])
        due_today = len([
            t for t in tasks
            if t.due_date and t.due_date.date() == datetime.utcnow().date()
            and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ])
        
        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_priority": by_priority,
            "overdue": overdue,
            "due_today": due_today,
            "completion_rate": (
                by_status.get("completed", 0) / total * 100
                if total > 0 else 0
            ),
        }
    
    def create_follow_up(
        self,
        contact_id: str,
        contact_name: str,
        days_from_now: int = 3,
        title: str = None,
        task_type: TaskType = TaskType.FOLLOW_UP,
        notes: str = "",
    ) -> Task:
        """Create a follow-up task for a contact."""
        due_date = datetime.utcnow() + timedelta(days=days_from_now)
        
        return self.create_task(
            title=title or f"Follow up with {contact_name}",
            task_type=task_type,
            priority=TaskPriority.MEDIUM,
            description=notes,
            due_date=due_date,
            contact_id=contact_id,
            contact_name=contact_name,
        )
    
    def get_upcoming_reminders(
        self,
        hours: int = 24,
    ) -> list[Task]:
        """Get tasks with reminders in the next N hours."""
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        
        return [
            t for t in self.tasks.values()
            if t.reminder_at and now <= t.reminder_at <= cutoff
            and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ]
    
    def bulk_update(
        self,
        task_ids: list[str],
        updates: dict,
    ) -> dict:
        """Bulk update multiple tasks."""
        updated = 0
        failed = 0
        
        for task_id in task_ids:
            result = self.update_task(task_id, updates)
            if result:
                updated += 1
            else:
                failed += 1
        
        return {
            "updated": updated,
            "failed": failed,
        }


# Singleton instance
_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """Get the task service singleton."""
    global _service
    if _service is None:
        _service = TaskService()
    return _service
