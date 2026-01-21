"""
Export Routes - Data Export API Endpoints
==========================================
REST API for exporting data.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from src.exports.export_service import (
    get_export_service,
    ExportFormat,
    ExportType,
    ExportStatus,
)

router = APIRouter(prefix="/exports", tags=["exports"])


class CreateExportRequest(BaseModel):
    """Request to create an export job."""
    export_type: str
    format: str = "csv"
    columns: Optional[list[dict]] = None
    filters: Optional[list[dict]] = None
    include_headers: bool = True


@router.post("")
async def create_export(request: CreateExportRequest):
    """Create a new export job."""
    service = get_export_service()
    
    try:
        export_type = ExportType(request.export_type)
        format = ExportFormat(request.format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    job = await service.create_export(
        export_type=export_type,
        format=format,
        columns=request.columns,
        filters=request.filters,
        include_headers=request.include_headers
    )
    
    # Process immediately for demo
    job = await service.process_export(job.id)
    
    return {
        "success": True,
        "job": {
            "id": job.id,
            "export_type": job.export_type.value,
            "format": job.format.value,
            "status": job.status.value,
            "record_count": job.record_count,
            "file_name": job.file_name,
            "file_size": job.file_size,
            "created_at": job.created_at.isoformat()
        }
    }


@router.get("")
async def list_exports(
    status: Optional[str] = None,
    export_type: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """List export jobs."""
    service = get_export_service()
    
    status_enum = ExportStatus(status) if status else None
    type_enum = ExportType(export_type) if export_type else None
    
    jobs = await service.list_jobs(
        status=status_enum,
        export_type=type_enum,
        limit=limit
    )
    
    return {
        "exports": [
            {
                "id": j.id,
                "export_type": j.export_type.value,
                "format": j.format.value,
                "status": j.status.value,
                "record_count": j.record_count,
                "file_name": j.file_name,
                "file_size": j.file_size,
                "progress_percent": j.progress_percent,
                "created_at": j.created_at.isoformat(),
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "expires_at": j.expires_at.isoformat() if j.expires_at else None
            }
            for j in jobs
        ],
        "count": len(jobs)
    }


@router.get("/templates")
async def get_export_templates():
    """Get predefined export templates."""
    service = get_export_service()
    
    templates = await service.get_export_templates()
    
    return {"templates": templates}


@router.get("/types")
async def list_export_types():
    """List available export types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in ExportType
        ]
    }


@router.get("/formats")
async def list_export_formats():
    """List available export formats."""
    return {
        "formats": [
            {"value": f.value, "name": f.name}
            for f in ExportFormat
        ]
    }


@router.get("/{job_id}")
async def get_export_job(job_id: str):
    """Get export job details."""
    service = get_export_service()
    
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return {
        "id": job.id,
        "export_type": job.export_type.value,
        "format": job.format.value,
        "status": job.status.value,
        "record_count": job.record_count,
        "file_name": job.file_name,
        "file_size": job.file_size,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None
    }


@router.get("/{job_id}/download")
async def download_export(job_id: str):
    """Download export file."""
    service = get_export_service()
    
    download = await service.download_export(job_id)
    if not download:
        raise HTTPException(status_code=404, detail="Export not found or expired")
    
    return Response(
        content=download["content"],
        media_type=download["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{download["file_name"]}"'
        }
    )


@router.get("/{job_id}/preview")
async def preview_export(
    job_id: str,
    limit: int = Query(default=10, le=100)
):
    """Preview export data (first N rows)."""
    service = get_export_service()
    
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    if job.status != ExportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Export not completed")
    
    # Parse content based on format
    preview_data = []
    
    if job.format == ExportFormat.JSON:
        import json
        content = json.loads(job.file_content)
        preview_data = content.get("data", [])[:limit]
    
    elif job.format == ExportFormat.CSV:
        import csv
        import io
        reader = csv.DictReader(io.StringIO(job.file_content))
        preview_data = [row for row in list(reader)[:limit]]
    
    return {
        "job_id": job_id,
        "format": job.format.value,
        "total_records": job.record_count,
        "preview_count": len(preview_data),
        "preview": preview_data
    }


@router.delete("/{job_id}")
async def delete_export_job(job_id: str):
    """Delete an export job."""
    service = get_export_service()
    
    success = await service.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return {"success": True, "deleted": job_id}


@router.post("/cleanup")
async def cleanup_expired_exports():
    """Clean up expired export jobs."""
    service = get_export_service()
    
    cleaned = await service.cleanup_expired()
    
    return {
        "success": True,
        "expired_count": cleaned
    }


@router.post("/quick/{export_type}")
async def quick_export(
    export_type: str,
    format: str = Query(default="csv")
):
    """Quick export with default settings."""
    service = get_export_service()
    
    try:
        type_enum = ExportType(export_type)
        format_enum = ExportFormat(format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    job = await service.create_export(
        export_type=type_enum,
        format=format_enum
    )
    
    job = await service.process_export(job.id)
    
    if job.status == ExportStatus.COMPLETED:
        download = await service.download_export(job.id)
        
        return Response(
            content=download["content"],
            media_type=download["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{download["file_name"]}"'
            }
        )
    else:
        raise HTTPException(status_code=500, detail=job.error_message or "Export failed")
