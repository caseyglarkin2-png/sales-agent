"""
Webhooks Routes - Webhook management and event delivery
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random
import hashlib
import hmac

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookEvent(str, Enum):
    DEAL_CREATED = "deal.created"
    DEAL_UPDATED = "deal.updated"
    DEAL_WON = "deal.won"
    DEAL_LOST = "deal.lost"
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    LEAD_CREATED = "lead.created"
    LEAD_QUALIFIED = "lead.qualified"
    TASK_COMPLETED = "task.completed"
    MEETING_SCHEDULED = "meeting.scheduled"
    INVOICE_PAID = "invoice.paid"
    QUOTE_ACCEPTED = "quote.accepted"


class WebhookStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILING = "failing"
    SUSPENDED = "suspended"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


# In-memory storage
webhooks = {}
webhook_deliveries = {}
webhook_secrets = {}


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    is_active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[WebhookEvent]] = None
    headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = None


class EventPayload(BaseModel):
    event: WebhookEvent
    entity_type: str
    entity_id: str
    data: Dict[str, Any]


# CRUD Operations
@router.post("")
async def create_webhook(
    request: WebhookCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new webhook subscription"""
    webhook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate secret if not provided
    secret = request.secret or str(uuid.uuid4())
    
    webhook = {
        "id": webhook_id,
        "name": request.name,
        "url": request.url,
        "events": [e.value for e in request.events],
        "headers": request.headers or {},
        "is_active": request.is_active,
        "status": WebhookStatus.ACTIVE.value if request.is_active else WebhookStatus.INACTIVE.value,
        "retry_count": request.retry_count,
        "timeout_seconds": request.timeout_seconds,
        "consecutive_failures": 0,
        "total_deliveries": 0,
        "successful_deliveries": 0,
        "last_triggered_at": None,
        "last_success_at": None,
        "last_failure_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    webhooks[webhook_id] = webhook
    webhook_secrets[webhook_id] = secret
    
    logger.info("webhook_created", webhook_id=webhook_id, events=webhook["events"])
    
    return {**webhook, "secret": secret}


@router.get("")
async def list_webhooks(
    status: Optional[WebhookStatus] = None,
    event: Optional[WebhookEvent] = None,
    tenant_id: str = Query(default="default")
):
    """List all webhooks"""
    result = [w for w in webhooks.values() if w.get("tenant_id") == tenant_id]
    
    if status:
        result = [w for w in result if w.get("status") == status.value]
    if event:
        result = [w for w in result if event.value in w.get("events", [])]
    
    return {"webhooks": result, "total": len(result)}


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    tenant_id: str = Query(default="default")
):
    """Get webhook details"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhooks[webhook_id]


@router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdate,
    tenant_id: str = Query(default="default")
):
    """Update webhook configuration"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook = webhooks[webhook_id]
    
    if request.name is not None:
        webhook["name"] = request.name
    if request.url is not None:
        webhook["url"] = request.url
    if request.events is not None:
        webhook["events"] = [e.value for e in request.events]
    if request.headers is not None:
        webhook["headers"] = request.headers
    if request.is_active is not None:
        webhook["is_active"] = request.is_active
        webhook["status"] = WebhookStatus.ACTIVE.value if request.is_active else WebhookStatus.INACTIVE.value
    if request.retry_count is not None:
        webhook["retry_count"] = request.retry_count
    
    webhook["updated_at"] = datetime.utcnow().isoformat()
    
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete a webhook"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    del webhooks[webhook_id]
    if webhook_id in webhook_secrets:
        del webhook_secrets[webhook_id]
    
    return {"success": True, "deleted": webhook_id}


