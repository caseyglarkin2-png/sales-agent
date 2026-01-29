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
        from src.db import get_session
        async with get_session() as session:
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


@router.get("/health/connectors")
async def connector_health_check() -> Dict[str, Any]:
    """
    Check health of all external API connectors.
    
    Calls health_check() on each connector and returns aggregated status.
    Used for debugging integration issues and monitoring.
    
    Sprint 68: Enhanced with real health checks from connectors.
    """
    import asyncio
    from datetime import datetime
    
    settings = get_settings()
    connectors = {}
    
    # Collect all health check tasks
    async def check_gmail():
        try:
            from src.connectors.gmail import GmailConnector
            connector = GmailConnector()
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_hubspot():
        try:
            from src.connectors.hubspot import HubSpotConnector
            connector = HubSpotConnector(api_key=settings.hubspot_api_key)
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_sendgrid():
        try:
            from src.connectors.sendgrid import SendGridConnector
            connector = SendGridConnector()
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_slack():
        try:
            from src.connectors.slack import SlackConnector
            connector = SlackConnector()
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_calendar():
        try:
            from src.connectors.calendar_connector import create_calendar_connector
            connector = create_calendar_connector()
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_drive():
        try:
            from src.connectors.drive import create_drive_connector
            connector = create_drive_connector()
            return await connector.health_check()
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    async def check_llm():
        try:
            from src.connectors.llm import get_llm
            connector = get_llm()
            if hasattr(connector, 'health_check'):
                return await connector.health_check()
            # Fallback: just check if configured
            if settings.openai_api_key:
                return {"status": "configured", "latency_ms": 0, "error": None}
            return {"status": "unhealthy", "latency_ms": 0, "error": "No API key configured"}
        except Exception as e:
            return {"status": "error", "latency_ms": 0, "error": str(e)}
    
    # Run all health checks in parallel
    results = await asyncio.gather(
        check_gmail(),
        check_hubspot(),
        check_sendgrid(),
        check_slack(),
        check_calendar(),
        check_drive(),
        check_llm(),
        return_exceptions=True,
    )
    
    connector_names = ["gmail", "hubspot", "sendgrid", "slack", "calendar", "drive", "llm"]
    
    for name, result in zip(connector_names, results):
        if isinstance(result, Exception):
            connectors[name] = {"status": "error", "latency_ms": 0, "error": str(result)}
        else:
            connectors[name] = result
    
    # Add circuit breaker status for gmail and hubspot
    try:
        from src.connectors.gmail import GmailConnector
        connectors["gmail"]["circuit_breaker"] = GmailConnector.get_circuit_breaker_state()
    except Exception:
        pass
    
    try:
        from src.connectors.hubspot import HubSpotConnector
        connectors["hubspot"]["circuit_breaker"] = HubSpotConnector.get_circuit_breaker_state()
    except Exception:
        pass
    
    # Calculate overall status
    healthy_count = sum(1 for c in connectors.values() if c.get("status") in ["healthy", "configured"])
    degraded_count = sum(1 for c in connectors.values() if c.get("status") == "degraded")
    total_count = len(connectors)
    
    # Check if any circuit breaker is open - that's degraded
    circuit_breakers_open = sum(
        1 for c in connectors.values()
        if c.get("circuit_breaker", {}).get("state") == "open"
    )
    
    if healthy_count == total_count and circuit_breakers_open == 0:
        overall_status = "healthy"
    elif healthy_count + degraded_count >= total_count * 0.5:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "summary": f"{healthy_count}/{total_count} connectors healthy, {circuit_breakers_open} circuit breakers open",
        "connectors": connectors,
        "timestamp": datetime.utcnow().isoformat(),
    }
