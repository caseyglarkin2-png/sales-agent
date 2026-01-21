"""
User Management Module
======================
User and team management for multi-user access.
"""

from src.users.user_service import (
    UserService,
    User,
    Team,
    UserRole,
    get_user_service,
)

__all__ = [
    "UserService",
    "User",
    "Team",
    "UserRole",
    "get_user_service",
]
