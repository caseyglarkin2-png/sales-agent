"""
Integration Hub Routes - Third-party integrations management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/integration-hub", tags=["Integration Hub"])


class IntegrationCategory(str, Enum):
    CRM = "crm"
    EMAIL = "email"
    CALENDAR = "calendar"
    COMMUNICATION = "communication"
    ENRICHMENT = "enrichment"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    STORAGE = "storage"
    PRODUCTIVITY = "productivity"
    FINANCE = "finance"


class IntegrationStatus(str, Enum):
    AVAILABLE = "available"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"


class SyncDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class SyncFrequency(str, Enum):
    REALTIME = "realtime"
    EVERY_5_MIN = "every_5_min"
    EVERY_15_MIN = "every_15_min"
    HOURLY = "hourly"
    DAILY = "daily"
    MANUAL = "manual"


# In-memory storage
integrations = {}
integration_connections = {}
field_mappings = {}
sync_logs = {}
webhooks = {}


# Available integrations catalog
INTEGRATION_CATALOG = {
    "salesforce": {"name": "Salesforce", "category": "crm", "description": "World's #1 CRM platform"},
    "hubspot": {"name": "HubSpot", "category": "crm", "description": "Inbound marketing, sales, and service software"},
    "pipedrive": {"name": "Pipedrive", "category": "crm", "description": "Sales CRM and pipeline management"},
    "gmail": {"name": "Gmail", "category": "email", "description": "Google email service"},
    "outlook": {"name": "Outlook", "category": "email", "description": "Microsoft email and calendar"},
    "google_calendar": {"name": "Google Calendar", "category": "calendar", "description": "Google scheduling service"},
    "slack": {"name": "Slack", "category": "communication", "description": "Team collaboration platform"},
    "zoom": {"name": "Zoom", "category": "communication", "description": "Video conferencing platform"},
    "teams": {"name": "Microsoft Teams", "category": "communication", "description": "Microsoft collaboration platform"},
    "clearbit": {"name": "Clearbit", "category": "enrichment", "description": "Data enrichment and intelligence"},
    "zoominfo": {"name": "ZoomInfo", "category": "enrichment", "description": "B2B intelligence platform"},
    "linkedin": {"name": "LinkedIn Sales Navigator", "category": "enrichment", "description": "Professional networking for sales"},
    "segment": {"name": "Segment", "category": "analytics", "description": "Customer data platform"},
    "mixpanel": {"name": "Mixpanel", "category": "analytics", "description": "Product analytics platform"},
    "marketo": {"name": "Marketo", "category": "marketing", "description": "Marketing automation platform"},
    "mailchimp": {"name": "Mailchimp", "category": "marketing", "description": "Email marketing platform"},
    "intercom": {"name": "Intercom", "category": "communication", "description": "Customer messaging platform"},
    "dropbox": {"name": "Dropbox", "category": "storage", "description": "Cloud file storage"},
    "google_drive": {"name": "Google Drive", "category": "storage", "description": "Google cloud storage"},
    "notion": {"name": "Notion", "category": "productivity", "description": "All-in-one workspace"},
    "stripe": {"name": "Stripe", "category": "finance", "description": "Online payment processing"},
    "quickbooks": {"name": "QuickBooks", "category": "finance", "description": "Accounting software"}
}


class ConnectionCreate(BaseModel):
    integration_id: str
    credentials: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None


class FieldMappingCreate(BaseModel):
    connection_id: str
    entity_type: str
    mappings: List[Dict[str, str]]


class SyncConfig(BaseModel):
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    sync_frequency: SyncFrequency = SyncFrequency.EVERY_15_MIN
    entities_to_sync: List[str]
    filters: Optional[Dict[str, Any]] = None


# Integration Catalog
@router.get("/catalog")
async def get_integration_catalog(
    category: Optional[IntegrationCategory] = None,
    search: Optional[str] = None
):
    """Get available integrations"""
    catalog = []
    
    for int_id, info in INTEGRATION_CATALOG.items():
        if category and info["category"] != category.value:
            continue
        if search and search.lower() not in info["name"].lower() and search.lower() not in info["description"].lower():
            continue
        
        catalog.append({
            "id": int_id,
            **info,
            "status": IntegrationStatus.AVAILABLE.value
        })
    
    return {"integrations": catalog, "total": len(catalog)}


@router.get("/catalog/{integration_id}")
async def get_integration_details(integration_id: str):
    """Get integration details"""
    if integration_id not in INTEGRATION_CATALOG:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    info = INTEGRATION_CATALOG[integration_id]
    
    # Define capabilities based on category
    capabilities = {
        "crm": ["contacts", "accounts", "opportunities", "activities"],
        "email": ["send", "receive", "tracking", "templates"],
        "calendar": ["events", "availability", "scheduling"],
        "communication": ["messages", "calls", "meetings"],
        "enrichment": ["companies", "contacts", "leads"],
        "analytics": ["events", "users", "metrics"],
        "marketing": ["campaigns", "leads", "email"],
        "storage": ["files", "folders", "sharing"],
        "productivity": ["tasks", "notes", "documents"],
        "finance": ["invoices", "payments", "subscriptions"]
    }
    
    return {
        "id": integration_id,
        **info,
        "capabilities": capabilities.get(info["category"], []),
        "auth_type": random.choice(["oauth2", "api_key", "basic"]),
        "documentation_url": f"https://docs.example.com/integrations/{integration_id}",
        "rate_limits": {"requests_per_minute": random.randint(60, 1000)}
    }


# Connections
@router.post("/connections")
async def create_connection(
    request: ConnectionCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Connect an integration"""
    if request.integration_id not in INTEGRATION_CATALOG:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    connection_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    info = INTEGRATION_CATALOG[request.integration_id]
    
    connection = {
        "id": connection_id,
        "integration_id": request.integration_id,
        "integration_name": info["name"],
        "category": info["category"],
        "status": IntegrationStatus.CONNECTED.value,
        "settings": request.settings or {},
        "sync_config": {
            "sync_direction": SyncDirection.BIDIRECTIONAL.value,
            "sync_frequency": SyncFrequency.EVERY_15_MIN.value,
            "entities_to_sync": []
        },
        "last_sync_at": None,
        "records_synced": 0,
        "owner_id": user_id,
        "tenant_id": tenant_id,
        "connected_at": now.isoformat()
    }
    
    integration_connections[connection_id] = connection
    
    logger.info("integration_connected", connection_id=connection_id, integration=request.integration_id)
    return connection


