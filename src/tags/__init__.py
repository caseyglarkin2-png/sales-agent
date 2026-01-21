"""
Tags Module
===========
Tagging system for organizing and categorizing entities.
"""

from .tags_service import (
    TagsService,
    Tag,
    EntityTag,
    TagCategory,
    get_tags_service,
)

__all__ = [
    "TagsService",
    "Tag",
    "EntityTag",
    "TagCategory",
    "get_tags_service",
]
