"""
Response Analytics Engine.

Tracks and analyzes email engagement metrics.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CampaignMetrics:
    """Metrics for a campaign or sequence."""
    campaign_id: str
    campaign_name: str
    
    # Counts
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    emails_replied: int = 0
    emails_bounced: int = 0
    
    # Meetings
    meetings_booked: int = 0
    
    # Calculated rates
    @property
    def open_rate(self) -> float:
        return (self.emails_opened / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def click_rate(self) -> float:
        return (self.emails_clicked / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def reply_rate(self) -> float:
        return (self.emails_replied / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def bounce_rate(self) -> float:
        return (self.emails_bounced / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    @property
    def meeting_rate(self) -> float:
        return (self.meetings_booked / self.emails_sent * 100) if self.emails_sent > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "emails_clicked": self.emails_clicked,
            "emails_replied": self.emails_replied,
            "emails_bounced": self.emails_bounced,
            "meetings_booked": self.meetings_booked,
            "open_rate": round(self.open_rate, 1),
            "click_rate": round(self.click_rate, 1),
            "reply_rate": round(self.reply_rate, 1),
            "bounce_rate": round(self.bounce_rate, 1),
            "meeting_rate": round(self.meeting_rate, 1),
        }


@dataclass 
class DailyStats:
    """Daily statistics."""
    date: str
    emails_sent: int = 0
    emails_opened: int = 0
    replies_received: int = 0
    meetings_booked: int = 0
    drafts_approved: int = 0
    drafts_rejected: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "replies_received": self.replies_received,
            "meetings_booked": self.meetings_booked,
            "drafts_approved": self.drafts_approved,
            "drafts_rejected": self.drafts_rejected,
        }


class AnalyticsEngine:
    """Tracks and analyzes engagement metrics."""
    
    def __init__(self, db=None):
        self.db = db
        
        # In-memory tracking (would be persisted in production)
        self.daily_stats: Dict[str, DailyStats] = {}
        self.campaign_metrics: Dict[str, CampaignMetrics] = {}
        self.contact_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def track_event(
        self,
        event_type: str,
        contact_email: str,
        campaign_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Track an engagement event.
        
        Args:
            event_type: Type of event (sent, opened, clicked, replied, bounced, meeting)
            contact_email: Contact email
            campaign_id: Optional campaign/sequence ID
            metadata: Additional event data
        """
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        
        # Record contact event
        self.contact_events[contact_email.lower()].append({
            "type": event_type,
            "timestamp": now.isoformat(),
            "campaign_id": campaign_id,
            "metadata": metadata or {},
        })
        
        # Update daily stats
        if date_str not in self.daily_stats:
            self.daily_stats[date_str] = DailyStats(date=date_str)
        
        stats = self.daily_stats[date_str]
        
        if event_type == "sent":
            stats.emails_sent += 1
        elif event_type == "opened":
            stats.emails_opened += 1
        elif event_type == "replied":
            stats.replies_received += 1
        elif event_type == "meeting":
            stats.meetings_booked += 1
        elif event_type == "approved":
            stats.drafts_approved += 1
        elif event_type == "rejected":
            stats.drafts_rejected += 1
        
        # Update campaign metrics
        if campaign_id:
            if campaign_id not in self.campaign_metrics:
                self.campaign_metrics[campaign_id] = CampaignMetrics(
                    campaign_id=campaign_id,
                    campaign_name=campaign_id,
                )
            
            metrics = self.campaign_metrics[campaign_id]
            
            if event_type == "sent":
                metrics.emails_sent += 1
            elif event_type == "opened":
                metrics.emails_opened += 1
            elif event_type == "clicked":
                metrics.emails_clicked += 1
            elif event_type == "replied":
                metrics.emails_replied += 1
            elif event_type == "bounced":
                metrics.emails_bounced += 1
            elif event_type == "meeting":
                metrics.meetings_booked += 1
        
        logger.info(f"Tracked {event_type} event for {contact_email}")
    
    def get_daily_stats(
        self,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get daily stats for recent days.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of daily stat objects
        """
        results = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            if date_str in self.daily_stats:
                results.append(self.daily_stats[date_str].to_dict())
            else:
                results.append(DailyStats(date=date_str).to_dict())
        
        return results
    
    def get_campaign_metrics(
        self,
        campaign_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get campaign metrics.
        
        Args:
            campaign_id: Optional specific campaign
            
        Returns:
            List of campaign metric objects
        """
        if campaign_id:
            if campaign_id in self.campaign_metrics:
                return [self.campaign_metrics[campaign_id].to_dict()]
            return []
        
        return [m.to_dict() for m in self.campaign_metrics.values()]
    
    def get_contact_timeline(
        self,
        contact_email: str,
    ) -> List[Dict[str, Any]]:
        """Get engagement timeline for a contact.
        
        Args:
            contact_email: Contact email
            
        Returns:
            List of events in chronological order
        """
        events = self.contact_events.get(contact_email.lower(), [])
        return sorted(events, key=lambda e: e.get("timestamp", ""))
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get overall summary metrics.
        
        Returns:
            Summary of all metrics
        """
        total_sent = sum(s.emails_sent for s in self.daily_stats.values())
        total_opened = sum(s.emails_opened for s in self.daily_stats.values())
        total_replied = sum(s.replies_received for s in self.daily_stats.values())
        total_meetings = sum(s.meetings_booked for s in self.daily_stats.values())
        
        return {
            "total_emails_sent": total_sent,
            "total_emails_opened": total_opened,
            "total_replies": total_replied,
            "total_meetings": total_meetings,
            "overall_open_rate": round((total_opened / total_sent * 100) if total_sent > 0 else 0, 1),
            "overall_reply_rate": round((total_replied / total_sent * 100) if total_sent > 0 else 0, 1),
            "overall_meeting_rate": round((total_meetings / total_sent * 100) if total_sent > 0 else 0, 1),
            "active_campaigns": len(self.campaign_metrics),
            "tracked_contacts": len(self.contact_events),
        }
    
    def get_top_performing_campaigns(
        self,
        limit: int = 5,
        sort_by: str = "reply_rate",
    ) -> List[Dict[str, Any]]:
        """Get top performing campaigns.
        
        Args:
            limit: Max campaigns to return
            sort_by: Metric to sort by
            
        Returns:
            List of top campaigns
        """
        campaigns = list(self.campaign_metrics.values())
        
        # Filter to campaigns with at least some activity
        campaigns = [c for c in campaigns if c.emails_sent >= 5]
        
        # Sort by metric
        if sort_by == "reply_rate":
            campaigns.sort(key=lambda c: c.reply_rate, reverse=True)
        elif sort_by == "open_rate":
            campaigns.sort(key=lambda c: c.open_rate, reverse=True)
        elif sort_by == "meeting_rate":
            campaigns.sort(key=lambda c: c.meeting_rate, reverse=True)
        
        return [c.to_dict() for c in campaigns[:limit]]


# Singleton
_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine(db=None) -> AnalyticsEngine:
    """Get singleton analytics engine."""
    global _engine
    if _engine is None:
        _engine = AnalyticsEngine(db=db)
    return _engine
