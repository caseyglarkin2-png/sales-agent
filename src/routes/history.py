"""
History/Relationship API Routes.

Endpoints for getting relationship history and context.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/relationship/{email}")
async def get_relationship_summary(email: str) -> Dict[str, Any]:
    """Get comprehensive relationship summary for a contact."""
    try:
        from src.enrichment.history_enricher import get_history_enricher
        
        hubspot = None
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
        except Exception:
            pass
        
        enricher = get_history_enricher(hubspot_connector=hubspot)
        
        summary = await enricher.get_relationship_summary(email=email)
        
        return {
            "status": "success",
            "summary": summary.to_dict(),
        }
        
    except Exception as e:
        logger.error(f"Error getting relationship summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/{email}")
async def get_meeting_context(email: str, limit: int = 5) -> Dict[str, Any]:
    """Get recent meeting summaries for context."""
    try:
        from src.enrichment.history_enricher import get_history_enricher
        
        hubspot = None
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
        except Exception:
            pass
        
        enricher = get_history_enricher(hubspot_connector=hubspot)
        
        meetings = await enricher.get_meeting_context(
            email=email,
            limit=limit,
        )
        
        return {
            "status": "success",
            "email": email,
            "meetings": meetings,
            "total": len(meetings),
        }
        
    except Exception as e:
        logger.error(f"Error getting meeting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
