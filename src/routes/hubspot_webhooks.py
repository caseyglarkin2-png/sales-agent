"""HubSpot CRM Webhooks for Real-Time Signal Ingestion.

Handles HubSpot workflow webhooks for:
- Deal stage changes
- Contact property updates
- Company updates
- Meeting outcomes
- Task completions

These webhooks provide real-time signals vs polling.
"""
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_db
from src.logger import get_logger
from src.models.signal import SignalSource
from src.services.signal_service import SignalService

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/webhooks/hubspot", tags=["HubSpot Webhooks"])


# =============================================================================
# Webhook Event Types
# =============================================================================

class HubSpotEventType(str, Enum):
    """HubSpot webhook event types we handle."""
    # Contact events
    CONTACT_CREATED = "contact.creation"
    CONTACT_UPDATED = "contact.propertyChange"
    CONTACT_DELETED = "contact.deletion"
    
    # Deal events
    DEAL_CREATED = "deal.creation"
    DEAL_UPDATED = "deal.propertyChange"
    DEAL_DELETED = "deal.deletion"
    
    # Company events
    COMPANY_CREATED = "company.creation"
    COMPANY_UPDATED = "company.propertyChange"
    
    # Engagement events
    MEETING_CREATED = "meeting.creation"
    MEETING_UPDATED = "meeting.propertyChange"
    NOTE_CREATED = "note.creation"
    TASK_CREATED = "task.creation"
    TASK_UPDATED = "task.propertyChange"
    EMAIL_CREATED = "email.creation"
    
    # Subscription changes
    SUBSCRIPTION_CHANGED = "subscription.change"


# =============================================================================
# Request Models
# =============================================================================

class HubSpotWebhookEvent(BaseModel):
    """Single webhook event from HubSpot."""
    eventId: int = Field(..., description="Unique event ID")
    subscriptionId: int = Field(..., description="Subscription ID")
    portalId: int = Field(..., description="HubSpot portal ID")
    appId: int = Field(..., description="App ID")
    occurredAt: int = Field(..., description="Event timestamp (ms)")
    eventType: str = Field(..., description="Event type")
    objectId: int = Field(..., description="Object ID (contact, deal, etc.)")
    propertyName: Optional[str] = Field(None, description="Changed property")
    propertyValue: Optional[str] = Field(None, description="New property value")
    sourceId: Optional[str] = Field(None, description="Source of change")


class HubSpotWebhookPayload(BaseModel):
    """Full webhook payload from HubSpot."""
    events: List[HubSpotWebhookEvent] = Field(default_factory=list)
    
    # HubSpot sends array directly, not wrapped
    @classmethod
    def from_list(cls, events: List[Dict]) -> "HubSpotWebhookPayload":
        return cls(events=[HubSpotWebhookEvent(**e) for e in events])


# =============================================================================
# Response Models
# =============================================================================

class WebhookProcessResult(BaseModel):
    """Result of processing webhook events."""
    received: int
    processed: int
    signals_created: int
    recommendations_created: int
    errors: List[str] = []


# =============================================================================
# Signature Verification
# =============================================================================

