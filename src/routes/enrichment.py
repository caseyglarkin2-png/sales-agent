"""API routes for contact enrichment."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.enrichment.contact_enricher import get_contact_enricher
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


class EnrichContactRequest(BaseModel):
    """Request to enrich a single contact."""
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    job_title: str = ""


class EnrichBatchRequest(BaseModel):
    """Request to enrich multiple contacts."""
    contacts: List[Dict[str, Any]]


@router.post("/contact")
async def enrich_contact(request: EnrichContactRequest) -> Dict[str, Any]:
    """Enrich a single contact with additional data."""
    try:
        enricher = get_contact_enricher()
        
        result = await enricher.enrich_contact(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            job_title=request.job_title,
        )
        
        return {
            "status": "success",
            "enriched_contact": result.model_dump(),
        }
    except Exception as e:
        logger.error(f"Error enriching contact {request.email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def enrich_batch(request: EnrichBatchRequest) -> Dict[str, Any]:
    """Enrich multiple contacts."""
    try:
        enricher = get_contact_enricher()
        
        results = await enricher.enrich_batch(
            contacts=request.contacts,
            max_concurrent=5,
        )
        
        return {
            "status": "success",
            "count": len(results),
            "enriched_contacts": [r.model_dump() for r in results],
        }
    except Exception as e:
        logger.error(f"Error enriching batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_enrichment_sources() -> Dict[str, Any]:
    """Get available enrichment sources."""
    import os
    
    sources = {
        "hubspot": bool(os.environ.get("HUBSPOT_API_KEY")),
        "clearbit": bool(os.environ.get("CLEARBIT_API_KEY")),
        "apollo": bool(os.environ.get("APOLLO_API_KEY")),
        "domain_extraction": True,  # Always available
    }
    
    return {
        "sources": sources,
        "active_count": sum(1 for v in sources.values() if v),
    }
