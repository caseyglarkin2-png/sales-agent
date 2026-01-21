"""
Teams Module
============
Team management and hierarchy for sales organization.
"""

from .team_service import (
    TeamService,
    Team,
    TeamMember,
    TeamRole,
    TeamType,
    get_team_service,
)

__all__ = [
    "TeamService",
    "Team",
    "TeamMember",
    "TeamRole",
    "TeamType",
    "get_team_service",
]
