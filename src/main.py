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


@app.get("/api/status", tags=["Health"])
async def system_status() -> JSONResponse:
    """System status endpoint with dashboard stats."""
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
            # Dashboard stats (mocked for now - will connect to DB later)
            "pending_drafts": 0,
            "approved_today": 0,
            "sent_today": 0,
            "workflows_today": 0,
        }
    )


@app.get("/api/drafts", tags=["Dashboard"])
async def get_drafts() -> JSONResponse:
    """Get pending drafts for dashboard."""
    # TODO: Connect to database when ready
    # For now return empty list
    return JSONResponse({"drafts": [], "total": 0})


@app.get("/api/workflows", tags=["Dashboard"])
async def get_workflows() -> JSONResponse:
    """Get recent workflow runs for dashboard."""
    # TODO: Connect to database when ready
    # For now return empty list
    return JSONResponse({"workflows": [], "total": 0})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
