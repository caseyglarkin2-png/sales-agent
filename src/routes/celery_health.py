"""Celery and Background Task Health Check Endpoints.

Task 8.18: Celery Beat Health Check
- Shows last-run timestamps for scheduled tasks
- Indicates if tasks are running on schedule
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import redis

from fastapi import APIRouter, Response, status

from src.config import get_settings
from src.logger import get_logger
from src.celery_app import celery_app

router = APIRouter(prefix="/api/health", tags=["Health", "Celery"])
logger = get_logger(__name__)

settings = get_settings()

# In-memory storage for task heartbeats (updated when tasks run)
# This is a simple approach; production might use Redis for persistence
_task_heartbeats: Dict[str, datetime] = {}


def update_task_heartbeat(task_name: str):
    """Update the last-run timestamp for a task."""
    _task_heartbeats[task_name] = datetime.utcnow()


def get_task_heartbeat(task_name: str) -> Optional[datetime]:
    """Get the last-run timestamp for a task."""
    return _task_heartbeats.get(task_name)


@dataclass
class ScheduledTask:
    """Scheduled task info from Celery Beat."""
    name: str
    schedule_seconds: float
    last_run: Optional[datetime]
    is_overdue: bool
    overdue_by_seconds: Optional[float]


def get_scheduled_tasks() -> List[ScheduledTask]:
    """Get list of scheduled tasks with their status."""
    tasks = []
    
    beat_schedule = celery_app.conf.beat_schedule or {}
    
    for task_key, task_config in beat_schedule.items():
        task_name = task_config.get("task", task_key)
        schedule = task_config.get("schedule", 0)
        
        # Handle different schedule types
        if isinstance(schedule, (int, float)):
            schedule_seconds = float(schedule)
        else:
            # For crontab or other schedule types, estimate
            schedule_seconds = 3600  # Default to 1 hour
        
        last_run = get_task_heartbeat(task_name)
        
        # Calculate if overdue (2x the schedule interval)
        is_overdue = False
        overdue_by = None
        if last_run:
            expected_next = last_run + timedelta(seconds=schedule_seconds)
            grace_period = timedelta(seconds=schedule_seconds * 2)  # 2x tolerance
            if datetime.utcnow() > last_run + grace_period:
                is_overdue = True
                overdue_by = (datetime.utcnow() - expected_next).total_seconds()
        else:
            # Never run - could be overdue if service has been up long enough
            pass  # Don't mark as overdue if we don't know
        
        tasks.append(ScheduledTask(
            name=task_name,
            schedule_seconds=schedule_seconds,
            last_run=last_run,
            is_overdue=is_overdue,
            overdue_by_seconds=overdue_by,
        ))
    
    return tasks


@router.get("/beat")
async def celery_beat_health(response: Response) -> Dict[str, Any]:
    """
    Celery Beat health check endpoint.
    
    Shows:
    - Status of each scheduled task
    - Last run timestamps
    - Whether tasks are running on schedule
    
    Returns:
        Health status with task details
    """
    tasks = get_scheduled_tasks()
    
    # Check if any tasks are overdue
    overdue_tasks = [t for t in tasks if t.is_overdue]
    all_healthy = len(overdue_tasks) == 0
    
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "overdue_count": len(overdue_tasks),
        "tasks": [
            {
                "name": t.name,
                "schedule_seconds": t.schedule_seconds,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "is_overdue": t.is_overdue,
                "overdue_by_seconds": t.overdue_by_seconds,
            }
            for t in tasks
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/workers")
async def celery_workers_health(response: Response) -> Dict[str, Any]:
    """
    Check Celery worker availability.
    
    Pings active workers to verify they're running.
    """
    try:
        # Inspect active workers
        inspect = celery_app.control.inspect()
        
        # Get ping response (with short timeout)
        ping_result = inspect.ping()
        
        if not ping_result:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "no_workers",
                "workers": [],
                "message": "No Celery workers are responding",
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        workers = list(ping_result.keys())
        
        return {
            "status": "healthy",
            "worker_count": len(workers),
            "workers": workers,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error checking Celery workers: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/queues")
async def celery_queues_status() -> Dict[str, Any]:
    """
    Get Celery queue statistics from Redis.
    
    Shows queue lengths and message counts.
    """
    try:
        r = redis.from_url(settings.redis_url)
        
        # Check the default celery queue
        queue_length = r.llen("celery")
        
        return {
            "status": "ok",
            "queues": {
                "celery": {
                    "length": queue_length,
                }
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error checking Celery queues: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/summary")
async def background_tasks_summary(response: Response) -> Dict[str, Any]:
    """
    Combined health summary for all background task systems.
    
    Aggregates beat, workers, and queues status.
    """
    issues = []
    
    # Check beat schedule
    tasks = get_scheduled_tasks()
    overdue_tasks = [t for t in tasks if t.is_overdue]
    if overdue_tasks:
        issues.append(f"{len(overdue_tasks)} scheduled tasks overdue")
    
    # Check workers (quick ping)
    try:
        inspect = celery_app.control.inspect()
        ping_result = inspect.ping()
        worker_count = len(ping_result) if ping_result else 0
        if worker_count == 0:
            issues.append("No Celery workers responding")
    except Exception:
        worker_count = 0
        issues.append("Failed to check worker status")
    
    # Check queues
    try:
        r = redis.from_url(settings.redis_url)
        queue_length = r.llen("celery")
        if queue_length > 100:
            issues.append(f"Queue backlog: {queue_length} messages")
    except Exception:
        queue_length = -1
        issues.append("Failed to check queue status")
    
    all_healthy = len(issues) == 0
    
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "scheduled_tasks": len(tasks),
        "overdue_tasks": len(overdue_tasks),
        "active_workers": worker_count,
        "queue_length": queue_length,
        "issues": issues,
        "timestamp": datetime.utcnow().isoformat(),
    }
