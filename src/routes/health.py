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
    
    Validates that API keys are present and connectors can authenticate.
    Used for debugging integration issues.
    """
    settings = get_settings()
    connectors = {}
    
    # Check OpenAI
    try:
        if settings.openai_api_key:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    connectors["openai"] = {"status": "connected", "message": "API key valid"}
                else:
                    connectors["openai"] = {"status": "error", "message": f"HTTP {resp.status_code}"}
        else:
            connectors["openai"] = {"status": "not_configured", "message": "OPENAI_API_KEY not set"}
    except Exception as e:
        connectors["openai"] = {"status": "error", "message": str(e)}
    
    # Check HubSpot
    try:
        if settings.hubspot_api_key:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                    headers={"Authorization": f"Bearer {settings.hubspot_api_key}"},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    connectors["hubspot"] = {"status": "connected", "message": "API key valid"}
                elif resp.status_code == 401:
                    connectors["hubspot"] = {"status": "auth_required", "message": "Needs OAuth - legacy key format"}
                else:
                    connectors["hubspot"] = {"status": "error", "message": f"HTTP {resp.status_code}"}
        else:
            connectors["hubspot"] = {"status": "not_configured", "message": "HUBSPOT_API_KEY not set"}
    except Exception as e:
        connectors["hubspot"] = {"status": "error", "message": str(e)}
    
    # Check Google (Service Account)
    try:
        import os
        google_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON") or settings.google_client_id
        if google_creds:
            connectors["google"] = {"status": "configured", "message": "Credentials present (needs OAuth flow for user access)"}
        else:
            connectors["google"] = {"status": "not_configured", "message": "GOOGLE_CREDENTIALS_JSON not set"}
    except Exception as e:
        connectors["google"] = {"status": "error", "message": str(e)}
    
    # Check Slack
    try:
        if settings.slack_bot_token:
            connectors["slack"] = {"status": "configured", "message": "Bot token present"}
        else:
            connectors["slack"] = {"status": "not_configured", "message": "SLACK_BOT_TOKEN not set"}
    except Exception as e:
        connectors["slack"] = {"status": "error", "message": str(e)}
    
    # Check Gemini (failover LLM)
    try:
        if settings.gemini_api_key:
            connectors["gemini"] = {"status": "configured", "message": "API key present (failover LLM)"}
        else:
            connectors["gemini"] = {"status": "not_configured", "message": "GEMINI_API_KEY not set (optional)"}
    except Exception as e:
        connectors["gemini"] = {"status": "error", "message": str(e)}
    
    # Overall status
    connected_count = sum(1 for c in connectors.values() if c["status"] in ["connected", "configured"])
    total_count = len(connectors)
    
    return {
        "status": "ok" if connected_count >= 2 else "degraded",
        "summary": f"{connected_count}/{total_count} connectors ready",
        "connectors": connectors,
        "timestamp": datetime.utcnow().isoformat(),
    }
