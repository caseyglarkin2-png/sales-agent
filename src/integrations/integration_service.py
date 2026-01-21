"""
Integration Service - Third-Party Integration Management
=========================================================
Handles CRM, marketing, and other integrations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class IntegrationType(str, Enum):
    """Integration type."""
    CRM = "crm"
    MARKETING = "marketing"
    EMAIL = "email"
    CALENDAR = "calendar"
    COMMUNICATION = "communication"
    ANALYTICS = "analytics"
    PAYMENT = "payment"
    STORAGE = "storage"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Integration status."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    PAUSED = "paused"


class SyncDirection(str, Enum):
    """Sync direction."""
    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


class SyncFrequency(str, Enum):
    """Sync frequency."""
    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


@dataclass
class FieldMapping:
    """Field mapping between systems."""
    id: str
    source_field: str
    target_field: str
    transform: Optional[str] = None  # Function name for transformation
    default_value: Optional[str] = None


@dataclass
class SyncConfig:
    """Sync configuration."""
    id: str
    entity_type: str  # contacts, deals, accounts, etc.
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    frequency: SyncFrequency = SyncFrequency.HOURLY
    
    # Mappings
    field_mappings: list[FieldMapping] = field(default_factory=list)
    
    # Filters
    filters: dict[str, Any] = field(default_factory=dict)
    
    # Settings
    create_new: bool = True
    update_existing: bool = True
    delete_missing: bool = False
    
    is_enabled: bool = True
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None


@dataclass
class SyncLog:
    """Sync execution log."""
    id: str
    integration_id: str
    config_id: str
    
    # Results
    status: str = "running"  # running, success, error
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    errors: list[str] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class OAuthCredentials:
    """OAuth credentials."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None


@dataclass
class Integration:
    """A third-party integration."""
    id: str
    name: str
    provider: str  # salesforce, hubspot, etc.
    integration_type: IntegrationType
    
    # Status
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    
    # Credentials
    credentials: Optional[dict[str, Any]] = None  # Encrypted in production
    oauth: Optional[OAuthCredentials] = None
    
    # Configuration
    sync_configs: list[SyncConfig] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    external_account_id: Optional[str] = None
    external_account_name: Optional[str] = None
    
    # Sync state
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Owner
    connected_by: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IntegrationProvider:
    """An available integration provider."""
    id: str
    name: str
    description: str
    integration_type: IntegrationType
    
    # Display
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    
    # Auth
    auth_type: str = "oauth2"  # oauth2, api_key, basic
    oauth_url: Optional[str] = None
    scopes: list[str] = field(default_factory=list)
    
    # Capabilities
    supported_entities: list[str] = field(default_factory=list)
    supports_realtime: bool = False
    supports_webhooks: bool = False
    
    is_available: bool = True


