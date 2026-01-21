"""
Webhook Subscriptions Routes - Webhook Management API
======================================================
REST API endpoints for managing webhook subscriptions and deliveries.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..webhook_subscriptions import (
    WebhookSubscriptionsService,
    get_webhook_subscriptions_service,
)
from ..webhook_subscriptions.webhook_subscriptions_service import (
    WebhookEventType,
    SubscriptionStatus,
    DeliveryStatus,
)


router = APIRouter(prefix="/webhook-subscriptions", tags=["Webhook Subscriptions"])


# Request models
class CreateSubscriptionRequest(BaseModel):
    """Create subscription request."""
    name: str
    url: str
    events: list[str]
    headers: Optional[dict[str, str]] = None
    retry_count: int = 3
    timeout_seconds: int = 30


class UpdateSubscriptionRequest(BaseModel):
    """Update subscription request."""
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    status: Optional[str] = None
    headers: Optional[dict[str, str]] = None


class TriggerEventRequest(BaseModel):
    """Trigger event request."""
    event_type: str
    payload: dict[str, Any]
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None


def get_service() -> WebhookSubscriptionsService:
    """Get webhook subscriptions service instance."""
    return get_webhook_subscriptions_service()


def parse_events(events: list[str]) -> list[WebhookEventType]:
    """Parse event type strings."""
    result = []
    for e in events:
        try:
            result.append(WebhookEventType(e))
        except ValueError:
            pass
    return result


# Enums
@router.get("/event-types")
async def list_event_types():
    """List available webhook event types."""
    service = get_service()
    return {"event_types": await service.list_event_types()}


@router.get("/statuses")
async def list_statuses():
    """List subscription statuses."""
    return {
        "statuses": [
            {"value": s.value, "name": s.name}
            for s in SubscriptionStatus
        ]
    }


# Subscriptions CRUD
@router.post("")
async def create_subscription(
    request: CreateSubscriptionRequest,
    org_id: str,
    user_id: Optional[str] = None,
):
    """Create a new webhook subscription."""
    service = get_service()
    
    events = parse_events(request.events)
    if not events:
        raise HTTPException(status_code=400, detail="At least one valid event type required")
    
    sub = await service.create_subscription(
        name=request.name,
        url=request.url,
        events=events,
        org_id=org_id,
        headers=request.headers,
        retry_count=request.retry_count,
        timeout_seconds=request.timeout_seconds,
        created_by=user_id,
    )
    
    return {
        "id": sub.id,
        "name": sub.name,
        "url": sub.url,
        "events": [e.value for e in sub.events],
        "secret": sub.secret,
        "status": sub.status.value,
        "created_at": sub.created_at.isoformat(),
    }


@router.get("")
async def list_subscriptions(
    org_id: str,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
):
    """List webhook subscriptions."""
    service = get_service()
    
    stat = None
    if status:
        try:
            stat = SubscriptionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    evt = None
    if event_type:
        try:
            evt = WebhookEventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event type")
    
    subs = await service.list_subscriptions(org_id, stat, evt)
    
    return {
        "subscriptions": [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "events": [e.value for e in s.events],
                "status": s.status.value,
                "success_count": s.success_count,
                "failure_count": s.failure_count,
                "last_triggered": s.last_triggered.isoformat() if s.last_triggered else None,
            }
            for s in subs
        ]
    }


@router.get("/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Get a subscription by ID."""
    service = get_service()
    sub = await service.get_subscription(subscription_id)
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {
        "id": sub.id,
        "name": sub.name,
        "url": sub.url,
        "events": [e.value for e in sub.events],
        "secret": sub.secret,
        "status": sub.status.value,
        "headers": sub.headers,
        "retry_count": sub.retry_count,
        "timeout_seconds": sub.timeout_seconds,
        "success_count": sub.success_count,
        "failure_count": sub.failure_count,
        "consecutive_failures": sub.consecutive_failures,
        "last_triggered": sub.last_triggered.isoformat() if sub.last_triggered else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat(),
        "created_by": sub.created_by,
    }


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
):
    """Update a subscription."""
    service = get_service()
    
    events = None
    if request.events:
        events = parse_events(request.events)
    
    status = None
    if request.status:
        try:
            status = SubscriptionStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    sub = await service.update_subscription(
        subscription_id=subscription_id,
        name=request.name,
        url=request.url,
        events=events,
        status=status,
        headers=request.headers,
    )
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True, "updated_at": sub.updated_at.isoformat()}


@router.delete("/{subscription_id}")
async def delete_subscription(subscription_id: str):
    """Delete a subscription."""
    service = get_service()
    
    if not await service.delete_subscription(subscription_id):
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True}


