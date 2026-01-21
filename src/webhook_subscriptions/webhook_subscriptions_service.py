"""
Webhook Subscriptions Service
=============================
Manage webhook subscriptions, event delivery, and retry logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid
import hashlib
import hmac
import json


class WebhookEventType(str, Enum):
    """Webhook event types."""
    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    LEAD_DELETED = "lead.deleted"
    LEAD_CONVERTED = "lead.converted"
    LEAD_SCORED = "lead.scored"
    
    # Contact events
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    
    # Company events
    COMPANY_CREATED = "company.created"
    COMPANY_UPDATED = "company.updated"
    COMPANY_DELETED = "company.deleted"
    
    # Deal events
    DEAL_CREATED = "deal.created"
    DEAL_UPDATED = "deal.updated"
    DEAL_DELETED = "deal.deleted"
    DEAL_STAGE_CHANGED = "deal.stage_changed"
    DEAL_WON = "deal.won"
    DEAL_LOST = "deal.lost"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_OVERDUE = "task.overdue"
    
    # Meeting events
    MEETING_SCHEDULED = "meeting.scheduled"
    MEETING_CANCELLED = "meeting.cancelled"
    MEETING_COMPLETED = "meeting.completed"
    
    # Email events
    EMAIL_SENT = "email.sent"
    EMAIL_OPENED = "email.opened"
    EMAIL_CLICKED = "email.clicked"
    EMAIL_REPLIED = "email.replied"
    EMAIL_BOUNCED = "email.bounced"
    
    # Call events
    CALL_STARTED = "call.started"
    CALL_ENDED = "call.ended"
    CALL_RECORDED = "call.recorded"
    
    # Campaign events
    CAMPAIGN_STARTED = "campaign.started"
    CAMPAIGN_PAUSED = "campaign.paused"
    CAMPAIGN_COMPLETED = "campaign.completed"
    
    # Sequence events
    SEQUENCE_ENROLLED = "sequence.enrolled"
    SEQUENCE_COMPLETED = "sequence.completed"
    SEQUENCE_UNENROLLED = "sequence.unenrolled"
    
    # Quote events
    QUOTE_CREATED = "quote.created"
    QUOTE_SENT = "quote.sent"
    QUOTE_ACCEPTED = "quote.accepted"
    QUOTE_REJECTED = "quote.rejected"
    
    # Contract events
    CONTRACT_CREATED = "contract.created"
    CONTRACT_SENT = "contract.sent"
    CONTRACT_SIGNED = "contract.signed"
    
    # Invoice events
    INVOICE_CREATED = "invoice.created"
    INVOICE_SENT = "invoice.sent"
    INVOICE_PAID = "invoice.paid"
    INVOICE_OVERDUE = "invoice.overdue"
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    
    # System events
    SYNC_COMPLETED = "sync.completed"
    IMPORT_COMPLETED = "import.completed"
    EXPORT_COMPLETED = "export.completed"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    SUSPENDED = "suspended"  # Too many failures


class DeliveryStatus(str, Enum):
    """Delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookSubscription:
    """Webhook subscription."""
    id: str
    name: str
    url: str
    events: list[WebhookEventType]
    secret: str
    org_id: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    headers: dict[str, str] = field(default_factory=dict)
    retry_count: int = 3
    timeout_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    last_triggered: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0


