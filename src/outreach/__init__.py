"""Outreach package."""

from .linkedin_manager import (
    LinkedInManager,
    LinkedInAction,
    LinkedInActionType,
    ActionStatus,
    get_linkedin_manager,
)

__all__ = [
    "LinkedInManager",
    "LinkedInAction",
    "LinkedInActionType",
    "ActionStatus",
    "get_linkedin_manager",
]
