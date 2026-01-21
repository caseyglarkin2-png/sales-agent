"""
Integrations Routes - Third-Party Integration API
=================================================
REST API endpoints for integration management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..integrations import (
    IntegrationService,
    IntegrationType,
    IntegrationStatus,
    SyncDirection,
    SyncFrequency,
    get_integration_service,
)


router = APIRouter(prefix="/integrations", tags=["Integrations"])


# Request/Response models
class CreateIntegrationRequest(BaseModel):
    """Create integration request."""
    name: str
    provider: str
    settings: Optional[dict[str, Any]] = None


class UpdateIntegrationRequest(BaseModel):
    """Update integration request."""
    name: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class ConnectRequest(BaseModel):
    """Connect integration request."""
    credentials: Optional[dict[str, Any]] = None
    oauth: Optional[dict[str, Any]] = None


class SyncConfigRequest(BaseModel):
    """Sync configuration request."""
    entity_type: str
    direction: Optional[str] = "bidirectional"
    frequency: Optional[str] = "hourly"
    field_mappings: Optional[list[dict[str, Any]]] = None
    filters: Optional[dict[str, Any]] = None
    create_new: bool = True
    update_existing: bool = True
    delete_missing: bool = False


class OAuthRequest(BaseModel):
    """OAuth request."""
    redirect_uri: str
    state: Optional[str] = None


class OAuthExchangeRequest(BaseModel):
    """OAuth token exchange request."""
    code: str
    redirect_uri: str


def get_service() -> IntegrationService:
    """Get integration service instance."""
    return get_integration_service()


# Provider endpoints
@router.get("/providers")
async def list_providers(
    integration_type: Optional[str] = None,
    available_only: bool = True
):
    """List available integration providers."""
    service = get_service()
    
    type_enum = None
    if integration_type:
        try:
            type_enum = IntegrationType(integration_type)
        except ValueError:
            pass
    
    providers = await service.list_providers(
        integration_type=type_enum,
        available_only=available_only
    )
    
    return {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "type": p.integration_type.value,
                "auth_type": p.auth_type,
                "supported_entities": p.supported_entities,
                "supports_realtime": p.supports_realtime,
                "supports_webhooks": p.supports_webhooks,
                "logo_url": p.logo_url,
            }
            for p in providers
        ]
    }


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str):
    """Get a provider by ID."""
    service = get_service()
    provider = await service.get_provider(provider_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {
        "id": provider.id,
        "name": provider.name,
        "description": provider.description,
        "type": provider.integration_type.value,
        "auth_type": provider.auth_type,
        "scopes": provider.scopes,
        "supported_entities": provider.supported_entities,
        "supports_realtime": provider.supports_realtime,
        "supports_webhooks": provider.supports_webhooks,
        "logo_url": provider.logo_url,
        "website_url": provider.website_url,
    }


# OAuth endpoints
@router.post("/providers/{provider_id}/oauth/url")
async def get_oauth_url(provider_id: str, request: OAuthRequest):
    """Get OAuth authorization URL."""
    service = get_service()
    
    url = await service.get_oauth_url(
        provider_id=provider_id,
        redirect_uri=request.redirect_uri,
        state=request.state
    )
    
    if not url:
        raise HTTPException(status_code=400, detail="OAuth not supported for this provider")
    
    return {"oauth_url": url}


@router.post("/providers/{provider_id}/oauth/exchange")
async def exchange_oauth_code(provider_id: str, request: OAuthExchangeRequest):
    """Exchange OAuth authorization code for tokens."""
    service = get_service()
    
    tokens = await service.exchange_oauth_code(
        provider_id=provider_id,
        code=request.code,
        redirect_uri=request.redirect_uri
    )
    
    if not tokens:
        raise HTTPException(status_code=400, detail="Failed to exchange code")
    
    return tokens


# Integration CRUD
@router.post("")
async def create_integration(request: CreateIntegrationRequest):
    """Create a new integration."""
    service = get_service()
    
    integration = await service.create_integration(
        name=request.name,
        provider=request.provider,
        settings=request.settings
    )
    
    if not integration:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {
        "id": integration.id,
        "name": integration.name,
        "provider": integration.provider,
        "type": integration.integration_type.value,
        "status": integration.status.value,
        "created_at": integration.created_at.isoformat(),
    }


@router.get("")
async def list_integrations(
    integration_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """List integrations."""
    service = get_service()
    
    type_enum = None
    if integration_type:
        try:
            type_enum = IntegrationType(integration_type)
        except ValueError:
            pass
    
    status_enum = None
    if status:
        try:
            status_enum = IntegrationStatus(status)
        except ValueError:
            pass
    
    integrations = await service.list_integrations(
        integration_type=type_enum,
        status=status_enum,
        limit=limit
    )
    
    return {
        "integrations": [
            {
                "id": i.id,
                "name": i.name,
                "provider": i.provider,
                "type": i.integration_type.value,
                "status": i.status.value,
                "last_sync": i.last_sync.isoformat() if i.last_sync else None,
                "sync_configs_count": len(i.sync_configs),
                "created_at": i.created_at.isoformat(),
            }
            for i in integrations
        ],
        "total": len(integrations)
    }


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    """Get an integration by ID."""
    service = get_service()
    integration = await service.get_integration(integration_id)
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {
        "id": integration.id,
        "name": integration.name,
        "provider": integration.provider,
        "type": integration.integration_type.value,
        "status": integration.status.value,
        "settings": integration.settings,
        "external_account_id": integration.external_account_id,
        "external_account_name": integration.external_account_name,
        "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
        "last_error": integration.last_error,
        "connected_by": integration.connected_by,
        "sync_configs": [
            {
                "id": c.id,
                "entity_type": c.entity_type,
                "direction": c.direction.value,
                "frequency": c.frequency.value,
                "is_enabled": c.is_enabled,
                "last_sync": c.last_sync.isoformat() if c.last_sync else None,
                "field_mappings_count": len(c.field_mappings),
            }
            for c in integration.sync_configs
        ],
        "created_at": integration.created_at.isoformat(),
        "updated_at": integration.updated_at.isoformat(),
    }


@router.patch("/{integration_id}")
async def update_integration(integration_id: str, request: UpdateIntegrationRequest):
    """Update an integration."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    integration = await service.update_integration(integration_id, updates)
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"success": True, "integration_id": integration_id}


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str):
    """Delete an integration."""
    service = get_service()
    
    if not await service.delete_integration(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"success": True}


