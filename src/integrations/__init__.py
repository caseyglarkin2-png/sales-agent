"""Integrations module for third-party integration management."""

from .integration_service import (
    IntegrationService,
    Integration,
    IntegrationType,
    IntegrationStatus,
    SyncConfig,
    get_integration_service,
)
