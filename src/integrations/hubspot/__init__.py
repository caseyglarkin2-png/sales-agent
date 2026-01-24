"""HubSpot Integration Module.

Provides rate-limited, cached access to HubSpot CRM data.
"""
from .client import (
    HubSpotClient,
    HubSpotCache,
    TokenBucket,
    HubSpotContact,
    HubSpotDeal,
    HubSpotCompany,
    HubSpotEmail,
    HubSpotMeeting,
    PipelineStage,
    get_hubspot_client,
)
from .signals import (
    Signal,
    SignalType,
    SignalDetector,
    get_signal_detector,
)
from .ingestion import (
    SignalIngestionService,
    IngestionResult,
    signal_to_queue_item,
    get_ingestion_service,
)

__all__ = [
    # Client
    "HubSpotClient",
    "HubSpotCache",
    "TokenBucket",
    "get_hubspot_client",
    # Models
    "HubSpotContact",
    "HubSpotDeal",
    "HubSpotCompany",
    "HubSpotEmail",
    "HubSpotMeeting",
    "PipelineStage",
    # Signals
    "Signal",
    "SignalType",
    "SignalDetector",
    "get_signal_detector",
    # Ingestion
    "SignalIngestionService",
    "IngestionResult",
    "signal_to_queue_item",
    "get_ingestion_service",
]
