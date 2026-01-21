"""API routes for HubSpot form submission import."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from src.logger import get_logger
from src.forms.form_importer import create_form_importer
from src.connectors.hubspot import create_hubspot_connector

logger = get_logger(__name__)

router = APIRouter(prefix="/api/forms", tags=["forms"])


class ImportFormSubmissionsRequest(BaseModel):
    """Request to import form submissions."""
    form_name: str = "CHAINge NA"
    limit: int = 50
    days_back: int = 90
    voice_profile: str = "freight_marketer_voice"


@router.post("/import-to-queue", response_model=Dict[str, Any])
async def import_form_submissions_to_queue(
    request: ImportFormSubmissionsRequest
) -> Dict[str, Any]:
    """Import HubSpot form submissions to contact queue.
    
    Fetches form submissions (e.g., CHAINge NA) from HubSpot and adds them
    to the contact queue for automated research and email generation.
    """
    try:
        logger.info(f"Importing form submissions: {request.form_name}")
        
        # Create importer with HubSpot connector
        hubspot = create_hubspot_connector()
        importer = create_form_importer(hubspot)
        
        # Import to queue
        result = await importer.import_to_contact_queue(
            form_name=request.form_name,
            limit=request.limit,
            days_back=request.days_back,
            voice_profile=request.voice_profile,
        )
        
        return {
            "status": "success",
            "form_name": request.form_name,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error importing form submissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/submissions", response_model=Dict[str, Any])
async def list_form_submissions(
    limit: int = 100,
    days_back: int = 90,
) -> Dict[str, Any]:
    """List recent form submissions from HubSpot."""
    try:
        hubspot = create_hubspot_connector()
        importer = create_form_importer(hubspot)
        
        submissions = await importer.get_form_submissions(
            form_guid=None,  # Get all recent
            limit=limit,
            days_back=days_back,
        )
        
        return {
            "submissions": submissions,
            "count": len(submissions),
        }
        
    except Exception as e:
        logger.error(f"Error listing form submissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
