"""Insights package."""

from .insights_engine import (
    InsightsEngine,
    Insight,
    InsightType,
    InsightPriority,
    get_insights_engine,
)

__all__ = [
    "InsightsEngine",
    "Insight",
    "InsightType",
    "InsightPriority",
    "get_insights_engine",
]
