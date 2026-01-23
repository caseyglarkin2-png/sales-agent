"""Health Check Endpoints for Kubernetes/Load Balancers."""

from fastapi import APIRouter, Response, status
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import text

from src.config import get_settings
from src.logger import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns 200 OK if service is running.
    Used by load balancers for basic liveness check.
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/healthz")
async def kubernetes_health() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the application process is running.
    Kubernetes will restart the pod if this fails.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if service is ready to accept traffic.
    Checks dependencies (database, redis, etc.).
    """
    checks = {}
    all_ready = True
    
    # Check database connection (truthful readiness)
    try:
        from src.db import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not_ready: {str(e)}"
        all_ready = False
    
    # Check Redis connection
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ready"
    except Exception as e:
        checks["redis"] = f"not_ready: {str(e)}"
        all_ready = False
    
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/startup")
async def startup_check() -> Dict[str, str]:
    """
    Kubernetes startup probe endpoint.
    
    Returns 200 when application has fully started.
    Used for slow-starting applications.
    """
    # Add any slow initialization checks here
    return {"status": "started"}