@router.get("/connections")
async def list_connections(
    category: Optional[IntegrationCategory] = None,
    status: Optional[IntegrationStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List connected integrations"""
    result = [c for c in integration_connections.values() if c.get("tenant_id") == tenant_id]
    
    if category:
        result = [c for c in result if c.get("category") == category.value]
    if status:
        result = [c for c in result if c.get("status") == status.value]
    
    return {"connections": result, "total": len(result)}


@router.get("/connections/{connection_id}")
async def get_connection(connection_id: str):
    """Get connection details"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = integration_connections[connection_id]
    
    # Get field mappings
    mappings = [m for m in field_mappings.values() if m.get("connection_id") == connection_id]
    
    # Get recent sync logs
    logs = [l for l in sync_logs.values() if l.get("connection_id") == connection_id]
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {
        **connection,
        "field_mappings": mappings,
        "recent_syncs": logs[:5]
    }


@router.put("/connections/{connection_id}")
async def update_connection(
    connection_id: str,
    settings: Optional[Dict[str, Any]] = None
):
    """Update connection settings"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = integration_connections[connection_id]
    
    if settings:
        connection["settings"].update(settings)
    
    connection["updated_at"] = datetime.utcnow().isoformat()
    
    return connection


@router.delete("/connections/{connection_id}")
async def disconnect_integration(connection_id: str):
    """Disconnect an integration"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    integration_connections.pop(connection_id)
    
    return {"message": "Integration disconnected", "connection_id": connection_id}


# Sync Configuration
@router.put("/connections/{connection_id}/sync-config")
async def update_sync_config(
    connection_id: str,
    config: SyncConfig
):
    """Update sync configuration"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = integration_connections[connection_id]
    
    connection["sync_config"] = {
        "sync_direction": config.sync_direction.value,
        "sync_frequency": config.sync_frequency.value,
        "entities_to_sync": config.entities_to_sync,
        "filters": config.filters
    }
    
    return connection


@router.post("/connections/{connection_id}/sync")
async def trigger_sync(connection_id: str, entity_type: Optional[str] = None):
    """Trigger manual sync"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    sync_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Simulate sync
    records_synced = random.randint(10, 500)
    
    sync_log = {
        "id": sync_id,
        "connection_id": connection_id,
        "entity_type": entity_type or "all",
        "status": "completed",
        "records_synced": records_synced,
        "records_created": random.randint(0, records_synced // 3),
        "records_updated": random.randint(0, records_synced // 2),
        "errors": random.randint(0, 5),
        "started_at": now.isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "duration_seconds": random.uniform(1, 30)
    }
    
    sync_logs[sync_id] = sync_log
    
    connection = integration_connections[connection_id]
    connection["last_sync_at"] = now.isoformat()
    connection["records_synced"] += records_synced
    
    return sync_log


@router.get("/connections/{connection_id}/sync-history")
async def get_sync_history(
    connection_id: str,
    limit: int = Query(default=20, le=50)
):
    """Get sync history"""
    logs = [l for l in sync_logs.values() if l.get("connection_id") == connection_id]
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"syncs": logs[:limit], "total": len(logs)}


# Field Mappings
@router.post("/field-mappings")
async def create_field_mapping(
    request: FieldMappingCreate,
    tenant_id: str = Query(default="default")
):
    """Create field mapping"""
    if request.connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    mapping_id = str(uuid.uuid4())
    
    mapping = {
        "id": mapping_id,
        "connection_id": request.connection_id,
        "entity_type": request.entity_type,
        "mappings": request.mappings,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    field_mappings[mapping_id] = mapping
    
    return mapping


@router.get("/field-mappings")
async def list_field_mappings(
    connection_id: str,
    entity_type: Optional[str] = None
):
    """List field mappings"""
    result = [m for m in field_mappings.values() if m.get("connection_id") == connection_id]
    
    if entity_type:
        result = [m for m in result if m.get("entity_type") == entity_type]
    
    return {"mappings": result, "total": len(result)}


@router.put("/field-mappings/{mapping_id}")
async def update_field_mapping(
    mapping_id: str,
    mappings: List[Dict[str, str]]
):
    """Update field mapping"""
    if mapping_id not in field_mappings:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    mapping = field_mappings[mapping_id]
    mapping["mappings"] = mappings
    mapping["updated_at"] = datetime.utcnow().isoformat()
    
    return mapping


@router.delete("/field-mappings/{mapping_id}")
async def delete_field_mapping(mapping_id: str):
    """Delete field mapping"""
    if mapping_id not in field_mappings:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    field_mappings.pop(mapping_id)
    
    return {"message": "Mapping deleted"}


# Webhooks
@router.post("/connections/{connection_id}/webhooks")
async def create_webhook(
    connection_id: str,
    event_types: List[str],
    target_url: str
):
    """Create webhook for integration events"""
    if connection_id not in integration_connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    webhook_id = str(uuid.uuid4())
    
    webhook = {
        "id": webhook_id,
        "connection_id": connection_id,
        "event_types": event_types,
        "target_url": target_url,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    webhooks[webhook_id] = webhook
    
    return webhook


@router.get("/connections/{connection_id}/webhooks")
async def list_webhooks(connection_id: str):
    """List webhooks for connection"""
    result = [w for w in webhooks.values() if w.get("connection_id") == connection_id]
    return {"webhooks": result, "total": len(result)}


# OAuth
@router.get("/oauth/{integration_id}/authorize")
async def get_oauth_url(integration_id: str, redirect_uri: str):
    """Get OAuth authorization URL"""
    if integration_id not in INTEGRATION_CATALOG:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    state = str(uuid.uuid4())
    
    return {
        "authorization_url": f"https://oauth.{integration_id}.com/authorize?client_id=xxx&redirect_uri={redirect_uri}&state={state}",
        "state": state
    }


@router.post("/oauth/{integration_id}/callback")
async def oauth_callback(
    integration_id: str,
    code: str,
    state: str
):
    """Handle OAuth callback"""
    if integration_id not in INTEGRATION_CATALOG:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Simulate token exchange
    return {
        "status": "success",
        "integration_id": integration_id,
        "message": "Integration connected successfully"
    }


# Health & Status
@router.get("/health")
async def check_integrations_health(tenant_id: str = Query(default="default")):
    """Check health of all connections"""
    connections = [c for c in integration_connections.values() if c.get("tenant_id") == tenant_id]
    
    health_status = []
    for conn in connections:
        health_status.append({
            "connection_id": conn["id"],
            "integration": conn["integration_name"],
            "status": conn["status"],
            "last_sync_at": conn.get("last_sync_at"),
            "is_healthy": conn["status"] == IntegrationStatus.CONNECTED.value
        })
    
    healthy_count = len([h for h in health_status if h["is_healthy"]])
    
    return {
        "integrations": health_status,
        "summary": {
            "total": len(health_status),
            "healthy": healthy_count,
            "unhealthy": len(health_status) - healthy_count
        }
    }


# Analytics
@router.get("/analytics")
async def get_integration_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get integration analytics"""
    tenant_connections = [c for c in integration_connections.values() if c.get("tenant_id") == tenant_id]
    tenant_logs = [l for l in sync_logs.values()]
    
    by_category = {}
    for category in IntegrationCategory:
        by_category[category.value] = len([
            c for c in tenant_connections if c.get("category") == category.value
        ])
    
    return {
        "total_connections": len(tenant_connections),
        "by_category": by_category,
        "total_syncs": len(tenant_logs),
        "total_records_synced": sum(c.get("records_synced", 0) for c in tenant_connections),
        "avg_sync_time_seconds": round(random.uniform(5, 30), 2),
        "sync_success_rate": round(random.uniform(0.95, 0.99), 3),
        "most_active_integrations": [
            {"integration": "salesforce", "syncs": random.randint(100, 500)},
            {"integration": "gmail", "syncs": random.randint(50, 300)},
            {"integration": "slack", "syncs": random.randint(30, 200)}
        ]
    }
