"""
Webhook Service - Outbound Webhook Management
==============================================
Register webhooks and deliver events to external endpoints.
"""

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of webhook events."""
    # Contact events
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    CONTACT_MERGED = "contact.merged"
    
    # Company events
    COMPANY_CREATED = "company.created"
    COMPANY_UPDATED = "company.updated"
    COMPANY_DELETED = "company.deleted"
    
    # Deal events
    DEAL_CREATED = "deal.created"
    DEAL_UPDATED = "deal.updated"
    DEAL_STAGE_CHANGED = "deal.stage_changed"
    DEAL_WON = "deal.won"
    DEAL_LOST = "deal.lost"
    DEAL_DELETED = "deal.deleted"
    
    # Email events
    EMAIL_SENT = "email.sent"
    EMAIL_DELIVERED = "email.delivered"
    EMAIL_OPENED = "email.opened"
    EMAIL_CLICKED = "email.clicked"
    EMAIL_BOUNCED = "email.bounced"
    EMAIL_REPLIED = "email.replied"
    EMAIL_UNSUBSCRIBED = "email.unsubscribed"
    
    # Sequence events
    SEQUENCE_STARTED = "sequence.started"
    SEQUENCE_COMPLETED = "sequence.completed"
    SEQUENCE_PAUSED = "sequence.paused"
    SEQUENCE_STEP_EXECUTED = "sequence.step_executed"
    
    # Campaign events
    CAMPAIGN_LAUNCHED = "campaign.launched"
    CAMPAIGN_COMPLETED = "campaign.completed"
    
    # Meeting events
    MEETING_SCHEDULED = "meeting.scheduled"
    MEETING_CANCELLED = "meeting.cancelled"
    MEETING_COMPLETED = "meeting.completed"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_OVERDUE = "task.overdue"
    
    # Integration events
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"
    
    # System events
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    API_ERROR = "api.error"


class DeliveryStatus(str, Enum):
    """Status of webhook delivery."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""
    id: str
    webhook_id: str
    event_id: str
    attempt_number: int
    status: DeliveryStatus
    request_headers: dict
    request_body: str
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookEvent:
    """Event to be delivered via webhooks."""
    id: str
    event_type: EventType
    resource_type: str
    resource_id: str
    data: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    organization_id: Optional[str] = None


