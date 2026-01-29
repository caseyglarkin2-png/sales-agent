"""
Integrations API
================

Manage user connections to third-party apps.

Ship Ship Ship: Each integration ships independently.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
from src.deps import get_current_user_id

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    """Status of a single integration"""
    app_name: str
    connected: bool
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    status: str  # 'active', 'error', 'disconnected'
    error_message: Optional[str] = None


class IntegrationsStatusResponse(BaseModel):
    """Overall integrations status for a user"""
    user_id: str
    connected: Dict[str, IntegrationStatus]
    available: List[str]


class IntegrationConfig(BaseModel):
    """Configuration for an integration"""
    app_name: str
    display_name: str
    icon_url: Optional[str] = None
    description: str
    features: List[str]
    oauth_provider: Optional[str] = None
    status: str  # 'active', 'coming_soon', 'beta'


# Registry of available integrations
AVAILABLE_INTEGRATIONS = {
    'google-drive': IntegrationConfig(
        app_name='google-drive',
        display_name='Google Drive',
        description='Import documents and training materials',
        features=['Import Google Docs', 'Import Sheets', 'Voice training', 'Auto-sync'],
        oauth_provider='google',
        status='active'
    ),
    'google-workspace': IntegrationConfig(
        app_name='google-workspace',
        display_name='Google Workspace',
        description='Full Google integration (Gmail, Calendar, Drive)',
        features=['Gmail', 'Calendar', 'Drive', 'Automated scheduling'],
        oauth_provider='google',
        status='active'
    ),
    'hubspot': IntegrationConfig(
        app_name='hubspot',
        display_name='HubSpot CRM',
        description='Sync contacts, deals, and activities',
        features=['Contact sync', 'Deal tracking', 'Activity logging', 'Voice training from notes'],
        oauth_provider='hubspot',
        status='active'
    ),
    'slack': IntegrationConfig(
        app_name='slack',
        display_name='Slack',
        description='Notifications and command execution',
        features=['Agent notifications', 'Commands', 'Collaboration', 'Status updates'],
        oauth_provider='slack',
        status='coming_soon'
    ),
    'yardflow-hitlist': IntegrationConfig(
        app_name='yardflow-hitlist',
        display_name='YardFlow Hitlist',
        description='Prospect management and list import',
        features=['Import lists', 'Sync status', 'Bidirectional updates', 'Automation'],
        oauth_provider='yardflow',
        status='coming_soon'
    ),
    'youtube': IntegrationConfig(
        app_name='youtube',
        display_name='YouTube',
        description='Extract transcripts for voice training',
        features=['Transcript extraction', 'Voice training', 'Video analysis', 'Auto-processing'],
        oauth_provider=None,  # No auth needed for public videos
        status='active'
    )
}


@router.get("/status", response_model=IntegrationsStatusResponse)
async def get_integrations_status(
    user_id: str = Depends(get_current_user_id)
) -> IntegrationsStatusResponse:
    """
    Get user's integration connection status.
    
    Returns which apps are connected and available.
    """
    
    # TODO: Query database for user's OAuth tokens
    # For now, return mock data showing YouTube as connected
    
    connected = {}
    
    # Check if user has Google OAuth token
    # If yes, mark google-drive and google-workspace as connected
    
    # For demo: YouTube is always "connected" (no auth needed)
    connected['youtube'] = IntegrationStatus(
        app_name='youtube',
        connected=True,
        connected_at=datetime.utcnow(),
        last_sync=datetime.utcnow(),
        status='active'
    )
    
    return IntegrationsStatusResponse(
        user_id=user_id,
        connected=connected,
        available=list(AVAILABLE_INTEGRATIONS.keys())
    )


@router.get("/available", response_model=List[IntegrationConfig])
async def list_available_integrations() -> List[IntegrationConfig]:
    """
    List all available integrations.
    
    Public endpoint - no auth required.
    """
    return list(AVAILABLE_INTEGRATIONS.values())


class TokenHealthStatus(BaseModel):
    """Token health status for an integration (Sprint 54)."""
    service: str
    connected: bool
    token_valid: bool
    expires_at: Optional[datetime] = None
    expires_in_hours: Optional[float] = None
    last_refreshed_at: Optional[datetime] = None
    warning: Optional[str] = None
    error: Optional[str] = None


class TokenHealthResponse(BaseModel):
    """Response for all token health statuses (Sprint 54)."""
    user_id: str
    tokens: List[TokenHealthStatus]
    overall_health: str  # 'healthy', 'warning', 'error', 'no_tokens'


@router.get("/tokens/health", response_model=TokenHealthResponse)
async def get_token_health(
    user_id: str = Depends(get_current_user_id)
) -> TokenHealthResponse:
    """
    Get health status of all OAuth tokens (Sprint 54).
    
    Returns detailed token status including expiry warnings.
    """
    from src.db import get_session
    from src.oauth_manager import OAuthToken
    from sqlalchemy import select
    from uuid import UUID
    
    tokens = []
    overall_health = "no_tokens"
    
    try:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        async with get_session() as db:
            query = select(OAuthToken).where(
                OAuthToken.user_id == user_uuid,
                OAuthToken.revoked == False
            )
            result = await db.execute(query)
            token_records = result.scalars().all()
            
            if token_records:
                overall_health = "healthy"
            
            for token in token_records:
                status = TokenHealthStatus(
                    service=token.service,
                    connected=True,
                    token_valid=True,
                    expires_at=token.expires_at,
                    last_refreshed_at=token.last_refreshed_at,
                )
                
                # Calculate expiry
                if token.expires_at:
                    now = datetime.utcnow()
                    if token.expires_at < now:
                        status.token_valid = False
                        status.error = "Token has expired"
                        overall_health = "error"
                    else:
                        delta = token.expires_at - now
                        status.expires_in_hours = delta.total_seconds() / 3600
                        
                        # Warning if expiring within 24 hours
                        if status.expires_in_hours < 24:
                            status.warning = f"Token expires in {status.expires_in_hours:.1f} hours"
                            if overall_health == "healthy":
                                overall_health = "warning"
                
                tokens.append(status)
                
    except Exception as e:
        # No tokens found or error - return empty list
        tokens.append(TokenHealthStatus(
            service="system",
            connected=False,
            token_valid=False,
            error=str(e)
        ))
        overall_health = "error"
    
    return TokenHealthResponse(
        user_id=user_id,
        tokens=tokens,
        overall_health=overall_health
    )


@router.post("/tokens/{service}/refresh")
async def refresh_token(
    service: str,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    Manually refresh an OAuth token (Sprint 54).
    
    Attempts to refresh the specified service's token.
    """
    from src.db import get_session
    from src.oauth_manager import TokenManager
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        async with get_session() as db:
            manager = TokenManager(db)
            
            # Get token with auto_refresh=True
            credentials = await manager.get_token(user_uuid, service, auto_refresh=True)
            
            if credentials:
                return {
                    "success": True,
                    "service": service,
                    "message": f"Token for {service} refreshed successfully"
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No token found for {service}. Please reconnect."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.get("/{app_name}/status", response_model=IntegrationStatus)
async def get_integration_status(
    app_name: str,
    user_id: str = Depends(get_current_user_id)
) -> IntegrationStatus:
    """
    Get status of a specific integration for the user.
    """
    
    if app_name not in AVAILABLE_INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Integration '{app_name}' not found")
    
    # TODO: Check database for OAuth token
    # For now, return disconnected status
    
    return IntegrationStatus(
        app_name=app_name,
        connected=False,
        status='disconnected'
    )


@router.post("/{app_name}/connect")
async def connect_integration(
    app_name: str,
    user_id: str = Depends(get_current_user_id)
) -> RedirectResponse:
    """
    Initiate OAuth connection for an integration.
    
    Redirects to appropriate OAuth provider.
    """
    
    if app_name not in AVAILABLE_INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Integration '{app_name}' not found")
    
    config = AVAILABLE_INTEGRATIONS[app_name]
    
    if config.status == 'coming_soon':
        raise HTTPException(status_code=400, detail="This integration is coming soon")
    
    if not config.oauth_provider:
        raise HTTPException(status_code=400, detail="This integration does not require OAuth")
    
    # Redirect to OAuth provider with post-auth redirect back to integrations
    if config.oauth_provider == 'google':
        # Sprint 60: Fixed - use correct OAuth route /auth/google (not /api/auth/google/authorize)
        return RedirectResponse(url="/auth/google?redirect=/caseyos/integrations")
    elif config.oauth_provider == 'hubspot':
        # TODO: Create HubSpot OAuth endpoint
        raise HTTPException(status_code=501, detail="HubSpot OAuth not implemented yet")
    elif config.oauth_provider == 'slack':
        raise HTTPException(status_code=501, detail="Slack OAuth coming soon")
    elif config.oauth_provider == 'yardflow':
        raise HTTPException(status_code=501, detail="YardFlow OAuth coming soon")
    else:
        raise HTTPException(status_code=400, detail="Unknown OAuth provider")


@router.delete("/{app_name}/disconnect")
async def disconnect_integration(
    app_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Disconnect an integration (revoke OAuth token).
    """
    
    if app_name not in AVAILABLE_INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Integration '{app_name}' not found")
    
    # TODO: Revoke OAuth token from database
    
    return {"success": True, "message": f"Disconnected from {app_name}"}


@router.post("/{app_name}/sync")
async def trigger_sync(
    app_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually trigger a sync for an integration.
    
    Ship Ship Ship: Build sync logic as each integration is added.
    """
    
    if app_name not in AVAILABLE_INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Integration '{app_name}' not found")
    
    # TODO: Implement sync logic per integration
    # For now, return success
    
    return {
        "success": True,
        "message": f"Sync triggered for {app_name}",
        "timestamp": datetime.utcnow()
    }


# ============================================================================
# HubSpot CRM Integration Endpoints
# ============================================================================

@router.get("/hubspot/contacts")
async def list_hubspot_contacts(
    limit: int = 100,
    after: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get contacts from HubSpot CRM.
    
    Uses HUBSPOT_API_KEY from Railway env vars.
    """
    try:
        # Get HubSpot API key from environment
        from src.config import settings
        api_key = settings.hubspot_api_key
        
        if not api_key:
            raise HTTPException(status_code=401, detail="HubSpot not configured")
        
        # Import connector
        from src.integrations.connectors.hubspot import HubSpotConnector
        
        # Create connector and get contacts
        connector = HubSpotConnector(api_key)
        result = await connector.get_contacts(limit=limit, after=after)
        
        await connector.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HubSpot contacts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get contacts: {str(e)}")


@router.get("/hubspot/deals")
async def list_hubspot_deals(
    limit: int = 100,
    after: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get deals from HubSpot CRM.
    """
    try:
        from src.config import settings
        api_key = settings.hubspot_api_key
        
        if not api_key:
            raise HTTPException(status_code=401, detail="HubSpot not configured")
        
        from src.integrations.connectors.hubspot import HubSpotConnector
        
        connector = HubSpotConnector(api_key)
        result = await connector.get_deals(limit=limit, after=after)
        
        await connector.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HubSpot deals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get deals: {str(e)}")


@router.get("/hubspot/companies")
async def list_hubspot_companies(
    limit: int = 100,
    after: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get companies from HubSpot CRM.
    """
    try:
        from src.config import settings
        api_key = settings.hubspot_api_key
        
        if not api_key:
            raise HTTPException(status_code=401, detail="HubSpot not configured")
        
        from src.integrations.connectors.hubspot import HubSpotConnector
        
        connector = HubSpotConnector(api_key)
        result = await connector.get_companies(limit=limit, after=after)
        
        await connector.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HubSpot companies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get companies: {str(e)}")


@router.post("/hubspot/search")
async def search_hubspot_contacts(
    email: Optional[str] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Search for contacts in HubSpot.
    """
    try:
        from src.config import settings
        api_key = settings.hubspot_api_key
        
        if not api_key:
            raise HTTPException(status_code=401, detail="HubSpot not configured")
        
        from src.integrations.connectors.hubspot import HubSpotConnector
        
        connector = HubSpotConnector(api_key)
        contacts = await connector.search_contacts(email=email, name=name, company=company)
        
        await connector.close()
        
        return {"contacts": [c.dict() for c in contacts]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search HubSpot contacts: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/hubspot/test")
async def test_hubspot_connection(user_id: str = Depends(get_current_user_id)):
    """
    Test HubSpot API connection.
    """
    try:
        from src.config import settings
        api_key = settings.hubspot_api_key
        
        if not api_key:
            return {"connected": False, "message": "HubSpot API key not configured"}
        
        from src.integrations.connectors.hubspot import HubSpotConnector
        
        connector = HubSpotConnector(api_key)
        connected = await connector.test_connection()
        
        await connector.close()
        
        return {
            "connected": connected,
            "message": "HubSpot connection successful" if connected else "HubSpot connection failed"
        }
        
    except Exception as e:
        logger.error(f"HubSpot test failed: {e}")
        return {"connected": False, "message": f"Error: {str(e)}"}


# ============================================================================
# Google Drive Integration Endpoints
# ============================================================================

@router.get("/google-drive/files")
async def list_drive_files(
    folder_id: Optional[str] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    List files from user's Google Drive.
    
    Args:
        folder_id: Folder ID (None for root)
        page_size: Files per page
        page_token: Pagination token
        
    Returns:
        Files list with pagination
    """
    from src.integrations.connectors.google_drive import GoogleDriveConnector
    from src.auth.google_oauth import GoogleOAuthManager
    
    # Get user's Google credentials
    oauth_manager = GoogleOAuthManager()
    credentials = await oauth_manager.get_user_credentials(user_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Google Drive. Please authorize first."
        )
    
    # Create Drive connector
    connector = GoogleDriveConnector(credentials)
    
    # List files
    result = await connector.list_files(
        folder_id=folder_id,
        page_size=page_size,
        page_token=page_token
    )
    
    return result


@router.get("/google-drive/folders")
async def list_drive_folders(
    parent_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    List folders from user's Google Drive.
    
    Args:
        parent_id: Parent folder ID (None for root)
        
    Returns:
        List of folders
    """
    from src.integrations.connectors.google_drive import GoogleDriveConnector
    from src.auth.google_oauth import GoogleOAuthManager
    
    oauth_manager = GoogleOAuthManager()
    credentials = await oauth_manager.get_user_credentials(user_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Google Drive. Please authorize first."
        )
    
    connector = GoogleDriveConnector(credentials)
    folders = await connector.get_folders(parent_id=parent_id)
    
    return {"folders": [f.dict() for f in folders]}


@router.get("/google-drive/search")
async def search_drive_files(
    q: str,
    page_size: int = 25,
    user_id: str = Depends(get_current_user_id)
):
    """
    Search for files in Google Drive.
    
    Args:
        q: Search query
        page_size: Max results
        
    Returns:
        List of matching files
    """
    from src.integrations.connectors.google_drive import GoogleDriveConnector
    from src.auth.google_oauth import GoogleOAuthManager
    
    oauth_manager = GoogleOAuthManager()
    credentials = await oauth_manager.get_user_credentials(user_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Google Drive. Please authorize first."
        )
    
    connector = GoogleDriveConnector(credentials)
    files = await connector.search_files(query=q, page_size=page_size)
    
    return {"files": [f.dict() for f in files]}


@router.get("/google-drive/file/{file_id}")
async def get_drive_file_info(
    file_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed info about a Drive file.
    
    Args:
        file_id: Google Drive file ID
        
    Returns:
        File information
    """
    from src.integrations.connectors.google_drive import GoogleDriveConnector
    from src.auth.google_oauth import GoogleOAuthManager
    
    oauth_manager = GoogleOAuthManager()
    credentials = await oauth_manager.get_user_credentials(user_id)
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Google Drive. Please authorize first."
        )
    
    connector = GoogleDriveConnector(credentials)
    file_info = await connector.get_file_info(file_id)
    
    return file_info.dict()


# HubSpot Contact Sync Endpoints
# ==============================

from src.hubspot_sync import get_sync_service, SyncStats


class HubSpotSyncRequest(BaseModel):
    """Request to trigger HubSpot sync"""
    batch_size: int = 100
    max_contacts: Optional[int] = None
    sync_type: str = "all"  # 'all' or 'chainge'


class HubSpotContactsResponse(BaseModel):
    """Response for contact queries"""
    contacts: List[Dict]
    total: int
    limit: int
    offset: int
    segment: Optional[str] = None


@router.post("/hubspot/sync", response_model=SyncStats)
async def sync_hubspot_contacts(
    request: HubSpotSyncRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Trigger a full HubSpot contact sync.
    
    Syncs ALL contacts from HubSpot including:
    - Contact properties (name, email, company, phone, etc.)
    - List memberships
    - Automatic segment tagging (CHAINge, High Value, Engaged, Cold)
    
    Pagination is handled automatically for 1000+ contacts.
    """
    try:
        sync_service = get_sync_service()
        
        if request.sync_type == "chainge":
            stats = await sync_service.sync_chainge_list()
        else:
            stats = await sync_service.sync_all_contacts(
                batch_size=request.batch_size,
                max_contacts=request.max_contacts
            )
        
        return stats
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/hubspot/synced-contacts", response_model=HubSpotContactsResponse)
async def get_synced_hubspot_contacts(
    segment: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get synced HubSpot contacts from local database with optional filtering.
    
    Query parameters:
    - segment: Filter by segment (chainge, high_value, engaged, cold)
    - limit: Max number of contacts to return (default 100)
    - offset: Pagination offset (default 0)
    
    Returns contacts from local database (previously synced from HubSpot).
    Use POST /hubspot/sync to sync contacts first.
    """
    try:
        sync_service = get_sync_service()
        result = sync_service.get_contacts(
            segment=segment,
            limit=limit,
            offset=offset
        )
        
        return HubSpotContactsResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contacts: {str(e)}")


@router.get("/hubspot/sync/stats", response_model=SyncStats)
async def get_hubspot_sync_stats(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get statistics from the last HubSpot sync.
    
    Returns:
    - Total contacts synced
    - Number of pages processed
    - Segment distribution
    - Errors encountered
    - Sync duration
    """
    try:
        sync_service = get_sync_service()
        return sync_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.delete("/hubspot/synced-contacts")
async def clear_synced_hubspot_contacts(
    user_id: str = Depends(get_current_user_id)
):
    """
    Clear all synced HubSpot contacts from local storage.
    
    Useful for testing or re-syncing from scratch.
    This only clears the local copy, not HubSpot data.
    """
    try:
        sync_service = get_sync_service()
        count = sync_service.clear_contacts()
        return {"cleared": count, "message": f"Cleared {count} contacts"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear contacts: {str(e)}")


# Ship Ship Ship: Add more endpoints as integrations are built
# - /api/integrations/{app_name}/data - Get synced data
# - /api/integrations/{app_name}/configure - Update integration settings
# - /api/integrations/{app_name}/test - Test connection
# - /api/integrations/webhooks/{app_name} - Handle webhooks
