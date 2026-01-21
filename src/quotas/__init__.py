"""
Quota Management Module
=======================
Sales quota management and tracking.
"""

from .quota_service import (
    QuotaService,
    get_quota_service,
    Quota,
    QuotaAssignment,
    QuotaAttainment,
    QuotaPeriod,
    QuotaType,
    QuotaStatus,
)

__all__ = [
    "QuotaService",
    "get_quota_service",
    "Quota",
    "QuotaAssignment",
    "QuotaAttainment",
    "QuotaPeriod",
    "QuotaType",
    "QuotaStatus",
]
