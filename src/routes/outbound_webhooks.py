"""
Outbound Webhook Routes - Outbound Webhook API Endpoints
=========================================================
REST API for managing outbound webhook subscriptions.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.webhooks.webhook_service import (
    get_webhook_service,
    EventType,
    DeliveryStatus,
)

router = APIRouter(prefix="/outbound-webhooks", tags=["outbound-webhooks"])


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""
    name: str
    url: str
    events: list[str]
    description: Optional[str] = None
    headers: Optional[dict] = None
    max_retries: int = 3


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook."""
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    headers: Optional[dict] = None
    max_retries: Optional[int] = None


class EmitEventRequest(BaseModel):
    """Request to emit a webhook event."""
    event_type: str
    resource_type: str
    resource_id: str
    data: dict


@router.post("")
async def create_webhook(request: CreateWebhookRequest):
    """Create a new webhook subscription."""
    service = get_webhook_service()
    
    # Parse event types
    try:
        events = [EventType(e) for e in request.events]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")
    
    webhook = await service.create_webhook(
        name=request.name,
        url=request.url,
        events=events,
        description=request.description,
        headers=request.headers,
        max_retries=request.max_retries
    )
    
    return {
        "success": True,
        "webhook": {
            "id": webhook.id,
            "name": webhook.name,
            "url": webhook.url,
            "secret": webhook.secret,  # Only shown on creation
            "events": [e.value for e in webhook.events],
            "is_active": webhook.is_active,
            "created_at": webhook.created_at.isoformat()
        }
    }


@router.get("")
async def list_webhooks(
    event_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """List all webhooks."""
    service = get_webhook_service()
    
    event_enum = EventType(event_type) if event_type else None
    
    webhooks = await service.list_webhooks(
        event_type=event_enum,
        is_active=is_active
    )
    
    return {
        "webhooks": [
            {
                "id": w.id,
                "name": w.name,
                "url": w.url,
                "events": [e.value for e in w.events],
                "is_active": w.is_active,
                "total_deliveries": w.total_deliveries,
                "successful_deliveries": w.successful_deliveries,
                "failed_deliveries": w.failed_deliveries,
                "last_delivery_at": w.last_delivery_at.isoformat() if w.last_delivery_at else None,
                "created_at": w.created_at.isoformat()
            }
            for w in webhooks
        ],
        "count": len(webhooks)
    }


@router.get("/events")
async def list_event_types():
    """List all available event types."""
    service = get_webhook_service()
    
    event_types = await service.get_event_types()
    
    return {"event_types": event_types}


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str):
    """Get a webhook by ID."""
    service = get_webhook_service()
    
    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": [e.value for e in webhook.events],
        "is_active": webhook.is_active,
        "headers": webhook.headers,
        "max_retries": webhook.max_retries,
        "retry_delay_seconds": webhook.retry_delay_seconds,
        "description": webhook.description,
        "total_deliveries": webhook.total_deliveries,
        "successful_deliveries": webhook.successful_deliveries,
        "failed_deliveries": webhook.failed_deliveries,
        "last_delivery_at": webhook.last_delivery_at.isoformat() if webhook.last_delivery_at else None,
        "last_error_at": webhook.last_error_at.isoformat() if webhook.last_error_at else None,
        "last_error_message": webhook.last_error_message,
        "created_at": webhook.created_at.isoformat(),
        "updated_at": webhook.updated_at.isoformat()
    }


@router.patch("/{webhook_id}")
async def update_webhook(webhook_id: str, request: UpdateWebhookRequest):
    """Update a webhook."""
    service = get_webhook_service()
    
    updates = request.dict(exclude_none=True)
    
    # Convert events if provided
    if "events" in updates:
        try:
            updates["events"] = [EventType(e) for e in updates["events"]]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")
    
    webhook = await service.update_webhook(webhook_id, updates)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "success": True,
        "webhook": {
            "id": webhook.id,
            "name": webhook.name,
            "is_active": webhook.is_active,
            "updated_at": webhook.updated_at.isoformat()
        }
    }


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    service = get_webhook_service()
    
    success = await service.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"success": True, "deleted": webhook_id}


@router.post("/{webhook_id}/regenerate-secret")
async def regenerate_secret(webhook_id: str):
    """Regenerate webhook secret."""
    service = get_webhook_service()
    
    new_secret = await service.regenerate_secret(webhook_id)
    if not new_secret:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "success": True,
        "webhook_id": webhook_id,
        "secret": new_secret
    }


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Send a test event to a webhook."""
    service = get_webhook_service()
    
    delivery = await service.test_webhook(webhook_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "success": delivery.status.value == "delivered",
        "delivery": {
            "id": delivery.id,
            "status": delivery.status.value,
            "response_status": delivery.response_status,
            "duration_ms": delivery.duration_ms,
            "error_message": delivery.error_message
        }
    }


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get delivery history for a webhook."""
    service = get_webhook_service()
    
    # Verify webhook exists
    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    status_enum = DeliveryStatus(status) if status else None
    
    deliveries = await service.get_deliveries(
        webhook_id=webhook_id,
        status=status_enum,
        limit=limit
    )
    
    return {
        "deliveries": [
            {
                "id": d.id,
                "event_id": d.event_id,
                "attempt_number": d.attempt_number,
                "status": d.status.value,
                "response_status": d.response_status,
                "duration_ms": d.duration_ms,
                "error_message": d.error_message,
                "timestamp": d.timestamp.isoformat()
            }
            for d in deliveries
        ],
        "count": len(deliveries)
    }


@router.get("/{webhook_id}/stats")
async def get_webhook_stats(
    webhook_id: str,
    days: int = Query(default=7, ge=1, le=90)
):
    """Get statistics for a webhook."""
    service = get_webhook_service()
    
    stats = await service.get_webhook_stats(webhook_id, days=days)
    if not stats:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return stats


@router.post("/emit")
async def emit_event(request: EmitEventRequest):
    """Emit an event to all subscribed webhooks."""
    service = get_webhook_service()
    
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {request.event_type}")
    
    event = await service.emit_event(
        event_type=event_type,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        data=request.data
    )
    
    # Process pending deliveries
    delivered = await service.process_pending_deliveries()
    
    return {
        "success": True,
        "event": {
            "id": event.id,
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat()
        },
        "webhooks_notified": delivered
    }


@router.post("/process")
async def process_pending_deliveries():
    """Process all pending webhook deliveries."""
    service = get_webhook_service()
    
    delivered = await service.process_pending_deliveries()
    
    return {
        "success": True,
        "deliveries_processed": delivered
    }


@router.post("/retry")
async def retry_failed_deliveries():
    """Retry failed webhook deliveries."""
    service = get_webhook_service()
    
    retried = await service.retry_failed_deliveries()
    
    return {
        "success": True,
        "deliveries_retried": retried
    }
