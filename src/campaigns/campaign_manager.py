"""
Campaign Manager.

Manages multi-touch outreach campaigns with tracking and reporting.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignType(Enum):
    COLD_OUTREACH = "cold_outreach"
    EVENT_PROMOTION = "event_promotion"
    CONTENT_SYNDICATION = "content_syndication"
    ACCOUNT_BASED = "account_based"
    REENGAGEMENT = "reengagement"
    PRODUCT_LAUNCH = "product_launch"


@dataclass
class CampaignMetrics:
    """Campaign performance metrics."""
    total_contacts: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    emails_replied: int = 0
    meetings_booked: int = 0
    opportunities_created: int = 0
    pipeline_value: float = 0.0
    
    @property
    def open_rate(self) -> float:
        return (self.emails_opened / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def reply_rate(self) -> float:
        return (self.emails_replied / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def meeting_rate(self) -> float:
        return (self.meetings_booked / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_contacts": self.total_contacts,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "emails_clicked": self.emails_clicked,
            "emails_replied": self.emails_replied,
            "meetings_booked": self.meetings_booked,
            "opportunities_created": self.opportunities_created,
            "pipeline_value": self.pipeline_value,
            "open_rate": round(self.open_rate, 1),
            "reply_rate": round(self.reply_rate, 1),
            "meeting_rate": round(self.meeting_rate, 1),
        }


@dataclass
class Campaign:
    """Marketing/Sales campaign."""
    id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus
    
    # Targeting
    target_personas: List[str]
    target_industries: Optional[List[str]] = None
    target_companies: Optional[List[str]] = None  # For ABM
    
    # Content
    sequence_id: Optional[str] = None  # Link to sequence
    template_ids: List[str] = None
    
    # Schedule
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Metadata
    description: Optional[str] = None
    owner: Optional[str] = None
    tags: List[str] = None
    
    # Tracking
    created_at: datetime = None
    updated_at: datetime = None
    metrics: CampaignMetrics = None
    
    # Contacts
    contact_emails: List[str] = None
    
    def __post_init__(self):
        if self.template_ids is None:
            self.template_ids = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metrics is None:
            self.metrics = CampaignMetrics()
        if self.contact_emails is None:
            self.contact_emails = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "campaign_type": self.campaign_type.value,
            "status": self.status.value,
            "target_personas": self.target_personas,
            "target_industries": self.target_industries,
            "target_companies": self.target_companies,
            "sequence_id": self.sequence_id,
            "template_ids": self.template_ids,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "description": self.description,
            "owner": self.owner,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metrics": self.metrics.to_dict(),
            "contact_count": len(self.contact_emails),
        }


class CampaignManager:
    """Manages outreach campaigns."""
    
    def __init__(self):
        self.campaigns: Dict[str, Campaign] = {}
    
    def create_campaign(
        self,
        name: str,
        campaign_type: CampaignType,
        target_personas: List[str],
        target_industries: Optional[List[str]] = None,
        target_companies: Optional[List[str]] = None,
        sequence_id: Optional[str] = None,
        template_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        description: Optional[str] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Campaign:
        """Create a new campaign.
        
        Args:
            name: Campaign name
            campaign_type: Type of campaign
            target_personas: Target personas
            target_industries: Target industries
            target_companies: Target companies (for ABM)
            sequence_id: Associated sequence
            template_ids: Template IDs to use
            start_date: Campaign start date
            end_date: Campaign end date
            description: Campaign description
            owner: Campaign owner
            tags: Campaign tags
            
        Returns:
            Created campaign
        """
        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
        
        campaign = Campaign(
            id=campaign_id,
            name=name,
            campaign_type=campaign_type,
            status=CampaignStatus.DRAFT,
            target_personas=target_personas,
            target_industries=target_industries,
            target_companies=target_companies,
            sequence_id=sequence_id,
            template_ids=template_ids or [],
            start_date=start_date,
            end_date=end_date,
            description=description,
            owner=owner,
            tags=tags or [],
        )
        
        self.campaigns[campaign_id] = campaign
        logger.info(f"Created campaign: {name} ({campaign_type.value})")
        
        return campaign
    
    def add_contacts(
        self,
        campaign_id: str,
        contacts: List[str],
    ) -> int:
        """Add contacts to a campaign.
        
        Args:
            campaign_id: Campaign ID
            contacts: List of email addresses
            
        Returns:
            Number of contacts added
        """
        if campaign_id not in self.campaigns:
            return 0
        
        campaign = self.campaigns[campaign_id]
        existing = set(campaign.contact_emails)
        
        added = 0
        for email in contacts:
            if email not in existing:
                campaign.contact_emails.append(email)
                added += 1
        
        campaign.metrics.total_contacts = len(campaign.contact_emails)
        campaign.updated_at = datetime.utcnow()
        
        logger.info(f"Added {added} contacts to campaign {campaign_id}")
        return added
    
    def start_campaign(self, campaign_id: str) -> bool:
        """Start a campaign."""
        if campaign_id not in self.campaigns:
            return False
        
        campaign = self.campaigns[campaign_id]
        
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
            return False
        
        campaign.status = CampaignStatus.ACTIVE
        campaign.start_date = campaign.start_date or datetime.utcnow()
        campaign.updated_at = datetime.utcnow()
        
        logger.info(f"Started campaign: {campaign.name}")
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        if campaign_id not in self.campaigns:
            return False
        
        campaign = self.campaigns[campaign_id]
        
        if campaign.status != CampaignStatus.ACTIVE:
            return False
        
        campaign.status = CampaignStatus.PAUSED
        campaign.updated_at = datetime.utcnow()
        
        return True
    
    def complete_campaign(self, campaign_id: str) -> bool:
        """Mark campaign as completed."""
        if campaign_id not in self.campaigns:
            return False
        
        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.COMPLETED
        campaign.end_date = datetime.utcnow()
        campaign.updated_at = datetime.utcnow()
        
        return True
    
    def record_send(self, campaign_id: str, count: int = 1):
        """Record emails sent."""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].metrics.emails_sent += count
    
    def record_open(self, campaign_id: str, count: int = 1):
        """Record email opens."""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].metrics.emails_opened += count
    
    def record_click(self, campaign_id: str, count: int = 1):
        """Record link clicks."""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].metrics.emails_clicked += count
    
    def record_reply(self, campaign_id: str, count: int = 1):
        """Record replies."""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].metrics.emails_replied += count
    
    def record_meeting(self, campaign_id: str, count: int = 1):
        """Record meetings booked."""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].metrics.meetings_booked += count
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign details."""
        campaign = self.campaigns.get(campaign_id)
        return campaign.to_dict() if campaign else None
    
    def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List campaigns with optional filters."""
        campaigns = list(self.campaigns.values())
        
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        
        if campaign_type:
            campaigns = [c for c in campaigns if c.campaign_type == campaign_type]
        
        return [
            c.to_dict() for c in 
            sorted(campaigns, key=lambda x: x.created_at, reverse=True)[:limit]
        ]
    
    def get_active_campaigns(self) -> List[Dict[str, Any]]:
        """Get all active campaigns."""
        return self.list_campaigns(status=CampaignStatus.ACTIVE)
    
    def get_campaign_performance(self) -> Dict[str, Any]:
        """Get aggregate performance across all campaigns."""
        totals = CampaignMetrics()
        
        for campaign in self.campaigns.values():
            totals.total_contacts += campaign.metrics.total_contacts
            totals.emails_sent += campaign.metrics.emails_sent
            totals.emails_opened += campaign.metrics.emails_opened
            totals.emails_clicked += campaign.metrics.emails_clicked
            totals.emails_replied += campaign.metrics.emails_replied
            totals.meetings_booked += campaign.metrics.meetings_booked
            totals.opportunities_created += campaign.metrics.opportunities_created
            totals.pipeline_value += campaign.metrics.pipeline_value
        
        return {
            "total_campaigns": len(self.campaigns),
            "active_campaigns": sum(1 for c in self.campaigns.values() if c.status == CampaignStatus.ACTIVE),
            "metrics": totals.to_dict(),
        }


# Singleton
_manager: Optional[CampaignManager] = None


def get_campaign_manager() -> CampaignManager:
    """Get singleton campaign manager."""
    global _manager
    if _manager is None:
        _manager = CampaignManager()
    return _manager