@dataclass
class WebhookEvent:
    """Webhook event to be delivered."""
    id: str
    event_type: WebhookEventType
    payload: dict[str, Any]
    org_id: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt."""
    id: str
    subscription_id: str
    event_id: str
    event_type: WebhookEventType
    url: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    request_body: Optional[str] = None
    request_headers: dict[str, str] = field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_time_ms: Optional[float] = None
    attempt_number: int = 1
    next_retry_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WebhookSubscriptionsService:
    """
    Webhook Subscriptions service.
    
    Manages webhook subscriptions, event delivery, signatures, and retries.
    """
    
    def __init__(self):
        """Initialize webhook subscriptions service."""
        self.subscriptions: dict[str, WebhookSubscription] = {}
        self.events: dict[str, WebhookEvent] = {}
        self.deliveries: dict[str, WebhookDelivery] = {}
        
        # Retry backoff schedule (in seconds)
        self.retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr
    
    async def create_subscription(
        self,
        name: str,
        url: str,
        events: list[WebhookEventType],
        org_id: str,
        headers: Optional[dict[str, str]] = None,
        retry_count: int = 3,
        timeout_seconds: int = 30,
        created_by: Optional[str] = None,
    ) -> WebhookSubscription:
        """Create a new webhook subscription."""
        # Generate secret for signature verification
        secret = self._generate_secret()
        
        subscription = WebhookSubscription(
            id=str(uuid.uuid4()),
            name=name,
            url=url,
            events=events,
            secret=secret,
            org_id=org_id,
            headers=headers or {},
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            created_by=created_by,
        )
        
        self.subscriptions[subscription.id] = subscription
        return subscription
    
    def _generate_secret(self) -> str:
        """Generate a webhook secret."""
        return f"whsec_{uuid.uuid4().hex}"
    
    async def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get a subscription by ID."""
        return self.subscriptions.get(subscription_id)
    
    async def list_subscriptions(
        self,
        org_id: str,
        status: Optional[SubscriptionStatus] = None,
        event_type: Optional[WebhookEventType] = None,
    ) -> list[WebhookSubscription]:
        """List subscriptions for an organization."""
        subs = [s for s in self.subscriptions.values() if s.org_id == org_id]
        
        if status:
            subs = [s for s in subs if s.status == status]
        
        if event_type:
            subs = [s for s in subs if event_type in s.events]
        
        return subs
    
    async def update_subscription(
        self,
        subscription_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        events: Optional[list[WebhookEventType]] = None,
        status: Optional[SubscriptionStatus] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[WebhookSubscription]:
        """Update a subscription."""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return None
        
        if name:
            sub.name = name
        if url:
            sub.url = url
        if events is not None:
            sub.events = events
        if status:
            sub.status = status
        if headers is not None:
            sub.headers = headers
        
        sub.updated_at = datetime.utcnow()
        return sub
    
    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False
    
    async def rotate_secret(self, subscription_id: str) -> Optional[str]:
        """Rotate a subscription's secret."""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return None
        
        sub.secret = self._generate_secret()
        sub.updated_at = datetime.utcnow()
        return sub.secret
    
    async def pause_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Pause a subscription."""
        return await self.update_subscription(
            subscription_id,
            status=SubscriptionStatus.PAUSED,
        )
    
    async def resume_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Resume a paused subscription."""
        sub = self.subscriptions.get(subscription_id)
        if sub:
            sub.status = SubscriptionStatus.ACTIVE
            sub.consecutive_failures = 0
            sub.updated_at = datetime.utcnow()
        return sub
    
    async def trigger_event(
        self,
        event_type: WebhookEventType,
        payload: dict[str, Any],
        org_id: str,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> WebhookEvent:
        """Trigger a webhook event."""
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            org_id=org_id,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        self.events[event.id] = event
        
        # Find matching subscriptions
        subscriptions = await self._find_matching_subscriptions(org_id, event_type)
        
        # Create deliveries for each subscription
        for sub in subscriptions:
            await self._create_delivery(sub, event)
        
        return event
    
    async def _find_matching_subscriptions(
        self,
        org_id: str,
        event_type: WebhookEventType,
    ) -> list[WebhookSubscription]:
        """Find subscriptions that match an event."""
        return [
            s for s in self.subscriptions.values()
            if s.org_id == org_id
            and s.status == SubscriptionStatus.ACTIVE
            and event_type in s.events
        ]
    
    async def _create_delivery(
        self,
        subscription: WebhookSubscription,
        event: WebhookEvent,
    ) -> WebhookDelivery:
        """Create a delivery for a subscription."""
        # Build request body
        body = {
            "id": event.id,
            "event": event.event_type.value,
            "data": event.payload,
            "occurred_at": event.occurred_at.isoformat(),
        }
        
        # Build headers
        timestamp = datetime.utcnow().isoformat()
        signature = self._compute_signature(subscription.secret, json.dumps(body))
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Id": event.id,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": signature,
            **subscription.headers,
        }
        
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            subscription_id=subscription.id,
            event_id=event.id,
            event_type=event.event_type,
            url=subscription.url,
            request_body=json.dumps(body),
            request_headers=headers,
        )
        
        self.deliveries[delivery.id] = delivery
        
        # In production, this would be queued for async delivery
        # For demo, simulate immediate delivery
        await self._attempt_delivery(delivery, subscription)
        
        return delivery
    
    def _compute_signature(self, secret: str, body: str) -> str:
        """Compute webhook signature."""
        return "sha256=" + hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def _attempt_delivery(
        self,
        delivery: WebhookDelivery,
        subscription: WebhookSubscription,
    ):
        """Attempt to deliver a webhook (simulated)."""
        import random
        import time
        
        start_time = time.time()
        
        # Simulate delivery (90% success rate)
        success = random.random() > 0.1
        
        delivery.response_time_ms = (time.time() - start_time) * 1000 + random.uniform(50, 200)
        
        if success:
            delivery.status = DeliveryStatus.DELIVERED
            delivery.response_status = 200
            delivery.response_body = '{"received": true}'
            delivery.delivered_at = datetime.utcnow()
            
            # Update subscription stats
            subscription.success_count += 1
            subscription.consecutive_failures = 0
            subscription.last_triggered = datetime.utcnow()
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.response_status = random.choice([500, 502, 503, 504])
            delivery.error_message = "Connection timeout" if random.random() > 0.5 else "Server error"
            
            # Update subscription stats
            subscription.failure_count += 1
            subscription.consecutive_failures += 1
            
            # Schedule retry if attempts remaining
            if delivery.attempt_number < subscription.retry_count:
                delivery.status = DeliveryStatus.RETRYING
                delay = self.retry_delays[min(delivery.attempt_number - 1, len(self.retry_delays) - 1)]
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            
            # Suspend subscription if too many consecutive failures
            if subscription.consecutive_failures >= 10:
                subscription.status = SubscriptionStatus.SUSPENDED
    
    async def retry_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Retry a failed delivery."""
        delivery = self.deliveries.get(delivery_id)
        if not delivery or delivery.status not in [DeliveryStatus.FAILED, DeliveryStatus.RETRYING]:
            return None
        
        subscription = self.subscriptions.get(delivery.subscription_id)
        if not subscription:
            return None
        
        # Create new delivery attempt
        delivery.attempt_number += 1
        delivery.status = DeliveryStatus.PENDING
        
        await self._attempt_delivery(delivery, subscription)
        return delivery
    
    async def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a delivery by ID."""
        return self.deliveries.get(delivery_id)
    
    async def list_deliveries(
        self,
        subscription_id: Optional[str] = None,
        event_id: Optional[str] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """List webhook deliveries."""
        deliveries = list(self.deliveries.values())
        
        if subscription_id:
            deliveries = [d for d in deliveries if d.subscription_id == subscription_id]
        
        if event_id:
            deliveries = [d for d in deliveries if d.event_id == event_id]
        
        if status:
            deliveries = [d for d in deliveries if d.status == status]
        
        # Sort by created_at descending
        deliveries.sort(key=lambda x: x.created_at, reverse=True)
        
        return deliveries[:limit]
    
    async def get_pending_retries(self) -> list[WebhookDelivery]:
        """Get deliveries pending retry."""
        now = datetime.utcnow()
        return [
            d for d in self.deliveries.values()
            if d.status == DeliveryStatus.RETRYING
            and d.next_retry_at
            and d.next_retry_at <= now
        ]
    
    async def get_event(self, event_id: str) -> Optional[WebhookEvent]:
        """Get an event by ID."""
        return self.events.get(event_id)
    
    async def list_events(
        self,
        org_id: str,
        event_type: Optional[WebhookEventType] = None,
        limit: int = 100,
    ) -> list[WebhookEvent]:
        """List webhook events."""
        events = [e for e in self.events.values() if e.org_id == org_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Sort by occurred_at descending
        events.sort(key=lambda x: x.occurred_at, reverse=True)
        
        return events[:limit]
    
    async def test_subscription(
        self,
        subscription_id: str,
    ) -> Optional[WebhookDelivery]:
        """Send a test webhook to a subscription."""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return None
        
        # Create test event
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type=WebhookEventType.SYNC_COMPLETED,  # Use a benign event type
            payload={
                "test": True,
                "message": "This is a test webhook",
                "timestamp": datetime.utcnow().isoformat(),
            },
            org_id=sub.org_id,
        )
        self.events[event.id] = event
        
        # Create and attempt delivery
        return await self._create_delivery(sub, event)
    
    async def get_subscription_stats(
        self,
        subscription_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get statistics for a subscription."""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return None
        
        deliveries = [d for d in self.deliveries.values() if d.subscription_id == subscription_id]
        
        successful = len([d for d in deliveries if d.status == DeliveryStatus.DELIVERED])
        failed = len([d for d in deliveries if d.status == DeliveryStatus.FAILED])
        pending = len([d for d in deliveries if d.status in [DeliveryStatus.PENDING, DeliveryStatus.RETRYING]])
        
        avg_response_time = 0.0
        delivered = [d for d in deliveries if d.response_time_ms]
        if delivered:
            avg_response_time = sum(d.response_time_ms for d in delivered) / len(delivered)
        
        return {
            "subscription_id": subscription_id,
            "total_deliveries": len(deliveries),
            "successful": successful,
            "failed": failed,
            "pending": pending,
            "success_rate": successful / len(deliveries) * 100 if deliveries else 0,
            "avg_response_time_ms": avg_response_time,
            "consecutive_failures": sub.consecutive_failures,
            "last_triggered": sub.last_triggered.isoformat() if sub.last_triggered else None,
        }
    
    async def list_event_types(self) -> list[dict[str, str]]:
        """List all available event types."""
        return [
            {"value": e.value, "name": e.name, "category": e.value.split(".")[0]}
            for e in WebhookEventType
        ]


# Singleton instance
_webhook_subscriptions_service: Optional[WebhookSubscriptionsService] = None


def get_webhook_subscriptions_service() -> WebhookSubscriptionsService:
    """Get or create webhook subscriptions service singleton."""
    global _webhook_subscriptions_service
    if _webhook_subscriptions_service is None:
        _webhook_subscriptions_service = WebhookSubscriptionsService()
    return _webhook_subscriptions_service
