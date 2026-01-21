"""
Goal Tracking Module
====================
Sales goals, quotas, and progress tracking.
"""

from src.goals.goal_service import (
    GoalService,
    Goal,
    GoalType,
    GoalPeriod,
    GoalProgress,
    get_goal_service,
)

__all__ = [
    "GoalService",
    "Goal",
    "GoalType",
    "GoalPeriod",
    "GoalProgress",
    "get_goal_service",
]
