"""
Import Routes.

API endpoints for contact imports.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from src.imports import get_contact_importer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/imports", tags=["imports"])


class ManualImportRequest(BaseModel):
    contacts: List[Dict[str, Any]]
    campaign_id: Optional[str] = None


class HubSpotImportRequest(BaseModel):
    list_id: str
    campaign_id: Optional[str] = None


@router.get("/")
async def list_jobs(limit: int = 20) -> Dict[str, Any]:
    """List import jobs."""
    importer = get_contact_importer()
    jobs = importer.list_jobs(limit=limit)
    
    return {
        "jobs": jobs,
        "count": len(jobs),
    }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get import statistics."""
    importer = get_contact_importer()
    return importer.get_import_stats()


@router.get("/contacts")
async def get_contacts(
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get imported contacts."""
    importer = get_contact_importer()
    contacts = importer.get_imported_contacts(limit=limit, offset=offset)
    
    return {
        "contacts": contacts,
        "count": len(contacts),
        "offset": offset,
    }


@router.get("/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get import job details."""
    importer = get_contact_importer()
    job = importer.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    return {
        "job": job,
    }


@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    campaign_id: Optional[str] = None,
    skip_duplicates: bool = True,
) -> Dict[str, Any]:
    """Import contacts from CSV file."""
    importer = get_contact_importer()
    
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    job = await importer.import_from_csv(
        csv_content=csv_content,
        campaign_id=campaign_id,
        skip_duplicates=skip_duplicates,
    )
    
    return {
        "status": "success",
        "job": job.to_dict(),
    }


@router.post("/csv-text")
async def import_csv_text(
    csv_content: str,
    campaign_id: Optional[str] = None,
    skip_duplicates: bool = True,
) -> Dict[str, Any]:
    """Import contacts from CSV text content."""
    importer = get_contact_importer()
    
    job = await importer.import_from_csv(
        csv_content=csv_content,
        campaign_id=campaign_id,
        skip_duplicates=skip_duplicates,
    )
    
    return {
        "status": "success",
        "job": job.to_dict(),
    }


@router.post("/manual")
async def import_manual(request: ManualImportRequest) -> Dict[str, Any]:
    """Import contacts from manual list."""
    importer = get_contact_importer()
    
    job = await importer.import_manual(
        contacts=request.contacts,
        campaign_id=request.campaign_id,
    )
    
    return {
        "status": "success",
        "job": job.to_dict(),
    }


@router.post("/hubspot")
async def import_hubspot(request: HubSpotImportRequest) -> Dict[str, Any]:
    """Import contacts from HubSpot list."""
    importer = get_contact_importer()
    
    job = await importer.import_from_hubspot_list(
        list_id=request.list_id,
        campaign_id=request.campaign_id,
    )
    
    return {
        "status": "success",
        "job": job.to_dict(),
    }