def verify_hubspot_signature(
    request_body: bytes,
    signature: str,
    client_secret: str,
    request_uri: str,
    request_method: str = "POST",
    timestamp: Optional[str] = None,
) -> bool:
    """
    Verify HubSpot webhook signature (v3).
    
    HubSpot uses HMAC-SHA256 for webhook signatures.
    See: https://developers.hubspot.com/docs/api/webhooks/validating-requests
    """
    if not client_secret:
        logger.warning("No HUBSPOT_WEBHOOK_SECRET configured, skipping signature verification")
        return True  # Allow in dev, but log warning
    
    try:
        # V3 signature: HMAC-SHA256 of requestMethod + requestUri + requestBody + timestamp
        if timestamp:
            source_string = f"{request_method}{request_uri}{request_body.decode('utf-8')}{timestamp}"
        else:
            source_string = f"{request_method}{request_uri}{request_body.decode('utf-8')}"
        
        expected_signature = hmac.new(
            client_secret.encode("utf-8"),
            source_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


# =============================================================================
# Event Processors
# =============================================================================

async def process_deal_event(
    event: HubSpotWebhookEvent,
    signal_service: SignalService,
) -> Optional[str]:
    """Process deal-related events."""
    
    # Map event types to signal event types
    if event.eventType == HubSpotEventType.DEAL_CREATED.value:
        event_type = "deal_created"
        description = f"New deal created (ID: {event.objectId})"
    elif event.eventType == HubSpotEventType.DEAL_UPDATED.value:
        if event.propertyName == "dealstage":
            event_type = "deal_stage_changed"
            description = f"Deal stage changed to: {event.propertyValue}"
        elif event.propertyName == "amount":
            event_type = "deal_amount_changed"
            description = f"Deal amount updated to: {event.propertyValue}"
        elif event.propertyName == "closedate":
            event_type = "deal_close_date_changed"
            description = f"Close date updated"
        else:
            event_type = "deal_property_changed"
            description = f"Deal property {event.propertyName} changed"
    else:
        return None
    
    signal, recommendation = await signal_service.create_and_process(
        source=SignalSource.HUBSPOT,
        event_type=event_type,
        payload={
            "deal_id": str(event.objectId),
            "property_name": event.propertyName,
            "property_value": event.propertyValue,
            "event_type": event.eventType,
            "occurred_at": event.occurredAt,
        },
        idempotency_key=f"hubspot-deal-{event.eventId}",
    )
    
    return signal.id if signal else None


async def process_contact_event(
    event: HubSpotWebhookEvent,
    signal_service: SignalService,
) -> Optional[str]:
    """Process contact-related events."""
    
    if event.eventType == HubSpotEventType.CONTACT_CREATED.value:
        event_type = "contact_created"
        description = f"New contact created (ID: {event.objectId})"
    elif event.eventType == HubSpotEventType.CONTACT_UPDATED.value:
        # Only create signals for important property changes
        important_properties = [
            "lifecyclestage", "hs_lead_status", "hubspot_owner_id",
            "jobtitle", "phone", "email",
        ]
        if event.propertyName not in important_properties:
            return None
        
        event_type = "contact_property_changed"
        description = f"Contact {event.propertyName} changed to: {event.propertyValue}"
    else:
        return None
    
    signal, recommendation = await signal_service.create_and_process(
        source=SignalSource.HUBSPOT,
        event_type=event_type,
        payload={
            "contact_id": str(event.objectId),
            "property_name": event.propertyName,
            "property_value": event.propertyValue,
            "event_type": event.eventType,
            "occurred_at": event.occurredAt,
        },
        idempotency_key=f"hubspot-contact-{event.eventId}",
    )
    
    return signal.id if signal else None


async def process_meeting_event(
    event: HubSpotWebhookEvent,
    signal_service: SignalService,
) -> Optional[str]:
    """Process meeting-related events."""
    
    if event.eventType == HubSpotEventType.MEETING_CREATED.value:
        event_type = "meeting_scheduled"
    elif event.eventType == HubSpotEventType.MEETING_UPDATED.value:
        if event.propertyName == "hs_meeting_outcome":
            event_type = "meeting_outcome_recorded"
        else:
            event_type = "meeting_updated"
    else:
        return None
    
    signal, recommendation = await signal_service.create_and_process(
        source=SignalSource.HUBSPOT,
        event_type=event_type,
        payload={
            "meeting_id": str(event.objectId),
            "property_name": event.propertyName,
            "property_value": event.propertyValue,
            "event_type": event.eventType,
            "occurred_at": event.occurredAt,
        },
        idempotency_key=f"hubspot-meeting-{event.eventId}",
    )
    
    return signal.id if signal else None


async def process_task_event(
    event: HubSpotWebhookEvent,
    signal_service: SignalService,
) -> Optional[str]:
    """Process task-related events."""
    
    if event.eventType == HubSpotEventType.TASK_CREATED.value:
        event_type = "task_created"
    elif event.eventType == HubSpotEventType.TASK_UPDATED.value:
        if event.propertyName == "hs_task_status":
            if event.propertyValue == "COMPLETED":
                event_type = "task_completed"
            else:
                event_type = "task_status_changed"
        else:
            return None  # Ignore other task property changes
    else:
        return None
    
    signal, recommendation = await signal_service.create_and_process(
        source=SignalSource.HUBSPOT,
        event_type=event_type,
        payload={
            "task_id": str(event.objectId),
            "property_name": event.propertyName,
            "property_value": event.propertyValue,
            "event_type": event.eventType,
            "occurred_at": event.occurredAt,
        },
        idempotency_key=f"hubspot-task-{event.eventId}",
    )
    
    return signal.id if signal else None


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/crm", status_code=status.HTTP_200_OK)
async def hubspot_crm_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hubspot_signature_v3: Optional[str] = Header(None, alias="X-HubSpot-Signature-v3"),
    x_hubspot_request_timestamp: Optional[str] = Header(None, alias="X-HubSpot-Request-Timestamp"),
) -> WebhookProcessResult:
    """
    Receive HubSpot CRM webhooks for real-time signals.
    
    Handles:
    - Deal stage changes
    - Contact updates
    - Meeting outcomes
    - Task completions
    
    Configure in HubSpot:
    1. Go to Settings > Integrations > Private Apps
    2. Select your app > Webhooks
    3. Subscribe to events you want
    4. Set URL: https://your-domain.com/api/webhooks/hubspot/crm
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature if configured
    if settings.hubspot_webhook_secret and x_hubspot_signature_v3:
        request_uri = str(request.url)
        if not verify_hubspot_signature(
            request_body=body,
            signature=x_hubspot_signature_v3,
            client_secret=settings.hubspot_webhook_secret,
            request_uri=request_uri,
            timestamp=x_hubspot_request_timestamp,
        ):
            logger.warning("Invalid HubSpot webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    
    # Parse events (HubSpot sends array directly)
    try:
        events_data = json.loads(body)
        if not isinstance(events_data, list):
            events_data = [events_data]
        payload = HubSpotWebhookPayload.from_list(events_data)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )
    
    logger.info(f"Received {len(payload.events)} HubSpot webhook events")
    
    # Process each event
    signal_service = SignalService(db)
    signals_created = 0
    recommendations_created = 0
    errors = []
    
    for event in payload.events:
        try:
            signal_id = None
            
            # Route to appropriate processor
            if event.eventType.startswith("deal."):
                signal_id = await process_deal_event(event, signal_service)
            elif event.eventType.startswith("contact."):
                signal_id = await process_contact_event(event, signal_service)
            elif event.eventType.startswith("meeting."):
                signal_id = await process_meeting_event(event, signal_service)
            elif event.eventType.startswith("task."):
                signal_id = await process_task_event(event, signal_service)
            else:
                logger.debug(f"Ignoring unhandled event type: {event.eventType}")
            
            if signal_id:
                signals_created += 1
                logger.info(f"Created signal {signal_id} from event {event.eventId}")
                
        except Exception as e:
            error_msg = f"Failed to process event {event.eventId}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return WebhookProcessResult(
        received=len(payload.events),
        processed=len(payload.events) - len(errors),
        signals_created=signals_created,
        recommendations_created=recommendations_created,
        errors=errors,
    )


@router.get("/crm/subscription-types")
async def list_subscription_types():
    """
    List available HubSpot webhook subscription types.
    
    Use these when configuring webhooks in HubSpot.
    """
    return {
        "recommended_subscriptions": [
            {
                "type": "deal.propertyChange",
                "properties": ["dealstage", "amount", "closedate"],
                "description": "Track deal stage changes and updates",
            },
            {
                "type": "deal.creation",
                "description": "New deals created",
            },
            {
                "type": "contact.propertyChange",
                "properties": ["lifecyclestage", "hs_lead_status"],
                "description": "Track lifecycle stage changes",
            },
            {
                "type": "meeting.creation",
                "description": "Meetings scheduled",
            },
            {
                "type": "meeting.propertyChange",
                "properties": ["hs_meeting_outcome"],
                "description": "Meeting outcomes recorded",
            },
            {
                "type": "task.propertyChange",
                "properties": ["hs_task_status"],
                "description": "Task completions",
            },
        ],
        "webhook_url": "https://your-domain.com/api/webhooks/hubspot/crm",
        "setup_docs": "https://developers.hubspot.com/docs/api/webhooks",
    }


@router.post("/test")
async def test_webhook_endpoint():
    """
    Test endpoint for HubSpot webhook configuration.
    
    HubSpot pings this during setup to verify the endpoint works.
    """
    return {"status": "ok", "message": "Webhook endpoint is ready"}
