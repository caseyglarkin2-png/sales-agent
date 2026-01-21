"""Dashboard package."""

from .aggregator import (
    DashboardAggregator,
    DashboardMetrics,
    get_dashboard_aggregator,
)

__all__ = [
    "DashboardAggregator",
    "DashboardMetrics",
    "get_dashboard_aggregator",
]