# Connection management
@router.post("/{integration_id}/connect")
async def connect_integration(integration_id: str, request: ConnectRequest):
    """Connect an integration with credentials."""
    service = get_service()
    
    if not await service.connect(
        integration_id=integration_id,
        credentials=request.credentials,
        oauth=request.oauth
    ):
        raise HTTPException(status_code=400, detail="Failed to connect")
    
    return {"success": True, "status": "connected"}


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str):
    """Disconnect an integration."""
    service = get_service()
    
    if not await service.disconnect(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"success": True, "status": "disconnected"}


@router.post("/{integration_id}/pause")
async def pause_integration(integration_id: str):
    """Pause an integration."""
    service = get_service()
    
    if not await service.pause(integration_id):
        raise HTTPException(status_code=400, detail="Cannot pause integration")
    
    return {"success": True, "status": "paused"}


@router.post("/{integration_id}/resume")
async def resume_integration(integration_id: str):
    """Resume a paused integration."""
    service = get_service()
    
    if not await service.resume(integration_id):
        raise HTTPException(status_code=400, detail="Cannot resume integration")
    
    return {"success": True, "status": "connected"}


@router.get("/{integration_id}/health")
async def check_integration_health(integration_id: str):
    """Check integration health."""
    service = get_service()
    
    health = await service.check_health(integration_id)
    return health


# Sync configuration
@router.post("/{integration_id}/sync-configs")
async def add_sync_config(integration_id: str, request: SyncConfigRequest):
    """Add a sync configuration."""
    service = get_service()
    
    try:
        direction = SyncDirection(request.direction)
    except ValueError:
        direction = SyncDirection.BIDIRECTIONAL
    
    try:
        frequency = SyncFrequency(request.frequency)
    except ValueError:
        frequency = SyncFrequency.HOURLY
    
    config = await service.add_sync_config(
        integration_id=integration_id,
        entity_type=request.entity_type,
        direction=direction,
        frequency=frequency,
        field_mappings=request.field_mappings,
        filters=request.filters or {},
        create_new=request.create_new,
        update_existing=request.update_existing,
        delete_missing=request.delete_missing,
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {
        "id": config.id,
        "entity_type": config.entity_type,
        "direction": config.direction.value,
        "frequency": config.frequency.value,
        "is_enabled": config.is_enabled,
    }


@router.patch("/{integration_id}/sync-configs/{config_id}")
async def update_sync_config(
    integration_id: str,
    config_id: str,
    updates: dict[str, Any]
):
    """Update a sync configuration."""
    service = get_service()
    
    config = await service.update_sync_config(integration_id, config_id, updates)
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"success": True, "config_id": config_id}


@router.delete("/{integration_id}/sync-configs/{config_id}")
async def remove_sync_config(integration_id: str, config_id: str):
    """Remove a sync configuration."""
    service = get_service()
    
    if not await service.remove_sync_config(integration_id, config_id):
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"success": True}


# Sync execution
@router.post("/{integration_id}/sync")
async def trigger_sync(
    integration_id: str,
    config_id: Optional[str] = None
):
    """Trigger a sync."""
    service = get_service()
    
    log = await service.trigger_sync(
        integration_id=integration_id,
        config_id=config_id
    )
    
    if not log:
        raise HTTPException(status_code=400, detail="Cannot trigger sync")
    
    return {
        "sync_id": log.id,
        "status": log.status,
        "records_processed": log.records_processed,
        "records_created": log.records_created,
        "records_updated": log.records_updated,
        "records_failed": log.records_failed,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    }


@router.get("/{integration_id}/sync-logs")
async def get_sync_logs(
    integration_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get sync logs for an integration."""
    service = get_service()
    
    logs = await service.get_sync_logs(integration_id, limit=limit)
    
    return {
        "logs": [
            {
                "id": log.id,
                "config_id": log.config_id,
                "status": log.status,
                "records_processed": log.records_processed,
                "records_created": log.records_created,
                "records_updated": log.records_updated,
                "records_failed": log.records_failed,
                "errors": log.errors,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            }
            for log in logs
        ],
        "total": len(logs)
    }