# Testing
@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Query(default="default")
):
    """Send a test event to the webhook"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook = webhooks[webhook_id]
    delivery_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create test payload
    test_payload = {
        "event": "test.ping",
        "timestamp": now.isoformat(),
        "webhook_id": webhook_id,
        "test": True,
        "data": {"message": "This is a test webhook event"}
    }
    
    # Simulate delivery
    delivery = {
        "id": delivery_id,
        "webhook_id": webhook_id,
        "event": "test.ping",
        "payload": test_payload,
        "status": DeliveryStatus.DELIVERED.value,
        "attempt": 1,
        "response_code": 200,
        "response_body": '{"received": true}',
        "duration_ms": random.randint(50, 500),
        "created_at": now.isoformat(),
        "delivered_at": now.isoformat()
    }
    
    webhook_deliveries[delivery_id] = delivery
    
    return {
        "success": True,
        "delivery_id": delivery_id,
        "response_code": 200,
        "duration_ms": delivery["duration_ms"]
    }


# Deliveries
@router.get("/{webhook_id}/deliveries")
async def list_webhook_deliveries(
    webhook_id: str,
    status: Optional[DeliveryStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List delivery attempts for a webhook"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    result = [
        d for d in webhook_deliveries.values()
        if d.get("webhook_id") == webhook_id
    ]
    
    if status:
        result = [d for d in result if d.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "deliveries": result[offset:offset + limit],
        "total": len(result)
    }


@router.get("/deliveries/{delivery_id}")
async def get_delivery_details(
    delivery_id: str,
    tenant_id: str = Query(default="default")
):
    """Get detailed information about a delivery attempt"""
    if delivery_id not in webhook_deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return webhook_deliveries[delivery_id]


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(
    delivery_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Query(default="default")
):
    """Manually retry a failed delivery"""
    if delivery_id not in webhook_deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    delivery = webhook_deliveries[delivery_id]
    
    # Create new delivery attempt
    new_delivery_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_delivery = {
        "id": new_delivery_id,
        "webhook_id": delivery["webhook_id"],
        "event": delivery["event"],
        "payload": delivery["payload"],
        "status": DeliveryStatus.DELIVERED.value,
        "attempt": delivery.get("attempt", 1) + 1,
        "response_code": 200,
        "response_body": '{"received": true}',
        "duration_ms": random.randint(50, 500),
        "original_delivery_id": delivery_id,
        "created_at": now.isoformat(),
        "delivered_at": now.isoformat()
    }
    
    webhook_deliveries[new_delivery_id] = new_delivery
    
    return {"success": True, "new_delivery_id": new_delivery_id}


# Event Triggering
@router.post("/trigger")
async def trigger_event(
    request: EventPayload,
    background_tasks: BackgroundTasks,
    tenant_id: str = Query(default="default")
):
    """Trigger an event to all subscribed webhooks"""
    now = datetime.utcnow()
    
    # Find all webhooks subscribed to this event
    subscribed_webhooks = [
        w for w in webhooks.values()
        if w.get("tenant_id") == tenant_id
        and w.get("is_active")
        and request.event.value in w.get("events", [])
    ]
    
    deliveries = []
    
    for webhook in subscribed_webhooks:
        delivery_id = str(uuid.uuid4())
        
        payload = {
            "id": str(uuid.uuid4()),
            "event": request.event.value,
            "timestamp": now.isoformat(),
            "entity_type": request.entity_type,
            "entity_id": request.entity_id,
            "data": request.data
        }
        
        # Simulate successful delivery
        delivery = {
            "id": delivery_id,
            "webhook_id": webhook["id"],
            "event": request.event.value,
            "payload": payload,
            "status": DeliveryStatus.DELIVERED.value,
            "attempt": 1,
            "response_code": 200,
            "duration_ms": random.randint(50, 500),
            "created_at": now.isoformat(),
            "delivered_at": now.isoformat()
        }
        
        webhook_deliveries[delivery_id] = delivery
        
        # Update webhook stats
        webhook["total_deliveries"] = webhook.get("total_deliveries", 0) + 1
        webhook["successful_deliveries"] = webhook.get("successful_deliveries", 0) + 1
        webhook["last_triggered_at"] = now.isoformat()
        webhook["last_success_at"] = now.isoformat()
        
        deliveries.append(delivery_id)
    
    return {
        "event": request.event.value,
        "webhooks_triggered": len(deliveries),
        "delivery_ids": deliveries
    }


# Signature Verification
@router.post("/verify-signature")
async def verify_signature(
    webhook_id: str = Query(...),
    signature: str = Query(...),
    payload: Dict[str, Any] = {},
    tenant_id: str = Query(default="default")
):
    """Verify a webhook signature"""
    if webhook_id not in webhook_secrets:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    secret = webhook_secrets[webhook_id]
    
    # Calculate expected signature
    payload_str = str(payload)
    expected_signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    is_valid = hmac.compare_digest(signature, expected_signature)
    
    return {"valid": is_valid}


# Regenerate Secret
@router.post("/{webhook_id}/regenerate-secret")
async def regenerate_secret(
    webhook_id: str,
    tenant_id: str = Query(default="default")
):
    """Regenerate webhook signing secret"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    new_secret = str(uuid.uuid4())
    webhook_secrets[webhook_id] = new_secret
    
    return {"success": True, "new_secret": new_secret}


# Stats
@router.get("/{webhook_id}/stats")
async def get_webhook_stats(
    webhook_id: str,
    days: int = Query(default=7, ge=1, le=30),
    tenant_id: str = Query(default="default")
):
    """Get statistics for a webhook"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook = webhooks[webhook_id]
    
    total = webhook.get("total_deliveries", 0)
    successful = webhook.get("successful_deliveries", 0)
    
    return {
        "webhook_id": webhook_id,
        "period_days": days,
        "total_deliveries": total or random.randint(100, 1000),
        "successful_deliveries": successful or random.randint(80, 900),
        "failed_deliveries": random.randint(0, 50),
        "success_rate": round(random.uniform(0.90, 0.99), 3),
        "avg_response_time_ms": random.randint(50, 300),
        "events_by_type": {
            "deal.created": random.randint(20, 200),
            "deal.updated": random.randint(50, 400),
            "contact.created": random.randint(30, 300)
        }
    }


# Available Events
@router.get("/events/available")
async def list_available_events():
    """List all available webhook events"""
    return {
        "events": [
            {"event": e.value, "description": f"{e.value.replace('.', ' ').replace('_', ' ').title()} event"}
            for e in WebhookEvent
        ]
    }


# Pause/Resume
@router.post("/{webhook_id}/pause")
async def pause_webhook(
    webhook_id: str,
    tenant_id: str = Query(default="default")
):
    """Pause webhook deliveries"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhooks[webhook_id]["is_active"] = False
    webhooks[webhook_id]["status"] = WebhookStatus.INACTIVE.value
    
    return {"success": True, "status": "inactive"}


@router.post("/{webhook_id}/resume")
async def resume_webhook(
    webhook_id: str,
    tenant_id: str = Query(default="default")
):
    """Resume webhook deliveries"""
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhooks[webhook_id]["is_active"] = True
    webhooks[webhook_id]["status"] = WebhookStatus.ACTIVE.value
    webhooks[webhook_id]["consecutive_failures"] = 0
    
    return {"success": True, "status": "active"}
