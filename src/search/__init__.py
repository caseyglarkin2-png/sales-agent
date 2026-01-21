"""
Search Module
=============
Advanced search and filtering across all entities.
"""

from .search_service import (
    SearchService,
    get_search_service,
    SearchResult,
    SearchResultItem,
    SearchFilter,
    SearchFacet,
    SearchSuggestion,
    SearchIndex,
    SearchableEntity,
    SearchOperator,
)

__all__ = [
    "SearchService",
    "get_search_service",
    "SearchResult",
    "SearchResultItem",
    "SearchFilter",
    "SearchFacet",
    "SearchSuggestion",
    "SearchIndex",
    "SearchableEntity",
    "SearchOperator",
]
