"""Integrations module for third-party integration management."""

from .integration_service import (
    IntegrationService,
    Integration,
    IntegrationType,
    IntegrationStatus,
    SyncConfig,
    SyncDirection,
    SyncFrequency,
    get_integration_service,
)