class IntegrationService:
    """Service for integration management."""
    
    def __init__(self):
        self.integrations: dict[str, Integration] = {}
        self.providers: dict[str, IntegrationProvider] = {}
        self.sync_logs: dict[str, list[SyncLog]] = {}
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize available providers."""
        providers = [
            IntegrationProvider(
                id="salesforce",
                name="Salesforce",
                description="Connect to Salesforce CRM",
                integration_type=IntegrationType.CRM,
                auth_type="oauth2",
                scopes=["api", "refresh_token"],
                supported_entities=["contacts", "accounts", "opportunities", "leads"],
                supports_webhooks=True,
            ),
            IntegrationProvider(
                id="hubspot",
                name="HubSpot",
                description="Connect to HubSpot CRM",
                integration_type=IntegrationType.CRM,
                auth_type="oauth2",
                scopes=["contacts", "deals"],
                supported_entities=["contacts", "companies", "deals"],
                supports_webhooks=True,
            ),
            IntegrationProvider(
                id="slack",
                name="Slack",
                description="Connect to Slack for notifications",
                integration_type=IntegrationType.COMMUNICATION,
                auth_type="oauth2",
                scopes=["chat:write", "channels:read"],
                supported_entities=["messages", "channels"],
            ),
            IntegrationProvider(
                id="gmail",
                name="Gmail",
                description="Connect Gmail for email sync",
                integration_type=IntegrationType.EMAIL,
                auth_type="oauth2",
                scopes=["gmail.readonly", "gmail.send"],
                supported_entities=["emails"],
                supports_realtime=True,
            ),
            IntegrationProvider(
                id="google_calendar",
                name="Google Calendar",
                description="Sync with Google Calendar",
                integration_type=IntegrationType.CALENDAR,
                auth_type="oauth2",
                scopes=["calendar.events"],
                supported_entities=["events"],
                supports_realtime=True,
            ),
            IntegrationProvider(
                id="stripe",
                name="Stripe",
                description="Payment processing with Stripe",
                integration_type=IntegrationType.PAYMENT,
                auth_type="api_key",
                supported_entities=["payments", "subscriptions", "invoices"],
                supports_webhooks=True,
            ),
            IntegrationProvider(
                id="mailchimp",
                name="Mailchimp",
                description="Email marketing with Mailchimp",
                integration_type=IntegrationType.MARKETING,
                auth_type="oauth2",
                supported_entities=["lists", "campaigns", "subscribers"],
            ),
        ]
        
        for provider in providers:
            self.providers[provider.id] = provider
    
    # Provider operations
    async def list_providers(
        self,
        integration_type: Optional[IntegrationType] = None,
        available_only: bool = True
    ) -> list[IntegrationProvider]:
        """List available integration providers."""
        providers = list(self.providers.values())
        
        if integration_type:
            providers = [p for p in providers if p.integration_type == integration_type]
        if available_only:
            providers = [p for p in providers if p.is_available]
        
        providers.sort(key=lambda p: p.name)
        return providers
    
    async def get_provider(self, provider_id: str) -> Optional[IntegrationProvider]:
        """Get a provider by ID."""
        return self.providers.get(provider_id)
    
    # Integration CRUD
    async def create_integration(
        self,
        name: str,
        provider: str,
        connected_by: Optional[str] = None,
        credentials: Optional[dict[str, Any]] = None,
        settings: Optional[dict[str, Any]] = None
    ) -> Optional[Integration]:
        """Create an integration."""
        provider_info = self.providers.get(provider)
        if not provider_info:
            return None
        
        integration = Integration(
            id=str(uuid.uuid4()),
            name=name,
            provider=provider,
            integration_type=provider_info.integration_type,
            connected_by=connected_by,
            credentials=credentials,
            settings=settings or {},
        )
        
        self.integrations[integration.id] = integration
        self.sync_logs[integration.id] = []
        
        return integration
    
    async def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get an integration by ID."""
        return self.integrations.get(integration_id)
    
    async def update_integration(
        self,
        integration_id: str,
        updates: dict[str, Any]
    ) -> Optional[Integration]:
        """Update an integration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return None
        
        for key, value in updates.items():
            if hasattr(integration, key):
                setattr(integration, key, value)
        
        integration.updated_at = datetime.utcnow()
        return integration
    
    async def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration."""
        if integration_id in self.integrations:
            del self.integrations[integration_id]
            return True
        return False
    
    async def list_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        status: Optional[IntegrationStatus] = None,
        limit: int = 100
    ) -> list[Integration]:
        """List integrations."""
        integrations = list(self.integrations.values())
        
        if integration_type:
            integrations = [i for i in integrations if i.integration_type == integration_type]
        if status:
            integrations = [i for i in integrations if i.status == status]
        
        integrations.sort(key=lambda i: i.name)
        return integrations[:limit]
    
    # Connection management
    async def connect(
        self,
        integration_id: str,
        credentials: Optional[dict[str, Any]] = None,
        oauth: Optional[dict[str, Any]] = None
    ) -> bool:
        """Connect an integration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return False
        
        if credentials:
            integration.credentials = credentials
        
        if oauth:
            integration.oauth = OAuthCredentials(
                access_token=oauth.get("access_token", ""),
                refresh_token=oauth.get("refresh_token"),
                expires_at=oauth.get("expires_at"),
                scope=oauth.get("scope"),
            )
        
        integration.status = IntegrationStatus.CONNECTED
        integration.updated_at = datetime.utcnow()
        
        return True
    
    async def disconnect(self, integration_id: str) -> bool:
        """Disconnect an integration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return False
        
        integration.status = IntegrationStatus.DISCONNECTED
        integration.credentials = None
        integration.oauth = None
        integration.updated_at = datetime.utcnow()
        
        return True
    
    async def pause(self, integration_id: str) -> bool:
        """Pause an integration."""
        integration = self.integrations.get(integration_id)
        if not integration or integration.status != IntegrationStatus.CONNECTED:
            return False
        
        integration.status = IntegrationStatus.PAUSED
        integration.updated_at = datetime.utcnow()
        
        return True
    
    async def resume(self, integration_id: str) -> bool:
        """Resume a paused integration."""
        integration = self.integrations.get(integration_id)
        if not integration or integration.status != IntegrationStatus.PAUSED:
            return False
        
        integration.status = IntegrationStatus.CONNECTED
        integration.updated_at = datetime.utcnow()
        
        return True
    
    # Sync configuration
    async def add_sync_config(
        self,
        integration_id: str,
        entity_type: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        frequency: SyncFrequency = SyncFrequency.HOURLY,
        field_mappings: list[dict[str, Any]] = None,
        **kwargs
    ) -> Optional[SyncConfig]:
        """Add a sync configuration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return None
        
        mappings = []
        if field_mappings:
            for m in field_mappings:
                mappings.append(FieldMapping(
                    id=str(uuid.uuid4()),
                    source_field=m.get("source", ""),
                    target_field=m.get("target", ""),
                    transform=m.get("transform"),
                    default_value=m.get("default"),
                ))
        
        config = SyncConfig(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            direction=direction,
            frequency=frequency,
            field_mappings=mappings,
            **kwargs
        )
        
        integration.sync_configs.append(config)
        integration.updated_at = datetime.utcnow()
        
        return config
    
    async def update_sync_config(
        self,
        integration_id: str,
        config_id: str,
        updates: dict[str, Any]
    ) -> Optional[SyncConfig]:
        """Update a sync configuration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return None
        
        config = next((c for c in integration.sync_configs if c.id == config_id), None)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        integration.updated_at = datetime.utcnow()
        return config
    
    async def remove_sync_config(
        self,
        integration_id: str,
        config_id: str
    ) -> bool:
        """Remove a sync configuration."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return False
        
        original = len(integration.sync_configs)
        integration.sync_configs = [c for c in integration.sync_configs if c.id != config_id]
        
        if len(integration.sync_configs) < original:
            integration.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Sync execution
    async def trigger_sync(
        self,
        integration_id: str,
        config_id: Optional[str] = None
    ) -> Optional[SyncLog]:
        """Trigger a sync."""
        integration = self.integrations.get(integration_id)
        if not integration or integration.status != IntegrationStatus.CONNECTED:
            return None
        
        # Find config to sync
        if config_id:
            config = next((c for c in integration.sync_configs if c.id == config_id), None)
            if not config:
                return None
        else:
            # Sync all enabled configs
            config = integration.sync_configs[0] if integration.sync_configs else None
        
        if not config:
            return None
        
        # Create sync log
        log = SyncLog(
            id=str(uuid.uuid4()),
            integration_id=integration_id,
            config_id=config.id,
        )
        
        self.sync_logs[integration_id].append(log)
        
        # Simulate sync (in real implementation, this would call the provider API)
        integration.status = IntegrationStatus.SYNCING
        
        # Simulate completion
        import random
        log.records_processed = random.randint(10, 100)
        log.records_created = random.randint(0, 10)
        log.records_updated = random.randint(0, 20)
        log.status = "success"
        log.completed_at = datetime.utcnow()
        
        config.last_sync = datetime.utcnow()
        integration.last_sync = datetime.utcnow()
        integration.status = IntegrationStatus.CONNECTED
        
        return log
    
    async def get_sync_logs(
        self,
        integration_id: str,
        limit: int = 50
    ) -> list[SyncLog]:
        """Get sync logs for an integration."""
        logs = self.sync_logs.get(integration_id, [])
        logs.sort(key=lambda l: l.started_at, reverse=True)
        return logs[:limit]
    
    # OAuth flow helpers
    async def get_oauth_url(
        self,
        provider_id: str,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> Optional[str]:
        """Get OAuth authorization URL."""
        provider = self.providers.get(provider_id)
        if not provider or provider.auth_type != "oauth2":
            return None
        
        # In real implementation, build OAuth URL
        # This is a placeholder
        return f"https://oauth.example.com/{provider_id}/authorize?redirect_uri={redirect_uri}&state={state}"
    
    async def exchange_oauth_code(
        self,
        provider_id: str,
        code: str,
        redirect_uri: str
    ) -> Optional[dict[str, Any]]:
        """Exchange OAuth code for tokens."""
        provider = self.providers.get(provider_id)
        if not provider:
            return None
        
        # In real implementation, exchange code for tokens
        # This is a placeholder
        return {
            "access_token": f"access_{uuid.uuid4()}",
            "refresh_token": f"refresh_{uuid.uuid4()}",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
    
    # Health check
    async def check_health(self, integration_id: str) -> dict[str, Any]:
        """Check integration health."""
        integration = self.integrations.get(integration_id)
        if not integration:
            return {"healthy": False, "error": "Integration not found"}
        
        if integration.status == IntegrationStatus.DISCONNECTED:
            return {"healthy": False, "error": "Integration disconnected"}
        
        if integration.status == IntegrationStatus.ERROR:
            return {"healthy": False, "error": integration.last_error}
        
        # In real implementation, make test API call
        return {
            "healthy": True,
            "status": integration.status.value,
            "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
        }


# Singleton instance
_integration_service: Optional[IntegrationService] = None


def get_integration_service() -> IntegrationService:
    """Get integration service singleton."""
    global _integration_service
    if _integration_service is None:
        _integration_service = IntegrationService()
    return _integration_service
