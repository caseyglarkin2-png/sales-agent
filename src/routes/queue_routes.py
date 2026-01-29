"""
Queue Routes - Background job and bulk processing management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/queue", tags=["Queue"])


class JobType(str, Enum):
    BULK_EMAIL = "bulk_email"
    BULK_IMPORT = "bulk_import"
    BULK_EXPORT = "bulk_export"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
    DATA_SYNC = "data_sync"
    REPORT_GENERATION = "report_generation"
    ENRICHMENT = "enrichment"
    DEDUPLICATION = "deduplication"
    SCORING = "scoring"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    NOTIFICATION = "notification"
    WEBHOOK_DELIVERY = "webhook_delivery"
    AI_PROCESSING = "ai_processing"


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class JobCreate(BaseModel):
    job_type: JobType
    name: Optional[str] = None
    priority: JobPriority = JobPriority.NORMAL
    payload: Dict[str, Any]
    scheduled_at: Optional[str] = None  # For scheduled jobs
    retry_config: Optional[Dict[str, Any]] = None
    timeout_seconds: int = Field(default=3600, ge=60, le=86400)
    webhook_url: Optional[str] = None  # Callback on completion


class BulkOperationCreate(BaseModel):
    operation_type: str  # update, delete, tag, assign, etc.
    entity_type: str  # contacts, deals, accounts, etc.
    entity_ids: Optional[List[str]] = None
    filter_criteria: Optional[Dict[str, Any]] = None  # Alternative to entity_ids
    changes: Dict[str, Any]  # What to update
    dry_run: bool = False


class QueueConfig(BaseModel):
    max_concurrent_jobs: int = Field(default=10, ge=1, le=100)
    default_timeout_seconds: int = Field(default=3600, ge=60, le=86400)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)


# In-memory storage
jobs = {}
bulk_operations = {}
queue_config = {}
worker_stats = {}


@router.post("/jobs")
async def create_job(
    request: JobCreate,
    tenant_id: str = Query(default="default")
):
    """Create a background job"""
    import uuid
    
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    job = {
        "id": job_id,
        "job_type": request.job_type.value,
        "name": request.name or f"{request.job_type.value}_{job_id[:8]}",
        "priority": request.priority.value,
        "payload": request.payload,
        "status": JobStatus.QUEUED.value,
        "progress": 0,
        "progress_message": "Queued for processing",
        "scheduled_at": request.scheduled_at,
        "retry_config": request.retry_config or {"max_retries": 3, "delay_seconds": 60},
        "retry_count": 0,
        "timeout_seconds": request.timeout_seconds,
        "webhook_url": request.webhook_url,
        "result": None,
        "error": None,
        "queued_at": now.isoformat(),
        "started_at": None,
        "completed_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    jobs[job_id] = job
    logger.info("job_created", job_id=job_id, type=request.job_type.value, priority=request.priority.value)
    return job


@router.get("/jobs")
async def list_jobs(
    job_type: Optional[JobType] = None,
    status: Optional[JobStatus] = None,
    priority: Optional[JobPriority] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List background jobs"""
    result = [j for j in jobs.values() if j.get("tenant_id") == tenant_id]
    
    if job_type:
        result = [j for j in result if j.get("job_type") == job_type.value]
    if status:
        result = [j for j in result if j.get("status") == status.value]
    if priority:
        result = [j for j in result if j.get("priority") == priority.value]
    
    # Sort by priority then created_at
    priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    result.sort(key=lambda x: (priority_order.get(x.get("priority", "normal"), 2), x.get("created_at", "")))
    
    return {
        "jobs": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status (lightweight endpoint for polling)"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress"),
        "progress_message": job.get("progress_message"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error": job.get("error")
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending or running job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] in [JobStatus.COMPLETED.value, JobStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    
    job["status"] = JobStatus.CANCELLED.value
    job["cancelled_at"] = datetime.utcnow().isoformat()
    
    logger.info("job_cancelled", job_id=job_id)
    return job


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """Retry a failed job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != JobStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Can only retry failed jobs")
    
    job["status"] = JobStatus.QUEUED.value
    job["retry_count"] = job.get("retry_count", 0) + 1
    job["error"] = None
    job["queued_at"] = datetime.utcnow().isoformat()
    
    logger.info("job_retried", job_id=job_id, retry_count=job["retry_count"])
    return job


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != JobStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Can only pause running jobs")
    
    job["status"] = JobStatus.PAUSED.value
    job["paused_at"] = datetime.utcnow().isoformat()
    
    logger.info("job_paused", job_id=job_id)
    return job


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != JobStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Can only resume paused jobs")
    
    job["status"] = JobStatus.RUNNING.value
    job["resumed_at"] = datetime.utcnow().isoformat()
    
    logger.info("job_resumed", job_id=job_id)
    return job


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a completed or cancelled job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] in [JobStatus.RUNNING.value, JobStatus.QUEUED.value]:
        raise HTTPException(status_code=400, detail="Cannot delete active jobs")
    
    del jobs[job_id]
    logger.info("job_deleted", job_id=job_id)
    return {"status": "deleted", "job_id": job_id}


@router.post("/bulk-operations")
async def create_bulk_operation(
    request: BulkOperationCreate,
    tenant_id: str = Query(default="default")
):
    """Create a bulk operation"""
    import uuid
    
    operation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Determine record count
    if request.entity_ids:
        record_count = len(request.entity_ids)
    else:
        record_count = 0  # Would be determined by filter
    
    operation = {
        "id": operation_id,
        "operation_type": request.operation_type,
        "entity_type": request.entity_type,
        "entity_ids": request.entity_ids,
        "filter_criteria": request.filter_criteria,
        "changes": request.changes,
        "dry_run": request.dry_run,
        "status": "pending" if not request.dry_run else "dry_run",
        "total_records": record_count,
        "processed_records": 0,
        "success_count": 0,
        "failure_count": 0,
        "failures": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "started_at": None,
        "completed_at": None
    }
    
    if request.dry_run:
        # Simulate dry run
        operation["status"] = "dry_run_complete"
        operation["preview"] = {
            "records_affected": record_count,
            "changes": request.changes,
            "warnings": []
        }
    else:
        # Create associated job
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "job_type": f"bulk_{request.operation_type}",
            "name": f"Bulk {request.operation_type} on {request.entity_type}",
            "priority": "normal",
            "payload": {"operation_id": operation_id},
            "status": JobStatus.QUEUED.value,
            "progress": 0,
            "tenant_id": tenant_id,
            "created_at": now.isoformat()
        }
        jobs[job_id] = job
        operation["job_id"] = job_id
    
    bulk_operations[operation_id] = operation
    logger.info("bulk_operation_created", operation_id=operation_id, type=request.operation_type, records=record_count)
    return operation


@router.get("/bulk-operations")
async def list_bulk_operations(
    operation_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List bulk operations"""
    result = [o for o in bulk_operations.values() if o.get("tenant_id") == tenant_id]
    
    if operation_type:
        result = [o for o in result if o.get("operation_type") == operation_type]
    if entity_type:
        result = [o for o in result if o.get("entity_type") == entity_type]
    if status:
        result = [o for o in result if o.get("status") == status]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "operations": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/bulk-operations/{operation_id}")
async def get_bulk_operation(operation_id: str):
    """Get bulk operation details"""
    if operation_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    return bulk_operations[operation_id]


@router.post("/bulk-operations/{operation_id}/execute")
async def execute_bulk_operation(operation_id: str):
    """Execute a pending bulk operation (after dry run)"""
    if operation_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    operation = bulk_operations[operation_id]
    
    if operation["status"] != "dry_run_complete":
        raise HTTPException(status_code=400, detail="Operation must be in dry_run_complete status")
    
    import uuid
    now = datetime.utcnow()
    
    # Create execution job
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "job_type": f"bulk_{operation['operation_type']}",
        "name": f"Bulk {operation['operation_type']} on {operation['entity_type']}",
        "priority": "normal",
        "payload": {"operation_id": operation_id},
        "status": JobStatus.QUEUED.value,
        "progress": 0,
        "tenant_id": operation["tenant_id"],
        "created_at": now.isoformat()
    }
    jobs[job_id] = job
    
    operation["job_id"] = job_id
    operation["status"] = "pending"
    operation["dry_run"] = False
    
    logger.info("bulk_operation_executed", operation_id=operation_id, job_id=job_id)
    return operation