@router.post("/{subscription_id}/rotate-secret")
async def rotate_secret(subscription_id: str):
    """Rotate a subscription's secret."""
    service = get_service()
    new_secret = await service.rotate_secret(subscription_id)
    
    if not new_secret:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"secret": new_secret}


@router.post("/{subscription_id}/pause")
async def pause_subscription(subscription_id: str):
    """Pause a subscription."""
    service = get_service()
    sub = await service.pause_subscription(subscription_id)
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True, "status": sub.status.value}


@router.post("/{subscription_id}/resume")
async def resume_subscription(subscription_id: str):
    """Resume a paused subscription."""
    service = get_service()
    sub = await service.resume_subscription(subscription_id)
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True, "status": sub.status.value}


@router.post("/{subscription_id}/test")
async def test_subscription(subscription_id: str):
    """Send a test webhook to a subscription."""
    service = get_service()
    delivery = await service.test_subscription(subscription_id)
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {
        "delivery_id": delivery.id,
        "status": delivery.status.value,
        "response_status": delivery.response_status,
        "response_time_ms": delivery.response_time_ms,
    }


@router.get("/{subscription_id}/stats")
async def get_subscription_stats(subscription_id: str):
    """Get statistics for a subscription."""
    service = get_service()
    stats = await service.get_subscription_stats(subscription_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return stats


# Events
@router.post("/events")
async def trigger_event(request: TriggerEventRequest, org_id: str):
    """Trigger a webhook event."""
    service = get_service()
    
    try:
        event_type = WebhookEventType(request.event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event type")
    
    event = await service.trigger_event(
        event_type=event_type,
        payload=request.payload,
        org_id=org_id,
        entity_id=request.entity_id,
        entity_type=request.entity_type,
    )
    
    return {
        "event_id": event.id,
        "event_type": event.event_type.value,
        "occurred_at": event.occurred_at.isoformat(),
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get an event by ID."""
    service = get_service()
    event = await service.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "id": event.id,
        "event_type": event.event_type.value,
        "payload": event.payload,
        "org_id": event.org_id,
        "entity_id": event.entity_id,
        "entity_type": event.entity_type,
        "occurred_at": event.occurred_at.isoformat(),
    }


@router.get("/events")
async def list_events(
    org_id: str,
    event_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List webhook events."""
    service = get_service()
    
    evt = None
    if event_type:
        try:
            evt = WebhookEventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event type")
    
    events = await service.list_events(org_id, evt, limit)
    
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]
    }


# Deliveries
@router.get("/deliveries")
async def list_deliveries(
    subscription_id: Optional[str] = None,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List webhook deliveries."""
    service = get_service()
    
    stat = None
    if status:
        try:
            stat = DeliveryStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    deliveries = await service.list_deliveries(subscription_id, event_id, stat, limit)
    
    return {
        "deliveries": [
            {
                "id": d.id,
                "subscription_id": d.subscription_id,
                "event_id": d.event_id,
                "event_type": d.event_type.value,
                "status": d.status.value,
                "response_status": d.response_status,
                "response_time_ms": d.response_time_ms,
                "attempt_number": d.attempt_number,
                "created_at": d.created_at.isoformat(),
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            }
            for d in deliveries
        ]
    }


@router.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: str):
    """Get a delivery by ID."""
    service = get_service()
    delivery = await service.get_delivery(delivery_id)
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    return {
        "id": delivery.id,
        "subscription_id": delivery.subscription_id,
        "event_id": delivery.event_id,
        "event_type": delivery.event_type.value,
        "url": delivery.url,
        "status": delivery.status.value,
        "request_headers": delivery.request_headers,
        "response_status": delivery.response_status,
        "response_body": delivery.response_body,
        "response_time_ms": delivery.response_time_ms,
        "attempt_number": delivery.attempt_number,
        "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
        "error_message": delivery.error_message,
        "created_at": delivery.created_at.isoformat(),
        "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
    }


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(delivery_id: str):
    """Retry a failed delivery."""
    service = get_service()
    delivery = await service.retry_delivery(delivery_id)
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not retryable")
    
    return {
        "delivery_id": delivery.id,
        "status": delivery.status.value,
        "attempt_number": delivery.attempt_number,
    }


@router.get("/deliveries/pending-retries")
async def get_pending_retries():
    """Get deliveries pending retry."""
    service = get_service()
    deliveries = await service.get_pending_retries()
    
    return {
        "pending_retries": [
            {
                "id": d.id,
                "subscription_id": d.subscription_id,
                "event_id": d.event_id,
                "attempt_number": d.attempt_number,
                "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
            }
            for d in deliveries
        ]
    }
