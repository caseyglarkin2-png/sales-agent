"""Email deliverability optimization."""

from src.deliverability.deliverability_optimizer import (
    DeliverabilityOptimizer,
    DeliverabilityScore,
    SpamCheckResult,
    WarmupStatus,
    DomainHealth,
    get_deliverability_optimizer,
)

__all__ = [
    "DeliverabilityOptimizer",
    "DeliverabilityScore",
    "SpamCheckResult",
    "WarmupStatus",
    "DomainHealth",
    "get_deliverability_optimizer",
]