@router.post("/bulk-operations/{operation_id}/cancel")
async def cancel_bulk_operation(operation_id: str):
    """Cancel a bulk operation"""
    if operation_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    operation = bulk_operations[operation_id]
    
    if operation["status"] in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel operation with status: {operation['status']}")
    
    operation["status"] = "cancelled"
    operation["cancelled_at"] = datetime.utcnow().isoformat()
    
    # Cancel associated job if exists
    if operation.get("job_id") and operation["job_id"] in jobs:
        jobs[operation["job_id"]]["status"] = JobStatus.CANCELLED.value
    
    logger.info("bulk_operation_cancelled", operation_id=operation_id)
    return operation


@router.put("/config")
async def update_queue_config(
    config: QueueConfig,
    tenant_id: str = Query(default="default")
):
    """Update queue configuration"""
    queue_config[tenant_id] = {
        "max_concurrent_jobs": config.max_concurrent_jobs,
        "default_timeout_seconds": config.default_timeout_seconds,
        "retry_attempts": config.retry_attempts,
        "retry_delay_seconds": config.retry_delay_seconds,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    logger.info("queue_config_updated", tenant_id=tenant_id)
    return queue_config[tenant_id]


@router.get("/config")
async def get_queue_config(tenant_id: str = Query(default="default")):
    """Get queue configuration"""
    return queue_config.get(tenant_id, {
        "max_concurrent_jobs": 10,
        "default_timeout_seconds": 3600,
        "retry_attempts": 3,
        "retry_delay_seconds": 60
    })


@router.get("/stats")
async def get_queue_stats(
    hours: int = Query(default=24, ge=1, le=168),
    tenant_id: str = Query(default="default")
):
    """Get queue statistics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    tenant_jobs = [j for j in jobs.values() if j.get("tenant_id") == tenant_id]
    
    # Filter by time
    recent_jobs = []
    for j in tenant_jobs:
        try:
            created = datetime.fromisoformat(j.get("created_at", "").replace("Z", "+00:00"))
            if created >= cutoff:
                recent_jobs.append(j)
        except (ValueError, TypeError) as e:
            logger.warning("job_date_parse_error", job_id=j.get("id"), error=str(e))
    
    # Count by status
    by_status = {}
    for j in tenant_jobs:
        status = j.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    
    # Count by type
    by_type = {}
    for j in recent_jobs:
        jtype = j.get("job_type", "unknown")
        by_type[jtype] = by_type.get(jtype, 0) + 1
    
    # Calculate averages
    completed = [j for j in recent_jobs if j.get("status") == "completed" and j.get("completed_at") and j.get("started_at")]
    if completed:
        total_duration = 0
        for j in completed:
            try:
                start = datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00"))
                total_duration += (end - start).total_seconds()
            except (ValueError, KeyError, TypeError) as e:
                logger.warning("job_duration_calc_error", job_id=j.get("id"), error=str(e))
        avg_duration = total_duration / len(completed)
    else:
        avg_duration = 0
    
    failed = len([j for j in recent_jobs if j.get("status") == "failed"])
    total = len(recent_jobs)
    
    return {
        "period_hours": hours,
        "total_jobs": len(tenant_jobs),
        "recent_jobs": total,
        "by_status": by_status,
        "by_type": by_type,
        "queued": by_status.get("queued", 0),
        "running": by_status.get("running", 0),
        "completed": by_status.get("completed", 0),
        "failed": failed,
        "failure_rate": round(failed / total * 100, 2) if total > 0 else 0,
        "average_duration_seconds": round(avg_duration, 2)
    }


@router.get("/workers")
async def get_worker_status(tenant_id: str = Query(default="default")):
    """Get worker status information"""
    # Mock worker status
    return {
        "workers": [
            {
                "id": "worker-1",
                "status": "running",
                "current_job": None,
                "jobs_processed": 150,
                "last_heartbeat": datetime.utcnow().isoformat(),
                "uptime_seconds": 86400
            },
            {
                "id": "worker-2",
                "status": "running",
                "current_job": "job-abc123",
                "jobs_processed": 145,
                "last_heartbeat": datetime.utcnow().isoformat(),
                "uptime_seconds": 86400
            }
        ],
        "total_workers": 2,
        "active_workers": 2
    }


@router.post("/purge")
async def purge_completed_jobs(
    older_than_days: int = Query(default=7, ge=1, le=90),
    tenant_id: str = Query(default="default")
):
    """Purge old completed/cancelled jobs"""
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    
    to_delete = []
    for job_id, job in jobs.items():
        if job.get("tenant_id") != tenant_id:
            continue
        if job.get("status") not in ["completed", "cancelled", "failed"]:
            continue
        try:
            created = datetime.fromisoformat(job.get("created_at", "").replace("Z", "+00:00"))
            if created < cutoff:
                to_delete.append(job_id)
        except (ValueError, TypeError) as e:
            logger.warning("job_purge_date_error", job_id=job_id, error=str(e))
    
    for job_id in to_delete:
        del jobs[job_id]
    
    logger.info("jobs_purged", count=len(to_delete), older_than_days=older_than_days)
    return {
        "purged_count": len(to_delete),
        "older_than_days": older_than_days
    }
