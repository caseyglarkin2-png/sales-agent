"""
Roles Module - Role-Based Access Control
=========================================
Handles roles, permissions, and access control.
"""

from .role_service import (
    RoleService,
    Role,
    Permission,
    RoleAssignment,
    ResourceType,
    Action,
    get_role_service,
    AccessScope,
)

__all__ = [
    "RoleService",
    "Role",
    "Permission",
    "RoleAssignment",
    "ResourceType",
    "Action",
    "get_role_service",
    "AccessScope",
]
