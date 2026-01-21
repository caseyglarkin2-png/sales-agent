"""
Pipeline/Deals Module
=====================
Sales pipeline and deal management.
"""

from src.pipeline.deal_service import (
    DealService,
    Deal,
    DealStage,
    Pipeline,
    DealActivity,
    get_deal_service,
)

__all__ = [
    "DealService",
    "Deal",
    "DealStage",
    "Pipeline",
    "DealActivity",
    "get_deal_service",
]
