"""
CaseyOS UI Routes.

Serves the unified CaseyOS dashboard and static assets.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["caseyos-ui"])

# Path to static assets
STATIC_DIR = Path(__file__).parent.parent / "static" / "caseyos"


@router.get("/caseyos", response_class=HTMLResponse)
async def caseyos_dashboard():
    """
    Serve the CaseyOS unified dashboard.
    
    This is the main entry point for the GTM command center UI.
    """
    index_path = STATIC_DIR / "index.html"
    
    if not index_path.exists():
        logger.error(f"CaseyOS index.html not found at {index_path}")
        return HTMLResponse(
            content="<h1>CaseyOS Dashboard</h1><p>Dashboard assets not found. Run build first.</p>",
            status_code=404
        )
    
    return FileResponse(
        index_path,
        media_type="text/html",
        headers={
            "X-API-Version": "v1",
            "X-CaseyOS-Version": "1.0.0",
        }
    )


@router.get("/caseyos/styles.css")
async def caseyos_styles():
    """Serve CaseyOS stylesheet."""
    css_path = STATIC_DIR / "styles.css"
    
    if not css_path.exists():
        return HTMLResponse(content="/* Not found */", status_code=404)
    
    return FileResponse(css_path, media_type="text/css")


@router.get("/caseyos/app.js")
async def caseyos_js():
    """Serve CaseyOS JavaScript."""
    js_path = STATIC_DIR / "app.js"
    
    if not js_path.exists():
        return HTMLResponse(content="// Not found", status_code=404)
    
    return FileResponse(js_path, media_type="application/javascript")


@router.get("/caseyos/health")
async def caseyos_health():
    """
    CaseyOS-specific health check.
    
    Used by the dashboard to check API availability.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "features": {
            "command_queue": True,
            "signals": True,
            "outcomes": True,
            "actions": True,
            "marketing_ops": True,
            "customer_success": True,
        }
    }
