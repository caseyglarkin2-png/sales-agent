"""
AI Recommendations Module
=========================
AI-powered recommendations for sales optimization.
"""

from .recommendations_service import (
    RecommendationsService,
    get_recommendations_service,
    Recommendation,
    RecommendationType,
    RecommendationCategory,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationFeedback,
)

__all__ = [
    "RecommendationsService",
    "get_recommendations_service",
    "Recommendation",
    "RecommendationType",
    "RecommendationCategory",
    "RecommendationPriority",
    "RecommendationStatus",
    "RecommendationFeedback",
]
