"""
Connectors Routes - Third-party service integrations and sync management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/connectors", tags=["Connectors"])


class ConnectorType(str, Enum):
    CALENDAR = "calendar"
    EMAIL = "email"
    CRM = "crm"
    STORAGE = "storage"
    COMMUNICATION = "communication"
    ANALYTICS = "analytics"
    SOCIAL = "social"
    PAYMENT = "payment"
    MARKETING = "marketing"


class ConnectorProvider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    SLACK = "slack"
    ZOOM = "zoom"
    LINKEDIN = "linkedin"
    STRIPE = "stripe"
    DROPBOX = "dropbox"
    BOX = "box"
    MAILCHIMP = "mailchimp"
    TWILIO = "twilio"
    ZENDESK = "zendesk"
    INTERCOM = "intercom"
    PIPEDRIVE = "pipedrive"


class ConnectorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ConnectorCreate(BaseModel):
    provider: ConnectorProvider
    connector_type: ConnectorType
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    scopes: Optional[List[str]] = None
    auto_sync: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    auto_sync: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class OAuthInitiate(BaseModel):
    provider: ConnectorProvider
    redirect_uri: str
    scopes: Optional[List[str]] = None
    state: Optional[str] = None


class OAuthCallback(BaseModel):
    provider: ConnectorProvider
    code: str
    state: Optional[str] = None


class SyncConfig(BaseModel):
    entity_types: Optional[List[str]] = None  # contacts, deals, events, etc.
    direction: str = "bidirectional"  # inbound, outbound, bidirectional
    conflict_resolution: str = "remote_wins"  # remote_wins, local_wins, newest_wins
    filters: Optional[Dict[str, Any]] = None


class FieldMapping(BaseModel):
    source_field: str
    target_field: str
    transform: Optional[str] = None  # none, uppercase, lowercase, date_format, etc.
    default_value: Optional[str] = None


# In-memory storage
connectors = {}
sync_logs = {}
field_mappings = {}
oauth_states = {}


@router.post("/oauth/initiate")
async def initiate_oauth(
    request: OAuthInitiate,
    tenant_id: str = Query(default="default")
):
    """Initiate OAuth flow for a connector"""
    import uuid
    
    state = request.state or str(uuid.uuid4())
    
    # Generate OAuth URL based on provider
    oauth_urls = {
        ConnectorProvider.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
        ConnectorProvider.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        ConnectorProvider.SALESFORCE: "https://login.salesforce.com/services/oauth2/authorize",
        ConnectorProvider.HUBSPOT: "https://app.hubspot.com/oauth/authorize",
        ConnectorProvider.SLACK: "https://slack.com/oauth/v2/authorize",
        ConnectorProvider.LINKEDIN: "https://www.linkedin.com/oauth/v2/authorization",
    }
    
    base_url = oauth_urls.get(request.provider, f"https://oauth.{request.provider.value}.com/authorize")
    
    # Store state for validation
    oauth_states[state] = {
        "provider": request.provider.value,
        "redirect_uri": request.redirect_uri,
        "scopes": request.scopes or [],
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    }
    
    oauth_url = f"{base_url}?client_id=YOUR_CLIENT_ID&redirect_uri={request.redirect_uri}&state={state}&response_type=code"
    if request.scopes:
        oauth_url += f"&scope={' '.join(request.scopes)}"
    
    logger.info("oauth_initiated", provider=request.provider.value)
    return {
        "oauth_url": oauth_url,
        "state": state,
        "provider": request.provider.value,
        "expires_in_seconds": 600
    }


@router.post("/oauth/callback")
async def handle_oauth_callback(
    request: OAuthCallback,
    tenant_id: str = Query(default="default")
):
    """Handle OAuth callback and create connector"""
    import uuid
    
    # Validate state
    state_data = oauth_states.get(request.state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    # Exchange code for tokens (mock)
    connector_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    connector = {
        "id": connector_id,
        "provider": request.provider.value,
        "connector_type": "oauth",
        "name": f"{request.provider.value.title()} Connection",
        "status": ConnectorStatus.ACTIVE.value,
        "access_token": f"mock_access_token_{connector_id[:8]}",
        "refresh_token": f"mock_refresh_token_{connector_id[:8]}",
        "token_expires_at": (now + timedelta(hours=1)).isoformat(),
        "scopes": state_data.get("scopes", []),
        "auto_sync": True,
        "sync_interval_minutes": 60,
        "last_sync": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    connectors[connector_id] = connector
    del oauth_states[request.state]
    
    logger.info("oauth_completed", connector_id=connector_id, provider=request.provider.value)
    return connector


@router.post("/")
async def create_connector(
    request: ConnectorCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new connector (API key based)"""
    import uuid
    
    connector_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    connector = {
        "id": connector_id,
        "provider": request.provider.value,
        "connector_type": request.connector_type.value,
        "name": request.name or f"{request.provider.value.title()} Connector",
        "status": ConnectorStatus.ACTIVE.value,
        "config": request.config or {},
        "scopes": request.scopes or [],
        "auto_sync": request.auto_sync,
        "sync_interval_minutes": request.sync_interval_minutes,
        "last_sync": None,
        "error_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    connectors[connector_id] = connector
    sync_logs[connector_id] = []
    
    logger.info("connector_created", connector_id=connector_id, provider=request.provider.value)
    return connector


@router.get("/")
async def list_connectors(
    provider: Optional[ConnectorProvider] = None,
    connector_type: Optional[ConnectorType] = None,
    status: Optional[ConnectorStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List all connectors"""
    result = [c for c in connectors.values() if c.get("tenant_id") == tenant_id]
    
    if provider:
        result = [c for c in result if c.get("provider") == provider.value]
    if connector_type:
        result = [c for c in result if c.get("connector_type") == connector_type.value]
    if status:
        result = [c for c in result if c.get("status") == status.value]
    
    return {"connectors": result, "total": len(result)}


@router.get("/{connector_id}")
async def get_connector(connector_id: str):
    """Get connector details"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connectors[connector_id]


@router.put("/{connector_id}")
async def update_connector(connector_id: str, request: ConnectorUpdate):
    """Update connector configuration"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = connectors[connector_id]
    
    if request.name is not None:
        connector["name"] = request.name
    if request.config is not None:
        connector["config"] = request.config
    if request.auto_sync is not None:
        connector["auto_sync"] = request.auto_sync
    if request.sync_interval_minutes is not None:
        connector["sync_interval_minutes"] = request.sync_interval_minutes
    if request.is_active is not None:
        connector["status"] = ConnectorStatus.ACTIVE.value if request.is_active else ConnectorStatus.INACTIVE.value
    
    connector["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("connector_updated", connector_id=connector_id)
    return connector


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    del connectors[connector_id]
    if connector_id in sync_logs:
        del sync_logs[connector_id]
    
    logger.info("connector_deleted", connector_id=connector_id)
    return {"status": "deleted", "connector_id": connector_id}


@router.post("/{connector_id}/test")
async def test_connector(connector_id: str):
    """Test connector connection"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = connectors[connector_id]
    
    # Mock connection test
    result = {
        "connector_id": connector_id,
        "provider": connector.get("provider"),
        "status": "success",
        "latency_ms": 145,
        "tested_at": datetime.utcnow().isoformat(),
        "details": {
            "authenticated": True,
            "permissions_valid": True,
            "rate_limit_remaining": 4950
        }
    }
    
    logger.info("connector_tested", connector_id=connector_id, status="success")
    return result


@router.post("/{connector_id}/sync")
async def trigger_sync(
    connector_id: str,
    config: Optional[SyncConfig] = None
):
    """Trigger manual sync for connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = connectors[connector_id]
    now = datetime.utcnow()
    
    import uuid
    sync_id = str(uuid.uuid4())
    
    sync_record = {
        "id": sync_id,
        "connector_id": connector_id,
        "started_at": now.isoformat(),
        "status": "completed",
        "completed_at": (now + timedelta(seconds=5)).isoformat(),
        "records_synced": 42,
        "records_created": 10,
        "records_updated": 30,
        "records_failed": 2,
        "entity_types": config.entity_types if config else ["all"],
        "direction": config.direction if config else "bidirectional"
    }
    
    if connector_id not in sync_logs:
        sync_logs[connector_id] = []
    sync_logs[connector_id].append(sync_record)
    
    connector["last_sync"] = now.isoformat()
    connector["updated_at"] = now.isoformat()
    
    logger.info("sync_completed", connector_id=connector_id, sync_id=sync_id)
    return sync_record


@router.get("/{connector_id}/sync-history")
async def get_sync_history(
    connector_id: str,
    limit: int = Query(default=20, le=100),
    offset: int = 0
):
    """Get sync history for connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    logs = sync_logs.get(connector_id, [])
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {
        "sync_logs": logs[offset:offset + limit],
        "total": len(logs),
        "limit": limit,
        "offset": offset
    }


@router.post("/{connector_id}/refresh-token")
async def refresh_connector_token(connector_id: str):
    """Refresh OAuth token for connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = connectors[connector_id]
    now = datetime.utcnow()
    
    # Mock token refresh
    connector["access_token"] = f"refreshed_token_{connector_id[:8]}"
    connector["token_expires_at"] = (now + timedelta(hours=1)).isoformat()
    connector["updated_at"] = now.isoformat()
    
    logger.info("token_refreshed", connector_id=connector_id)
    return {
        "status": "token_refreshed",
        "expires_at": connector["token_expires_at"]
    }


@router.post("/{connector_id}/field-mappings")
async def create_field_mapping(
    connector_id: str,
    mappings: List[FieldMapping],
    entity_type: str = "contact"
):
    """Configure field mappings for connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    key = f"{connector_id}:{entity_type}"
    
    field_mappings[key] = {
        "connector_id": connector_id,
        "entity_type": entity_type,
        "mappings": [m.dict() for m in mappings],
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info("field_mappings_created", connector_id=connector_id, entity_type=entity_type)
    return field_mappings[key]


@router.get("/{connector_id}/field-mappings")
async def get_field_mappings(
    connector_id: str,
    entity_type: Optional[str] = None
):
    """Get field mappings for connector"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    if entity_type:
        key = f"{connector_id}:{entity_type}"
        return field_mappings.get(key, {"mappings": []})
    
    # Return all mappings for connector
    result = []
    for key, mapping in field_mappings.items():
        if key.startswith(f"{connector_id}:"):
            result.append(mapping)
    
    return {"mappings": result}


@router.get("/{connector_id}/available-fields")
async def get_available_fields(connector_id: str, entity_type: str = "contact"):
    """Get available fields from remote system"""
    if connector_id not in connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = connectors[connector_id]
    
    # Mock available fields based on provider
    fields_by_provider = {
        "salesforce": ["Id", "Name", "Email", "Phone", "Company", "Title", "OwnerId", "CreatedDate", "LastModifiedDate"],
        "hubspot": ["id", "firstname", "lastname", "email", "phone", "company", "jobtitle", "createdate", "lastmodifieddate"],
        "google": ["id", "name", "emailAddress", "phoneNumber", "organization"],
        "microsoft": ["id", "displayName", "mail", "mobilePhone", "companyName", "jobTitle"]
    }
    
    fields = fields_by_provider.get(connector.get("provider"), ["id", "name", "email"])
    
    return {
        "entity_type": entity_type,
        "provider": connector.get("provider"),
        "fields": [{"name": f, "type": "string"} for f in fields]
    }


@router.get("/providers")
async def list_available_providers():
    """List all available connector providers"""
    providers = [
        {
            "id": p.value,
            "name": p.value.title(),
            "types": ["calendar", "email"] if p in [ConnectorProvider.GOOGLE, ConnectorProvider.MICROSOFT] else ["crm"],
            "auth_type": "oauth" if p in [ConnectorProvider.GOOGLE, ConnectorProvider.MICROSOFT, ConnectorProvider.SALESFORCE] else "api_key",
            "documentation_url": f"https://docs.example.com/connectors/{p.value}"
        }
        for p in ConnectorProvider
    ]
    return {"providers": providers}


@router.get("/stats")
async def get_connector_stats(tenant_id: str = Query(default="default")):
    """Get connector statistics"""
    tenant_connectors = [c for c in connectors.values() if c.get("tenant_id") == tenant_id]
    
    by_status = {}
    by_provider = {}
    by_type = {}
    
    for c in tenant_connectors:
        status = c.get("status", "unknown")
        provider = c.get("provider", "unknown")
        ctype = c.get("connector_type", "unknown")
        
        by_status[status] = by_status.get(status, 0) + 1
        by_provider[provider] = by_provider.get(provider, 0) + 1
        by_type[ctype] = by_type.get(ctype, 0) + 1
    
    # Count total syncs
    total_syncs = sum(len(logs) for logs in sync_logs.values())
    
    return {
        "total_connectors": len(tenant_connectors),
        "by_status": by_status,
        "by_provider": by_provider,
        "by_type": by_type,
        "total_syncs": total_syncs
    }
