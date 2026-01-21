"""
Task Management Module
======================
Sales task management and follow-up tracking.
"""

from src.tasks.task_service import (
    TaskService,
    Task,
    TaskType,
    TaskPriority,
    TaskStatus,
    get_task_service,
)

__all__ = [
    "TaskService",
    "Task",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "get_task_service",
]
