"""
Email Tracking Service - Email Engagement Tracking
==================================================
Handles email opens, clicks, replies, and engagement analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid
import hashlib


class EmailStatus(str, Enum):
    """Email delivery status."""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"


class BounceType(str, Enum):
    """Bounce type."""
    HARD = "hard"
    SOFT = "soft"
    TEMPORARY = "temporary"


@dataclass
class EmailOpen:
    """An email open event."""
    id: str
    email_id: str
    
    # Tracking
    opened_at: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Geolocation (from IP)
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    
    # Device info
    device_type: Optional[str] = None  # desktop, mobile, tablet
    os: Optional[str] = None
    browser: Optional[str] = None
    email_client: Optional[str] = None


@dataclass
class EmailClick:
    """An email click event."""
    id: str
    email_id: str
    
    # Link info
    url: str
    link_id: Optional[str] = None
    link_text: Optional[str] = None
    
    # Tracking
    clicked_at: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Device info
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None


@dataclass
class EmailReply:
    """An email reply event."""
    id: str
    email_id: str
    
    # Reply info
    subject: Optional[str] = None
    snippet: Optional[str] = None  # First part of reply
    
    # Classification
    is_auto_reply: bool = False
    sentiment: Optional[str] = None  # positive, neutral, negative
    
    replied_at: datetime = field(default_factory=datetime.utcnow)
    message_id: Optional[str] = None


@dataclass
class EmailBounce:
    """An email bounce event."""
    id: str
    email_id: str
    
    bounce_type: BounceType = BounceType.SOFT
    reason: Optional[str] = None
    diagnostic_code: Optional[str] = None
    
    bounced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EmailTrack:
    """Email tracking record."""
    id: str
    
    # Email info
    message_id: str
    subject: str
    recipient_email: str
    
    # Related entities
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    sequence_id: Optional[str] = None
    campaign_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Status
    status: EmailStatus = EmailStatus.QUEUED
    
    # Tracking tokens
    open_tracking_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    click_tracking_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Events
    opens: list[EmailOpen] = field(default_factory=list)
    clicks: list[EmailClick] = field(default_factory=list)
    replies: list[EmailReply] = field(default_factory=list)
    bounce: Optional[EmailBounce] = None
    
    # Timestamps
    queued_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    first_opened_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    first_clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    
    # Stats
    open_count: int = 0
    click_count: int = 0
    unique_clicks: int = 0
    
    # Links in email
    tracked_links: list[dict[str, str]] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


class EmailTrackingService:
    """Service for email tracking."""
    
    def __init__(self):
        self.emails: dict[str, EmailTrack] = {}
        self.open_tracking_map: dict[str, str] = {}  # tracking_id -> email_id
        self.click_tracking_map: dict[str, str] = {}  # tracking_id -> email_id
    
    # Email tracking CRUD
    async def create_tracking(
        self,
        message_id: str,
        subject: str,
        recipient_email: str,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        sequence_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tracked_links: Optional[list[dict[str, str]]] = None
    ) -> EmailTrack:
        """Create email tracking record."""
        email = EmailTrack(
            id=str(uuid.uuid4()),
            message_id=message_id,
            subject=subject,
            recipient_email=recipient_email,
            contact_id=contact_id,
            account_id=account_id,
            sequence_id=sequence_id,
            campaign_id=campaign_id,
            user_id=user_id,
            queued_at=datetime.utcnow(),
            tracked_links=tracked_links or [],
        )
        
        self.emails[email.id] = email
        self.open_tracking_map[email.open_tracking_id] = email.id
        self.click_tracking_map[email.click_tracking_id] = email.id
        
        return email
    
    async def get_tracking(self, email_id: str) -> Optional[EmailTrack]:
        """Get email tracking by ID."""
        return self.emails.get(email_id)
    
    async def get_by_message_id(self, message_id: str) -> Optional[EmailTrack]:
        """Get tracking by message ID."""
        for email in self.emails.values():
            if email.message_id == message_id:
                return email
        return None
    
    async def list_tracking(
        self,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        sequence_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[EmailStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[EmailTrack], int]:
        """List email tracking records."""
        emails = list(self.emails.values())
        
        if contact_id:
            emails = [e for e in emails if e.contact_id == contact_id]
        if account_id:
            emails = [e for e in emails if e.account_id == account_id]
        if sequence_id:
            emails = [e for e in emails if e.sequence_id == sequence_id]
        if campaign_id:
            emails = [e for e in emails if e.campaign_id == campaign_id]
        if user_id:
            emails = [e for e in emails if e.user_id == user_id]
        if status:
            emails = [e for e in emails if e.status == status]
        if from_date:
            emails = [e for e in emails if e.created_at >= from_date]
        if to_date:
            emails = [e for e in emails if e.created_at <= to_date]
        
        emails.sort(key=lambda e: e.created_at, reverse=True)
        total = len(emails)
        
        return emails[offset:offset + limit], total
    
    # Status updates
    async def mark_sent(self, email_id: str) -> Optional[EmailTrack]:
        """Mark email as sent."""
        email = self.emails.get(email_id)
        if not email:
            return None
        
        email.status = EmailStatus.SENT
        email.sent_at = datetime.utcnow()
        
        return email
    
    async def mark_delivered(self, email_id: str) -> Optional[EmailTrack]:
        """Mark email as delivered."""
        email = self.emails.get(email_id)
        if not email:
            return None
        
        email.status = EmailStatus.DELIVERED
        email.delivered_at = datetime.utcnow()
        
        return email
    
    # Open tracking
    async def record_open(
        self,
        tracking_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[EmailOpen]:
        """Record an email open."""
        email_id = self.open_tracking_map.get(tracking_id)
        if not email_id:
            return None
        
        email = self.emails.get(email_id)
        if not email:
            return None
        
        # Parse user agent for device info
        device_type = self._detect_device(user_agent)
        
        open_event = EmailOpen(
            id=str(uuid.uuid4()),
            email_id=email_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
        )
        
        email.opens.append(open_event)
        email.open_count += 1
        
        if not email.first_opened_at:
            email.first_opened_at = open_event.opened_at
            email.status = EmailStatus.OPENED
        
        email.last_opened_at = open_event.opened_at
        
        return open_event
    
    async def record_open_by_email_id(
        self,
        email_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[EmailOpen]:
        """Record an email open by email ID."""
        email = self.emails.get(email_id)
        if not email:
            return None
        
        return await self.record_open(
            email.open_tracking_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    # Click tracking
    async def record_click(
        self,
        tracking_id: str,
        url: str,
        link_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[EmailClick]:
        """Record an email click."""
        email_id = self.click_tracking_map.get(tracking_id)
        if not email_id:
            return None
        
        email = self.emails.get(email_id)
        if not email:
            return None
        
        device_type = self._detect_device(user_agent)
        
        click_event = EmailClick(
            id=str(uuid.uuid4()),
            email_id=email_id,
            url=url,
            link_id=link_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
        )
        
        email.clicks.append(click_event)
        email.click_count += 1
        
        # Track unique clicks by URL
        unique_urls = set(c.url for c in email.clicks)
        email.unique_clicks = len(unique_urls)
        
        if not email.first_clicked_at:
            email.first_clicked_at = click_event.clicked_at
            email.status = EmailStatus.CLICKED
        
        return click_event
    
    # Reply tracking
    async def record_reply(
        self,
        email_id: str,
        subject: Optional[str] = None,
        snippet: Optional[str] = None,
        is_auto_reply: bool = False,
        sentiment: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Optional[EmailReply]:
        """Record an email reply."""
        email = self.emails.get(email_id)
        if not email:
            return None
        
        reply_event = EmailReply(
            id=str(uuid.uuid4()),
            email_id=email_id,
            subject=subject,
            snippet=snippet,
            is_auto_reply=is_auto_reply,
            sentiment=sentiment,
            message_id=message_id,
        )
        
        email.replies.append(reply_event)
        
        if not email.replied_at and not is_auto_reply:
            email.replied_at = reply_event.replied_at
            email.status = EmailStatus.REPLIED
        
        return reply_event
    
    # Bounce tracking
    async def record_bounce(
        self,
        email_id: str,
        bounce_type: BounceType = BounceType.SOFT,
        reason: Optional[str] = None,
        diagnostic_code: Optional[str] = None
    ) -> Optional[EmailBounce]:
        """Record an email bounce."""
        email = self.emails.get(email_id)
        if not email:
            return None
        
        bounce = EmailBounce(
            id=str(uuid.uuid4()),
            email_id=email_id,
            bounce_type=bounce_type,
            reason=reason,
            diagnostic_code=diagnostic_code,
        )
        
        email.bounce = bounce
        email.bounced_at = bounce.bounced_at
        email.status = EmailStatus.BOUNCED
        
        return bounce
    
    # Unsubscribe
    async def record_unsubscribe(self, email_id: str) -> bool:
        """Record an unsubscribe."""
        email = self.emails.get(email_id)
        if not email:
            return False
        
        email.status = EmailStatus.UNSUBSCRIBED
        return True
    
    # Complaint
    async def record_complaint(self, email_id: str) -> bool:
        """Record a spam complaint."""
        email = self.emails.get(email_id)
        if not email:
            return False
        
        email.status = EmailStatus.COMPLAINED
        return True
    
    # Analytics
    async def get_email_stats(
        self,
        user_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        sequence_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get email statistics."""
        emails, _ = await self.list_tracking(
            user_id=user_id,
            campaign_id=campaign_id,
            sequence_id=sequence_id,
            from_date=from_date,
            to_date=to_date,
            limit=100000
        )
        
        total = len(emails)
        if total == 0:
            return {
                "total_sent": 0,
                "delivered": 0,
                "opened": 0,
                "clicked": 0,
                "replied": 0,
                "bounced": 0,
                "open_rate": 0,
                "click_rate": 0,
                "reply_rate": 0,
                "bounce_rate": 0,
            }
        
        delivered = len([e for e in emails if e.status not in [EmailStatus.QUEUED, EmailStatus.BOUNCED]])
        opened = len([e for e in emails if e.open_count > 0])
        clicked = len([e for e in emails if e.click_count > 0])
        replied = len([e for e in emails if e.replied_at])
        bounced = len([e for e in emails if e.status == EmailStatus.BOUNCED])
        
        return {
            "total_sent": total,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "replied": replied,
            "bounced": bounced,
            "open_rate": (opened / delivered * 100) if delivered > 0 else 0,
            "click_rate": (clicked / opened * 100) if opened > 0 else 0,
            "reply_rate": (replied / delivered * 100) if delivered > 0 else 0,
            "bounce_rate": (bounced / total * 100) if total > 0 else 0,
            "total_opens": sum(e.open_count for e in emails),
            "total_clicks": sum(e.click_count for e in emails),
        }
    
    async def get_link_performance(
        self,
        campaign_id: Optional[str] = None,
        sequence_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get link click performance."""
        emails, _ = await self.list_tracking(
            campaign_id=campaign_id,
            sequence_id=sequence_id,
            limit=100000
        )
        
        link_stats: dict[str, dict[str, Any]] = {}
        
        for email in emails:
            for click in email.clicks:
                url = click.url
                if url not in link_stats:
                    link_stats[url] = {
                        "url": url,
                        "clicks": 0,
                        "unique_clickers": set(),
                    }
                
                link_stats[url]["clicks"] += 1
                if email.contact_id:
                    link_stats[url]["unique_clickers"].add(email.contact_id)
        
        return [
            {
                "url": stats["url"],
                "clicks": stats["clicks"],
                "unique_clickers": len(stats["unique_clickers"]),
            }
            for stats in sorted(link_stats.values(), key=lambda x: x["clicks"], reverse=True)
        ]
    
    async def get_daily_stats(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get daily email stats."""
        from_date = datetime.utcnow() - timedelta(days=days)
        
        emails, _ = await self.list_tracking(
            user_id=user_id,
            from_date=from_date,
            limit=100000
        )
        
        daily: dict[str, dict[str, int]] = {}
        
        for i in range(days):
            date = (from_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily[date] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}
        
        for email in emails:
            date = email.created_at.strftime("%Y-%m-%d")
            if date in daily:
                daily[date]["sent"] += 1
                if email.open_count > 0:
                    daily[date]["opened"] += 1
                if email.click_count > 0:
                    daily[date]["clicked"] += 1
                if email.replied_at:
                    daily[date]["replied"] += 1
        
        return [
            {"date": date, **stats}
            for date, stats in sorted(daily.items())
        ]
    
    async def get_device_breakdown(
        self,
        campaign_id: Optional[str] = None
    ) -> dict[str, int]:
        """Get device type breakdown for opens."""
        emails, _ = await self.list_tracking(
            campaign_id=campaign_id,
            limit=100000
        )
        
        devices: dict[str, int] = {}
        
        for email in emails:
            for open_event in email.opens:
                device = open_event.device_type or "unknown"
                devices[device] = devices.get(device, 0) + 1
        
        return devices
    
    def _detect_device(self, user_agent: Optional[str]) -> Optional[str]:
        """Detect device type from user agent."""
        if not user_agent:
            return None
        
        ua_lower = user_agent.lower()
        
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            return "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            return "tablet"
        else:
            return "desktop"
    
    # URL generation helpers
    def generate_tracking_pixel_url(self, email_id: str, base_url: str) -> str:
        """Generate tracking pixel URL."""
        email = self.emails.get(email_id)
        if not email:
            return ""
        
        return f"{base_url}/track/open/{email.open_tracking_id}"
    
    def generate_tracked_url(
        self,
        email_id: str,
        original_url: str,
        base_url: str,
        link_id: Optional[str] = None
    ) -> str:
        """Generate tracked URL."""
        email = self.emails.get(email_id)
        if not email:
            return original_url
        
        # Create a unique link tracking ID
        link_hash = hashlib.md5(f"{email.click_tracking_id}:{original_url}".encode()).hexdigest()[:12]
        
        return f"{base_url}/track/click/{email.click_tracking_id}/{link_hash}?url={original_url}"


# Singleton instance
_email_tracking_service: Optional[EmailTrackingService] = None


def get_email_tracking_service() -> EmailTrackingService:
    """Get email tracking service singleton."""
    global _email_tracking_service
    if _email_tracking_service is None:
        _email_tracking_service = EmailTrackingService()
    return _email_tracking_service
