"""Campaigns package."""

from .campaign_manager import (
    CampaignManager,
    Campaign,
    CampaignStatus,
    CampaignType,
    CampaignMetrics,
    get_campaign_manager,
)

from .campaign_generator import (
    CampaignGenerator,
    CampaignSegment,
    CampaignStats,
    create_campaign_generator,
    EMAIL_TEMPLATES,
    INDUSTRY_PAIN_POINTS,
)

__all__ = [
    "CampaignManager",
    "Campaign",
    "CampaignStatus",
    "CampaignType",
    "CampaignMetrics",
    "get_campaign_manager",
    "CampaignGenerator",
    "CampaignSegment",
    "CampaignStats",
    "create_campaign_generator",
    "EMAIL_TEMPLATES",
    "INDUSTRY_PAIN_POINTS",
]
