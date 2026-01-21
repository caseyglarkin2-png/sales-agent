"""FastAPI application entry point."""
import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.logger import configure_logging, get_logger
from src.middleware import TraceIDMiddleware
from src.routes import agents as agents_routes
from src.routes import operator as operator_routes
from src.routes import webhooks as webhooks_routes
from src.routes import voice as voice_routes
from src.routes import metrics as metrics_routes
from src.routes import bulk as bulk_routes
from src.routes import enrichment as enrichment_routes
from src.routes import proposals as proposals_routes
from src.routes import sequences as sequences_routes
from src.routes import docs as docs_routes
from src.routes import accounts as accounts_routes
from src.routes import history as history_routes

# Configure logging
settings = get_settings()
configure_logging(log_level=settings.log_level, log_format=settings.log_format)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Sales Agent",
    description="Operator-mode prospecting and nurturing agent",
    version="0.1.0",
)

# Add middleware
app.add_middleware(TraceIDMiddleware)

# Include routers
app.include_router(agents_routes.router)
app.include_router(operator_routes.router)
app.include_router(webhooks_routes.router)
app.include_router(voice_routes.router)
app.include_router(metrics_routes.router)
app.include_router(bulk_routes.router)
app.include_router(enrichment_routes.router)
app.include_router(proposals_routes.router)
app.include_router(sequences_routes.router)
app.include_router(docs_routes.router)
app.include_router(accounts_routes.router)
app.include_router(history_routes.router)

# Mount static files for dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup."""
    logger.info("Sales Agent starting up", env=settings.api_env)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown."""
    logger.info("Sales Agent shutting down")


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@app.get("/", tags=["Root"])
async def root() -> FileResponse:
    """Serve operator dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse(
        {
            "service": "sales-agent",
            "version": "0.1.0",
            "status": "running",
            "environment": settings.api_env,
            "dashboard": "/static/index.html",
            "docs": "/docs",
        }
    )


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard():
    """Operator dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse({"error": "Dashboard not found"}, status_code=404)


@app.get("/voice-profiles", tags=["Dashboard"])
async def voice_profiles_page():
    """Voice profiles management page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "voice-profiles.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/agents", tags=["Dashboard"])
async def agents_page():
    """Agents visibility page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "agents.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/admin", tags=["Dashboard"])
async def admin_page():
    """Admin panel page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/api/status", tags=["Health"])
async def system_status() -> JSONResponse:
    """System status endpoint with dashboard stats."""
    # Get actual stats from database
    pending_count = 0
    workflows_today = 0
    try:
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        pending = await queue.get_pending_approvals()
        pending_count = len(pending)
        
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        stats = await db.get_workflow_stats()
        workflows_today = stats.get("today", {}).get("total", 0)
    except Exception as e:
        logger.warning(f"Could not fetch dashboard stats: {e}")
    
    return JSONResponse(
        {
            "status": "operational",
            "operator_mode": settings.operator_mode_enabled,
            "approval_required": settings.operator_approval_required,
            "mode": "DRAFT_ONLY" if settings.mode_draft_only else "SEND_ALLOWED",
            "rate_limits": {
                "max_emails_per_day": settings.max_emails_per_day,
                "max_emails_per_week": settings.max_emails_per_week,
            },
            "pending_drafts": pending_count,
            "approved_today": 0,
            "sent_today": 0,
            "workflows_today": workflows_today,
        }
    )


@app.get("/api/drafts", tags=["Dashboard"])
async def get_drafts() -> JSONResponse:
    """Get pending drafts for dashboard."""
    try:
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        pending = await queue.get_pending_approvals()
        return JSONResponse({"drafts": pending, "total": len(pending)})
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return JSONResponse({"drafts": [], "total": 0, "error": str(e)})


@app.get("/api/workflows", tags=["Dashboard"])
async def get_workflows() -> JSONResponse:
    """Get recent workflow runs for dashboard."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        recent = await db.get_recent_workflows(limit=50)
        # Convert datetime objects to strings
        for w in recent:
            for k, v in w.items():
                if hasattr(v, 'isoformat'):
                    w[k] = v.isoformat()
        return JSONResponse({"workflows": recent, "total": len(recent)})
    except Exception as e:
        logger.error(f"Error fetching workflows: {e}")
        return JSONResponse({"workflows": [], "total": 0, "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