@dataclass
class Webhook:
    """Webhook subscription."""
    id: str
    name: str
    url: str
    secret: str  # For signing payloads
    events: list[EventType]  # Events to subscribe to
    is_active: bool = True
    
    # Headers to include
    headers: dict = field(default_factory=dict)
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Stats
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    organization_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class WebhookService:
    """Service for webhook management and delivery."""
    
    def __init__(self):
        self.webhooks: dict[str, Webhook] = {}
        self.events: list[WebhookEvent] = []
        self.deliveries: list[WebhookDelivery] = []
        self._pending_deliveries: list[tuple[str, WebhookEvent]] = []
        self._create_sample_webhooks()
    
    def _create_sample_webhooks(self):
        """Create sample webhooks for demo."""
        samples = [
            Webhook(
                id="webhook_1",
                name="CRM Sync Webhook",
                url="https://crm.example.com/webhooks/sales-agent",
                secret="whsec_sample123456",
                events=[
                    EventType.CONTACT_CREATED,
                    EventType.CONTACT_UPDATED,
                    EventType.DEAL_WON,
                    EventType.DEAL_LOST
                ],
                description="Sync important events to CRM",
                total_deliveries=150,
                successful_deliveries=148,
                failed_deliveries=2
            ),
            Webhook(
                id="webhook_2",
                name="Slack Notifications",
                url="https://hooks.slack.com/services/T00/B00/XXX",
                secret="whsec_slack789",
                events=[
                    EventType.DEAL_WON,
                    EventType.MEETING_SCHEDULED
                ],
                description="Post to #sales channel",
                headers={"Content-Type": "application/json"},
                total_deliveries=45,
                successful_deliveries=45,
                failed_deliveries=0
            )
        ]
        
        for webhook in samples:
            self.webhooks[webhook.id] = webhook
    
    def _generate_secret(self) -> str:
        """Generate a webhook secret."""
        return f"whsec_{uuid4().hex}"
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Sign a payload with HMAC-SHA256."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def create_webhook(
        self,
        name: str,
        url: str,
        events: list[EventType],
        description: Optional[str] = None,
        headers: Optional[dict] = None,
        max_retries: int = 3,
        organization_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Webhook:
        """Create a new webhook subscription."""
        webhook_id = f"webhook_{uuid4().hex[:8]}"
        secret = self._generate_secret()
        
        webhook = Webhook(
            id=webhook_id,
            name=name,
            url=url,
            secret=secret,
            events=events,
            description=description,
            headers=headers or {},
            max_retries=max_retries,
            organization_id=organization_id,
            created_by=created_by
        )
        
        self.webhooks[webhook_id] = webhook
        
        logger.info(f"Created webhook: {name} ({webhook_id})")
        
        return webhook
    
    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self.webhooks.get(webhook_id)
    
    async def update_webhook(
        self,
        webhook_id: str,
        updates: dict[str, Any]
    ) -> Optional[Webhook]:
        """Update a webhook."""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return None
        
        allowed_fields = [
            "name", "url", "events", "is_active", "headers",
            "max_retries", "retry_delay_seconds", "description"
        ]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(webhook, key, value)
        
        webhook.updated_at = datetime.utcnow()
        
        logger.info(f"Updated webhook: {webhook_id}")
        
        return webhook
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            logger.info(f"Deleted webhook: {webhook_id}")
            return True
        return False
    
    async def list_webhooks(
        self,
        event_type: Optional[EventType] = None,
        is_active: Optional[bool] = None,
        organization_id: Optional[str] = None
    ) -> list[Webhook]:
        """List webhooks with optional filters."""
        results = list(self.webhooks.values())
        
        if event_type:
            results = [w for w in results if event_type in w.events]
        
        if is_active is not None:
            results = [w for w in results if w.is_active == is_active]
        
        if organization_id:
            results = [w for w in results if w.organization_id == organization_id]
        
        return results
    
    async def regenerate_secret(self, webhook_id: str) -> Optional[str]:
        """Regenerate webhook secret."""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return None
        
        new_secret = self._generate_secret()
        webhook.secret = new_secret
        webhook.updated_at = datetime.utcnow()
        
        logger.info(f"Regenerated secret for webhook: {webhook_id}")
        
        return new_secret
    
    async def emit_event(
        self,
        event_type: EventType,
        resource_type: str,
        resource_id: str,
        data: dict,
        organization_id: Optional[str] = None
    ) -> WebhookEvent:
        """Emit an event to be delivered to subscribed webhooks."""
        event = WebhookEvent(
            id=f"evt_{uuid4().hex[:12]}",
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            data=data,
            organization_id=organization_id
        )
        
        self.events.append(event)
        
        # Find subscribed webhooks
        for webhook in self.webhooks.values():
            if not webhook.is_active:
                continue
            
            if event_type in webhook.events:
                # Queue delivery
                self._pending_deliveries.append((webhook.id, event))
        
        logger.info(f"Emitted event: {event_type.value} for {resource_type}/{resource_id}")
        
        return event
    
    async def deliver_event(
        self,
        webhook: Webhook,
        event: WebhookEvent,
        attempt: int = 1
    ) -> WebhookDelivery:
        """Deliver an event to a webhook endpoint."""
        import json
        
        # Build payload
        payload = {
            "id": event.id,
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "data": {
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                **event.data
            }
        }
        
        payload_str = json.dumps(payload)
        
        # Sign payload
        signature = self._sign_payload(payload_str, webhook.secret)
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": webhook.id,
            "X-Event-ID": event.id,
            "X-Event-Type": event.event_type.value,
            **webhook.headers
        }
        
        delivery = WebhookDelivery(
            id=f"dlv_{uuid4().hex[:12]}",
            webhook_id=webhook.id,
            event_id=event.id,
            attempt_number=attempt,
            status=DeliveryStatus.PENDING,
            request_headers=headers,
            request_body=payload_str
        )
        
        # Simulate HTTP request (in production, use httpx/aiohttp)
        start_time = datetime.utcnow()
        
        try:
            # Mock delivery - in production this would be an actual HTTP POST
            await asyncio.sleep(0.05)  # Simulate network latency
            
            # Simulate success most of the time
            import random
            if random.random() > 0.95:  # 5% failure rate
                raise Exception("Connection timeout")
            
            delivery.status = DeliveryStatus.DELIVERED
            delivery.response_status = 200
            delivery.response_body = '{"received": true}'
            
            webhook.successful_deliveries += 1
            webhook.last_delivery_at = datetime.utcnow()
            
            logger.info(f"Delivered event {event.id} to webhook {webhook.id}")
            
        except Exception as e:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            
            webhook.failed_deliveries += 1
            webhook.last_error_at = datetime.utcnow()
            webhook.last_error_message = str(e)
            
            logger.error(f"Failed to deliver event {event.id} to webhook {webhook.id}: {e}")
            
            # Schedule retry if attempts remaining
            if attempt < webhook.max_retries:
                delivery.status = DeliveryStatus.RETRYING
        
        end_time = datetime.utcnow()
        delivery.duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        webhook.total_deliveries += 1
        
        self.deliveries.append(delivery)
        
        return delivery
    
    async def process_pending_deliveries(self) -> int:
        """Process all pending webhook deliveries."""
        delivered = 0
        
        pending = self._pending_deliveries.copy()
        self._pending_deliveries.clear()
        
        for webhook_id, event in pending:
            webhook = self.webhooks.get(webhook_id)
            if webhook and webhook.is_active:
                await self.deliver_event(webhook, event)
                delivered += 1
        
        return delivered
    
    async def retry_failed_deliveries(self) -> int:
        """Retry failed deliveries."""
        retried = 0
        
        for delivery in self.deliveries:
            if delivery.status == DeliveryStatus.RETRYING:
                webhook = self.webhooks.get(delivery.webhook_id)
                if not webhook:
                    continue
                
                # Find the original event
                event = None
                for e in self.events:
                    if e.id == delivery.event_id:
                        event = e
                        break
                
                if event:
                    await self.deliver_event(
                        webhook,
                        event,
                        attempt=delivery.attempt_number + 1
                    )
                    retried += 1
        
        return retried
    
    async def get_deliveries(
        self,
        webhook_id: Optional[str] = None,
        event_id: Optional[str] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 50
    ) -> list[WebhookDelivery]:
        """Get webhook deliveries with filters."""
        results = self.deliveries.copy()
        
        if webhook_id:
            results = [d for d in results if d.webhook_id == webhook_id]
        
        if event_id:
            results = [d for d in results if d.event_id == event_id]
        
        if status:
            results = [d for d in results if d.status == status]
        
        # Sort by timestamp descending
        results.sort(key=lambda d: d.timestamp, reverse=True)
        
        return results[:limit]
    
    async def get_webhook_stats(
        self,
        webhook_id: str,
        days: int = 7
    ) -> Optional[dict]:
        """Get statistics for a webhook."""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return None
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_deliveries = [
            d for d in self.deliveries
            if d.webhook_id == webhook_id and d.timestamp >= cutoff
        ]
        
        # Calculate success rate
        successful = len([d for d in recent_deliveries if d.status == DeliveryStatus.DELIVERED])
        total = len(recent_deliveries)
        success_rate = (successful / total * 100) if total > 0 else 100
        
        # Average response time
        durations = [d.duration_ms for d in recent_deliveries if d.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Status distribution
        status_dist = {}
        for d in recent_deliveries:
            status = d.status.value
            status_dist[status] = status_dist.get(status, 0) + 1
        
        return {
            "webhook_id": webhook_id,
            "period_days": days,
            "total_deliveries": total,
            "successful": successful,
            "failed": len([d for d in recent_deliveries if d.status == DeliveryStatus.FAILED]),
            "success_rate": round(success_rate, 2),
            "avg_response_time_ms": round(avg_duration, 2),
            "status_distribution": status_dist,
            "lifetime_stats": {
                "total": webhook.total_deliveries,
                "successful": webhook.successful_deliveries,
                "failed": webhook.failed_deliveries
            }
        }
    
    async def test_webhook(self, webhook_id: str) -> Optional[WebhookDelivery]:
        """Send a test event to a webhook."""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return None
        
        test_event = WebhookEvent(
            id=f"test_{uuid4().hex[:8]}",
            event_type=EventType.CONTACT_CREATED,  # Use a common event type
            resource_type="test",
            resource_id="test_resource",
            data={
                "test": True,
                "message": "This is a test webhook delivery"
            }
        )
        
        delivery = await self.deliver_event(webhook, test_event)
        
        return delivery
    
    async def get_event_types(self) -> list[dict]:
        """Get all available event types grouped by category."""
        categories = {
            "contact": [],
            "company": [],
            "deal": [],
            "email": [],
            "sequence": [],
            "campaign": [],
            "meeting": [],
            "task": [],
            "integration": [],
            "system": []
        }
        
        for event_type in EventType:
            category = event_type.value.split(".")[0]
            if category in categories:
                categories[category].append({
                    "value": event_type.value,
                    "name": event_type.name
                })
        
        return [
            {"category": cat, "events": events}
            for cat, events in categories.items()
            if events
        ]


# Global service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get or create the webhook service singleton."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service
