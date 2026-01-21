"""
Territories Module - Territory Management
==========================================
Manage sales territories and assignments.
"""

from .territory_service import (
    TerritoryService,
    Territory,
    TerritoryAssignment,
    TerritoryRule,
    get_territory_service,
)

__all__ = [
    "TerritoryService",
    "Territory",
    "TerritoryAssignment",
    "TerritoryRule",
    "get_territory_service",
]
