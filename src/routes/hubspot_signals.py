"""HubSpot Signal Ingestion API Routes.

Sprint 3 Tasks 3.5 + 3.6 - Status endpoint and manual refresh trigger.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.auth.decorators import get_current_user
from src.models.user import User
from src.integrations.hubspot.client import get_hubspot_client
from src.integrations.hubspot.signals import SignalDetector
from src.integrations.hubspot.ingestion import SignalIngestionService, IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hubspot", tags=["hubspot"])


# =============================================================================
# Response Models
# =============================================================================

class IngestionStatusResponse(BaseModel):
    """Response for ingestion status."""
    status: str
    last_ingestion: Optional[Dict[str, Any]] = None
    queue_status: Dict[str, int] = {}
    items_created_today: int = 0
    hubspot_connected: bool = False


class RefreshResponse(BaseModel):
    """Response for manual refresh."""
    message: str
    signals_detected: int
    items_created: int
    items_skipped: int
    duration_seconds: float


class HubSpotStatusResponse(BaseModel):
    """Response for HubSpot connection status."""
    connected: bool
    rate_limit_stats: Dict[str, int] = {}
    cache_stats: Dict[str, int] = {}


class SignalPreview(BaseModel):
    """A previewed signal."""
    type: str
    priority: str
    title: str
    description: str
    reasoning: str
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    idempotency_hash: str


class SignalPreviewResponse(BaseModel):
    """Response for signal preview."""
    count: int
    signals: List[SignalPreview]


# =============================================================================
# State (in production, use Redis or similar)
# =============================================================================

_last_ingestion_result: Optional[IngestionResult] = None
_ingestion_running: bool = False


# =============================================================================
# Routes
# =============================================================================

@router.get("/signals/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current signal ingestion status.
    
    Returns:
    - Last ingestion results
    - Queue item counts by status
    - HubSpot connection status
    """
    service = SignalIngestionService(db)
    
    # Check HubSpot connection
    hubspot_connected = False
    try:
        client = get_hubspot_client()
        hubspot_connected = await client.test_connection()
        await client.close()
    except Exception as e:
        logger.warning(f"HubSpot connection check failed: {e}")
    
    status = await service.get_ingestion_status()
    
    return IngestionStatusResponse(
        status=status.get("status", "unknown"),
        last_ingestion=_last_ingestion_result.to_dict() if _last_ingestion_result else None,
        queue_status=status.get("queue_status", {}),
        items_created_today=status.get("items_created_today", 0),
        hubspot_connected=hubspot_connected,
    )


@router.post("/signals/refresh", response_model=RefreshResponse)
async def trigger_refresh(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger signal detection and ingestion.
    
    This will:
    1. Connect to HubSpot and fetch latest data
    2. Detect signals from the data
    3. Create queue items for new signals
    
    Idempotent: running multiple times won't create duplicates.
    """
    global _last_ingestion_result, _ingestion_running
    
    if _ingestion_running:
        raise HTTPException(
            status_code=429,
            detail="Ingestion already in progress. Please wait."
        )
    
    _ingestion_running = True
    
    try:
        # Get HubSpot client
        client = get_hubspot_client()
        
        # Detect signals
        detector = SignalDetector(client)
        signals = await detector.detect_all()
        
        # Ingest into queue
        service = SignalIngestionService(db)
        result = await service.ingest_signals(signals, owner=current_user.email)
        
        # Store result
        _last_ingestion_result = result
        
        await client.close()
        
        return RefreshResponse(
            message=f"Detected {result.signals_detected} signals, created {result.items_created} new queue items",
            signals_detected=result.signals_detected,
            items_created=result.items_created,
            items_skipped=result.items_skipped,
            duration_seconds=result.duration_seconds,
        )
        
    except ValueError as e:
        logger.error(f"HubSpot not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail="HubSpot API key not configured. Set HUBSPOT_API_KEY environment variable."
        )
    except Exception as e:
        logger.error(f"Signal refresh failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Signal refresh failed: {str(e)}"
        )
    finally:
        _ingestion_running = False


@router.get("/status", response_model=HubSpotStatusResponse)
async def get_hubspot_status(
    current_user: User = Depends(get_current_user),
):
    """Get HubSpot connection and rate limit status."""
    try:
        client = get_hubspot_client()
        connected = await client.test_connection()
        
        response = HubSpotStatusResponse(
            connected=connected,
            rate_limit_stats=client.stats,
            cache_stats=client.cache.stats if client.cache else {},
        )
        
        await client.close()
        return response
        
    except ValueError as e:
        # API key not configured
        return HubSpotStatusResponse(
            connected=False,
            rate_limit_stats={},
            cache_stats={},
        )
    except Exception as e:
        logger.error(f"HubSpot status check failed: {e}")
        return HubSpotStatusResponse(
            connected=False,
            rate_limit_stats={},
            cache_stats={},
        )


@router.get("/signals/preview", response_model=SignalPreviewResponse)
async def preview_signals(
    current_user: User = Depends(get_current_user),
):
    """Preview what signals would be detected without ingesting.
    
    Useful for testing signal detection rules.
    """
    try:
        client = get_hubspot_client()
        detector = SignalDetector(client)
        signals = await detector.detect_all()
        await client.close()
        
        return SignalPreviewResponse(
            count=len(signals),
            signals=[
                SignalPreview(
                    type=s.type.value,
                    priority=s.priority.value,
                    title=s.title,
                    description=s.description,
                    reasoning=s.reasoning,
                    contact_id=s.contact_id,
                    deal_id=s.deal_id,
                    idempotency_hash=s.idempotency_hash,
                )
                for s in signals
            ],
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail="HubSpot API key not configured. Set HUBSPOT_API_KEY environment variable."
        )
    except Exception as e:
        logger.error(f"Signal preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Signal preview failed: {str(e)}"
        )
